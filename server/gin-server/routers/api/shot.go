package api

import (
	"net/http"
	"time"

	"testgin/models"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// 获取分镜列表
func GetShots(c *gin.Context) {
	projectID := c.Param("project_id")

	// TODO: 从数据库获取分镜列表
	shots := []models.Shot{
		{
			ID:          uuid.NewString(),
			ProjectId:   projectID,
			Order:       1,
			Title:       "分镜1",
			Description: "分镜描述1",
			Prompt:      "提示词1",
			Status:      "created",
			ImagePath:   "",
			AudioPath:   "",
			Transition:  "",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
	}

	c.JSON(http.StatusOK, gin.H{
		"shots":       shots,
		"project_id":  projectID,
		"total_shots": len(shots),
	})
}

// 生成分镜
func CreateShot(c *gin.Context) {
	projectID := c.Param("project_id")
	var req struct {
		Title      string `form:"title"`
		Prompt     string `form:"prompt"`
		Transition string `form:"transition"`
	}
	if err := c.ShouldBindQuery(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	shot := models.Shot{
		ID:          uuid.NewString(),
		ProjectId:   projectID,
		Order:       1, // TODO: 真实顺序应从数据库获取
		Title:       req.Title,
		Description: "",
		Prompt:      req.Prompt,
		Status:      "created",
		ImagePath:   "",
		AudioPath:   "",
		Transition:  req.Transition,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	// TODO: 持久化到数据库

	c.JSON(http.StatusOK, gin.H{
		"shot_id": shot.ID,
		"task_id": uuid.NewString(), // TODO: 实际任务ID
		"message": "分镜生成任务已创建",
	})
}

// 获取分镜详情
func GetShotDetail(c *gin.Context) {
	projectID := c.Param("project_id")
	shotID := c.Param("shot_id")

	// TODO: 从数据库获取分镜详情
	shot := models.Shot{
		ID:          shotID,
		ProjectId:   projectID,
		Order:       1,
		Title:       "分镜标题",
		Description: "分镜描述",
		Prompt:      "分镜提示词",
		Status:      "created",
		ImagePath:   "",
		AudioPath:   "",
		Transition:  "",
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	c.JSON(http.StatusOK, gin.H{
		"shot": shot,
	})
}

// 删除分镜
func DeleteShot(c *gin.Context) {
	projectID := c.Param("project_id")
	shotID := c.Param("shot_id")
	// TODO: 从数据库删除分镜

	c.JSON(http.StatusOK, gin.H{
		"message":    "分镜已删除",
		"shot_id":    shotID,
		"project_id": projectID,
	})

}

// 视频生成
func GenerateShotVideo(c *gin.Context) {
	projectID := c.Param("project_id")
	//TODO: 触发视频生成任务

	c.JSON(http.StatusOK, gin.H{
		"message":    "视频生成任务已创建",
		"project_id": projectID,
		"task_id":    uuid.NewString(), // TODO: 实际任务ID
	})

}
