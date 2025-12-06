#!/bin/bash
# 本地运行脚本 - 使用系统 Qt 框架
cd "$(dirname "$0")"
DYLD_FRAMEWORK_PATH=/opt/homebrew/lib ./StoryToVideoGenerator.app/Contents/MacOS/StoryToVideoGenerator "$@"
