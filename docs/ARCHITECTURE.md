# 技术架构设计 / Architecture

## 总体架构 / Overall

项目采用 **Client → Server → Gateway → Model** 的分层架构，默认以 **单机 Docker Compose** 方式部署（Linux + NVIDIA GPU）。
- **Client**：Qt/QML 桌面客户端（iOS 计划中）
- **Server**：Go/Gin（业务 API、任务/状态、存储编排）
- **Gateway**：FastAPI（任务编排 + ffmpeg 合成 + 静态资源服务 `/files/...`）
- **Model Node**：FastAPI（聚合 LLM/txt2img/img2vid/TTS）
- **Ollama**：运行在宿主机，由 Model Node 通过 `OLLAMA_HOST` 访问

```mermaid
graph TD
  Client[Client (Qt/QML)]
  Server[Go Server (Gin)]
  Gateway[Gateway (FastAPI)]
  Model[Model Node (FastAPI)]
  Ollama[Ollama (host)]
  MySQL[(MySQL)]
  Redis[(Redis + Asynq)]
  MinIO[(MinIO)]

  Client -->|REST/WS| Server
  Server -->|HTTP| Gateway
  Gateway -->|HTTP| Model
  Model -->|HTTP| Ollama
  Server --> MySQL
  Server --> Redis
  Server --> MinIO
```

## 数据流 / Data Flow（视频生成）
1) Client 调用 Server API 创建项目/分镜并触发生成。
2) Server 入队任务并驱动 Gateway 执行编排。
3) Gateway 调用 Model Node：LLM → txt2img → img2vid → tts → ffmpeg 合成。
4) 产物写入 `/data`（Docker 卷），由 Gateway `/files/...` 统一对外访问。
5) Server 更新任务状态并通过 WebSocket/轮询返回进度。

## 部署 / Deployment
- 编排文件：`docker-compose.yml`
- 示例环境变量：`.env.cloud.example`（复制为 `.env`）
- 部署脚本：`deploy-server.sh`
- SVD 开关：`SVD_ENABLED=0` 可关闭图生视频；Gateway 会自动降级为静态视频片段并继续流程。
