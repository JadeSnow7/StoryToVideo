# StoryToVideo macOS Client - Quick Start Guide

## 🚀 Installation (30 seconds)

### Option 1: DMG Installer (Recommended)
```bash
# Download StoryToVideoGenerator-v1.0.0.dmg from Releases
# Then:
open StoryToVideoGenerator-v1.0.0.dmg
# Drag StoryToVideoGenerator.app to /Applications
# Launch from Launchpad or Applications folder
```

### Option 2: From Source
```bash
cd client/12.2StoryToVideo
bash deploy.sh
# DMG created at: StoryToVideoGenerator.dmg
```

## ⚙️ First Time Setup

### 1. Configure Backend API
Edit the application settings to point to your backend API server:
- Default: `http://localhost:8000`
- Modify in: Application Preferences

### 2. Create Your First Project
1. Launch the application
2. Click "Create Project"
3. Enter project name and description
4. Configure assets and storyboards
5. Save and manage through the UI

## 📂 Data Location
```
~/Library/Application Support/StoryToVideoGenerator/data/
```
Contains:
- Project files
- Configuration
- Cache data

## 🔍 Verify Installation

### Check Code Signature
```bash
codesign -v /Applications/StoryToVideoGenerator.app
# Should return: valid on disk
```

### Test Launch
```bash
/Applications/StoryToVideoGenerator.app/Contents/MacOS/StoryToVideoGenerator
# App should open without errors
```

## 🛠️ Build from Source

### Prerequisites
```bash
# Install Qt 6.9.3 via Homebrew
brew install qt

# Or install Xcode tools
xcode-select --install
```

### Build Steps
```bash
cd client/12.2StoryToVideo

# Automated build (recommended)
bash deploy.sh

# Or manual steps:
/opt/homebrew/bin/qmake StoryToVideoGenerator.pro
make -j$(sysctl -n hw.ncpu)
/opt/homebrew/bin/macdeployqt StoryToVideoGenerator.app/Contents/MacOS/..
codesign --deep --force --sign - StoryToVideoGenerator.app
```

### Build Output
- Application: `StoryToVideoGenerator.app`
- DMG Installer: `StoryToVideoGenerator.dmg`

## 🐛 Troubleshooting

### "Cannot open application" error
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine /Applications/StoryToVideoGenerator.app

# Verify signature
codesign -v /Applications/StoryToVideoGenerator.app
```

### Network connection issues
1. Check backend server is running
2. Verify API endpoint in application settings
3. Check firewall settings: `sudo lsof -i :8000`

### Clear application cache
```bash
rm -rf ~/Library/Application\ Support/StoryToVideoGenerator/data/
# App will recreate on next launch
```

## 📊 System Information

Check your system compatibility:
```bash
# Check macOS version
sw_vers

# Check processor type
uname -m
# Should output: arm64 (Apple Silicon) or x86_64 (Intel)
```

**Supported:**
- ✅ macOS 14.0 (Sonoma)
- ✅ macOS 15.x (Sequoia)
- ✅ Apple Silicon (M1/M2/M3/M4)
- ✅ Intel x86_64

## 📖 Documentation

- Full setup: `docs/deploy.md`
- Architecture: `docs/ARCHITECTURE.md`
- API Reference: `docs/apis.md`

## ❓ FAQ

**Q: Does the app need internet connection?**
A: Only when connecting to backend API. Local features work offline.

**Q: Where is data stored?**
A: `~/Library/Application Support/StoryToVideoGenerator/data/`

**Q: Can I move the app?**
A: Yes, move `StoryToVideoGenerator.app` anywhere in `/Applications` or use the DMG installer.

**Q: How do I uninstall?**
A: Move `StoryToVideoGenerator.app` to Trash. Optionally delete: `~/Library/Application Support/StoryToVideoGenerator/`

**Q: Is it safe to delete the data folder?**
A: Yes, app will recreate it on next launch (you'll lose local data though).

## 🔄 Updates

Check for updates:
```bash
git pull origin main
cd client/12.2StoryToVideo
bash deploy.sh
```

## 📝 Release Notes

See `RELEASE_NOTES_v1.0.0.md` for full details on v1.0.0 features and fixes.

## 🆘 Support

Report issues at: https://github.com/JadeSnow7/StoryToVideo/issues

---

**Version**: v1.0.0  
**Last Updated**: December 7, 2025
