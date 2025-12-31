package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"StoryToVideo-server/config"
	"StoryToVideo-server/models"

	"github.com/go-redis/redis/v8"
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
	// 启动前清理旧任务
	if err := p.CleanupStaleTasks(); err != nil {
		log.Printf("[Warning] 清理旧任务失败: %v", err)
	}

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
	if err := srv.Start(mux); err != nil {
		log.Fatalf("could not start server: %v", err)
	}
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		sig := <-sigCh
		log.Printf("Shutting down Task Processor (signal: %s)...", sig)
		srv.Shutdown()
		os.Exit(0)
	}()
}

// CleanupStaleTasks 清理启动前遗留的任务（Redis 队列 + 数据库状态）
func (p *Processor) CleanupStaleTasks() error {
	log.Println("正在清理遗留任务...")

	// 1. 清理 Redis 队列中的任务
	if err := p.flushRedisQueues(); err != nil {
		log.Printf("[Warning] 清理 Redis 队列失败: %v", err)
	}

	// 2. 将数据库中 pending/processing 的任务标记为 cancelled
	result := p.DB.Model(&models.Task{}).
		Where("status IN ?", []string{models.TaskStatusPending, models.TaskStatusProcessing}).
		Updates(map[string]interface{}{
			"status":      models.TaskStatusCancelled,
			"error":       "服务重启，任务已取消",
			"finished_at": time.Now(),
			"updated_at":  time.Now(),
		})

	if result.Error != nil {
		return fmt.Errorf("更新数据库任务状态失败: %v", result.Error)
	}

	log.Printf("已取消 %d 个遗留任务", result.RowsAffected)
	return nil
}

// flushRedisQueues 清空 Asynq 使用的 Redis 队列
func (p *Processor) flushRedisQueues() error {
	ctx := context.Background()

	rdb := redis.NewClient(&redis.Options{
		Addr:     config.AppConfig.Redis.Addr,
		Password: config.AppConfig.Redis.Password,
		DB:       0,
	})
	defer rdb.Close()

	// Asynq 使用的队列 key 模式
	// 参考: https://github.com/hibiken/asynq/wiki/Queue-Names
	queueKeys := []string{
		"asynq:{default}:pending",
		"asynq:{default}:active",
		"asynq:{default}:scheduled",
		"asynq:{default}:retry",
		"asynq:{default}:archived",
		"asynq:{default}:completed",
	}

	for _, key := range queueKeys {
		deleted, err := rdb.Del(ctx, key).Result()
		if err != nil {
			log.Printf("[Warning] 删除 %s 失败: %v", key, err)
		} else if deleted > 0 {
			log.Printf("已清理队列: %s", key)
		}
	}

	// 清理任务详情（可选，如果需要完全清理）
	// 这会删除所有以 asynq: 开头的 key
	iter := rdb.Scan(ctx, 0, "asynq:*", 0).Iterator()
	for iter.Next(ctx) {
		if err := rdb.Del(ctx, iter.Val()).Err(); err != nil {
			log.Printf("[Warning] 删除 %s 失败: %v", iter.Val(), err)
		}
	}

	return iter.Err()
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

	taskResult, err := p.pollJobResult(pollCtx, jobID, task.ID)
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
		processingErr = p.handleImageResult(shotId, task.ID, taskResult)

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
		processingErr = p.handleVideoResult(shotId, task.ProjectId, task.ID, taskResult)

	default:
		processingErr = fmt.Errorf("unknown task type: %s", task.Type)
	}

	if processingErr != nil {
		log.Printf("[Error] 数据处理失败: %v", processingErr)
		task.UpdateStatus(p.DB, models.TaskStatusFailed, taskResult, processingErr.Error())
		return nil
	}
	// 新增：解锁依赖此任务的 blocked 任务并尝试入队
	p.unlockDependentTasks(task.ID, task.ProjectId)

	// 5. 成功完成
	task.UpdateStatus(p.DB, models.TaskStatusSuccess, taskResult, "")
	log.Printf("Task %s completed successfully", task.ID)
	return nil
	// 5. 成功完成
	// task.UpdateStatus(p.DB, models.TaskStatusSuccess, taskResult, "")
	// log.Printf("Task %s completed successfully", task.ID)
	// return nil
}
func (p *Processor) unlockDependentTasks(completedTaskID, projectID string) {
	rows, err := models.DB.Query(`SELECT id, parameters FROM task WHERE project_id = ? AND status = ?`, projectID, models.TaskStatusBlocked)
	if err != nil {
		log.Printf("unlockDependentTasks: query blocked tasks failed: %v", err)
		return
	}
	defer rows.Close()

	for rows.Next() {
		var tid string
		var paramsBytes []byte
		if err := rows.Scan(&tid, &paramsBytes); err != nil {
			continue
		}

		var tp models.TaskParameters
		if len(paramsBytes) > 0 {
			_ = json.Unmarshal(paramsBytes, &tp)
		}
		if tp.DependsOn == nil || len(tp.DependsOn) == 0 {
			continue
		}

		// 检查 completedTaskID 是否在 depends_on 中
		contains := false
		for _, d := range tp.DependsOn {
			if d == completedTaskID {
				contains = true
				break
			}
		}
		if !contains {
			continue
		}

		// 从 depends_on 中移除 completedTaskID
		newDeps := make([]string, 0, len(tp.DependsOn))
		for _, d := range tp.DependsOn {
			if d != completedTaskID {
				newDeps = append(newDeps, d)
			}
		}
		tp.DependsOn = newDeps

		// 序列化回 parameters
		newParams, _ := json.Marshal(tp)

		if len(newDeps) == 0 {
			// 所有依赖已满足：置为 pending 并入队
			if _, err := models.DB.Exec(`UPDATE task SET parameters = ?, status = ?, updated_at = ? WHERE id = ?`, newParams, models.TaskStatusPending, time.Now(), tid); err != nil {
				log.Printf("unlockDependentTasks: update task %s -> pending failed: %v", tid, err)
				continue
			}
			log.Printf("unlockDependentTasks: task %s unlocked -> pending; enqueueing", tid)
			if err := EnqueueTask(tid); err != nil {
				log.Printf("unlockDependentTasks: enqueue task %s failed: %v", tid, err)
			}
		} else {
			// 仍有未满足的依赖，更新 parameters 并保持 blocked
			if _, err := models.DB.Exec(`UPDATE task SET parameters = ?, updated_at = ? WHERE id = ?`, newParams, time.Now(), tid); err != nil {
				log.Printf("unlockDependentTasks: update task %s parameters failed: %v", tid, err)
				continue
			}
			log.Printf("unlockDependentTasks: task %s still blocked (remaining deps: %d)", tid, len(newDeps))
		}
	}
}

// ============================================================================
// 通信层：请求分发与轮询
// ============================================================================

// dispatchWorkerRequest 发送 POST 请求，返回 job_id
// 保留switch结构以便未来根据 task.Type 构建不同请求体，目前均发送到 /v1/generate
func (p *Processor) dispatchWorkerRequest(task *models.Task) (string, error) {
	var apiPath string
	// var specificParams map[string]interface{}

	// switch task.Type {
	// case models.TaskTypeStoryboard: // 故事 -> 分镜
	// 	var project models.Project
	// 	if err := p.DB.First(&project, "id = ?", task.ProjectId).Error; err != nil {
	// 		return "", fmt.Errorf("project not found: %v", err)
	// 	}
	// 	params := task.Parameters.ShotDefaults
	// 	if params == nil {
	// 		return "", fmt.Errorf("missing shot_defaults parameters")
	// 	}

	// 	specificParams = map[string]interface{}{
	// 		"shot_count": params.ShotCount,
	// 		"style":      params.Style,
	// 		"story_text": params.StoryText,
	// 	}

	// case models.TaskTypeShotImage, "regenerate_shot":
	// 	// 文生图：生成关键帧
	// 	params := task.Parameters.Shot
	// 	if params == nil {
	// 		return "", fmt.Errorf("missing shot parameters")
	// 	}

	// 	specificParams = map[string]interface{}{
	// 		"transition":   params.Transition,
	// 		"shot_id":      params.ShotId,
	// 		"image_width":  params.ImageWidth,
	// 		"image_height": params.ImageHeight,
	// 		"prompt":       params.Prompt,
	// 	}

	// case models.TaskTypeProjectAudio:
	// 	// TTS 生成
	// 	params := task.Parameters.TTS
	// 	if params == nil {
	// 		return "", fmt.Errorf("missing tts parameters")
	// 	}

	// 	specificParams = map[string]interface{}{
	// 		"voice":       params.Voice,
	// 		"lang":        params.Lang,
	// 		"sample_rate": params.SampleRate,
	// 		"format":      params.Format,
	// 	}

	// case models.TaskTypeVideoGen: // 图 -> 视频
	// 	parameters := task.Parameters.Video
	// 	if parameters == nil {
	// 		return "", fmt.Errorf("missing video parameters")
	// 	}

	// 	shot, err := models.GetShotByIDGorm(p.DB, task.ShotId)
	// 	if err != nil {
	// 		return "", fmt.Errorf("shot not found")
	// 	}
	// 	if shot.ImagePath == "" {
	// 		return "", fmt.Errorf("shot has no image_path (unable to gen video)")
	// 	}

	// 	fps := 24
	// 	if parameters.FPS != 0 {
	// 		fps = parameters.FPS
	// 	}

	// 	resolution := "1280x720"
	// 	if parameters.Resolution != "" {
	// 		resolution = parameters.Resolution
	// 	}

	// 	specificParams = map[string]interface{}{
	// 		"resolution": resolution,
	// 		"fps":        fps,
	// 		"format":     parameters.Format,
	// 		"bitrate":    parameters.Bitrate,
	// 	}

	// default:
	// 	return "", fmt.Errorf("unsupported task type: %s", task.Type)
	// }

	specificParams := make(map[string]interface{})

	if task.Parameters.ShotDefaults != nil {
		specificParams["shot_defaults"] = task.Parameters.ShotDefaults
	}
	if task.Parameters.Shot != nil {
		specificParams["shot"] = task.Parameters.Shot
	}
	if task.Parameters.TTS != nil {
		specificParams["tts"] = task.Parameters.TTS
	}
	if task.Parameters.Video != nil {
		specificParams["video"] = task.Parameters.Video
	}
	// 添加其他需要的参数，如 depends_on
	if len(task.Parameters.DependsOn) > 0 {
		specificParams["depends_on"] = task.Parameters.DependsOn
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
	fullURL := p.WorkerEndpoint + apiPath //
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
func (p *Processor) pollJobResult(ctx context.Context, jobID string, taskID string) (*models.TaskResult, error) {
	jobURL := fmt.Sprintf("%s/v1/jobs/%s", p.WorkerEndpoint, jobID)

	timeoutDuration := 30 * time.Minute
	timeout := time.After(timeoutDuration)
	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	httpClient := &http.Client{} // 可配置 Transport/Timeout
	lastProgress := -1
	lastMessage := ""

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

			if taskID != "" && (taskResp.Progress != lastProgress || taskResp.Message != lastMessage) {
				lastProgress = taskResp.Progress
				lastMessage = taskResp.Message
				progress := taskResp.Progress
				if progress < 0 {
					progress = 0
				} else if progress > 100 {
					progress = 100
				}
				var messagePtr *string
				if taskResp.Message != "" {
					message := taskResp.Message
					messagePtr = &message
				}
				if err := models.UpdateTaskStatus(
					taskID,
					models.TaskStatusProcessing,
					&progress,
					messagePtr,
					nil,
					nil,
					nil,
					nil,
				); err != nil {
					log.Printf("更新任务进度失败: %v", err)
				}
			}

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
	var shotsToCreate []models.Shot
	if result.ResourceUrl != "" {
		log.Printf("下载分镜 JSON: %s", result.ResourceUrl)
		resp, err := http.Get(p.WorkerEndpoint + result.ResourceUrl) // /data
		if err != nil {
			return fmt.Errorf("下载分镜 JSON 失败: %v", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return fmt.Errorf("下载分镜 JSON 状态码: %d", resp.StatusCode)
		}
		var storyboardItems []struct {
			SceneId   string  `json:"scene_id"`
			Title     string  `json:"title"`
			Prompt    string  `json:"prompt"`
			Narration string  `json:"narration"`
			Bgm       *string `json:"bgm"`
			Path      string  `json:"path,omitempty"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&storyboardItems); err != nil {
			return fmt.Errorf("解析分镜 JSON 失败: %v", err)
		}
		if len(storyboardItems) == 0 {
			return fmt.Errorf("分镜 JSON 中没有 shots 数据")
		}
		// 将 storyboardItems 内容记录到日志（JSON 格式，超长时截断）
		if b, err := json.MarshalIndent(storyboardItems, "", "  "); err == nil {
			s := string(b)
			const maxLog = 2000
			if len(s) > maxLog {
				s = s[:maxLog] + "...(truncated)"
			}
			log.Printf("storyboardItems (%d): %s", len(storyboardItems), s)
		} else {
			log.Printf("无法序列化 storyboardItems: %v", err)
		}
		for i, shot := range storyboardItems {
			order := i + 1
			var audioPath string
			if shot.Bgm != nil && *shot.Bgm != "" {
				audioPath = *shot.Bgm
			}
			newShot := models.Shot{
				ID:          uuid.NewString(),
				ProjectId:   projectID,
				Order:       order,
				Title:       shot.Title,
				Description: shot.Narration,
				Prompt:      shot.Prompt,
				Status:      models.ShotStatusPending,
				ImagePath:   shot.Path,
				AudioPath:   audioPath,
				Transition:  "",
				CreatedAt:   time.Now(),
				UpdatedAt:   time.Now(),
			}
			shotsToCreate = append(shotsToCreate, newShot)
		}
	} else if result.TaskShots != nil && len(result.TaskShots.GeneratedShots) > 0 {
		// 备选：从 task_shots.generated_shots 直接读取
		log.Printf("从 task_shots 解析分镜数据，共 %d 个", len(result.TaskShots.GeneratedShots))

		for i, shot := range result.TaskShots.GeneratedShots {
			order := i + 1
			newShot := models.Shot{
				ID:          uuid.NewString(),
				ProjectId:   projectID,
				Order:       order,
				Title:       shot.Title,
				Description: shot.Narration, // 使用 narration 作为描述
				Prompt:      shot.Prompt,
				Status:      models.ShotStatusPending,
				ImagePath:   shot.Path,
				AudioPath:   "",
				Transition:  "",
				CreatedAt:   time.Now(),
				UpdatedAt:   time.Now(),
			}
			shotsToCreate = append(shotsToCreate, newShot)
		}
	} else {
		return fmt.Errorf("分镜结果为空: resource_url 和 task_shots 均无有效数据")
	}
	// 批量插入数据库
	if len(shotsToCreate) > 0 {
		if err := models.BatchCreateShots(p.DB, shotsToCreate); err != nil {
			return fmt.Errorf("批量创建分镜失败: %v", err)
		}
	}
	log.Printf("[handleStoryboardResult] Worker 返回了 %d 个分镜", len(shotsToCreate))

	log.Printf("Successfully created %d shots for project %s", len(shotsToCreate), projectID)

	var blockedTasks []models.Task
	if err := p.DB.Where("project_id = ? AND type = ? AND status = ?",
		projectID, models.TaskTypeShotImage, models.TaskStatusBlocked).
		Order("created_at ASC").
		Find(&blockedTasks).Error; err != nil {
		return fmt.Errorf("查询阻塞任务失败: %v", err)
	}
	log.Printf("[handleStoryboardResult] 预创建了 %d 个 blocked 任务", len(blockedTasks))
	// 将 blocked 任务与 shot 一一配对
	for i, blockedTask := range blockedTasks {
		if i >= len(shotsToCreate) {
			// 如果预创建的任务比实际生成的 shot 多，删除多余任务
			log.Printf("删除多余的 blocked 任务: %s", blockedTask.ID)
			p.DB.Delete(&blockedTask)
			continue
		}

		shot := shotsToCreate[i]

		// 更新任务：填充 ShotId 和 Prompt
		updates := map[string]interface{}{
			"shot_id":    shot.ID,
			"status":     models.TaskStatusPending,
			"message":    "分镜已生成，准备生成图片",
			"updated_at": time.Now(),
		}

		// 更新 parameters 中的 shot 信息
		blockedTask.Parameters.Shot = &models.ShotParams{
			ShotId:      shot.ID,
			Prompt:      shot.Prompt,
			ImageWidth:  blockedTask.Parameters.Shot.ImageWidth,  // 保留原有设置
			ImageHeight: blockedTask.Parameters.Shot.ImageHeight, // 保留原有设置
		}

		// 序列化 parameters
		paramsBytes, err := json.Marshal(blockedTask.Parameters)
		if err != nil {
			log.Printf("序列化 parameters 失败: %v", err)
			continue
		}
		updates["parameters"] = string(paramsBytes)

		if err := p.DB.Model(&models.Task{}).Where("id = ?", blockedTask.ID).Updates(updates).Error; err != nil {
			log.Printf("更新任务 %s 失败: %v", blockedTask.ID, err)
			continue
		}

		// 入队执行
		if err := EnqueueTask(blockedTask.ID); err != nil {
			log.Printf("任务 %s 入队失败: %v", blockedTask.ID, err)
		} else {
			log.Printf("任务 %s 已解锁并入队，关联 Shot: %s", blockedTask.ID, shot.ID)
		}
	}

	// 如果实际生成的 shot 比预创建的任务多，创建新任务
	if len(shotsToCreate) > len(blockedTasks) {
		for i := len(blockedTasks); i < len(shotsToCreate); i++ {
			shot := shotsToCreate[i]
			newTask := models.Task{
				ID:        uuid.NewString(),
				ProjectId: projectID,
				ShotId:    shot.ID,
				Type:      models.TaskTypeShotImage,
				Status:    models.TaskStatusPending,
				Progress:  0,
				Message:   "分镜已生成，准备生成图片",
				Parameters: models.TaskParameters{
					Shot: &models.ShotParams{
						ShotId:      shot.ID,
						Prompt:      shot.Prompt,
						ImageWidth:  "1024",
						ImageHeight: "1024",
					},
				},
				CreatedAt: time.Now(),
				UpdatedAt: time.Now(),
			}

			if err := models.CreateTask(&newTask); err != nil {
				log.Printf("创建额外生图任务失败: %v", err)
				continue
			}

			if err := EnqueueTask(newTask.ID); err != nil {
				log.Printf("额外任务 %s 入队失败: %v", newTask.ID, err)
			} else {
				log.Printf("创建并入队额外任务 %s，关联 Shot: %s", newTask.ID, shot.ID)
			}
		}
	}

	return nil
}

// 处理图像生成结果 -> 更新 ImagePath
// taskID 用于版本化 MinIO 对象名，便于追踪和避免缓存问题
func (p *Processor) handleImageResult(shotID string, taskID string, result *models.TaskResult) error {
	shotID = strings.TrimSpace(shotID)
	// ==== 新增：基本校验与净化 ====
	if shotID == "" {
		return fmt.Errorf("missing shot id for image task")
	}
	// 替换可能的路径分隔符/非法片段，防止把完整路径或 URL 当作对象名段
	shotID = strings.ReplaceAll(shotID, "/", "-")
	shotID = strings.ReplaceAll(shotID, "\\", "-")
	// 去除首尾空白后的再次检查
	if shotID == "" {
		return fmt.Errorf("invalid shot id after sanitization")
	}
	// ==== 校验结束 ====
	var finalURL string
	var err error

	// 优先从 resource_url 获取
	if result.ResourceUrl != "" {
		objectName := fmt.Sprintf("shots/%s/image_%s.png", shotID, taskID)
		finalURL, err = processResourceToMinIO(result, objectName)
		if err != nil {
			return fmt.Errorf("处理图片资源失败: %v", err)
		}
	} else {
		// 备选：从 task_shots 获取路径
		var remotePath string
		if result.TaskShots != nil && len(result.TaskShots.GeneratedShots) > 0 {
			remotePath = result.TaskShots.GeneratedShots[0].Path
		}

		if remotePath == "" {
			return fmt.Errorf("图片路径为空: resource_url 和 task_shots.path 均无有效数据")
		}
		downloadUrl := p.getWorkerFileUrl(remotePath)
		log.Printf("正在从 Worker 下载图片: %s", downloadUrl)

		objectName := fmt.Sprintf("shots/%s/image_%s.png", shotID, taskID)
		finalURL, err = downloadAndUploadToMinIO(downloadUrl, objectName)
		if err != nil {
			return fmt.Errorf("处理图片失败 (下载URL: %s): %v", downloadUrl, err)
		}
	}

	result.ResourceUrl = finalURL
	shot, err := models.GetShotByIDGorm(p.DB, shotID)
	if err != nil {
		return err
	}
	shot.ImagePath = finalURL
	if err := p.DB.Save(shot).Error; err != nil {
		return fmt.Errorf("更新 shot 图片路径失败: %v", err)
	}

	log.Printf("图片 %s 上传成功: %s", shotID, finalURL)
	if result != nil {
		result.ResourceUrl = finalURL
		result.ResourceType = "image"
	}
	return shot.UpdateImage(p.DB, finalURL)
}

func (p *Processor) handleTTSResult(shotId string, result *models.TaskResult) error {
	shotId = strings.TrimSpace(shotId)
	// ==== 新增：基本校验与净化 ====
	if shotId == "" {
		return fmt.Errorf("missing shot id for image task")
	}
	// 替换可能的路径分隔符/非法片段，防止把完整路径或 URL 当作对象名段
	shotId = strings.ReplaceAll(shotId, "/", "-")
	shotId = strings.ReplaceAll(shotId, "\\", "-")
	// 去除首尾空白后的再次检查
	if shotId == "" {
		return fmt.Errorf("invalid shot id after sanitization")
	}
	objectName := fmt.Sprintf("shots/%s/audio.mp3", shotId)
	finalURL, err := processResourceToMinIO(result, objectName)
	if err != nil {
		return fmt.Errorf("处理音频资源失败: %v", err)
	}

	log.Printf("音频上传成功: %s", finalURL)
	result.ResourceUrl = finalURL
	return p.DB.Model(&models.Shot{}).Where("id = ?", shotId).Updates(map[string]interface{}{
		"audio_path": finalURL,
		"updated_at": time.Now(),
	}).Error
}

// 处理视频生成结果 -> 更新 VideoUrl
func (p *Processor) handleVideoResult(shotID string, projectID string, taskID string, result *models.TaskResult) error {
	var finalURL string
	var err error
	shotID = strings.TrimSpace(shotID)
	if shotID == "" {
		projectID = strings.TrimSpace(projectID)
		if projectID == "" {
			return fmt.Errorf("missing project id for video task")
		}
		// Project-level video
		if result.ResourceUrl != "" {
			objectName := fmt.Sprintf("projects/%s/video_%s.mp4", projectID, taskID)
			finalURL, err = processResourceToMinIO(result, objectName)
			if err != nil {
				return fmt.Errorf("处理视频资源失败: %v", err)
			}
		} else if result.TaskVideo != nil && result.TaskVideo.Path != "" {
			downloadUrl := p.getWorkerFileUrl(result.TaskVideo.Path)
			log.Printf("正在从 Worker 下载视频: %s", downloadUrl)
			objectName := fmt.Sprintf("projects/%s/video_%s.mp4", projectID, taskID)
			finalURL, err = downloadAndUploadToMinIO(downloadUrl, objectName)
			if err != nil {
				return fmt.Errorf("处理视频失败: %v", err)
			}
		} else {
			return fmt.Errorf("视频路径为空: resource_url 和 task_video.path 均无有效数据")
		}
		result.ResourceUrl = finalURL
		log.Printf("项目视频上传成功: %s", finalURL)
		return p.DB.Model(&models.Project{}).Where("id = ?", projectID).Updates(map[string]interface{}{
			"video_url":  finalURL,
			"status":     models.ProjectStatusVideoGenerated,
			"updated_at": time.Now(),
		}).Error
	}
	// 替换可能的路径分隔符/非法片段，防止把完整路径或 URL 当作对象名段
	shotID = strings.ReplaceAll(shotID, "/", "-")
	shotID = strings.ReplaceAll(shotID, "\\", "-")
	// 去除首尾空白后的再次检查
	if shotID == "" {
		return fmt.Errorf("invalid shot id after sanitization")
	}
	// 优先从 resource_url 获取
	if result.ResourceUrl != "" {
		objectName := fmt.Sprintf("shots/%s/video.mp4", shotID)
		finalURL, err = processResourceToMinIO(result, objectName)
		if err != nil {
			return fmt.Errorf("处理视频资源失败: %v", err)
		}
	} else if result.TaskVideo != nil && result.TaskVideo.Path != "" {
		// 备选：从 task_video 获取路径
		downloadUrl := p.getWorkerFileUrl(result.TaskVideo.Path)
		log.Printf("正在从 Worker 下载视频: %s", downloadUrl)

		objectName := fmt.Sprintf("shots/%s/video.mp4", shotID)
		finalURL, err = downloadAndUploadToMinIO(downloadUrl, objectName)
		if err != nil {
			return fmt.Errorf("处理视频失败: %v", err)
		}
	} else {
		return fmt.Errorf("视频路径为空: resource_url 和 task_video.path 均无有效数据")
	}
	result.ResourceUrl = finalURL
	log.Printf("视频上传成功: %s", finalURL)
	return p.DB.Model(&models.Shot{}).Where("id = ?", shotID).Updates(map[string]interface{}{
		"video_url":  finalURL,
		"status":     models.ShotStatusCompleted,
		"updated_at": time.Now(),
	}).Error
}

func (p *Processor) getWorkerFileUrl(filePath string) string {
	// 方案 A: 假设 Worker 提供了一个通用的下载 API
	// 例如: http://worker-frp-addr/v1/download?path=/home/stv/...
	baseUrl := p.WorkerEndpoint // config.yaml 中的 worker地址

	// 如果是相对路径 (data/final/...)，可能需要拼接
	// 如果是绝对路径 (/home/stv/...)，直接传给 API

	// 这里使用 QueryEscape 处理路径中的特殊字符
	return fmt.Sprintf("%s/v1/download?path=%s", baseUrl, url.QueryEscape(filePath))

	// 方案 B: 如果 Worker 只是简单的静态文件服务 (例如 python -m http.server)
	// return fmt.Sprintf("%s/%s", baseUrl, filePath)
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
	resp, err := http.Get(config.AppConfig.Worker.Addr + sourceURL)
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
