#!/usr/bin/env bash
# 一键调用端到端推理脚本，需服务已启动
# 用法：
#   ./scripts/run_infer.sh "故事文本" "风格" [分镜数] [fps] [总帧数]

set -euo pipefail

STORY=${1:-}
STYLE=${2:-""}
SCENES=${3:-3}
FPS=${4:-12}
VIDEO_FRAMES=${5:-16}

if [[ -z "$STORY" ]]; then
  echo "用法: $0 \"故事文本\" \"风格\" [分镜数=3] [fps=12] [总帧数=16]"
  exit 1
fi

# 默认参数
HEIGHT=512
WIDTH=768
IMG_STEPS=4
CFG_SCALE=1.5
SPEED=1.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

python "$ROOT/scripts/run_pipeline.py" \
  --story "$STORY" \
  --style "$STYLE" \
  --scenes "$SCENES" \
  --height "$HEIGHT" --width "$WIDTH" \
  --img-steps "$IMG_STEPS" --cfg-scale "$CFG_SCALE" \
  --fps "$FPS" --video-frames "$VIDEO_FRAMES" \
  --speed "$SPEED"
