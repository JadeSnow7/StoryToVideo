#!/usr/bin/env bash
# 一键后台启动 4 个服务：LLM / TXT2IMG / IMG2VID / TTS
# 日志输出到 logs/*.log

set -euo pipefail

ENV_NAME="story2video"
SESSION="storyvideo"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] conda 未安装或不在 PATH" >&2
  exit 1
fi

# 激活环境并配置库路径
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"
CONDA_PREFIX=$(conda info --base)/envs/$ENV_NAME
export PATH="$CONDA_PREFIX/bin:$PATH"
TORCH_LIB=$(python - <<'PY'
import torch, pathlib
print(pathlib.Path(torch.__file__).parent / 'lib')
PY
)
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$TORCH_LIB:${LD_LIBRARY_PATH:-}"

# img2vid 本地模型路径（指向 snapshot 目录）
IMG2VID_MODEL="$ROOT/pretrained_models/svd-img2vid/models--stabilityai--stable-video-diffusion-img2vid/snapshots/9cf024d5bfa8f56622af86c884f26a52f6676f2e"
export MODEL_ID="$IMG2VID_MODEL"

# 结束旧进程
pkill -f "uvicorn services.llm.main:app" 2>/dev/null || true
pkill -f "uvicorn services.txt2img.main:app" 2>/dev/null || true
pkill -f "uvicorn services.img2vid.main:app" 2>/dev/null || true
pkill -f "uvicorn services.tts.main:app" 2>/dev/null || true

# 启动服务（后台 nohup）
nohup python -m uvicorn services.llm.main:app --host 0.0.0.0 --port 8001 \
  > "$LOG_DIR/llm.log" 2>&1 &
nohup python -m uvicorn services.txt2img.main:app --host 0.0.0.0 --port 8002 \
  > "$LOG_DIR/txt2img.log" 2>&1 &
nohup python -m uvicorn services.img2vid.main:app --host 0.0.0.0 --port 8003 \
  > "$LOG_DIR/img2vid.log" 2>&1 &
nohup python -m uvicorn services.tts.main:app --host 0.0.0.0 --port 8004 \
  > "$LOG_DIR/tts.log" 2>&1 &

echo "服务已启动，日志目录：$LOG_DIR"
echo "健康检查："
echo "  curl -s http://localhost:8001/health"
echo "  curl -s http://localhost:8002/health"
echo "  curl -s http://localhost:8003/health"
echo "  curl -s http://localhost:8004/health"
