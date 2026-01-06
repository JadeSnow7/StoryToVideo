// Package routers initializes HTTP routes for the StoryToVideo server.
package routers

import (
	"StoryToVideo-server/internal/routers/api"

	"github.com/gin-gonic/gin"
)

// InitRouter sets up and returns the Gin router
func InitRouter() *gin.Engine {
	r := gin.Default()
	r.Static("/static", "./static")

	v1 := r.Group("/v1/api")
	{
		// Health check
		v1.GET("/health", api.HealthCheck)

		// Projects
		v1.POST("/projects", api.CreateProject)
		v1.GET("/projects/:project_id", api.GetProject)
		v1.PUT("/projects/:project_id", api.UpdateProject)
		v1.DELETE("/projects/:project_id", api.DeleteProject)

		// Tasks
		v1.GET("/tasks/:task_id", api.GetTaskStatus)

		// Shots
		v1.POST("/projects/:project_id/shots/:shot_id", api.UpdateShot)
		v1.GET("/projects/:project_id/shots", api.GetShots)
		v1.GET("/projects/:project_id/shots/:shot_id", api.GetShotDetail)
		v1.DELETE("/shots/:shot_id", api.DeleteShot)

		// Video generation
		v1.POST("/projects/:project_id/video", api.GenerateShotVideo)

		// TTS generation
		v1.POST("/projects/:project_id/tts", api.GenerateProjectTTS)
	}

	// WebSocket endpoint (outside /v1/api group)
	r.GET("/tasks/:task_id/wss", api.TaskProgressWebSocket)

	return r
}
