#!/bin/bash
SESSION="storyvideo"

# 启动环境
ENV_NAME="story2video"
CONDA_PREFIX=$(conda info --base)/envs/$ENV_NAME
export PATH="$CONDA_PREFIX/bin:$PATH"
# 计算 torch 库路径，避免 here-doc 结束符误解析
TORCH_LIB=$(python - <<'PY'
import torch, pathlib
print(pathlib.Path(torch.__file__).parent / 'lib')
PY
)
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$TORCH_LIB:${LD_LIBRARY_PATH:-}"

# 杀掉旧服务
pkill -f "uvicorn services.llm.main:app" || true
pkill -f "uvicorn services.txt2img.main:app" || true
pkill -f "uvicorn services.img2vid.main:app" || true
pkill -f "uvicorn services.tts.main:app" || true

# 创建 tmux 会话
tmux new-session -d -s $SESSION -n llm
tmux send-keys "conda activate $ENV_NAME && python -m uvicorn services.llm.main:app --host 0.0.0.0 --port 8001" C-m

tmux new-window -t $SESSION -n txt2img
tmux send-keys -t txt2img "conda activate $ENV_NAME && python -m uvicorn services.txt2img.main:app --host 0.0.0.0 --port 8002" C-m

tmux new-window -t $SESSION -n img2vid
tmux send-keys -t img2vid "conda activate $ENV_NAME && python -m uvicorn services.img2vid.main:app --host 0.0.0.0 --port 8003" C-m

tmux new-window -t $SESSION -n tts
tmux send-keys -t tts "conda activate $ENV_NAME && python -m uvicorn services.tts.main:app --host 0.0.0.0 --port 8004" C-m

# 附加到会话
tmux attach -t $SESSION
