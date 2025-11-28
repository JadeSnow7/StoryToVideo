package api

import (
	"net/http"
	"time"

	"testgin/models"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// 创建项目
func CreateProject(c *gin.Context) {
	var req struct {
		Title       string `form:"Title"`
		StoryText   string `form:"StoryText"`
		Style       string `form:"Style"`
		Description string `form:"Description"`
	}
	if err := c.ShouldBindQuery(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	project := models.Project{
		ID:          uuid.NewString(),
		Title:       req.Title,
		StoryText:   req.StoryText,
		Style:       req.Style,
		Description: req.Description,
		Status:      "created",
		CoverImage:  "",
		Duration:    0,
		VideoUrl:    "",
		ShotCount:   0,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	// TODO: 持久化到数据库

	// 创建任务（示例，实际逻辑可根据业务调整）
	taskID := uuid.NewString()
	status := "pending"

	c.JSON(http.StatusOK, gin.H{
		"ProjectID": project.ID,
		"TaskID":    taskID,
		"Status":    status,
	})
}

// 获取项目详情
func GetProject(c *gin.Context) {
	projectID := c.Param("project_id")

	// TODO: 从数据库获取项目、分镜、最近任务
	project := models.Project{
		ID:          projectID,
		Title:       "示例标题",
		StoryText:   "示例故事",
		Style:       "示例风格",
		Status:      "created",
		CoverImage:  "",
		Duration:    0,
		VideoUrl:    "",
		Description: "",
		ShotCount:   0,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}
	shots := []models.Shot{}
	recentTask := struct{}{}

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
		Title       string `form:"Title"`
		Description string `form:"Description"`
	}
	if err := c.ShouldBindQuery(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// TODO: 数据库更新项目
	updateAt := time.Now()

	c.JSON(http.StatusOK, gin.H{
		"id":       projectID,
		"updateAT": updateAt,
	})
}

// 删除项目
func DeleteProject(c *gin.Context) {
	//projectID := c.Param("project_id")

	// TODO: 数据库删除项目
	deleteAt := time.Now()

	c.JSON(http.StatusOK, gin.H{
		"success":  true,
		"deleteAt": deleteAt,
		"message":  "项目已删除",
	})
}
