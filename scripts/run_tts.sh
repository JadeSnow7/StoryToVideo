#!/usr/bin/env bash
set -euo pipefail

if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate storyvideo || true
fi

export MODEL_ID="${MODEL_ID:-./CosyVoice/pretrained_models/CosyVoice-300M-Instruct}"
export DEVICE="${DEVICE:-cuda}"
export OUTPUT_DIR="${OUTPUT_DIR:-data/audio}"

# Ensure torch/torchaudio shared libs are discoverable
TORCH_LIB=$(python -c "import torch, pathlib; print(pathlib.Path(torch.__file__).parent / 'lib')")
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:$TORCH_LIB"

uvicorn services.tts.main:app --host 0.0.0.0 --port 8004
