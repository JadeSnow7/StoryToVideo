package service

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"StoryToVideo-server/internal/config"

	"github.com/hibiken/asynq"
)

const (
	TypeGenerateTask = "task:generate"
)

type TaskPayload struct {
	TaskID string `json:"task_id"`
}

var QueueClient *asynq.Client

// InitQueue initializes the Redis-backed task queue
func InitQueue() {
	QueueClient = asynq.NewClient(asynq.RedisClientOpt{
		Addr:     config.AppConfig.Redis.Addr,
		Password: config.AppConfig.Redis.Password,
	})
}

// EnqueueTask enqueues a task for background processing
func EnqueueTask(taskID string) error {
	payload, err := json.Marshal(TaskPayload{TaskID: taskID})
	if err != nil {
		return fmt.Errorf("marshal payload failed: %w", err)
	}

	task := asynq.NewTask(TypeGenerateTask, payload,
		asynq.MaxRetry(3),
		asynq.Timeout(20*time.Minute),
		asynq.Retention(24*time.Hour),
	)

	info, err := QueueClient.Enqueue(task)
	if err != nil {
		return fmt.Errorf("enqueue failed: %w", err)
	}

	log.Printf("[Queue] Task Enqueued: ID=%s, TaskID=%s", taskID, info.ID)
	return nil
}
