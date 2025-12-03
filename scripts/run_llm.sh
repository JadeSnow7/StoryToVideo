#!/usr/bin/env bash
set -euo pipefail

# Activate conda env if available
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate storyvideo || true
fi

export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export LLM_MODEL="${LLM_MODEL:-qwen2.5:0.5b}"

uvicorn services.llm.main:app --host 0.0.0.0 --port 8001
