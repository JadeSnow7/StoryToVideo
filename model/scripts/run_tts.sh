#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$MODEL_DIR/.." && pwd)"
cd "$REPO_ROOT"
export MODEL_ROOT="$REPO_ROOT"

if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate storyvideo || true
fi

export MODEL_ID="${MODEL_ID:-$REPO_ROOT/pretrained_models/CosyVoice2-0.5B/iic/CosyVoice2-0___5B}"
export DEVICE="${DEVICE:-cuda}"
export OUTPUT_DIR="${OUTPUT_DIR:-data/audio}"

# Ensure torch/torchaudio shared libs are discoverable
TORCH_LIB=$(python -c "import torch, pathlib; print(pathlib.Path(torch.__file__).parent / 'lib')")
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:$TORCH_LIB"

uvicorn model.services.tts:app --host 0.0.0.0 --port 8004
