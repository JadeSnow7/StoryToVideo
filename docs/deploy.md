# 部署与启动指南（本地/内网环境）

## 环境要求
- OS：Linux x86_64。
- Python：3.10/3.11。
- CUDA：12.x；显卡建议 >=24GB 显存，SD Turbo + SVD 更稳。
- 依赖工具：git、ffmpeg、Ollama、FRP（frpc）、uvicorn/FastAPI、pip/uv/poetry。
- 可选性能优化：`xformers`、`flash-attn`。

## 目录布局（示例）
```
workspace/
  docs/
  gateway/
  services/
    llm/
    txt2img/
    img2vid/
    tts/
  data/
    storyboards/ frames/ clips/ audio/ final/
  scripts/
  docker/
```

## 依赖安装（示例命令）
```bash
# 1) Python 环境
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 安装通用依赖（待补充 requirements.txt）
pip install fastapi uvicorn[standard] pydantic[dotenv] pillow tqdm
pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121
pip install diffusers transformers accelerate safetensors xformers
pip install soundfile ffmpeg-python
```

## 模型下载与启动
### LLM：Qwen2.5-0.5B @ Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:0.5b
# 启动 ollama 服务（默认 11434）
ollama serve
# llm-service 可用 FastAPI 包装调用 ollama API（/api/chat）
```

### 文生图：Stable Diffusion Turbo @ diffusers
```bash
# 在 services/txt2img/ 下编写启动脚本，示例依赖：
pip install "git+https://github.com/huggingface/diffusers.git"
# 运行示例（伪命令，实际脚本需另写）
python services/txt2img/main.py --model "stabilityai/sd-turbo" --device cuda:0
```

### 图生视频：Stable-Video-Diffusion-Img2Vid @ diffusers
```bash
pip install opencv-python
python services/img2vid/main.py --model "stabilityai/stable-video-diffusion-img2vid" --device cuda:0
```

### TTS：CosyVoice-mini
```bash
# 需准备 cosyvoice 模型文件，可在启动脚本中自动下载
pip install modelscope
python services/tts/main.py --model cosyvoice-mini --device cuda:0
```

## 网关与编排
```bash
# 启动 FastAPI 网关
uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```
- 网关负责：路由转发、任务状态、序列化请求、ffmpeg 合成。
- ffmpeg 合成示例（编排层执行）：
```bash
ffmpeg -y -i clips_list.txt -filter_complex "[0:v]concat=n=6:v=1:a=0" -an /data/final/final.mp4
# 叠加旁白
ffmpeg -y -i /data/final/final.mp4 -i /data/audio/merged.wav -shortest -c:v copy -c:a aac /data/final/final_mix.mp4
```

## FRP 对接（暴露网关）
1) 准备 `frpc.ini`：
```
[common]
server_addr = <frps_host>
server_port = 7000
token = <token>

[story-gateway]
type = tcp
local_ip = 127.0.0.1
local_port = 8000
remote_port = 18000
```
2) 启动：`frpc -c frpc.ini`
3) 对外访问：`http://<frps_host>:18000/` → 网关 API。

## Docker/容器（可选）
- 为每个服务提供单独 Dockerfile；使用 Compose 编排 GPU（`runtime: nvidia` 或 `--gpus all`）。
- Compose 关键点：挂载 `./data`、暴露网关 8000、内部网络互联、指定 `NVIDIA_VISIBLE_DEVICES`。

## 首次联调步骤（建议）
1) 单测各服务：llm-service 出分镜；txt2img 出 1~2 张图；img2vid 将图转 1 秒短片；tts 输出 1 条音频。
2) 网关串联 `/render`，跑 1~2 场景小样本，确认状态流转与路径正确。
3) 配置 FRP 暴露网关，使用 curl 或前端脚本远程调用验证。
4) 根据显存与速度调参：降低分辨率/步数/帧率，或改为多卡分配。
