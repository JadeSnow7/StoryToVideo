package service

import "remote-storyboard/models"

// WorkerRequest 是 Go 发送给 Python 的标准请求体
type WorkerRequest struct {
    TaskID     string                 `json:"task_id"`
    TaskType   string                 `json:"task_type"` // 明确告知 Worker 这是一个 story 生成还是 shot 重绘
    Payload    map[string]interface{} `json:"payload"`   // 具体的参数，如 prompt, style 等
}

// WorkerResponse 是 Python 返回给 Go 的标准响应体
type WorkerResponse struct {
    Status string         `json:"status"` // "success" or "failed"
    Result models.JSONMap `json:"result"` // 成功时的结果数据
    Error  string         `json:"error"`  // 失败时的错误信息
}

