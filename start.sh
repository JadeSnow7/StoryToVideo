#!/bin/bash
SESSION="storyvideo"

# 启动环境
ENV_NAME="story2video"
CONDA_PREFIX=$(conda info --base)/envs/$ENV_NAME
export PATH="$CONDA_PREFIX/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export MODEL_ROOT="$SCRIPT_DIR"
# 计算 torch 库路径，避免 here-doc 结束符误解析
TORCH_LIB=$(python - <<'PY'
import torch, pathlib
print(pathlib.Path(torch.__file__).parent / 'lib')
PY
)
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$TORCH_LIB:${LD_LIBRARY_PATH:-}"
# 统一数据路径配置
export DATA_DIR="$SCRIPT_DIR/data"
export STATIC_ROOT="$DATA_DIR"
export OUTPUT_DIR="$DATA_DIR/frames"       # txt2img 输出
export FINAL_DIR="$DATA_DIR/final"         # gateway/video 输出
export CLIPS_DIR="$DATA_DIR/clips"         # gateway/clips 输出
export AUDIO_DIR="$DATA_DIR/audio"         # tts 输出
export STORYBOARD_DIR="$DATA_DIR/storyboard"

# Performance Tuning
export SVD_STEPS=4
export SVD_MAX_FRAMES=10
export IMG2VID_MAX_FRAMES=10

# 确保目录存在
mkdir -p "$OUTPUT_DIR" "$FINAL_DIR" "$CLIPS_DIR" "$AUDIO_DIR" "$STORYBOARD_DIR"

# 传递给所有 tmux 窗口的 env 命令前缀（包含离线模式设置）
ENV_VARS="export STATIC_ROOT=$STATIC_ROOT OUTPUT_DIR=$OUTPUT_DIR FINAL_DIR=$FINAL_DIR CLIPS_DIR=$CLIPS_DIR STORYBOARD_DIR=$STORYBOARD_DIR AUDIO_DIR=$AUDIO_DIR HF_HOME=$HOME/.cache/huggingface TRANSFORMERS_OFFLINE=1 DIFFUSERS_OFFLINE=1 MODELSCOPE_CACHE=$HOME/.cache/modelscope MODELSCOPE_OFFLINE_MODE=1 HF_HUB_OFFLINE=1"
# 杀掉旧服务
pkill -f "uvicorn model.services.llm:app" || true
pkill -f "uvicorn model.services.txt2img:app" || true
pkill -f "uvicorn model.services.img2vid:app" || true
pkill -f "uvicorn model.services.tts:app" || true
pkill -f "uvicorn gateway.main:app" || true

# 激活 conda 环境
conda activate $ENV_NAME

# 强制使用离线模型
export HF_HOME="$HOME/.cache/huggingface"
export TRANSFORMERS_OFFLINE=1
export DIFFUSERS_OFFLINE=1
export MODELSCOPE_CACHE="$HOME/.cache/modelscope"
export MODELSCOPE_OFFLINE_MODE=1
export HF_HUB_OFFLINE=1

# 获取环境 Python 绝对路径
PYTHON_BIN="$CONDA_PREFIX/bin/python"

# 创建 tmux 会话 (直接使用绝对路径 Python，无需 conda activate)
tmux new-session -d -s $SESSION -n llm
tmux send-keys "cd $SCRIPT_DIR && $ENV_VARS && $PYTHON_BIN -m uvicorn model.services.llm:app --host 0.0.0.0 --port 8001" C-m

tmux new-window -t $SESSION -n gateway
tmux send-keys -t gateway "cd $SCRIPT_DIR && $ENV_VARS && $PYTHON_BIN -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000" C-m

tmux new-window -t $SESSION -n txt2img
tmux send-keys -t txt2img "cd $SCRIPT_DIR && $ENV_VARS && $PYTHON_BIN -m uvicorn model.services.txt2img:app --host 0.0.0.0 --port 8002" C-m

tmux new-window -t $SESSION -n img2vid
tmux send-keys -t img2vid "cd $SCRIPT_DIR && $ENV_VARS && $PYTHON_BIN -m uvicorn model.services.img2vid:app --host 0.0.0.0 --port 8003" C-m

tmux new-window -t $SESSION -n tts
tmux send-keys -t tts "cd $SCRIPT_DIR && $ENV_VARS && $PYTHON_BIN -m uvicorn model.services.tts:app --host 0.0.0.0 --port 8004" C-m

# 附加到会话
tmux attach -t $SESSION
