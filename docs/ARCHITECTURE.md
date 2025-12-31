# 技术架构设计 / Architecture

## 总体架构 / Overall
Client-Server-Worker 三层，FRP 连接本地模型。 / Three-tier with FRP to local models.
```
graph TD
    subgraph Client [PC 客户端 (Qt/QML)]
        UI[QML UI]
        NET[Network Manager]
        VM[ViewModel]
        STORE[SQLite/File Cache]
        PLAYER[FFmpeg Player]
    end

    subgraph Cloud [Server (Django/Gin)]
        API[API Gateway]
        AUTH[Auth]
        TASK[Task Queue]
        DB[(PostgreSQL)]
        OSS[Object Storage]
    end

    subgraph Local [Local Model Node]
        FRPC[FRP Client]
        FASTAPI[Model API]
        LLM[Qwen]
        SD[SD Turbo]
        TTS[CosyVoice]
        SVD[SVD Img2Vid]
    end

    UI --> NET
    NET -- REST/WS --> API
    API --> DB
    API --> TASK
    TASK -- FRP Tunnel --> FRPC
    FRPC --> FASTAPI
    FASTAPI --> LLM & SD & TTS & SVD
    FASTAPI -- Upload --> OSS
    OSS -- CDN URL --> UI
```

## 客户端模块 / Client
- UI：Qt QML 5 页（Assets/Create/Storyboard/Shot Detail/Preview）。 / Five pages in QML.
- 网络：QNetworkAccessManager + WebSocket；任务状态轮询兜底。 / REST+WS with poll fallback.
- 状态：ViewModel 单向数据流；状态枚举 PENDING/RUNNING/SUCCESS/FAILED。 / Unidirectional state + enums.
- 媒体：FFmpeg + OpenGL 播放、合成、截图；导出 MP4。 / FFmpeg/OpenGL playback/export.
- 存储：SQLite + QFile 缓存项目/图片/视频；离线可读。 / SQLite + file cache, offline readable.

## 服务端模块 / Server
- 网关：Django/DRF 或 Gin；鉴权、速率、日志。 / Gateway with auth/rate/logging.
- 任务：Celery/RQ/Arq；超时/重试；Webhook 回调。 / Task queue with timeout/retry/webhook.
- 存储：PostgreSQL/MySQL；OSS/TOS 资源。 / DB + object storage.
- 部署：Nginx+Gunicorn；ALLOWED_HOSTS 配置；静态资源收集。 / Deployed behind Nginx/Gunicorn.

## 模型节点 / Model node
- FastAPI 包装模型 HTTP/RPC： / FastAPI wrapping models:
  - LLM：Qwen2.5-0.5B (Ollama) → 分镜 JSON/Narration。 / storyboard JSON.
  - T2I：SD Turbo (diffusers) → 关键帧图。 / keyframes.
  - I2V：SVD Img2Vid（可选）。 / optional img2vid.
  - TTS：CosyVoice-mini → 旁白音频。 / narration audio.
- FRP：公网 frps + 本地 frpc 暴露端口。 / Expose ports via FRP.

## 数据流示例（生成分镜图片） / Example flow (shot image)
1) 客户端 POST `/api/story/{id}/shot/{shot_id}/generate`。 / Client hits generate.
2) 服务端创建 Task=PENDING，推入队列。 / Server enqueues task.
3) Worker 经 FRP 调用本地模型 `POST /sd_generate`。 / Worker calls local model via FRP.
4) 本地生成图片并上传 OSS，获得 URL。 / Local uploads to OSS, gets URL.
5) 本地回调 `/api/webhook/task_complete`，状态 SUCCESS，写 URL。 / Callback updates status+URL.
6) 服务端通过 WS 推送；客户端刷新图像。 / WS notify client.

## API 草案 / API draft
- POST `/api/projects/create`
- GET `/api/projects/{id}/storyboard`
- POST `/api/shots/{id}/update_prompt`
- POST `/api/shots/{id}/generate_image`
- POST `/api/shots/{id}/generate_video` (可选 / optional)
- GET `/api/tasks/{task_id}/status`
- POST `/api/webhook/task_complete`

## 数据模型 / Data models
- Project(id,title,style,created_at)
- Shot(id,project_id,order,prompt,narration,image_url,status,video_url)
- Task(id,type,payload,status,result_data,err_msg)

## 部署建议 / Deployment
- Server：字节云 ECS；Ubuntu 22.04；Python 3.10+；Nginx+Gunicorn；PostgreSQL/MySQL；对象存储 TOS。 / Cloud ECS with Django stack.
- 模型：本地 GPU；FastAPI；通过 FRP 暴露；与 Server 解耦。 / Local GPU FastAPI exposed via FRP, decoupled.
