# StoryToVideo Model Node / 模型端

一站式聚合 LLM（分镜）、文生图、图生视频、TTS 四个 FastAPI 服务。默认以单进程跑在 `uvicorn model.main:app`，也可分端口启动各子服务。

## 目录与组件
- `main.py`：聚合入口，路由前缀 `/llm` `/txt2img` `/img2vid` `/tts`。
- `services/`：各子服务实现（Ollama+Qwen、SD-Turbo、SVD-Img2Vid、CosyVoice2）。
- `scripts/`：本地启动与一键推理脚本（`run_*`、`start_services.sh`、`run_pipeline.py`）。
- `Dockerfile`、`docker-compose.gpu.yml`：CUDA 12.4 + PyTorch 2.4 镜像，附带 GPU 版 Ollama。

## 运行方式
### 1) 单进程聚合（推荐）
```bash
cd StoryToVideo
MODEL_ROOT="$PWD" uvicorn model.main:app --host 0.0.0.0 --port 8000
# 健康检查: curl http://localhost:8000/health
# 关键接口:
#   POST /llm/storyboard
#   POST /txt2img/generate
#   POST /img2vid/generate
#   POST /tts/narration
```

### 2) 分服务调试（原 8001~8004 端口）
```bash
cd StoryToVideo
./model/scripts/start_services.sh
# 或单独启动：
# ./model/scripts/run_llm.sh
# ./model/scripts/run_txt2img.sh
# ./model/scripts/run_img2vid.sh
# ./model/scripts/run_tts.sh
```

### 3) 一键端到端推理
```bash
cd StoryToVideo
./model/scripts/run_infer.sh "很久以前有只蓝色鲸鱼..." "赛博朋克风"
# run_pipeline.py 支持 --base-url/LLM_URL 等参数覆盖默认的 http://localhost:8000
```

## Docker Compose（单机部署）
```bash
cd StoryToVideo
docker compose up -d --build model
```
- 模型服务：`http://localhost:8000`（聚合路由如 `/llm/storyboard`）。
- Ollama：宿主机 `http://localhost:11434`（默认通过 `OLLAMA_HOST=http://host.docker.internal:11434` 供容器访问）。

## 环境与依赖
- 需要 CUDA 12.x GPU；`requirements.txt` 覆盖 FastAPI + diffusers + torch 等。
- CosyVoice2 需要预置 `pretrained_models/CosyVoice2-0.5B/iic/CosyVoice2-0___5B` 与 `CosyVoice` 代码（compose 已挂载目录，可通过 `MODEL_ID` 自定义路径）。
- 文生图/图生视频默认输出到容器内 `/data/frames`、`/data/clips`，TTS 输出 `/data/audio`，最终视频 `/data/final`（由 `docker-compose.yml` 统一挂载）。

## 典型集成
- 单机部署下，网关与服务端通过 Docker 网络访问 `model:8000`；模型侧通过 `OLLAMA_HOST` 调用宿主机 Ollama。
