// ...existing code...
package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"
	"time"

	"StoryToVideo-server/config"
	"StoryToVideo-server/models"

	"github.com/google/uuid"
	"github.com/hibiken/asynq"
	"gorm.io/gorm"
)

func CancelWorkerJob(jobID string) error {
	if jobID == "" {
		return fmt.Errorf("empty job id")
	}
	url := config.AppConfig.Worker.Addr + "/v1/jobs/" + jobID
	req, err := http.NewRequest(http.MethodDelete, url, nil)
	if err != nil {
		return fmt.Errorf("create delete request failed: %w", err)
	}
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("worker delete request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var respData map[string]interface{}
		_ = json.NewDecoder(resp.Body).Decode(&respData)
		return fmt.Errorf("worker delete status: %d, body: %+v", resp.StatusCode, respData)
	}
	return nil
}

// 新增：poll 取消注册表（taskID -> cancelFunc）
var pollCancelRegistry = struct {
	sync.RWMutex
	m map[string]context.CancelFunc
}{
	m: make(map[string]context.CancelFunc),
}

// RegisterPollCancel 注册轮询的 cancelFunc（由 HandleGenerateTask 在开始轮询时调用）
func RegisterPollCancel(taskID string, cancel context.CancelFunc) {
	pollCancelRegistry.Lock()
	defer pollCancelRegistry.Unlock()
	pollCancelRegistry.m[taskID] = cancel
}

// UnregisterPollCancel 注销轮询的 cancelFunc（在轮询结束或 task 完成时调用）
func UnregisterPollCancel(taskID string) {
	pollCancelRegistry.Lock()
	defer pollCancelRegistry.Unlock()
	delete(pollCancelRegistry.m, taskID)
}

// CancelPollTask 外部调用以取消正在轮询的任务，返回是否实际找到并取消
func CancelPollTask(taskID string) bool {
	pollCancelRegistry.Lock()
	defer pollCancelRegistry.Unlock()
	if cancel, ok := pollCancelRegistry.m[taskID]; ok {
		cancel()
		delete(pollCancelRegistry.m, taskID)
		return true
	}
	return false
}

// Processor 处理队列任务
type Processor struct {
	DB             *gorm.DB
	WorkerEndpoint string
}

func NewProcessor(db *gorm.DB) *Processor {
	// 从配置中获取 Worker 地址
	return &Processor{
		DB:             db,
		WorkerEndpoint: config.AppConfig.Worker.Addr,
	}
}

// StartProcessor 启动任务消费者
func (p *Processor) StartProcessor(concurrency int) {
	srv := asynq.NewServer(
		asynq.RedisClientOpt{
			Addr:     config.AppConfig.Redis.Addr,
			Password: config.AppConfig.Redis.Password,
		},
		asynq.Config{
			Concurrency: concurrency,
			Queues: map[string]int{
				"default": 1,
			},
		},
	)
	mux := asynq.NewServeMux()
	mux.HandleFunc(TypeGenerateTask, p.HandleGenerateTask)

	log.Printf("Starting Task Processor with concurrency %d...", concurrency)
	go func() {
		if err := srv.Run(mux); err != nil {
			log.Fatalf("could not run server: %v", err)
		}
	}()
}

// HandleGenerateTask 核心处理逻辑
func (p *Processor) HandleGenerateTask(ctx context.Context, t *asynq.Task) error {

	var payload TaskPayload
	if err := json.Unmarshal(t.Payload(), &payload); err != nil {
		return fmt.Errorf("json.Unmarshal failed: %v: %w", err, asynq.SkipRetry)
	}

	// 1. 获取任务 (使用 GORM)
	task, err := models.GetTaskByIDGorm(p.DB, payload.TaskID)
	if err != nil {
		return fmt.Errorf("task not found: %v", err)
	}

	log.Printf("Processing Task: %s | Type: %s", task.ID, task.Type)
	// 标记为 processing
	if err := task.UpdateStatus(p.DB, models.TaskStatusProcessing, nil, ""); err != nil {
		log.Printf("UpdateStatus processing failed: %v", err)
	}

	if task.Type == "create_project" {
		// 直接标记为完成
		task.UpdateStatus(p.DB, models.TaskStatusSuccess, nil, "Project initialized")
		return nil
	}
	jobID, err := p.dispatchWorkerRequest(task)
	if err != nil {
		log.Printf("Worker 请求失败: %v", err)
		task.UpdateStatus(p.DB, models.TaskStatusFailed, nil, fmt.Sprintf("Worker Request Failed: %v", err))
		return err // 返回 err 触发重试
	}
	if err := models.UpdateTaskStatus(task.ID, models.TaskStatusProcessing, nil, nil, &models.TaskResult{ResourceId: jobID}, nil, nil, nil); err != nil {
		log.Printf("写入 job_id 到 task.result 失败: %v", err)
	}
	log.Printf("任务已提交，Job ID: %s，开始轮询结果...", jobID)
	// 为轮询创建可取消的子上下文并注册 cancel（外部 API 可通过 CancelPollTask 取消）
	pollCtx, cancel := context.WithCancel(ctx)
	RegisterPollCancel(task.ID, cancel)
	// 确保在本函数结束时注销
	defer UnregisterPollCancel(task.ID)

	taskResult, err := p.pollJobResult(pollCtx, jobID)
	if err != nil {
		log.Printf("轮询任务失败: %v", err)
		task.UpdateStatus(p.DB, models.TaskStatusFailed, nil, fmt.Sprintf("Job Failed: %v", err))
		return nil // 业务失败，不再重试
	}

	// 3. 根据类型处理结果 (TOS存储 + DB更新)
	var processingErr error

	switch task.Type {
	case models.TaskTypeStoryboard: // 故事 -> 分镜
		processingErr = p.handleStoryboardResult(task.ProjectId, taskResult)

	case models.TaskTypeShotImage, "regenerate_shot": // 关键帧 -> 生图, or 重新生成图像
		shotId := task.ShotId
		if shotId == "" && task.Parameters.Shot != nil {
			shotId = task.Parameters.Shot.ShotId
		}
		processingErr = p.handleImageResult(shotId, taskResult)

	case models.TaskTypeProjectAudio: // 文本 -> 语音
		shotId := task.ShotId
		if shotId == "" && task.Parameters.Shot != nil {
			shotId = task.Parameters.Shot.ShotId
		}
		processingErr = p.handleTTSResult(shotId, taskResult)

	case models.TaskTypeVideoGen: // 图 -> 视频
		shotId := task.ShotId
		if shotId == "" && task.Parameters.Shot != nil {
			shotId = task.Parameters.Shot.ShotId
		}
		processingErr = p.handleVideoResult(shotId, taskResult)

	default:
		processingErr = fmt.Errorf("unknown task type: %s", task.Type)
	}

	if processingErr != nil {
		log.Printf("[Error] 数据处理失败: %v", processingErr)
		task.UpdateStatus(p.DB, models.TaskStatusFailed, taskResult, processingErr.Error())
		return nil
	}

	// 5. 成功完成
	task.UpdateStatus(p.DB, models.TaskStatusSuccess, taskResult, "")
	log.Printf("Task %s completed successfully", task.ID)
	return nil
}

// ============================================================================
// 通信层：请求分发与轮询
// ============================================================================

// dispatchWorkerRequest 发送 POST 请求，返回 job_id
// 保留switch结构以便未来根据 task.Type 构建不同请求体，目前均发送到 /v1/generate
func (p *Processor) dispatchWorkerRequest(task *models.Task) (string, error) {
	var apiPath string
	var specificParams map[string]interface{}

	switch task.Type {
	case models.TaskTypeStoryboard: // 故事 -> 分镜
		var project models.Project
		if err := p.DB.First(&project, "id = ?", task.ProjectId).Error; err != nil {
			return "", fmt.Errorf("project not found: %v", err)
		}
		params := task.Parameters.ShotDefaults
		if params == nil {
			return "", fmt.Errorf("missing shot_defaults parameters")
		}

		specificParams = map[string]interface{}{
			"shot_count": params.ShotCount,
			"style":      params.Style,
			"story_text": params.StoryText,
		}

	case models.TaskTypeShotImage, "regenerate_shot":
		// 文生图：生成关键帧
		params := task.Parameters.Shot
		if params == nil {
			return "", fmt.Errorf("missing shot parameters")
		}

		specificParams = map[string]interface{}{
			"transition":   params.Transition,
			"shot_id":      params.ShotId,
			"image_width":  params.ImageWidth,
			"image_height": params.ImageHeight,
			"prompt":       params.Prompt,
		}

	case models.TaskTypeProjectAudio:
		// TTS 生成
		params := task.Parameters.TTS
		if params == nil {
			return "", fmt.Errorf("missing tts parameters")
		}

		specificParams = map[string]interface{}{
			"voice":       params.Voice,
			"lang":        params.Lang,
			"sample_rate": params.SampleRate,
			"format":      params.Format,
		}

	case models.TaskTypeVideoGen: // 图 -> 视频
		parameters := task.Parameters.Video
		if parameters == nil {
			return "", fmt.Errorf("missing video parameters")
		}

		shot, err := models.GetShotByIDGorm(p.DB, task.ShotId)
		if err != nil {
			return "", fmt.Errorf("shot not found")
		}
		if shot.ImagePath == "" {
			return "", fmt.Errorf("shot has no image_path (unable to gen video)")
		}

		fps := 24
		if parameters.FPS != 0 {
			fps = parameters.FPS
		}

		resolution := "1280x720"
		if parameters.Resolution != "" {
			resolution = parameters.Resolution
		}

		specificParams = map[string]interface{}{
			"resolution": resolution,
			"fps":        fps,
			"format":     parameters.Format,
			"bitrate":    parameters.Bitrate,
		}

	default:
		return "", fmt.Errorf("unsupported task type: %s", task.Type)
	}

	// 发送 HTTP 请求
	reqBody := map[string]interface{}{
		"id":                 task.ID,
		"project_id":         task.ProjectId,
		"type":               task.Type,
		"status":             task.Status,
		"progress":           task.Progress,
		"message":            task.Message,
		"result":             task.Result,
		"error":              task.Error,
		"parameters":         specificParams,
		"estimated_duration": task.EstimatedDuration,
		"started_at":         task.StartedAt,
		"finished_at":        task.FinishedAt,
		"created_at":         task.CreatedAt,
		"updated_at":         task.UpdatedAt,
	}

	apiPath = "/v1/generate"
	fullURL := p.WorkerEndpoint + apiPath
	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("marshal request failed: %v", err)
	}
	log.Printf("POST %s", fullURL)

	resp, err := http.Post(fullURL, "application/json", bytes.NewBuffer(jsonBody))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusAccepted {
		return "", fmt.Errorf("worker status code: %d", resp.StatusCode)
	}

	var respData map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&respData); err != nil {
		return "", fmt.Errorf("decode response failed: %v", err)
	}

	// 优先返回根节点的 id
	if id, ok := respData["id"].(string); ok {
		return id, nil
	}
	if jobID, ok := respData["job_id"].(string); ok {
		return jobID, nil
	}
	return "", fmt.Errorf("response missing 'id'")
}

// pollJobResult 轮询 GET /v1/jobs/{job_id} 直到完成，返回 TaskResult
func (p *Processor) pollJobResult(ctx context.Context, jobID string) (*models.TaskResult, error) {
	jobURL := fmt.Sprintf("%s/v1/jobs/%s", p.WorkerEndpoint, jobID)

	timeoutDuration := 30 * time.Minute
	timeout := time.After(timeoutDuration)
	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	httpClient := &http.Client{} // 可配置 Transport/Timeout

	for {
		select {
		case <-timeout:
			return nil, fmt.Errorf("polling timeout")
		case <-ctx.Done():
			return nil, fmt.Errorf("polling canceled: %v", ctx.Err())
		case <-ticker.C:
			req, err := http.NewRequestWithContext(ctx, http.MethodGet, jobURL, nil)
			if err != nil {
				log.Printf("创建请求失败: %v", err)
				continue
			}

			resp, err := httpClient.Do(req)
			if err != nil {
				// 如果是 ctx 取消导致的 err，会在上面的 <-ctx.Done() 捕获
				log.Printf("轮询网络错误(重试中): %v", err)
				continue
			}

			// var taskResp models.Task
			// bodyBytes, err := io.ReadAll(resp.Body)
			// if err != nil {
			// 	resp.Body.Close()
			// 	log.Printf("读取响应体失败: %v", err)
			// 	continue
			// }
			// if err := json.Unmarshal(bodyBytes, &taskResp); err != nil {
			// 	bodyStr := string(bodyBytes)
			// 	if len(bodyStr) > 2000 {
			// 		bodyStr = bodyStr[:2000] + "..."
			// 	}
			// 	log.Printf("解析响应失败: %v, body: %s", err, bodyStr)
			// 	resp.Body.Close()
			// 	continue
			// }
			// resp.Body.Close()
			var taskResp models.Task
			bodyBytes, err := io.ReadAll(resp.Body)
			if err != nil {
				resp.Body.Close()
				log.Printf("读取响应体失败: %v", err)
				continue
			}
			// 改为先解到中间结构，时间字段用 *string 接收，避免直接解析到 time.Time 导致失败
			var raw struct {
				ID                string                 `json:"id"`
				ProjectId         *string                `json:"projectId"`
				ShotId            *string                `json:"shotId"`
				Type              string                 `json:"type"`
				Status            string                 `json:"status"`
				Progress          int                    `json:"progress"`
				Message           string                 `json:"message"`
				Parameters        map[string]interface{} `json:"parameters"`
				Result            models.TaskResult      `json:"result"`
				Error             string                 `json:"error"`
				EstimatedDuration int                    `json:"estimatedDuration"`
				StartedAt         *string                `json:"startedAt"`
				FinishedAt        *string                `json:"finishedAt"`
				CreatedAt         *string                `json:"createdAt"`
				UpdatedAt         *string                `json:"updatedAt"`
			}
			if err := json.Unmarshal(bodyBytes, &raw); err != nil {
				bodyStr := string(bodyBytes)
				if len(bodyStr) > 2000 {
					bodyStr = bodyStr[:2000] + "..."
				}
				log.Printf("解析响应失败: %v, body: %s", err, bodyStr)
				resp.Body.Close()
				continue
			}
			// helper: 兼容多种时间格式（带/不带时区）
			parseTime := func(s *string) time.Time {
				if s == nil || *s == "" {
					return time.Time{}
				}
				layouts := []string{time.RFC3339Nano, time.RFC3339, "2006-01-02T15:04:05.999999", "2006-01-02T15:04:05"}
				for _, l := range layouts {
					if tm, err := time.Parse(l, *s); err == nil {
						return tm
					}
				}
				return time.Time{}
			}
			// 将 raw 转回 models.Task
			taskResp = models.Task{
				ID:                raw.ID,
				ProjectId:         "",
				ShotId:            "",
				Type:              raw.Type,
				Status:            raw.Status,
				Progress:          raw.Progress,
				Message:           raw.Message,
				Parameters:        models.TaskParameters{}, // 若需要，可进一步从 raw.Parameters 解析
				Result:            raw.Result,
				Error:             raw.Error,
				EstimatedDuration: raw.EstimatedDuration,
				StartedAt:         parseTime(raw.StartedAt),
				FinishedAt:        parseTime(raw.FinishedAt),
				CreatedAt:         parseTime(raw.CreatedAt),
				UpdatedAt:         parseTime(raw.UpdatedAt),
			}
			resp.Body.Close()

			status := taskResp.Status
			if status == models.TaskStatusSuccess || status == "success" || status == "completed" || status == "succeeded" {
				return &taskResp.Result, nil
			}
			if status == models.TaskStatusFailed || status == "error" {
				return nil, fmt.Errorf("worker reported failure: %s", taskResp.Error)
			}
			// 其他状态继续轮询
		}
	}
}

func (p *Processor) handleStoryboardResult(projectID string, result *models.TaskResult) error {
	if result.ResourceUrl == "" {
		return fmt.Errorf("storyboard result missing ResourceUrl")
	}

	log.Printf("下载分镜 JSON: %s", result.ResourceUrl)
	resp, err := http.Get(result.ResourceUrl)
	if err != nil {
		return fmt.Errorf("下载分镜 JSON 失败: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("下载分镜 JSON 状态码: %d", resp.StatusCode)
	}
	var storyboardData struct {
		Shots []struct {
			Title       string `json:"title"`
			Description string `json:"description"`
			Prompt      string `json:"prompt"`
			Order       int    `json:"order,omitempty"`
			Transition  string `json:"transition,omitempty"`
		} `json:"shots"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&storyboardData); err != nil {
		return fmt.Errorf("解析分镜 JSON 失败: %v", err)
	}

	if len(storyboardData.Shots) == 0 {
		return fmt.Errorf("分镜 JSON 中没有 shots 数据")
	}

	var shotsToCreate []models.Shot
	for i, shot := range storyboardData.Shots {
		order := shot.Order
		if order == 0 {
			order = i + 1
		}

		newShot := models.Shot{
			ID:          uuid.NewString(),
			ProjectId:   projectID,
			Order:       order,
			Title:       shot.Title,
			Description: shot.Description,
			Prompt:      shot.Prompt,
			Status:      models.ShotStatusPending,
			ImagePath:   "",
			AudioPath:   "",
			Transition:  shot.Transition,
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		}
		shotsToCreate = append(shotsToCreate, newShot)
	}

	// 4. 批量插入数据库
	if len(shotsToCreate) > 0 {
		if err := models.BatchCreateShots(p.DB, shotsToCreate); err != nil {
			return fmt.Errorf("批量创建分镜失败: %v", err)
		}
	}
	log.Printf("Successfully created %d shots for project %s", len(shotsToCreate), projectID)
	return nil
}

// 处理图像生成结果 -> 更新 ImagePath
func (p *Processor) handleImageResult(shotID string, result *models.TaskResult) error {
	objectName := fmt.Sprintf("shots/%s/image.png", shotID)
	finalURL, err := processResourceToMinIO(result, objectName)
	if err != nil {
		return fmt.Errorf("处理图片资源失败: %v", err)
	}

	shot, err := models.GetShotByIDGorm(p.DB, shotID)
	if err != nil {
		return err
	}
	log.Printf("图片id %s上传成功: %s", shotID, finalURL)
	return shot.UpdateImage(p.DB, finalURL)
}

func (p *Processor) handleTTSResult(shotId string, result *models.TaskResult) error {
	objectName := fmt.Sprintf("shots/%s/audio.mp3", shotId)
	finalURL, err := processResourceToMinIO(result, objectName)
	if err != nil {
		return fmt.Errorf("处理音频资源失败: %v", err)
	}

	log.Printf("音频上传成功: %s", finalURL)
	return p.DB.Model(&models.Shot{}).Where("id = ?", shotId).Updates(map[string]interface{}{
		"audio_path": finalURL,
		"updated_at": time.Now(),
	}).Error
}

// 处理视频生成结果 -> 更新 VideoUrl
func (p *Processor) handleVideoResult(shotID string, result *models.TaskResult) error {
	objectName := fmt.Sprintf("shots/%s/video.mp4", shotID)
	finalURL, err := processResourceToMinIO(result, objectName)
	if err != nil {
		return fmt.Errorf("处理视频资源失败: %v", err)
	}

	log.Printf("视频上传成功: %s", finalURL)
	return p.DB.Model(&models.Shot{}).Where("id = ?", shotID).Updates(map[string]interface{}{
		"video_url":  finalURL,
		"status":     models.ShotStatusCompleted,
		"updated_at": time.Now(),
	}).Error
}

// processResourceToMinIO 通用资源处理函数
func processResourceToMinIO(result *models.TaskResult, objectName string) (string, error) {
	resourceUrl := result.ResourceUrl
	if resourceUrl == "" {
		return "", fmt.Errorf("resourceUrl is empty")
	}
	return downloadAndUploadToMinIO(resourceUrl, objectName)
}

func downloadAndUploadToMinIO(sourceURL, objectName string) (string, error) {
	resp, err := http.Get(sourceURL)
	if err != nil {
		return "", fmt.Errorf("download failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("download status: %d", resp.StatusCode)
	}

	return UploadToMinIO(resp.Body, objectName, resp.ContentLength)
}

// 工具函数：安全获取 string
func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}
