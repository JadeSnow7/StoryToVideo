# Model Node (Local GPU) / 模型节点

Purpose: host generation capabilities decoupled from server; accessed via HTTP (FastAPI) and optionally exposed through FRP.
目的：承载生成能力，与服务端解耦，通过 FastAPI/HTTP 暴露，必要时用 FRP 打通。

## Suggested components / 推荐组件
- LLM: Qwen2.5-0.5B via Ollama → story structure / storyboard JSON / narration draft. 文本生成分镜 JSON/旁白。
- T2I: Stable Diffusion Turbo (diffusers) → keyframes. / 关键帧生图
- I2V (optional): Stable-Video-Diffusion-Img2Vid → short clips. / 图生视频（可选）
- TTS: CosyVoice-mini → narration audio. / 旁白语音

## Minimal FastAPI skeleton (pseudo) / 最小示例
```python
from fastapi import FastAPI
app = FastAPI()

@app.post("/llm/storyboard")
async def storyboard(req: dict):
    return {"shots": [...]}

@app.post("/sd_generate")
async def sd_generate(req: dict):
    return {"url": "https://.../image.png"}
```

## GPU Dockerized model node (RTX 4060 Laptop, CUDA 12.4)
针对截图中的 Windows 11 + RTX 4060 Laptop + 最新 NVIDIA 驱动（550+），新增了一个可直接构建的 GPU 模型容器。容器默认暴露 FastAPI 模型桩服务，并附带一个 GPU 版 Ollama 服务用来拉取 Qwen2.5-0.5B。

### 1) Host prerequisites / 主机前置
- Windows 11 + WSL2 + Docker Desktop；NVIDIA 550+ 驱动（支持 CUDA 12.4）。
- 安装 `nvidia-container-toolkit`，确保 `nvidia-smi` 在 WSL 中可用：
  ```bash
  # inside WSL
  distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
  ```

### 2) Build & run / 构建与运行
```bash
cd model
# 构建 CUDA12.4 + PyTorch 2.4.0 的模型服务镜像
docker compose -f docker-compose.gpu.yml build
# 启动模型节点（FastAPI）和 GPU 版 Ollama
docker compose -f docker-compose.gpu.yml up -d
```
- FastAPI 模型桩：`http://localhost:8000`（健康检查 `/health`，业务接口 `/llm/storyboard`、`/sd_generate`、`/img2vid`、`/tts`）。详见 [完整 API 文档](./API.md)，或查看便于飞书分享的精简版接口说明 [docs/FEISHU_MODEL_API.md](../docs/FEISHU_MODEL_API.md)。
- Ollama：`http://localhost:11434`。

### 3) Pull Qwen 模型（在容器内执行）
```bash
# 进入 ollama 容器，拉取 Qwen2.5 0.5B
docker compose -f docker-compose.gpu.yml exec ollama ollama pull qwen2.5:0.5b
```

### 4) 挂载与缓存
- `./weights` 挂载到容器 `/models`，用于 HF/SD/SVD/CosyVoice 等权重缓存。
- Ollama 权重持久化到 compose 中的 `ollama` 卷，可跨重启保留。

### 5) 接入提示
- 将真实推理逻辑接到 `model/main.py` 中的 TODO（Qwen/Ollama、SD Turbo、SVD、CosyVoice）。
- 如果需要对外暴露端口到公网，复用仓库 `frp/` 下的示例配置。

### 6) 本地自动化测试
- 安装依赖（含 pytest）：`pip install -r requirements.txt`
- 运行测试：
  ```bash
  cd model
  pytest
  ```

### 7) 镜像构建后如何测试 API
容器启动后，可直接在宿主机用 `curl`/Postman/浏览器验证：

- 健康检查：
  ```bash
  curl http://localhost:8000/health
  ```
- 分镜/LLM：
  ```bash
  curl -X POST http://localhost:8000/llm/storyboard \
    -H "Content-Type: application/json" \
    -d '{"story": "夕阳下的海边散步", "style": "pixar"}'
  ```
- 文生图（Stable Diffusion Turbo 桩）：
  ```bash
  curl -X POST http://localhost:8000/sd_generate \
    -H "Content-Type: application/json" \
    -d '{"prompt": "sunset beach cinematic", "style": "anime", "width": 1024, "height": 576}'
  ```
- 图生视频（Stable Video Diffusion 桩）：
  ```bash
  curl -X POST http://localhost:8000/img2vid \
    -H "Content-Type: application/json" \
    -d '{"image_url": "https://example.com/keyframe.png", "duration_seconds": 3.0, "transition": "dissolve"}'
  ```
- 旁白 TTS（CosyVoice 桩）：
  ```bash
  curl -X POST http://localhost:8000/tts \
    -H "Content-Type: application/json" \
    -d '{"text": "欢迎使用 StoryToVideo", "voice": "female"}'
  ```

> 也可以打开 `http://localhost:8000/docs` 使用 FastAPI 提供的交互式 Swagger UI 进行可视化调试；出现错误时用 `docker compose -f docker-compose.gpu.yml logs -f model` 查看容器日志。

### 8) 将镜像推送到仓库（供前后端同学复用）
构建完成后，可将镜像推送到 Docker Hub 或 GHCR，便于前后端直接 `pull` 部署。

- **Docker Hub 示例**
  ```bash
  # 1) 构建（如果尚未构建）
  docker compose -f docker-compose.gpu.yml build

  # 2) 登录 Docker Hub
  docker login

  # 3) 打 tag 并推送（替换 yourname 为你的仓库命名空间）
  docker tag storytovideo-model-node:cuda12.4 yourname/storytovideo-model-node:cuda12.4
  docker push yourname/storytovideo-model-node:cuda12.4
  ```

- **GitHub Container Registry (GHCR) 示例**
  ```bash
  export GH_USER="your-github-username"
  echo "$GH_PAT" | docker login ghcr.io -u "$GH_USER" --password-stdin

  docker tag storytovideo-model-node:cuda12.4 ghcr.io/$GH_USER/storytovideo-model-node:cuda12.4
  docker push ghcr.io/$GH_USER/storytovideo-model-node:cuda12.4
  ```

- **前后端同学使用方法**：直接 `docker pull <registry-tag>`，或在部署 compose 中用远端镜像替换本地构建：
  ```yaml
  services:
    model-node:
      image: ghcr.io/your-namespace/storytovideo-model-node:cuda12.4
      runtime: nvidia
      ports:
        - "8000:8000"
      volumes:
        - ./weights:/models
  ```
  若需要从私有仓库拉取，请提前配置 `docker login` 或在 CI/CD 中通过密钥注入。

## Deployment / 部署
- Run on local GPU; package models separately from server. / 本地 GPU 运行，独立包模型。
- Expose ports via `frpc` to cloud `frps`. / 用 frpc 将端口暴露给公网 frps。
- Upload outputs to OSS/TOS and return URLs. / 产物上传 OSS/TOS 并返回 URL。
