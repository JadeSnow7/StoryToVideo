# SD Turbo 部署（文生图服务）

基于 `model/services/txt2img.py` 的 FastAPI 服务，默认端口 8002（单服务）或挂在聚合入口 `/txt2img/generate`。

## 启动
```bash
cd StoryToVideo
# 聚合模式（推荐）
MODEL_ROOT="$PWD" uvicorn model.main:app --host 0.0.0.0 --port 8000
# 仅文生图单服务
uvicorn model.services.txt2img:app --host 0.0.0.0 --port 8002
```

## 示例调用
```bash
curl -X POST http://localhost:8000/txt2img/generate \
  -H "Content-Type: application/json" \
  -d '{
        "prompt": "A cinematic cyberpunk street with neon lights, night, rain",
        "scene_id": "s1",
        "style": {"width": 768, "height": 512, "num_inference_steps": 4, "guidance_scale": 1.5}
      }'
```
- 输出图片会存到 `data/frames`（可通过 `OUTPUT_DIR` 覆盖）。
- 如果需要固定种子，传 `seed` 字段。

## Docker（可选）
```bash
cd StoryToVideo/model
docker compose -f docker-compose.gpu.yml up -d
# 默认暴露 http://localhost:8000/txt2img/generate
```
