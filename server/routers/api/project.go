// ...existing code...
package api

import (
	"database/sql"
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"time"

	//"StoryToVideo-server/config"
	"StoryToVideo-server/models"

	"StoryToVideo-server/service"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
) //119.45.124.222 //localhost

// 创建项目
func CreateProject(c *gin.Context) {
	var req struct {
		Title     string `form:"Title" json:"title"`
		StoryText string `form:"StoryText" json:"story_text"`
		Style     string `form:"Style" json:"style"`
		ShotCount int    `form:"ShotCount" json:"shot_count"`
	}
	if err := c.ShouldBindQuery(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 默认分镜数量
	if req.ShotCount <= 0 {
		req.ShotCount = 5
	}

	project := models.Project{
		ID:          uuid.NewString(),
		Title:       req.Title,
		StoryText:   req.StoryText,
		Style:       req.Style,
		Status:      "created",
		CoverImage:  "",
		Duration:    0,
		VideoUrl:    "",
		Description: "",
		ShotCount:   req.ShotCount,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	// 1) 插入 project 到 DB
	if err := models.CreateProject(&project); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建项目失败: " + err.Error()})
		return
	}

	// 2) 创建项目文本生成任务（project_text）
	textTask := models.Task{
		ID:        uuid.NewString(),
		ProjectId: project.ID,
		ShotId:    "",
		Type:      models.TaskTypeStoryboard,
		Status:    models.TaskStatusPending,
		Progress:  0,
		Message:   "项目创建任务已创建,正在生成分镜脚本...",
		Parameters: models.TaskParameters{
			ShotDefaults: &models.ShotDefaultsParams{
				ShotCount: req.ShotCount,
				Style:     req.Style,
				StoryText: req.StoryText,
			},
			Shot:  &models.ShotParams{},
			Video: &models.VideoParams{},
			TTS:   &models.TTSParams{},
		},
		Result:            models.TaskResult{},
		Error:             "",
		EstimatedDuration: 0,
		StartedAt:         time.Time{},
		FinishedAt:        time.Time{},
		CreatedAt:         time.Now(),
		UpdatedAt:         time.Now(),
	}

	if err := models.CreateTask(&textTask); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建文本任务失败: " + err.Error()})
		return
	}
	// 将文本任务入队执行
	if err := service.EnqueueTask(textTask.ID); err != nil {
		log.Printf("文本任务入队失败: %v", err)
	}

	// 3) 创建 n 个分镜图片生成任务，状态为 blocked，并设置依赖为 textTask.ID
	var shotTaskIDs []string
	for i := 0; i < req.ShotCount; i++ {
		shotTask := models.Task{
			ID:        uuid.NewString(),
			ProjectId: project.ID,
			Type:      models.TaskTypeShotImage,
			Status:    models.TaskStatusBlocked,
			Progress:  0,
			Message:   "等待文本任务完成以生成分镜图片",
			Parameters: models.TaskParameters{
				Shot: &models.ShotParams{
					Prompt:      "",
					Transition:  "",
					ImageWidth:  "1024",
					ImageHeight: "1024",
				},
				DependsOn: []string{textTask.ID},
			},
			Result:            models.TaskResult{},
			Error:             "",
			EstimatedDuration: 0,
			CreatedAt:         time.Now(),
			UpdatedAt:         time.Now(),
		}
		if err := models.CreateTask(&shotTask); err != nil {
			log.Printf("创建分镜任务失败: %v", err)
			continue
		}
		shotTaskIDs = append(shotTaskIDs, shotTask.ID)
		// 不入队，等待依赖解锁 (文本任务完成后由 watcher 或处理器解锁并入队)
	}

	c.JSON(http.StatusOK, gin.H{
		"project_id":    project.ID,
		"text_task_id":  textTask.ID,
		"shot_task_ids": shotTaskIDs,
	})
}

// 获取项目详情
func GetProject(c *gin.Context) {
	projectID := c.Param("project_id")

	// 从数据库获取项目
	project, err := models.GetProjectByID(projectID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "项目未找到: " + err.Error()})
		return
	}

	// 获取分镜列表
	shots, err := models.GetShotsByProjectID(projectID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取分镜失败: " + err.Error()})
		return
	}

	// 获取最近任务（如果有）
	var recentTask *models.Task
	row := models.DB.QueryRow(`SELECT id, project_id, shot_id, type, status, progress, message, parameters, result, error, estimated_duration, started_at, finished_at, created_at, updated_at FROM task WHERE project_id = ? ORDER BY created_at DESC LIMIT 1`, projectID)
	var t models.Task
	var paramsBytes, resultBytes []byte
	var startedAt, finishedAt, createdAt, updatedAt sql.NullTime
	var shotIDNull sql.NullString
	var messageNull sql.NullString
	var errorNull sql.NullString

	if err := row.Scan(&t.ID, &t.ProjectId, &shotIDNull, &t.Type, &t.Status, &t.Progress, &messageNull, &paramsBytes, &resultBytes, &errorNull, &t.EstimatedDuration, &startedAt, &finishedAt, &createdAt, &updatedAt); err != nil {
		if err != sql.ErrNoRows {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "查询最近任务失败: " + err.Error()})
			return
		}
		// 没有任务，recentTask 保持 nil
	} else {
		if messageNull.Valid {
			t.Message = messageNull.String
		} else {
			t.Message = ""
		}
		if errorNull.Valid {
			t.Error = errorNull.String
		} else {
			t.Error = ""
		}
		// 反序列化 parameters/result
		_ = json.Unmarshal(paramsBytes, &t.Parameters)
		_ = json.Unmarshal(resultBytes, &t.Result)
		if startedAt.Valid {
			t.StartedAt = startedAt.Time
		}
		if finishedAt.Valid {
			t.FinishedAt = finishedAt.Time
		}
		if createdAt.Valid {
			t.CreatedAt = createdAt.Time
		}
		if updatedAt.Valid {
			t.UpdatedAt = updatedAt.Time
		}
		recentTask = &t
	}

	c.JSON(http.StatusOK, gin.H{
		"project_detail": project,
		"shots":          shots,
		"recent_task":    recentTask,
	})
}

// 更新项目信息
func UpdateProject(c *gin.Context) {
	projectID := c.Param("project_id")
	var req struct {
		Title       string `form:"Title" json:"title"`
		Description string `form:"Description" json:"description"`
		StoryText   string `form:"StoryText" json:"story_text"`
		ShotCount   int    `form:"ShotCount" json:"shot_count"`
	}
	if err := c.ShouldBindQuery(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 1) 更新 title/description（保持原有函数）
	if err := models.UpdateProjectByID(projectID, req.Title, req.Description); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新项目失败: " + err.Error()})
		return
	}

	// 2) 可选更新 story_text / shot_count（仅在请求提供时更新）
	sets := []string{}
	args := []interface{}{}
	if req.StoryText != "" {
		sets = append(sets, "story_text = ?")
		args = append(args, req.StoryText)
	}
	if req.ShotCount > 0 {
		sets = append(sets, "shot_count = ?")
		args = append(args, req.ShotCount)
	}
	if len(sets) > 0 {
		query := "UPDATE project SET " + strings.Join(sets, ", ") + ", updated_at = ? WHERE id = ?"
		args = append(args, time.Now(), projectID)
		if _, err := models.DB.Exec(query, args...); err != nil {
			log.Printf("额外更新 project 字段失败: %v", err)
			// 不阻塞主流程，记录日志即可
		}
	}
	// 3) 先取消正在 processing 的任务（尝试向 Worker 发起取消），再删除 pending/blocked
	rows, err := models.DB.Query(`SELECT id, result FROM task WHERE project_id = ? AND status = ?`, projectID, models.TaskStatusProcessing)
	if err != nil {
		log.Printf("查询 processing 任务失败: %v", err)
	} else {
		defer rows.Close()
		for rows.Next() {
			var tid string
			var resBytes []byte
			if err := rows.Scan(&tid, &resBytes); err != nil {
				continue
			}
			// 1) 解析 result 中的 job_id（如果有），并尝试通知 worker 删除
			var tr models.TaskResult
			if len(resBytes) > 0 {
				_ = json.Unmarshal(resBytes, &tr)
			}
			if tr.ResourceId != "" {
				if err := service.CancelWorkerJob(tr.ResourceId); err != nil {
					log.Printf("通知 worker 删除 job %s 失败: %v", tr.ResourceId, err)
				} else {
					log.Printf("已通知 worker 删除 job %s", tr.ResourceId)
				}
			}

			// 2) 取消本地轮询（如果存在）
			if cancelled := service.CancelPollTask(tid); cancelled {
				log.Printf("Cancelled poll for task %s", tid)
			}
			// 3) 标记为 cancelled（入库）
			msg := "cancelled due to project update"
			if err := models.UpdateTaskStatus(tid, models.TaskStatusCancelled, nil, &msg, nil, nil, nil, nil); err != nil {
				log.Printf("标记任务取消失败 %s: %v", tid, err)
			} else {
				log.Printf("任务 %s 标记为 cancelled", tid)
			}
		}
	}
	// 3) 删除旧的未开始任务（pending / blocked），避免重复
	res, err := models.DB.Exec(`DELETE FROM task WHERE project_id = ? AND status IN (?, ?)`, projectID, models.TaskStatusPending, models.TaskStatusBlocked)
	deletedCount := int64(0)
	if err != nil {
		log.Printf("删除旧任务失败: %v", err)
	} else {
		if n, _ := res.RowsAffected(); n >= 0 {
			deletedCount = n
		}
	}
	log.Printf("Deleted %d pending/blocked tasks for project %s", deletedCount, projectID)

	// 4) 重新创建文本任务 + blocked 的分镜任务（和 CreateProject 一致）
	// 读取当前 project，用于 story_text / shot_count
	project, err := models.GetProjectByID(projectID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取项目失败: " + err.Error()})
		return
	}

	// 若请求中提供新的 StoryText 或 ShotCount，优先使用请求值
	if req.StoryText != "" {
		project.StoryText = req.StoryText
	}
	shotCount := project.ShotCount
	if req.ShotCount > 0 {
		shotCount = req.ShotCount
	}

	textTask := models.Task{
		ID:        uuid.NewString(),
		ProjectId: project.ID,
		ShotId:    "",
		Type:      models.TaskTypeStoryboard,
		Status:    models.TaskStatusPending,
		Progress:  0,
		Message:   "项目文本生成任务已创建, 正在生成分镜脚本...",
		Parameters: models.TaskParameters{
			ShotDefaults: &models.ShotDefaultsParams{
				ShotCount: shotCount,
				Style:     project.Style,
				StoryText: project.StoryText,
			},
			Shot:  &models.ShotParams{},
			Video: &models.VideoParams{},
			TTS:   &models.TTSParams{},
		},
		Result:            models.TaskResult{},
		Error:             "",
		EstimatedDuration: 0,
		CreatedAt:         time.Now(),
		UpdatedAt:         time.Now(),
	}

	if err := models.CreateTask(&textTask); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建文本任务失败: " + err.Error()})
		return
	}
	if err := service.EnqueueTask(textTask.ID); err != nil {
		log.Printf("文本任务入队失败: %v", err)
	}

	// 创建依赖的分镜任务（blocked）
	var shotTaskIDs []string
	for i := 0; i < shotCount; i++ {
		shotTask := models.Task{
			ID:        uuid.NewString(),
			ProjectId: project.ID,
			Type:      models.TaskTypeShotImage,
			Status:    models.TaskStatusBlocked,
			Progress:  0,
			Message:   "等待文本任务完成以生成分镜图片",
			Parameters: models.TaskParameters{
				Shot: &models.ShotParams{
					Prompt:      "",
					Transition:  "",
					ImageWidth:  "1024",
					ImageHeight: "1024",
				},
				DependsOn: []string{textTask.ID},
			},
			Result:            models.TaskResult{},
			Error:             "",
			EstimatedDuration: 0,
			CreatedAt:         time.Now(),
			UpdatedAt:         time.Now(),
		}
		if err := models.CreateTask(&shotTask); err != nil {
			log.Printf("创建分镜任务失败: %v", err)
			continue
		}
		shotTaskIDs = append(shotTaskIDs, shotTask.ID)
	}

	updatedProject, err := models.GetProjectByID(projectID)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"id":         projectID,
			"updateAT":   time.Now(),
			"deleted":    deletedCount,
			"text_task":  textTask.ID,
			"shot_tasks": shotTaskIDs,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"project":    updatedProject,
		"updateAT":   updatedProject.UpdatedAt,
		"deleted":    deletedCount,
		"text_task":  textTask.ID,
		"shot_tasks": shotTaskIDs,
	})
}

// 删除项目
func DeleteProject(c *gin.Context) {
	projectID := c.Param("project_id")

	// 在删除前取消正在 processing 的任务并标记 cancelled
	rows, err := models.DB.Query(`SELECT id, result FROM task WHERE project_id = ? AND status = ?`, projectID, models.TaskStatusProcessing)
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var tid string
			var resBytes []byte
			if err := rows.Scan(&tid, &resBytes); err != nil {
				continue
			}

			// 解析 job_id 并通知 worker 删除
			var tr models.TaskResult
			if len(resBytes) > 0 {
				_ = json.Unmarshal(resBytes, &tr)
			}
			if tr.ResourceId != "" {
				if err := service.CancelWorkerJob(tr.ResourceId); err != nil {
					log.Printf("通知 worker 删除 job %s 失败: %v", tr.ResourceId, err)
				} else {
					log.Printf("已通知 worker 删除 job %s", tr.ResourceId)
				}
			}

			if service.CancelPollTask(tid) {
				log.Printf("Cancelled poll for task %s before project delete", tid)
			}
			msg := "cancelled due to project delete"
			_ = models.UpdateTaskStatus(tid, models.TaskStatusCancelled, nil, &msg, nil, nil, nil, nil)
		}
	}

	// 数据库删除项目（级联会删除相关分镜和任务）
	if err := models.DeleteProjectByID(projectID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除项目失败: " + err.Error()})
		return
	}

	deleteAt := time.Now()

	c.JSON(http.StatusOK, gin.H{
		"success":  true,
		"deleteAt": deleteAt,
		"message":  "项目已删除",
	})
}

// ...existing code...
