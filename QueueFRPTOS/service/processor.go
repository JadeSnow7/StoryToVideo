package service

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "time"

    "github.com/hibiken/asynq"
	"github.com/google/uuid"
    "gorm.io/gorm"
    "remote-storyboard/models"
)

// Processor 处理队列任务
type Processor struct {
    DB *gorm.DB
    WorkerEndpoint string 
}

func NewProcessor(db *gorm.DB, workerAddr string) *Processor {
    return &Processor{DB: db, 
        WorkerEndpoint: workerAddr,
    }
}

// Start 启动任务消费者
func (p *Processor) Start(redisAddr string, concurrency int) {
    srv := asynq.NewServer(
        asynq.RedisClientOpt{Addr: redisAddr},
        asynq.Config{
            Concurrency: concurrency,
            Queues: map[string]int{
                "default": 1,
            },
        },
    )
    mux := asynq.NewServeMux()
    mux.HandleFunc(TypeGenerateTask, p.HandleGenerateTask)

    go func() {
        if err := srv.Run(mux); err != nil {
            log.Fatalf("could not run server: %v", err)
        }
    }()
}

// HandleGenerateTask 处理分镜生成任务
func (p *Processor) HandleGenerateTask(ctx context.Context, t *asynq.Task) error {
    var payload TaskPayload
    if err := json.Unmarshal(t.Payload(), &payload); err != nil {
        return fmt.Errorf("json.Unmarshal failed: %v: %w", err, asynq.SkipRetry)
    }
    // . 获取任务详情（获取参数）
    var task models.Task
    if err := p.DB.First(&task, "id = ?", payload.TaskID).Error; err != nil {
        return fmt.Errorf("task not found: %v", err)
    }
	log.Printf("Processing Task: %s | Type: %s", task.ID, task.Type)
    p.updateStatus(task.ID, models.TaskStatusProcessing, nil, "")

    workerReq := map[string]interface{}{
            "task_id": task.ID,
			"type":    task.Type,
            "params": task.Parameters,
        }

    if task.Type == models.TaskTypeShotGen {
        if val, ok := task.Parameters["prompt"]; ok {
            workerReq["prompt"] = val
        }
    } else {
        if val, ok := task.Parameters["story_text"]; ok {
            workerReq["prompt"] = val
        }
    }

    workerResp, err := p.callWorker(workerReq)
	if err != nil {
		log.Printf("Worker call failed: %v", err)
		p.updateStatus(task.ID, models.TaskStatusFailed, nil, fmt.Sprintf("Worker connection error: %v", err))
		return err
	}

	// 6. 处理 Worker 返回的业务错误
	if workerResp.Status != "success" {
		p.updateStatus(task.ID, models.TaskStatusFailed, nil, workerResp.Error)
		return nil 
	}

	var processingErr error
	
	if task.Type == models.TaskTypeShotGen {
		p.handleShotUpdate(task.ShotID, workerResp.Result)

	} else if task.Type == models.TaskTypeStoryboard {
        if err := p.handleStoryboardCreation(task.ID, task.ProjectID, workerResp.Result); err != nil {
            processingErr = fmt.Errorf("failed to create shots: %v", err)
            log.Printf("[Error] %v", processingErr)
        }
	}
	if processingErr != nil {
        p.updateStatus(task.ID, models.TaskStatusFailed, workerResp.Result, processingErr.Error())
        return nil 
    }

    p.updateStatus(task.ID, models.TaskStatusSuccess, workerResp.Result, "")
    log.Printf("Task %s completed successfully", task.ID)
	
	
	return nil
}

func (p *Processor) handleStoryboardCreation(taskID string, projectID string, result models.JSONMap) error {
    // 1. 提取 shots 列表（用于写入数据库）
    shotsData, ok := result["shots"]
    if !ok {
        return fmt.Errorf("worker response does not contain 'shots' field")
    }

    shotsList, ok := shotsData.([]interface{})
    if !ok {
        return fmt.Errorf("'shots' field is not a list")
    }

    // 2. 【新增】提取并保存 JSON URL（供前端使用）
    jsonURL, _ := result["url"].(string)
    if jsonURL != "" {
        // 可以将这个 URL 存储到 Task 表的 result 字段中
        log.Printf("Storyboard JSON available at: %s", jsonURL)
    }

    // 3. 批量创建 Shot 记录（逻辑不变）
    type workerShot struct {
        Title       string `json:"title"`
        Description string `json:"description"`
        Prompt      string `json:"prompt"`
    }

    var shotsToCreate []models.Shot
    for i, shotData := range shotsList {
        jsonBytes, _ := json.Marshal(shotData)
        var ws workerShot
        if err := json.Unmarshal(jsonBytes, &ws); err != nil {
            log.Printf("Skipping shot %d due to unmarshal error: %v", i, err)
            continue
        }

        newShot := models.Shot{
            ID:        uuid.NewString(),
            ProjectID: projectID,
            Prompt:    ws.Prompt,
            Order:     i,
            Status:    "pending", // 初始状态为待生成图片
        }
        shotsToCreate = append(shotsToCreate, newShot)
    }

    // 4. 批量插入数据库
    if len(shotsToCreate) > 0 {
        if err := p.DB.Create(&shotsToCreate).Error; err != nil {
            return fmt.Errorf("batch insert shots failed: %w", err)
        }
        log.Printf("Successfully created %d shots for project %s", len(shotsToCreate), projectID)
    }

    return nil
}

func getString(m map[string]interface{}, key string) string {
    if v, ok := m[key].(string); ok {
        return v
    }
    return ""
}

// callWorker 封装 HTTP 请求细节
func (p *Processor) callWorker(reqBody map[string]interface{}) (*WorkerResponse, error) {
	jsonBody, _ := json.Marshal(reqBody)
	
	resp, err := http.Post(p.WorkerEndpoint, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("worker returned status code: %d", resp.StatusCode)
	}

	var workerResp WorkerResponse
	if err := json.NewDecoder(resp.Body).Decode(&workerResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}

	return &workerResp, nil
}

// handleShotUpdate 将生成结果更新回 Shot 表
func (p *Processor) handleShotUpdate(shotID string, result models.JSONMap) {
	if shotID == "" {
		return
	}
	updates := map[string]interface{}{}
	
	if images, ok := result["images"].([]interface{}); ok && len(images) > 0 {
		if url, ok := images[0].(string); ok {
			updates["image_path"] = url
			updates["status"] = "completed" 
		}
	}
	if len(updates) > 0 {
		if err := p.DB.Model(&models.Shot{}).Where("id = ?", shotID).Updates(updates).Error; err != nil {
			log.Printf("Failed to update shot %s: %v", shotID, err)
		} else {
			log.Printf("Updated shot %s with new image", shotID)
		}
	}
}

// updateStatus 辅助函数：更新 Task 表状态
func (p *Processor) updateStatus(taskID, status string, result models.JSONMap, errStr string) {
	updates := map[string]interface{}{
		"status":     status,
		"updated_at": time.Now(),
	}
	if result != nil {
		updates["result"] = result
	}
	if errStr != "" {
		updates["error"] = errStr
	}
	p.DB.Model(&models.Task{}).Where("id = ?", taskID).Updates(updates)
}

