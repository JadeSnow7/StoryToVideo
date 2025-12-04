// ...existing code...
package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"time"

	"gorm.io/gorm"
)

// 任务状态（在系统中统一使用这些状态）
const (
	// pending: 任务已就绪，等待执行器取走执行
	TaskStatusPending = "pending"
	// blocked: 任务因依赖未满足被阻塞（例如 shot_image 等待 project_text 完成）
	TaskStatusBlocked = "blocked"
	// processing: 任务正在执行中
	TaskStatusProcessing = "processing"
	TaskStatusSuccess    = "finished"
	TaskStatusFailed     = "failed"
	// cancelled: 任务被用户/系统取消（例如项目更新时取消正在 processing 的任务）
	TaskStatusCancelled = "cancelled"

	// 定义三种核心任务类型
	TaskTypeStoryboard   = "generate_storyboard" // 文本 -> 分镜脚本
	TaskTypeShotImage    = "generate_shot"       // 关键帧 -> 生图
	TaskTypeProjectAudio = "generate_audio"      // 文本 -> 旁白语音
	TaskTypeVideoGen     = "generate_video"      // (可选) 图 -> 视频
)

type Task struct {
	ID                string         `gorm:"primaryKey;type:varchar(64)" json:"id"`
	ProjectId         string         `json:"projectId"`
	ShotId            string         `json:"shotId,omitempty"`
	Type              string         `json:"type"`
	Status            string         `json:"status"`
	Progress          int            `json:"progress"`
	Message           string         `json:"message"`
	Parameters        TaskParameters `gorm:"type:json" json:"parameters"`
	Result            TaskResult     `gorm:"type:json" json:"result"`
	Error             string         `json:"error"`
	EstimatedDuration int            `json:"estimatedDuration"`
	StartedAt         time.Time      `json:"startedAt"`
	FinishedAt        time.Time      `json:"finishedAt"`
	CreatedAt         time.Time      `json:"createdAt"`
	UpdatedAt         time.Time      `json:"updatedAt"`
}

type TaskParameters struct {
	ShotDefaults *ShotDefaultsParams `json:"shot_defaults,omitempty"`
	Shot         *ShotParams         `json:"shot,omitempty"`
	Video        *VideoParams        `json:"video,omitempty"`
	TTS          *TTSParams          `json:"tts,omitempty"`
	DependsOn    []string            `json:"depends_on,omitempty"`
}

type ShotDefaultsParams struct {
	ShotCount int    `json:"shot_count"`
	Style     string `json:"style"`
	StoryText string `json:"storyText"`
}

type ShotParams struct {
	Transition  string `json:"transition"`
	ShotId      string `json:"shotId,omitempty"`
	ImageWidth  string `json:"image_width"`
	ImageHeight string `json:"image_height"`
	Prompt      string `json:"prompt"`
	Style       string `json:"style"`
	ImageLLM    string `json:"image_llm"`
	GenerateTTS bool   `json:"generate_tts"`
}

type VideoParams struct {
	Resolution string `json:"resolution"`
	FPS        int    `json:"fps"`
	Format     string `json:"format"`
	Bitrate    int    `json:"bitrate"`
}

type TTSParams struct {
	Voice      string `json:"voice"`
	Lang       string `json:"lang"`
	SampleRate int    `json:"sample_rate"`
	Format     string `json:"format"`
}

// TaskResult 仅保留最小资源定位信息
type TaskResult struct {
	ResourceType string                 `json:"resource_type"` // e.g., "image", "audio", "json"
	ResourceId   string                 `json:"resource_id"`
	ResourceUrl  string                 `json:"resource_url"`
}

// 实现 driver.Valuer 接口: Go Struct -> JSON String (存入数据库)
func (p TaskParameters) Value() (driver.Value, error) {
	return json.Marshal(p)
}

// 实现 sql.Scanner 接口: JSON String -> Go Struct (从数据库读取)
func (p *TaskParameters) Scan(value interface{}) error {
	if value == nil {
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return errors.New(fmt.Sprint("Failed to unmarshal JSONB value:", value))
	}
	return json.Unmarshal(bytes, p)
}

// 实现 driver.Valuer 接口
func (r TaskResult) Value() (driver.Value, error) {
	return json.Marshal(r)
}

// 实现 sql.Scanner 接口
func (r *TaskResult) Scan(value interface{}) error {
	if value == nil {
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return errors.New(fmt.Sprint("Failed to unmarshal JSONB value:", value))
	}
	return json.Unmarshal(bytes, r)
}

type TaskShotsResult struct {
	GeneratedShots []Shot  `json:"generated_shots"`
	TotalShots     int     `json:"total_shots"`
	TotalTime      float64 `json:"total_time"`
}

type TaskVideoResult struct {
	Path       string `json:"path"`
	Duration   string `json:"duration"`
	FPS        string `json:"fps"`
	Resolution string `json:"resolution"`
	Format     string `json:"format"`
	TotalTime  string `json:"total_time"`
}

func (t *Task) UpdateStatus(db *gorm.DB, status string, result interface{}, errMsg string) error {
	updates := map[string]interface{}{
		"status":     status,
		"updated_at": time.Now(),
	}
	if result != nil {
		jsonBytes, err := json.Marshal(result)
		if err != nil {
			log.Printf("序列化任务结果失败: %v", err)
			// 如果序列化失败，可以选择不更新 result，或者存一个错误提示
		} else {
			updates["result"] = jsonBytes
		}
	}

	if errMsg != "" {
		updates["error"] = errMsg
	}
	return db.Model(t).Updates(updates).Error
}

func GetTaskByIDGorm(db *gorm.DB, taskID string) (*Task, error) {
	var task Task
	if err := db.First(&task, "id = ?", taskID).Error; err != nil {
		return nil, err
	}
	return &task, nil
}

// 强制指定表名为 "task" (解决 Error 1146 表不存在的问题)
func (Task) TableName() string {
	return "task"
}
