# 部署与启动指南（单机 Docker）

## 前置条件
- OS：Linux x86_64
- Docker + `docker compose`
- NVIDIA Driver + NVIDIA Container Toolkit
- 宿主机 Ollama（默认端口 `11434`）

## 一键启动（推荐）
```bash
# 0) 宿主机启动 Ollama 并拉取模型
ollama serve
ollama pull qwen2.5:0.5b

# 1) 启动全栈
cd StoryToVideo
cp .env.cloud.example .env
./deploy-server.sh up
```

服务入口：
- Gateway：`http://127.0.0.1:8000`
- Go Server：`http://127.0.0.1:8080`
- MinIO Console：`http://127.0.0.1:9001`

## 配置说明
- 唯一编排文件：`docker-compose.yml`
- 变量覆盖：复制 `.env.cloud.example` → `.env` 并按需修改
- SVD 开关：`SVD_ENABLED=0` 关闭图生视频；网关会自动降级为静态视频片段并继续流程
- 智能降级：网关可在 img2vid 失败后对后续场景直接走 fallback（见 `.env` 中 `IMG2VID_*` 变量）

## 健康检查
```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8080/v1/api/health
```

## 单服务调试（可选）
```bash
docker compose up -d --build model
docker compose up -d --build gateway
docker compose up -d --build server
```
