package models

import "time"

type Shot struct {
    ID          string    `gorm:"primaryKey;type:varchar(64)" json:"id"`
    ProjectId   string    `json:"projectId"`
    Order       int       `json:"order"`
    Title       string    `json:"title"`
    Description string    `json:"description"`
    Prompt      string    `json:"prompt"`
    Status      string    `json:"status"`
    ImagePath   string    `json:"imagePath"`
    AudioPath   string    `json:"audioPath"`
    Transition  string    `json:"transition"`
    CreatedAt   time.Time `json:"createdAt"`
    UpdatedAt   time.Time `json:"updatedAt"`
}