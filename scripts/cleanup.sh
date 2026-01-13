#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Removing AppleDouble files (._*)..."
find . -name "._*" -print -delete

echo "==> Removing .DS_Store files..."
find . -name ".DS_Store" -print -delete

echo "==> Removing Python __pycache__ directories..."
find . -name "__pycache__" -type d -print -exec rm -rf {} +

echo "==> Removing large artifacts and binaries..."
rm -f "storytovideo-deploy.tar.gz"
rm -f "server/StoryToVideoServer" "server/server-linux" "server/server.log"

if [ -d "server/log" ]; then
  find "server/log" -type f -name "*.log" -print -delete
fi

echo "==> Cleanup complete."
