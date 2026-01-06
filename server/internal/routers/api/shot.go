// ...existing code...
package api

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"StoryToVideo-server/internal/models"
	"StoryToVideo-server/internal/service"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// 获取分镜列表
func GetShots(c *gin.Context) {
	projectID := c.Param("project_id")

	shots, err := models.GetShotsByProjectID(projectID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取分镜失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"shots":       shots,
		"project_id":  projectID,
		"total_shots": len(shots),
	})
}

// 更新分镜并可触发重生任务（改为使用新 TaskType）
func UpdateShot(c *gin.Context) {
	projectID := c.Param("project_id")
	shotID := c.Param("shot_id")

	var req struct {
		Title      string `form:"title" json:"title"`
		Prompt     string `form:"prompt" json:"prompt"`
		Transition string `form:"transition" json:"transition"`
		Style      string `form:"style" json:"style"`
	}
	body, err := c.GetRawData()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if len(body) > 0 {
		if err := json.Unmarshal(body, &req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
	} else {
		if err := c.ShouldBindQuery(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
	}

	// 确保分镜存在
	if _, err := models.GetShotByID(projectID, shotID); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "分镜未找到: " + err.Error()})
		return
	}

	// 在更新分镜前，取消与该 shot 相关的正在 processing 的 task（如果有）
	rows, err := models.DB.Query(`SELECT id, result FROM task WHERE shot_id = ? AND status = ?`, shotID, models.TaskStatusProcessing)
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var tid string
			var resBytes []byte
			if err := rows.Scan(&tid, &resBytes); err != nil {
				continue
			}
			// 尝试解析 job_id 并通知 worker 删除
			var tr models.TaskResult
			if len(resBytes) > 0 {
				_ = json.Unmarshal(resBytes, &tr)
			}
			if tr.ResourceId != "" {
				if err := service.CancelWorkerJob(tr.ResourceId); err != nil {
					log.Printf("通知 worker 删除 job %s 失败: %v", tr.ResourceId, err)
				} else {
					log.Printf("已通知 worker 删除 job %s (shot update)", tr.ResourceId)
				}
			}

			if service.CancelPollTask(tid) {
				log.Printf("Cancelled poll for task %s (shot update)", tid)
			}
			msg := "cancelled due to shot update"
			_ = models.UpdateTaskStatus(tid, models.TaskStatusCancelled, nil, &msg, nil, nil, nil, nil)
		}
	}

	// 更新分镜数据库字段（只更新非空参数）
	if err := models.UpdateShotByID(projectID, shotID, req.Title, req.Prompt, req.Transition); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "更新分镜失败: " + err.Error()})
		return
	}
	style := req.Style
	if style == "" {
		if project, err := models.GetProjectByID(projectID); err == nil {
			style = project.Style
		}
	}

	// 创建重新生成分镜的任务（使用 models.TaskTypeShotImage）
	// Prompt 优先使用请求中的值，否则使用数据库中已有值（调用方已确保存在）
	prompt := req.Prompt

	task := models.Task{
		ID:        uuid.NewString(),
		ProjectId: projectID,
		Type:      models.TaskTypeShotImage,
		Status:    models.TaskStatusPending,
		Progress:  0,
		Message:   "分镜更新并已创建生成任务",
		Parameters: models.TaskParameters{
			Shot: &models.ShotParams{
				ShotId:      shotID,
				Style:       style,
				Prompt:      prompt,
				ImageLLM:    "",
				GenerateTTS: false,
				ImageWidth:  "1024",
				ImageHeight: "1024",
			},
			Video: &models.VideoParams{},
		},
		Result:            models.TaskResult{},
		Error:             "",
		EstimatedDuration: 0,
		StartedAt:         time.Time{},
		FinishedAt:        time.Time{},
		CreatedAt:         time.Now(),
		UpdatedAt:         time.Now(),
	}

	if err := models.CreateTask(&task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建任务失败: " + err.Error()})
		return
	}

	if err := service.EnqueueTask(task.ID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "任务入队失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"shot_id": shotID,
		"task_id": task.ID,
		"message": "分镜已更新并创建生成任务",
	})
}

// 获取分镜详情
func GetShotDetail(c *gin.Context) {
	projectID := c.Param("project_id")
	shotID := c.Param("shot_id")

	shot, err := models.GetShotByID(projectID, shotID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "分镜未找到: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"shot": shot,
	})
}

// 删除分镜
func DeleteShot(c *gin.Context) {
	projectID := c.Param("project_id")
	shotID := c.Param("shot_id")

	// 如果路由未提供 project_id，则尝试按 shot_id 删除（直接执行 SQL）
	if projectID == "" {
		// 在删除前尝试取消 processing 的相关任务
		rows, err := models.DB.Query(`SELECT id, result FROM task WHERE shot_id = ? AND status = ?`, shotID, models.TaskStatusProcessing)
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var tid string
				var resBytes []byte
				if err := rows.Scan(&tid, &resBytes); err != nil {
					continue
				}
				var tr models.TaskResult
				if len(resBytes) > 0 {
					_ = json.Unmarshal(resBytes, &tr)
				}
				if tr.ResourceId != "" {
					if err := service.CancelWorkerJob(tr.ResourceId); err != nil {
						log.Printf("通知 worker 删除 job %s 失败: %v", tr.ResourceId, err)
					} else {
						log.Printf("已通知 worker 删除 job %s (shot delete)", tr.ResourceId)
					}
				}

				if service.CancelPollTask(tid) {
					log.Printf("Cancelled poll for task %s (shot delete)", tid)
				}
				msg := "cancelled due to shot delete"
				_ = models.UpdateTaskStatus(tid, models.TaskStatusCancelled, nil, &msg, nil, nil, nil, nil)
			}
		}
		if _, err := models.DB.Exec(`DELETE FROM shot WHERE id = ?`, shotID); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "删除分镜失败: " + err.Error()})
			return
		}
	} else {
		// 同样先取消 processing 任务
		rows, err := models.DB.Query(`SELECT id FROM task WHERE shot_id = ? AND status = ?`, shotID, models.TaskStatusProcessing)
		if err == nil {
			defer rows.Close()
			for rows.Next() {
				var tid string
				if err := rows.Scan(&tid); err != nil {
					continue
				}
				if service.CancelPollTask(tid) {
					log.Printf("Cancelled poll for task %s (shot delete)", tid)
				}
				msg := "cancelled due to shot delete"
				_ = models.UpdateTaskStatus(tid, models.TaskStatusCancelled, nil, &msg, nil, nil, nil, nil)
			}
		}

		if err := models.DeleteShotByID(projectID, shotID); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "删除分镜失败: " + err.Error()})
			return
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"message":    "分镜已删除",
		"shot_id":    shotID,
		"project_id": projectID,
	})
}

// 触发整片视频生成任务（创建 task 并入队）
func GenerateShotVideo(c *gin.Context) {
	projectID := c.Param("project_id")

	var req struct {
		ShotID string `json:"shot_id" form:"shot_id"`
		FPS    int    `json:"fps" form:"fps"`
	}
	// 允许从 Query 或 Body 绑定
	if err := c.ShouldBind(&req); err != nil {
	}

	// 允许 shot_id 为空（表示生成整个项目的视频）
	/*
		if req.ShotID == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "shot_id is required"})
			return
		}
	*/

	// 1. 创建任务对象
	task := models.Task{
		ID:        uuid.NewString(),
		ProjectId: projectID,
		ShotId:    req.ShotID,
		Type:      models.TaskTypeVideoGen,
		Status:    models.TaskStatusPending,
		Progress:  0,
		Message:   "视频生成任务排队中",
		Parameters: models.TaskParameters{
			Video: &models.VideoParams{
				FPS:        req.FPS, // 默认值或从 req 获取
				Resolution: "1280x720",
			},
			Shot: &models.ShotParams{},
		},
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	// 如果是以项目为维度的视频生成 (ShotID 为空)，我们需要填充 ShotDefaults (StoryText, Style 等)
	// 供 Gateway 的 "Full video pipeline" 使用 (重新生成 Storyboard/Assets)
	if req.ShotID == "" {
		project, err := models.GetProjectByID(projectID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Project not found for video generation: " + err.Error()})
			return
		}
		task.Parameters.ShotDefaults = &models.ShotDefaultsParams{
			StoryText: project.StoryText,
			Style:     project.Style,
			ShotCount: project.ShotCount,
		}
	}

	// 2. 存入数据库
	if err := models.CreateTask(&task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "创建任务失败: " + err.Error()})
		return
	}

	// 3. 推送到 Redis 队列
	if err := service.EnqueueTask(task.ID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "任务入队失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":    "视频生成任务已创建",
		"project_id": projectID,
		"shot_id":    req.ShotID,
		"task_id":    task.ID,
	})
}
