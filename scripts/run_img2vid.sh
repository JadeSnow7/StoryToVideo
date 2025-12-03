#!/usr/bin/env bash
set -euo pipefail

if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate storyvideo || true
fi

export MODEL_ID="${MODEL_ID:-stabilityai/stable-video-diffusion-img2vid}"
export DEVICE="${DEVICE:-cuda}"
export OUTPUT_DIR="${OUTPUT_DIR:-data/clips}"

uvicorn services.img2vid.main:app --host 0.0.0.0 --port 8003
