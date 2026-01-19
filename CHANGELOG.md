# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-07

### 🎯 Project Overview
StoryToVideo v1.0.0 is the first stable release of a comprehensive system that transforms text-based stories into engaging video narratives. The project integrates AI models (LLM, Stable Diffusion, TTS) with a modern desktop client and cloud backend.

### ✨ Added

#### Core Features
- **Client (Qt 6 Desktop App)**
  - Story management interface with asset browser
  - Shot/scene preview with video player
  - Real-time storyboard visualization
  - Export functionality for generated content

- **Backend Services**
  - LLM service for story understanding and shot generation
  - Stable Diffusion integration for image generation
  - Text-to-Speech (TTS) synthesis
  - Image-to-Video conversion using CogVideoX
  - Task queue with job status tracking

- **API Gateway**
  - RESTful API for client-server communication
  - Project and shot resource management
  - Task creation and monitoring
  - Async job processing

#### Build & Deployment
- Dockerized model services (GPU-ready)
- Unified deployment configuration
- Cross-platform build scripts

#### Code Quality
- Comprehensive API documentation
- Architecture documentation
- Deployment guides

### 🔧 Fixed

#### macOS Code Signing Issues
- **Issue**: App crashed on startup with "Code Signature Invalid" error
- **Root Cause**: Manual framework manipulation breaking dyld signature verification
- **Solution**: 
  - Removed manual QtMultimediaQuick.framework copying
  - Use macdeployqt for automatic framework management
  - Implemented Xcode-integrated code signing with `--deep` flag
  - Preserves framework integrity throughout build process

#### Client UI/API Compatibility
- Updated MediaPlayer API calls for Qt 6.x compatibility
  - `onError` → `onErrorOccurred`
  - `onStatusChanged` → `onMediaStatusChanged`
  - `status` → `mediaStatus` property names
- Fixed data storage paths using QStandardPaths
- Corrected network API endpoint paths

#### Server & Gateway
- Fixed project creation task registration
- Aligned shot endpoints with API specification
- Improved resource schema consistency
- Stabilized image-to-video conversion

### 📁 Repository Cleanup
- Removed 67MB DMG installation package from version control
- Removed generated test output files (MP4s and images)
- Updated .gitignore with comprehensive exclusion rules
- Reduced repository bloat for faster cloning and CI/CD

### 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    StoryToVideo v1.0.0                       │
├─────────────────────────────────────────────────────────────┤
│ Client (Qt 6)      │    Gateway (Python)    │  Backend Services  │
│ ─────────────────  │ ──────────────────────  │ ──────────────────  │
│ • Story Manager    │ • RESTful API (FastAPI) │ • LLM Service      │
│ • Shot Editor      │ • Task Scheduler       │ • Stable Diffusion │
│ • Video Preview    │ • Job Tracking         │ • TTS              │
│ • Asset Browser    │ • Resource Management  │ • Image2Video      │
│                    │                        │ • Task Queue       │
└─────────────────────────────────────────────────────────────┘
```

### 📦 Deployment

**Docker Services**:
- Model services run in GPU-enabled containers
- FastAPI gateway for API layer
- Database backend for persistence

**Build Process**:
- Qt 6.9.3 framework with Homebrew on macOS
- qmake for C++ project management
- macdeployqt for framework bundling
- Code signing with Xcode toolchain

### 🚀 Getting Started

#### Prerequisites
- macOS 14.0+ with Apple Silicon or Intel
- Xcode Command Line Tools
- Homebrew with Qt 6 installed

#### Build Desktop Client
```bash
cd client/12.2StoryToVideo
bash deploy.sh
```

#### Build & Deploy Backend
```bash
# Using Docker (single-machine)
cp .env.cloud.example .env
./deploy-server.sh up

# Or (without script)
docker compose -f docker-compose.yml up -d --build
```

### 🐛 Known Issues
- QML layout warnings in AssetsPage (non-blocking)
- Unused parameters in ViewModel (code cleanup in progress)

### 📋 Development Team
- Frontend: Qt/QML development
- Backend: Python (FastAPI, PyTorch)
- DevOps: Docker deployment

### 📄 License
See LICENSE file for details.

### 🔗 Resources
- [Architecture Documentation](./docs/ARCHITECTURE.md)
- [Deployment Guide](./docs/deploy.md)
- [API Documentation](./docs/apis.md)
- [PRD](./docs/PRD.md)

---

## Previous Releases

For information about previous releases, see the [Git commit history](https://github.com/JadeSnow7/StoryToVideo/commits/main).
