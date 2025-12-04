package service

import (
	"encoding/json"
	"fmt"
	"log"
	"time"
    "StoryToVideo-server/config"

	"github.com/hibiken/asynq"
)

const (
    TypeGenerateTask = "task:generate" 
)

type TaskPayload struct {
	TaskID string `json:"task_id"`
}

var QueueClient *asynq.Client

// InitQueue 初始化
func InitQueue() {
    QueueClient = asynq.NewClient(asynq.RedisClientOpt{
        Addr:     config.AppConfig.Redis.Addr,
        Password: config.AppConfig.Redis.Password,
    })
}

// EnqueueGenerateTask 通用的生成任务入队接口
func EnqueueTask(taskID string) error {
    payload, err := json.Marshal(TaskPayload{TaskID: taskID})
    if err != nil {
        return fmt.Errorf("marshal payload failed: %w", err)
    }

    task := asynq.NewTask(TypeGenerateTask, payload,
        asynq.MaxRetry(3),                      // 失败重试 3 次
        asynq.Timeout(20*time.Minute),          // 显卡生成较慢，设置较长超时
        asynq.Retention(24*time.Hour),          // 任务结果在 Redis 保留时间
    )

    info, err := QueueClient.Enqueue(task)
    if err != nil {
        return fmt.Errorf("enqueue failed: %w", err)
    }
    
    log.Printf("[Queue] Task Enqueued: ID=%s, TaskID=%s", taskID, info.ID)
    return nil
}