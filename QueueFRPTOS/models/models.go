//为了防止“魔法字符串”（Hardcoded strings）到处飞，我们先定义好状态常量和结构体。
//确保 JSONMap 能够正确处理数据库交互。
package models

import (
	"database/sql/driver"
	"encoding/json"
	"time"
)

// --- 常量定义 ---
const (
	TaskStatusPending    = "pending"    // 排队中
	TaskStatusProcessing = "processing" // 处理中（已发送给Worker）
	TaskStatusSuccess    = "success"    // 成功
	TaskStatusFailed     = "failed"     // 失败
	
	TaskTypeStoryboard   = "storyboard" // 任务类型：分镜生成
    TaskTypeShotGen      = "shot_generation" // 单独生成/重绘一个分镜
)

// --- 工具类型 ---
type JSONMap map[string]interface{}

// 实现 Gorm 的 Valuer 接口（写入数据库）
func (j JSONMap) Value() (driver.Value, error) {
	if j == nil {
		return "{}", nil
	}
	return json.Marshal(j)
}

// 实现 Gorm 的 Scanner 接口（读取数据库）
func (j *JSONMap) Scan(value interface{}) error {
	if value == nil {
		*j = make(JSONMap)
		return nil
	}
	bytes, ok := value.([]byte)
	if !ok {
		return nil // 或者报错
	}
	return json.Unmarshal(bytes, j)
}

// --- 表结构 ---

type Project struct {
    ID          string    `gorm:"primaryKey" json:"id"`
    Title       string    `gorm:"not null" json:"title"`
    StoryText   string    `gorm:"type:text" json:"story_text"`
    Style       string    `gorm:"size:20" json:"style"` // movie/animation/realistic
    Status      string    `gorm:"size:20;default:draft" json:"status"` // draft/generating/completed
    
    // 资产页需要的展示信息
    CoverImage  string    `gorm:"type:text" json:"cover_image"` // 封面图（第一个分镜的图片）
    Duration    float64   `gorm:"default:0" json:"duration"`    // 视频总时长
    VideoURL    string    `gorm:"type:text" json:"video_url"`   // 最终视频URL    
    CreatedAt   time.Time `json:"created_at"`
    UpdatedAt   time.Time `json:"updated_at"`
    // 关联关系简化
    Shots []Shot `gorm:"foreignKey:ProjectID" json:"shots,omitempty"`
    Tasks []Task `gorm:"foreignKey:ProjectID" json:"-"`
}

type Task struct {
	ID        string    `gorm:"primaryKey" json:"id"`
	ProjectID string    `gorm:"index" json:"project_id"`
    ShotID    string    `gorm:"index" json:"shot_id,omitempty"`
	Type      string    `gorm:"size:50" json:"type"`   // e.g. "storyboard"
	Status    string    `gorm:"size:20" json:"status"` // pending/processing/success/failed
	
	// 输入参数：发送给 Worker 的具体指令（如：{"style": "anime", "ratio": "16:9"}）
	Parameters JSONMap `gorm:"type:json" json:"parameters"`
	
	// 输出结果：Worker 返回的数据（如：{"images": ["url1", "url2"]}）
	Result     JSONMap `gorm:"type:json" json:"result"`
	
	Error      string    `gorm:"type:text" json:"error"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}


type Shot struct {
    ID          string    `gorm:"primaryKey" json:"id"`
    ProjectID   string    `gorm:"not null;index" json:"project_id"`
    Order       int       `gorm:"not null" json:"order"`
    Title       string    `gorm:"not null" json:"title"`
    Description string    `gorm:"type:text" json:"description"`
    Prompt      string    `gorm:"type:text" json:"prompt"`
    Narration   string    `gorm:"type:text" json:"narration"`
    
    // 状态统一管理
    Status      string    `gorm:"size:20;default:pending" json:"status"` // pending/generating/completed/failed
    
    // 生成结果 - 直接存储文件信息
    ImagePath   string    `gorm:"type:text" json:"image_path"`  // 图片存储路径
    AudioPath   string    `gorm:"type:text" json:"audio_path"`  // 音频存储路径
    
    // 效果参数
    Transition  string    `gorm:"size:50;default:crossfade" json:"transition"`
    Duration    float64   `gorm:"default:3.0" json:"duration"`
    
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at"`
    
    Project Project `gorm:"foreignKey:ProjectID" json:"-"`
}
