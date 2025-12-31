package main

import (
	"fmt"
	"StoryToVideo-server/config"
	"StoryToVideo-server/models"
	"StoryToVideo-server/routers"
	"StoryToVideo-server/service"
)

func main() {
	config.InitConfig()
	fmt.Println("Server starting on port", config.AppConfig.Server.Port)
	models.InitDB()
	fmt.Println("Database initialized")

	service.InitQueue()
	fmt.Println("Queue initialized")
	
	service.InitMinIO()
	fmt.Println("MinIO initialized")
	
	processor := service.NewProcessor(models.GormDB)
	processor.StartProcessor(5)

	r := routers.InitRouter()
	r.Run(config.AppConfig.Server.Port)
}
