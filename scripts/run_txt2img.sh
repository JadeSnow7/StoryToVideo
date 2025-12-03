#!/usr/bin/env bash
set -euo pipefail

if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate storyvideo || true
fi

export MODEL_ID="${MODEL_ID:-stabilityai/sd-turbo}"
export DEVICE="${DEVICE:-cuda}"
export OUTPUT_DIR="${OUTPUT_DIR:-data/frames}"

uvicorn services.txt2img.main:app --host 0.0.0.0 --port 8002
