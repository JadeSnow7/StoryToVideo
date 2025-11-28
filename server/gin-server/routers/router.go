package routers

import (
	"testgin/routers/api"

	"github.com/gin-gonic/gin"
)

func InitRouter() *gin.Engine {
	r := gin.Default()
	v1 := r.Group("/v1/api")
	{
		v1.POST("/projects", api.CreateProject)
		v1.GET("/projects/:project_id", api.GetProject)
		v1.PUT("/projects/:project_id", api.UpdateProject)
		v1.DELETE("/projects/:project_id", api.DeleteProject)

		v1.POST("/projects/:project_id/shots", api.CreateShot)
		v1.GET("/projects/:project_id/shots", api.GetShots)
		v1.GET("/projects/:project_id/shots/:shot_id", api.GetShotDetail)
		v1.DELETE("/shots/:shot_id", api.DeleteShot)
		v1.POST("/projects/{project_id}/video", api.GenerateShotVideo)
	}
	v1.GET("/tasks/:task_id/ws", api.TaskProgressWebSocket)
	return r
}
