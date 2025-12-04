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

export MODEL_ID="${MODEL_ID:-stabilityai/stable-video-diffusion-img2vid}"
export DEVICE="${DEVICE:-cuda}"
export OUTPUT_DIR="${OUTPUT_DIR:-data/clips}"

uvicorn model.services.img2vid:app --host 0.0.0.0 --port 8003
