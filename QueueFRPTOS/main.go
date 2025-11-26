package main

import (
	"log"
	"remote-storyboard/controllers"
	"remote-storyboard/models"
	"remote-storyboard/service"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/spf13/viper"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)
func main() {
	viper.SetConfigName("config") 
    viper.SetConfigType("yaml")   /
    viper.AddConfigPath(".")      

	if err := viper.ReadInConfig(); err != nil {
        log.Fatalf("Error reading config file: %s", err)
    }
    log.Println("Config loaded successfully")

	db, err := gorm.Open(sqlite.Open(viper.GetString("database.source")), &gorm.Config{})
	if err != nil {
		log.Fatal("failed to connect database")
	}
	db.AutoMigrate(&models.Project{}, &models.Task{}, &models.Shot{})

	// 2. 配置信息
    redisAddr := viper.GetString("redis.addr")
    redisPassword := viper.GetString("redis.password")
    workerAddr := viper.GetString("worker.addr")
    serverPort := viper.GetString("server.port")

	// 3. 初始化任务队列生产者
	service.InitQueue(redisAddr, redisPassword)

	// 4. 启动任务队列消费者 (后台运行)
	processor := service.NewProcessor(db, workerAddr)
	processor.Start(redisAddr,10)

	// 5. 初始化 Web API
	gin.SetMode(viper.GetString("server.mode"))
	r := gin.Default()
	r.Use(cors.New(cors.Config{
    AllowOrigins:     []string{"http://localhost:3000"}, 
    AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
    AllowHeaders:     []string{"Origin", "Content-Type"},
    ExposeHeaders:    []string{"Content-Length"},
    AllowCredentials: true,
}))
	projCtrl := &controllers.ProjectController{DB: db}

	api := r.Group("/api")
	{
		// 触发分镜生成
		api.POST("/projects/:project_id/generate-storyboard", projCtrl.GenerateStoryboard)
		api.POST("/shots/:shot_id/generate", projCtrl.GenerateShot)
		api.POST("/projects", func(c *gin.Context) {
            var p models.Project
            if err := c.ShouldBindJSON(&p); err == nil {
                p.ID = uuid.New().String() 
                db.Create(&p)
                c.JSON(200, p)
            } else {
                c.JSON(400, gin.H{"error": err.Error()})
            }
        })
        
        // 获取项目列表
        api.GET("/projects", func(c *gin.Context) {
            var projects []models.Project
            db.Find(&projects)
            c.JSON(200, projects)
        })
		// 还需要一个查询任务状态的接口，前端轮询用
		api.GET("/tasks/:task_id", func(c *gin.Context) {
			var task models.Task
			if err := db.First(&task, "id = ?", c.Param("task_id")).Error; err != nil {
				c.JSON(404, gin.H{"error": "Task not found"})
				return
			}
			c.JSON(200, task)
		})
	}

	log.Println("Server running on :8080")
	if err := r.Run(serverPort); err != nil {
        log.Fatal("Server run failed:", err)
    }
}