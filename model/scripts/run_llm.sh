#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$MODEL_DIR/.." && pwd)"
cd "$REPO_ROOT"
export MODEL_ROOT="$REPO_ROOT"

# Activate conda env if available
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate storyvideo || true
fi

export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export LLM_MODEL="${LLM_MODEL:-qwen2.5:0.5b}"

uvicorn model.services.llm:app --host 0.0.0.0 --port 8001
