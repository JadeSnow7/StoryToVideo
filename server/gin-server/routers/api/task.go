package api

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "github.com/gorilla/websocket"
    "time"
)

var upgrader = websocket.Upgrader{
    CheckOrigin: func(r *http.Request) bool {
        return true
    },
}

// 任务进度 WebSocket 推送
func TaskProgressWebSocket(c *gin.Context) {
    taskID := c.Param("task_id")
    conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "WebSocket升级失败"})
        return
    }
    defer conn.Close()

    // 示例：每秒推送一次进度
    for progress := 0; progress <= 100; progress += 10 {
        msg := map[string]interface{}{
            "task_id":  taskID,
            "progress": progress,
            "status":   "running",
            "message":  "任务进行中",
        }
        if err := conn.WriteJSON(msg); err != nil {
            break
        }
        time.Sleep(time.Second)
    }
    // 任务完成推送
    conn.WriteJSON(map[string]interface{}{
        "task_id":  taskID,
        "progress": 100,
        "status":   "finished",
        "message":  "任务已完成",
    })
}