package main

import (
	"fmt"
	"os"

	"StoryToVideo-server/internal/config"
	"StoryToVideo-server/internal/models"
	"StoryToVideo-server/internal/routers"
	"StoryToVideo-server/internal/service"
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

	// Graceful message
	fmt.Printf("StoryToVideo Server listening on %s\n", config.AppConfig.Server.Port)

	if err := r.Run(config.AppConfig.Server.Port); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to start server: %v\n", err)
		os.Exit(1)
	}
}
