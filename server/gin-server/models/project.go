package models

import "time"

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