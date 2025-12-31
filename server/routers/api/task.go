package api

import (
	"net/http"
	"time"

	"StoryToVideo-server/models"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

// 任务进度 WebSocket 推送（改为以数据库为来源：先读取 DB，然后循环轮询 DB 并推送）
// 外部服务轮询并写回 DB 的逻辑应由后台协程/任务执行器负责，这里只订阅并推送 DB 中的最新数据。
func TaskProgressWebSocket(c *gin.Context) {
	taskID := c.Param("task_id")
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "WebSocket升级失败"})
		return
	}
	defer conn.Close()

	// 先从 DB 读取当前任务状态并推送
	t, err := models.GetTaskByID(taskID)
	if err != nil {
		// 若任务不存在，仍可保持连接并等待任务被创建/更新，或直接返回错误
		conn.WriteJSON(map[string]interface{}{"error": "task not found: " + err.Error()})
		return
	}
	_ = conn.WriteJSON(t)

	// 轮询 DB 并推送差异（简单实现：每秒查询一次直到状态为 finished）
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()

	prevStatus := t.Status
	prevProgress := t.Progress

	for range ticker.C {
		cur, err := models.GetTaskByID(taskID)
		if err != nil {
			// 若查询失败，继续重试；也可以选择断开连接
			continue
		}

		// 若状态/进度等有变化则推送
		if cur.Status != prevStatus || cur.Progress != prevProgress {
			if err := conn.WriteJSON(cur); err != nil {
				break
			}
			prevStatus = cur.Status
			prevProgress = cur.Progress
		}

		if cur.Status == "finished" || cur.Status == "failed" {
			// 发送最终状态后关闭连接
			_ = conn.WriteJSON(cur)
			break
		}
	}
}

// 查询任务状态：GET /v1/api/tasks/:task_id
func GetTaskStatus(c *gin.Context) {
	taskID := c.Param("task_id")
	t, err := models.GetTaskByID(taskID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"task": t})
}
