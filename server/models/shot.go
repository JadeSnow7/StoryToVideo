package models

import (
	"time"

	"gorm.io/gorm"
)

const (
	ShotStatusPending    = "pending"
	ShotStatusProcessing = "processing"
	ShotStatusCompleted  = "completed"
	ShotStatusFailed     = "failed"
)

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

func BatchCreateShots(db *gorm.DB, shots []Shot) error {
	if len(shots) == 0 {
		return nil
	}
	return db.Create(&shots).Error
}

func (s *Shot) UpdateImage(db *gorm.DB, imagePath string) error {
	updates := map[string]interface{}{
		"image_path": imagePath,
		"status":     ShotStatusCompleted,
		"updated_at": time.Now(),
	}
	return db.Model(s).Updates(updates).Error
}

func GetShotByIDGorm(db *gorm.DB, shotID string) (*Shot, error) {
    var shot Shot
    if err := db.First(&shot, "id = ?", shotID).Error; err != nil {
        return nil, err
    }
    return &shot, nil
}

func (Shot) TableName() string {
    return "shot"
}
