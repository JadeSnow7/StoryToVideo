// ...existing code...
package api

import (
    "log"
    "net/http"
    "time"

    "StoryToVideo-server/models"

    "StoryToVideo-server/service"

    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
) //119.45.124.222 //localhost

// ...existing code...

// 新增：项目音频生成（TTS）接口实现
func GenerateProjectTTS(c *gin.Context) {
    projectID := c.Param("project_id")

    // 默认 TTS 参数（可扩展为从请求体读取）
    ttsDefaults := models.TTSParams{
        Voice:      "xiaoyan",
        Lang:       "zh-CN",
        SampleRate: 24000,
        Format:     "mp3",
    }

    task := models.Task{
        ID:        uuid.NewString(),
        ProjectId: projectID,
        Type:      models.TaskTypeProjectAudio,
        Status:    models.TaskStatusPending,
        Progress:  0,
        Message:   "项目音频 (TTS) 生成任务已创建",
        Parameters: models.TaskParameters{
            TTS: &ttsDefaults,
        },
        Result:            models.TaskResult{},
        Error:             "",
        EstimatedDuration: 0,
        CreatedAt:         time.Now(),
        UpdatedAt:         time.Now(),
    }

    if err := models.CreateTask(&task); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "创建 TTS 任务失败: " + err.Error()})
        return
    }

    if err := service.EnqueueTask(task.ID); err != nil {
        log.Printf("TTS 任务入队失败: %v", err)
        // 仍返回成功创建但提示入队失败
        c.JSON(http.StatusOK, gin.H{
            "task_id":    task.ID,
            "message":    "音频任务已创建，但入队失败",
            "project_id": projectID,
        })
        return
    }

    c.JSON(http.StatusOK, gin.H{
        "task_id":    task.ID,
        "message":    "音频生成任务已创建",
        "project_id": projectID,
    })
}

// ...existing code...