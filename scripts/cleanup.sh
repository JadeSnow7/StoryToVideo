#!/usr/bin/env bash
set -e

# Change to the root of the repository
cd "$(dirname "$0")/.."

echo "==> Cleaning up AppleDouble files (._*)..."
find . -name "._*" -delete

echo "==> Cleaning up .DS_Store files..."
find . -name ".DS_Store" -delete

echo "==> Cleaning up Qt temporary objects (*.o.tmp)..."
find . -name "*.o.tmp" -delete

echo "==> Cleaning up Python cache (__pycache__)..."
find . -name "__pycache__" -type d -exec rm -rf {} +

echo "==> Removal of large artifacts..."
# Server binaries
if [ -f "server/StoryToVideoServer" ]; then
    echo "Removing server/StoryToVideoServer..."
    rm -f server/StoryToVideoServer
fi
if [ -f "server/server-linux" ]; then
    echo "Removing server/server-linux..."
    rm -f server/server-linux
fi

# Deployment archive
if [ -f "storytovideo-deploy.tar.gz" ]; then
    echo "Removing storytovideo-deploy.tar.gz..."
    rm -f storytovideo-deploy.tar.gz
fi

# Logs
if [ -f "server/server.log" ]; then
    echo "Removing server/server.log..."
    rm -f server/server.log
fi

# Client logs (large runtime artifacts)
if [ -f "client/12.2StoryToVideo/client.log" ]; then
    echo "Removing client/12.2StoryToVideo/client.log..."
    rm -f client/12.2StoryToVideo/client.log
fi

# Clean log directory strictly (keep .gitkeep if exists, but here we just purge logs)
# Using nullglob to avoid error if no files match
shopt -s nullglob
files=(server/log/*.log)
if [ ${#files[@]} -gt 0 ]; then
    echo "Removing logs in server/log/..."
    rm -f server/log/*.log
fi

echo "==> Cleanup complete."
