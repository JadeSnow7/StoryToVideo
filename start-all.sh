#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REMOTE_HOST="${STV_REMOTE_HOST:-172.23.197.11}"
REMOTE_PORT="${STV_REMOTE_PORT:-2222}"
REMOTE_USER="${STV_REMOTE_USER:-stv}"
REMOTE_DIR="${STV_REMOTE_DIR:-}"
REMOTE_ENV="${STV_REMOTE_ENV:-stroy2video}"
SESSION_NAME="${STV_TMUX_SESSION:-storyvideo}"

API_BASE_URL="${STORYTOVIDEO_API_BASE_URL:-http://127.0.0.1:8080}"
export STORYTOVIDEO_API_BASE_URL="$API_BASE_URL"

echo "==> Starting remote model services + gateway ($REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT)..."
if [[ "${SKIP_REMOTE:-0}" == "1" ]]; then
  echo "SKIP_REMOTE=1 set; skipping remote startup."
else
  SSH_ARGS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o ConnectionAttempts=1 -p "$REMOTE_PORT")
  if [[ -n "${STV_SSH_KEY:-}" ]]; then
    SSH_ARGS+=(-i "$STV_SSH_KEY")
  fi
  if command -v sshpass >/dev/null 2>&1 && [[ -n "${STV_SSH_PASS:-}" ]]; then
    SSH_ARGS+=(-o PreferredAuthentications=password -o PubkeyAuthentication=no)
    if ! sshpass -p "$STV_SSH_PASS" ssh "${SSH_ARGS[@]}" "${REMOTE_USER}@${REMOTE_HOST}" \
      REMOTE_ENV="$REMOTE_ENV" REMOTE_DIR="$REMOTE_DIR" SESSION_NAME="$SESSION_NAME" bash -s <<'EOF'
set -euo pipefail
REMOTE_ENV="${REMOTE_ENV:-stroy2video}"
REMOTE_DIR="${REMOTE_DIR:-$HOME/workspace/StoryToVideo}"
SESSION_NAME="${SESSION_NAME:-storyvideo}"
REMOTE_DIR="${REMOTE_DIR/#\~/$HOME}"
cd "$REMOTE_DIR"

PYTHON_BIN="python3"
CONDA_SH=""
if command -v conda >/dev/null 2>&1; then
  CONDA_BASE=$(conda info --base)
  CONDA_SH="$CONDA_BASE/etc/profile.d/conda.sh"
else
  for d in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/mambaforge" "$HOME/miniforge3"; do
    if [[ -f "$d/etc/profile.d/conda.sh" ]]; then
      CONDA_SH="$d/etc/profile.d/conda.sh"
      break
    fi
  done
fi

ACTIVE_ENV=""
if [[ -n "$CONDA_SH" ]]; then
  # shellcheck source=/dev/null
  source "$CONDA_SH"
  for env in "$REMOTE_ENV" "stroy2video" "story2video"; do
    if conda env list | awk '{print $1}' | grep -qx "$env"; then
      ACTIVE_ENV="$env"
      break
    fi
  done
  if [[ -n "$ACTIVE_ENV" ]]; then
    conda activate "$ACTIVE_ENV"
    PYTHON_BIN="python"
  fi
fi

MODEL_ROOT="$REMOTE_DIR"
TORCH_LIB=""
if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  set +e
  TORCH_LIB=$("$PYTHON_BIN" - <<'PY'
import torch, pathlib
print(pathlib.Path(torch.__file__).parent / 'lib')
PY
)
  set -e
fi

RUN_LD_LIBRARY_PATH=""
if [[ -n "${CONDA_PREFIX:-}" ]]; then
  RUN_LD_LIBRARY_PATH="$CONDA_PREFIX/lib"
  if [[ -n "$TORCH_LIB" ]]; then
    RUN_LD_LIBRARY_PATH="$RUN_LD_LIBRARY_PATH:$TORCH_LIB"
  fi
  if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
    RUN_LD_LIBRARY_PATH="$RUN_LD_LIBRARY_PATH:$LD_LIBRARY_PATH"
  fi
else
  RUN_LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
fi

CMD_PREFIX="export MODEL_ROOT=\"$MODEL_ROOT\" && export LD_LIBRARY_PATH=\"$RUN_LD_LIBRARY_PATH\" && cd \"$REMOTE_DIR\""
if [[ -n "$CONDA_SH" ]]; then
  CMD_PREFIX="source $CONDA_SH && $CMD_PREFIX"
fi
if [[ -n "$ACTIVE_ENV" ]]; then
  CMD_PREFIX="source $CONDA_SH && conda activate $ACTIVE_ENV && $CMD_PREFIX"
fi

echo "Using conda env: ${ACTIVE_ENV:-none}"

tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
pkill -f "uvicorn model.services.llm:app" || true
pkill -f "uvicorn model.services.txt2img:app" || true
pkill -f "uvicorn model.services.img2vid:app" || true
pkill -f "uvicorn model.services.tts:app" || true
pkill -f "uvicorn gateway.main:app" || true

RUN_PREFIX=""
tmux new-session -d -s "$SESSION_NAME" -n llm "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.llm:app --host 0.0.0.0 --port 8001'"
tmux new-window -t "$SESSION_NAME" -n gateway "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000'"
tmux new-window -t "$SESSION_NAME" -n txt2img "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.txt2img:app --host 0.0.0.0 --port 8002'"
tmux new-window -t "$SESSION_NAME" -n img2vid "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.img2vid:app --host 0.0.0.0 --port 8003'"
tmux new-window -t "$SESSION_NAME" -n tts "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.tts:app --host 0.0.0.0 --port 8004'"

tmux ls
EOF
    then
      echo "Remote startup failed (sshpass)."
    fi
  else
    echo "STV_SSH_PASS not set; falling back to interactive ssh."
    if ! ssh "${SSH_ARGS[@]}" "${REMOTE_USER}@${REMOTE_HOST}" \
      REMOTE_ENV="$REMOTE_ENV" REMOTE_DIR="$REMOTE_DIR" SESSION_NAME="$SESSION_NAME" bash -s <<'EOF'
set -euo pipefail
REMOTE_ENV="${REMOTE_ENV:-stroy2video}"
REMOTE_DIR="${REMOTE_DIR:-$HOME/workspace/StoryToVideo}"
SESSION_NAME="${SESSION_NAME:-storyvideo}"
REMOTE_DIR="${REMOTE_DIR/#\~/$HOME}"
cd "$REMOTE_DIR"

PYTHON_BIN="python3"
CONDA_SH=""
if command -v conda >/dev/null 2>&1; then
  CONDA_BASE=$(conda info --base)
  CONDA_SH="$CONDA_BASE/etc/profile.d/conda.sh"
else
  for d in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/mambaforge" "$HOME/miniforge3"; do
    if [[ -f "$d/etc/profile.d/conda.sh" ]]; then
      CONDA_SH="$d/etc/profile.d/conda.sh"
      break
    fi
  done
fi

ACTIVE_ENV=""
if [[ -n "$CONDA_SH" ]]; then
  # shellcheck source=/dev/null
  source "$CONDA_SH"
  for env in "$REMOTE_ENV" "stroy2video" "story2video"; do
    if conda env list | awk '{print $1}' | grep -qx "$env"; then
      ACTIVE_ENV="$env"
      break
    fi
  done
  if [[ -n "$ACTIVE_ENV" ]]; then
    conda activate "$ACTIVE_ENV"
    PYTHON_BIN="python"
  fi
fi

MODEL_ROOT="$REMOTE_DIR"
TORCH_LIB=""
if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  set +e
  TORCH_LIB=$("$PYTHON_BIN" - <<'PY'
import torch, pathlib
print(pathlib.Path(torch.__file__).parent / 'lib')
PY
)
  set -e
fi

RUN_LD_LIBRARY_PATH=""
if [[ -n "${CONDA_PREFIX:-}" ]]; then
  RUN_LD_LIBRARY_PATH="$CONDA_PREFIX/lib"
  if [[ -n "$TORCH_LIB" ]]; then
    RUN_LD_LIBRARY_PATH="$RUN_LD_LIBRARY_PATH:$TORCH_LIB"
  fi
  if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
    RUN_LD_LIBRARY_PATH="$RUN_LD_LIBRARY_PATH:$LD_LIBRARY_PATH"
  fi
else
  RUN_LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
fi

CMD_PREFIX="export MODEL_ROOT=\"$MODEL_ROOT\" && export LD_LIBRARY_PATH=\"$RUN_LD_LIBRARY_PATH\" && cd \"$REMOTE_DIR\""
if [[ -n "$CONDA_SH" ]]; then
  CMD_PREFIX="source $CONDA_SH && $CMD_PREFIX"
fi
if [[ -n "$ACTIVE_ENV" ]]; then
  CMD_PREFIX="source $CONDA_SH && conda activate $ACTIVE_ENV && $CMD_PREFIX"
fi

echo "Using conda env: ${ACTIVE_ENV:-none}"

tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
pkill -f "uvicorn model.services.llm:app" || true
pkill -f "uvicorn model.services.txt2img:app" || true
pkill -f "uvicorn model.services.img2vid:app" || true
pkill -f "uvicorn model.services.tts:app" || true
pkill -f "uvicorn gateway.main:app" || true

RUN_PREFIX=""
tmux new-session -d -s "$SESSION_NAME" -n llm "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.llm:app --host 0.0.0.0 --port 8001'"
tmux new-window -t "$SESSION_NAME" -n gateway "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000'"
tmux new-window -t "$SESSION_NAME" -n txt2img "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.txt2img:app --host 0.0.0.0 --port 8002'"
tmux new-window -t "$SESSION_NAME" -n img2vid "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.img2vid:app --host 0.0.0.0 --port 8003'"
tmux new-window -t "$SESSION_NAME" -n tts "bash -lc '$CMD_PREFIX && $PYTHON_BIN -m uvicorn model.services.tts:app --host 0.0.0.0 --port 8004'"

tmux ls
EOF
    then
      echo "Remote startup failed (interactive ssh)."
    fi
  fi
fi

echo "==> Starting local Docker dependencies (mysql/redis/minio)..."
cd "$ROOT_DIR"
docker compose -f docker-compose.local.yml up -d

echo "==> Starting Go Server..."
cd "$ROOT_DIR/server"
pkill -f StoryToVideoServer || true
if [ ! -x "./StoryToVideoServer" ]; then
  echo "Building StoryToVideoServer..."
  go build -o StoryToVideoServer ./cmd/api
fi
mkdir -p log
nohup ./StoryToVideoServer > log/server.log 2>&1 &

echo "==> Starting Qt Client..."
cd "$ROOT_DIR/client/12.2StoryToVideo"
nohup ./StoryToVideoGenerator.app/Contents/MacOS/StoryToVideoGenerator > client.log 2>&1 &

sleep 1
echo "==> Health check (gateway + server)..."
curl -s --max-time 3 --connect-timeout 3 http://172.23.197.11:8000/health || true
curl -s --max-time 3 --connect-timeout 3 -o /dev/null -w "server http code: %{http_code}\n" http://127.0.0.1:8080/v1/api/projects || true

echo "Done."
