# StoryToVideo v1.0.0 - Initial Release 🎉

## Overview
**StoryToVideo** is a comprehensive platform that transforms text descriptions into video stories. This is the **macOS client** - a native Qt-based application for managing video projects, shots, and assets.

## ✨ Key Features

### 🎬 Project Management
- Create, view, and manage video projects
- Organize projects by assets and storyboards
- Real-time project status tracking

### 🎞️ Shot Management
- Detailed shot configuration and preview
- Video export and preview functionality
- Media player with QtMultimedia support

### 📁 Asset Management
- Local asset storage and organization
- Quick asset access from project interface

### 🌐 Backend Integration
- Seamless connection to backend API
- Network request handling with Qt networking
- JSON data serialization/deserialization

### 💾 Data Persistence
- Cross-platform data storage with QStandardPaths
- Persistent local cache for better UX
- Standard macOS application data location: `~/Library/Application Support/StoryToVideoGenerator/`

## 🔧 Technical Stack

- **Language**: C++ / QML (Qt 6.9.3)
- **Platform**: macOS ARM64 (Apple Silicon) and Intel
- **Build System**: qmake + make
- **Packaging**: macdeployqt + DMG installer

## 🐛 Major Fixes in This Release

### Code Signature Invalid Crash (RESOLVED) ✅
**Problem**: Application crashed on startup with "Code Signature Invalid" when launched from DMG
- **Root Cause**: Manual framework modification using `install_name_tool` broke code signing
- **Solution**: Eliminated manual framework manipulation in favor of automatic `macdeployqt` handling
- **Verification**: Full recursive code signing with Xcode's `codesign --deep`
- **Result**: Application now launches successfully without crashes

### Qt 6.x API Updates
- Updated MediaPlayer signals: `onError` → `onErrorOccurred`
- Updated status tracking: `onStatusChanged` → `onMediaStatusChanged`
- Updated status constants: `MediaPlayer.Loaded` → `MediaPlayer.LoadedMedia`

### Data Storage Improvements
- Replaced working directory storage with system standard paths
- Data now stored in: `~/Library/Application Support/StoryToVideoGenerator/data/`

## 📦 Installation

### From DMG Installer
1. Download `StoryToVideoGenerator-v1.0.0.dmg` from Releases
2. Mount the DMG file
3. Drag `StoryToVideoGenerator.app` to `/Applications`
4. Launch from Applications folder or Launchpad

### From Source
```bash
cd /Users/huaodong/StoryToVideo/client/12.2StoryToVideo
bash deploy.sh
```

The script will:
1. Clean previous builds
2. Compile with qmake + make
3. Bundle frameworks with macdeployqt
4. Sign the application with Xcode tools
5. Create DMG installer

## ✅ Build Process Improvements

### Automated Workflow
The new `deploy.sh` script provides:
- ✅ Reproducible builds
- ✅ Automatic framework bundling
- ✅ Proper code signing
- ✅ DMG creation
- ✅ Signature verification

### Framework Management
All Qt frameworks are automatically bundled:
- QtCore, QtGui, QtQml, QtQuick
- QtMultimedia (for video playback)
- QtNetwork (for API communication)
- QtSql (for local database)
- And all transitive dependencies

## 🔄 Repository Cleanup

This release includes important repository maintenance:

### Removed from Git
- 67 MB DMG installer file (no longer tracked)
- Generated test outputs (MP4/PNG files)
- Build artifacts (*.o, moc_*.cpp, qrc_*.cpp)

### Updated .gitignore
Added patterns for:
- `*.dmg, *.pkg, *.exe` - Binary installers
- `client/*/.xcode/` - Xcode build directories
- `client/*/Release/` - Release builds
- `server/gin-server/static/tasks/*/` - Test outputs

## 📋 Commits Included

**Latest commits in this release:**
- **e3dcdce**: Remove redundant build artifacts from git
- **39c9772**: Fix macOS Code Signature Invalid crash with improved deployment workflow
- **d43b663**: Fix gateway and client API path issues
- **3650f3e**: Fix network API paths and JSON parsing
- Plus 40+ commits with platform features and infrastructure

## 🚀 Next Steps

### Planned for Future Releases
- [ ] Apple Developer ID signing for notarization
- [ ] Automatic updates mechanism
- [ ] Cloud project sync
- [ ] Video preview streaming
- [ ] Extended asset library
- [ ] Batch project operations
- [ ] Windows/Linux ports

### Known Limitations
- Requires manual configuration of backend API endpoint
- No automatic backup/recovery of local data
- Limited to macOS platform (v1.0.0)
- Qt frameworks only bundled for macOS ARM64

## 📝 System Requirements

### Runtime Environment
- **OS**: macOS 14.0 or later
- **Processor**: Apple Silicon (ARM64) or Intel x86_64
- **Memory**: 4 GB RAM minimum (8 GB recommended)
- **Disk Space**: 500 MB available

### Build Environment (if building from source)
- macOS 14.0+
- Xcode Command Line Tools or full Xcode
- Qt 6.9.3 (via Homebrew: `brew install qt`)
- qmake (included with Qt)

### No External Dependencies Required at Runtime
- All Qt libraries are bundled in the application
- Backend API server connection required

## 🆘 Troubleshooting

### Application Won't Launch
1. Verify code signature: `codesign -v /Applications/StoryToVideoGenerator.app`
2. Check for quarantine attribute: `xattr -l /Applications/StoryToVideoGenerator.app`
3. Remove if needed: `xattr -d com.apple.quarantine /Applications/StoryToVideoGenerator.app`

### Network Connection Issues
1. Verify backend API endpoint configuration
2. Check firewall settings
3. Ensure network connectivity

### Data Storage
Data is stored in: `~/Library/Application Support/StoryToVideoGenerator/data/`
- Safe to delete for a fresh start
- Automatically recreated on next launch

## 📄 Documentation

- [Client README](https://github.com/JadeSnow7/StoryToVideo/blob/main/client/12.2StoryToVideo/README.md)
- [Architecture Documentation](https://github.com/JadeSnow7/StoryToVideo/blob/main/docs/ARCHITECTURE.md)
- [Deployment Guide](https://github.com/JadeSnow7/StoryToVideo/blob/main/docs/deploy.md)

## 🔐 Security Notes

### Code Signing
- Application is properly signed for macOS
- Signature verified during build
- Safe to distribute and install

### Data Privacy
- All local data stored in user's Application Support directory
- No data sent to external services except configured backend
- Network communication via standard HTTPS (when configured)

## 👥 Credits

This release was built by the StoryToVideo development team.

---

**Release Date**: December 7, 2025  
**Version**: v1.0.0  
**Git Tag**: v1.0.0  
**Commit Hash**: e3dcdceb3352b09248483f54c79a1f73ac530eab  
**License**: See LICENSE file in repository
