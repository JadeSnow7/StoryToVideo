package models

import "time"

type Task struct {
    ID               string         `gorm:"primaryKey;type:varchar(64)" json:"id"`
    ProjectId        string         `json:"projectId"`
    ShotId           string         `json:"shotId"`
    Type             string         `json:"type"`
    Status           string         `json:"status"`
    Progress         int            `json:"progress"`
    Message          string         `json:"message"`
    Parameters       TaskParameters `gorm:"type:json" json:"parameters"`
    Result           TaskResult     `gorm:"type:json" json:"result"`
    Error            string         `json:"error"`
    EstimatedDuration int           `json:"estimatedDuration"`
    StartedAt        time.Time      `json:"startedAt"`
    FinishedAt       time.Time      `json:"finishedAt"`
    CreatedAt        time.Time      `json:"createdAt"`
    UpdatedAt        time.Time      `json:"updatedAt"`
}

type TaskParameters struct {
    Shot  TaskShotParameters  `json:"shot"`
    Video TaskVideoParameters `json:"video"`
}

type TaskShotParameters struct {
    Style       string `json:"style"`
    TextLLM     string `json:"text_llm"`
    ImageLLM    string `json:"image_llm"`
    GenerateTTS bool   `json:"generate_tts"`
    ShotCount   int    `json:"shot_count"`
    ImageWidth  int    `json:"image_width"`
    ImageHeight int    `json:"image_height"`
}

type TaskVideoParameters struct {
    Format           string `json:"format"`
    Resolution       string `json:"resolution"`
    FPS              string `json:"fps"`
    TransitionEffects string `json:"transition_effects"`
}

type TaskResult struct {
    TaskShots TaskShotsResult `json:"task_shots"`
    TaskVideo TaskVideoResult `json:"task_video"`
}

type TaskShotsResult struct {
    GeneratedShots []Shot `json:"generated_shots"`
    TotalShots     int    `json:"total_shots"`
    TotalTime      float64 `json:"total_time"`
}

type TaskVideoResult struct {
    Path      string `json:"path"`
    Duration  string `json:"duration"`
    FPS       string `json:"fps"`
    Resolution string `json:"resolution"`
    Format    string `json:"format"`
    TotalTime string `json:"total_time"`
}