# Gateway (模型侧编排服务)

统一暴露模型侧接口，按 `type` 路由到不同子服务：

- `generate_storyboard` → LLM (`/storyboard`)
- `generate_shot`      → 文生图 (`/generate`)
- `generate_audio`     → TTS (`/narration`)
- 其他/默认 `generate_video` → 全链路：LLM → txt2img → img2vid → TTS → ffmpeg 合成，返回 MP4

主要接口
---------
- `POST /v1/api/generate`：接收 Task 结构，返回 `job_id/message/error`
- `GET  /v1/api/jobs/{job_id}`：查询任务状态（包含 progress/status 等）
- `GET  /tasks/{job_id}/stream`：SSE 实时进度
- `DELETE /v1/api/jobs/{job_id}`：取消任务
- 静态资源：`/files/...` 映射到项目 `data/` 目录（例：`data/final/foo.mp4` → `/files/final/foo.mp4`）

本地启动
--------
```bash
conda activate story2video
python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000
```
或在项目根运行 `./start.sh`（tmux），会同时拉起 gateway + 4 个子服务。

示例请求
--------
```bash
# 全链路生成（示例）
curl -s -X POST http://127.0.0.1:8000/v1/api/generate \
  -H "Content-Type: application/json" \
  -d @../docs/vi_generate_sample.json

# 查看状态
curl -s http://127.0.0.1:8000/v1/api/jobs/<job_id>
# 实时流
curl -N http://127.0.0.1:8000/tasks/<job_id>/stream
```
