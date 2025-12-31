package models

import "time"

// 项目状态常量（用于在业务层统一描述项目进度）
const (
	ProjectStatusCreated         = "created"          // 项目已创建，未开始任何生成任务
	ProjectStatusTextGenerated   = "text_generated"   // 项目故事文本已生成（project_text 完成）
	ProjectStatusShotsGenerated  = "shots_generated"  // 分镜已生成（shots 条目已写入 DB）
	ProjectStatusImagesGenerated = "images_generated" // 分镜图片已全部生成
	ProjectStatusVideoGenerated  = "video_generated"  // 整片视频已生成
	ProjectStatusAudioGenerated  = "audio_generated"  // 整片配音已生成
	ProjectStatusReady           = "ready"            // 所有生成完成，可播放/导出
	ProjectStatusFailed          = "failed"           // 项目生成过程出错
)

type Project struct {
    ID         string    `gorm:"primaryKey;type:varchar(64)" json:"id"`
    Title      string    `json:"title"`
    StoryText  string    `json:"storyText"`
    Style      string    `json:"style"`
    Status     string    `json:"status"`
    CoverImage string    `json:"coverImage"`
    Duration   int       `json:"duration"`
    VideoUrl   string    `json:"videoUrl"`
    Description string   `json:"description"`
    ShotCount  int       `json:"shotCount"`
    CreatedAt  time.Time `json:"createdAt"`
    UpdatedAt  time.Time `json:"updatedAt"`
}

func (Project) TableName() string {
    return "project"
}
