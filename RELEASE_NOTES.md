# StoryToVideo v1.0.0 Release

**Release Date**: December 7, 2025

Welcome to the first stable release of StoryToVideo! This release represents a major milestone with a fully functional AI-powered story-to-video generation pipeline.

## 🎯 What's New

### Desktop Client (Qt 6)
- ✅ Modern Qt 6 interface with story management
- ✅ Real-time shot preview and editing
- ✅ Video player with media controls
- ✅ Asset browser for project resources
- ✅ Export and distribution features
- ✅ **Fixed macOS Code Signature Invalid crashes** - App now runs reliably from any location

### Backend AI Services
- ✅ LLM service for intelligent story parsing
- ✅ Stable Diffusion image generation
- ✅ Professional TTS audio synthesis
- ✅ CogVideoX image-to-video conversion
- ✅ Async task queue with job tracking
- ✅ RESTful API gateway for client communication

### Infrastructure
- ✅ Docker containerization for GPU support
- ✅ FRP tunneling for remote deployment
- ✅ Unified configuration management
- ✅ Comprehensive documentation

## 🔧 Critical Bug Fixes

### macOS Code Signature Issue (RESOLVED)
**Problem**: Application crashed immediately on launch with "Code Signature Invalid" error.

**Root Cause**: Manual manipulation of `QtMultimediaQuick.framework` binaries during build process broke code signature verification.

**Solution**:
- Eliminated manual framework copying
- Delegated framework bundling to `macdeployqt`
- Implemented proper Xcode code signing pipeline
- Result: App runs reliably on any macOS ARM64 machine

## 📥 Installation

### Download
Pre-built macOS ARM64 application available at:
- GitHub Releases: `StoryToVideoGenerator.dmg`

### From Source
```bash
git clone https://github.com/JadeSnow7/StoryToVideo.git
cd StoryToVideo/client/12.2StoryToVideo
bash deploy.sh
```

## 📖 Documentation

- [Architecture Overview](../../docs/ARCHITECTURE.md)
- [Deployment Guide](../../docs/deploy.md)
- [API Documentation](../../docs/apis.md)
- [Build Instructions](../../docs/pipeline.md)

## 🐛 Known Issues
- Non-critical QML layout warnings in AssetsPage (display-only, no functional impact)
- Some unused function parameters (code cleanup in progress)

## 📊 Technical Details

**Client Stack**:
- Qt 6.9.3
- QML/C++
- OpenGL rendering

**Backend Stack**:
- Python 3.10+
- FastAPI
- PyTorch with CUDA support
- Redis for task queuing

**Deployment**:
- Docker containers
- Docker Compose orchestration
- FRP for secure tunneling

## 🙏 Contributors

- Frontend development and Qt optimization
- Backend service implementation
- DevOps and deployment infrastructure

## 🚀 Next Steps

### Planned for v1.1.0
- Enhanced story editing capabilities
- Batch processing mode
- Advanced asset management
- Performance optimizations

### Planned for v2.0.0
- Multi-language support
- Cloud sync capabilities
- Advanced editing timeline
- Real-time collaboration features

## 💬 Feedback

Please report issues via [GitHub Issues](https://github.com/JadeSnow7/StoryToVideo/issues)

---

**Version**: 1.0.0  
**Release Date**: 2025-12-07  
**Status**: ✅ Stable
