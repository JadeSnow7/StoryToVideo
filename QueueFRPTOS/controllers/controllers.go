package controllers

import (
    "net/http"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
    "remote-storyboard/models"
    "remote-storyboard/service"
    "gorm.io/gorm"
)

type ProjectController struct {
    DB *gorm.DB
}

// GenerateStoryboard 触发分镜生成
func (pc *ProjectController) GenerateStoryboard(c *gin.Context) {
    projectID := c.Param("project_id")

    // 1. 校验项目是否存在
    var project models.Project
    if err := pc.DB.First(&project, "id = ?", projectID).Error; err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Project not found"})
        return
    }

    // 2. 创建 Task 记录
    taskID := uuid.New().String()
    newTask := models.Task{
        ID:        taskID,
        ProjectID: projectID,
        Type:      models.TaskTypeStoryboard,
        Status:    models.TaskStatusPending,
        Parameters: models.JSONMap{
            "style":       project.Style, 
            "need_images": true,
            "story_text":  project.StoryText,
        },
        CreatedAt: time.Now(),
        UpdatedAt: time.Now(),
    }

    if err := pc.DB.Create(&newTask).Error; err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create task record"})
        return
    }

    // 3. 推入消息队列
    err := service.EnqueueTask(taskID)
    if err != nil {
        // 如果入队失败，应该回滚 DB 或标记任务为失败
        pc.DB.Model(&newTask).Update("status", models.TaskStatusFailed)
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to enqueue task"})
        return
    }

    c.JSON(http.StatusAccepted, gin.H{
        "message": "Task queued successfully",
        "task_id": taskID,
        "status":  models.TaskStatusPending,
    })
}

func (pc *ProjectController) GenerateShot(c *gin.Context) {
    shotID := c.Param("shot_id")
    
    // 1. 查分镜，获取它的 ProjectID 和当前的 Prompt
    var shot models.Shot
    if err := pc.DB.First(&shot, "id = ?", shotID).Error; err != nil {
        c.JSON(404, gin.H{"error": "Shot not found"})
        return
    }
    var project models.Project
    if err := pc.DB.First(&project, "id = ?", shot.ProjectID).Error; err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Project not found"})
        return
    }

    // 2. 创建 Task，这次关联 ShotID
    taskID := uuid.New().String()
    newTask := models.Task{
        ID:        taskID,
        ProjectID: shot.ProjectID, 
        ShotID:    shot.ID,        
        Type:      models.TaskTypeShotGen, 
        Status:    models.TaskStatusPending,
        Parameters: models.JSONMap{
            "prompt": shot.Prompt, // 直接使用分镜的 prompt
            "style":   project.Style,     
            "need_images": true,
        },
        CreatedAt: time.Now(),
        UpdatedAt: time.Now(),
    }

    if err := pc.DB.Create(&newTask).Error; err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create task record"})
        return
    }

    // 3. 推入消息队列
    err := service.EnqueueTask(taskID)
    if err != nil {
        pc.DB.Model(&newTask).Update("status", models.TaskStatusFailed)
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to enqueue task"})
        return
    }

    c.JSON(http.StatusAccepted, gin.H{
        "message": "Task queued successfully",
        "task_id": taskID,
        "status":  models.TaskStatusPending,
    })
}
