#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="StoryToVideoGenerator"
APP_BUNDLE="$PROJECT_DIR/${APP_NAME}.app"
DMG_FILE="$PROJECT_DIR/${APP_NAME}.dmg"

echo "========================================="
echo "🔨 Building $APP_NAME for macOS..."
echo "========================================="

# Step 1: Clean previous build
echo "Step 1: Cleaning previous build artifacts..."
cd "$PROJECT_DIR"
rm -rf .xcode build Release Makefile "${APP_NAME}.xcodeproj" 2>/dev/null || true
rm -f qrc_*.cpp moc_*.cpp *.o 2>/dev/null || true

# Step 2: Generate Makefile
echo "Step 2: Generating Makefile with qmake..."
/opt/homebrew/bin/qmake ${APP_NAME}.pro

# Step 3: Compile
echo "Step 3: Compiling..."
NCPU=$(sysctl -n hw.ncpu)
make clean
make -j$NCPU

# Step 4: Run macdeployqt
echo "Step 4: Bundling frameworks with macdeployqt..."
/opt/homebrew/bin/macdeployqt "${APP_BUNDLE}/Contents/MacOS/.." -always-overwrite

# Step 5: Sign the app bundle
echo "Step 5: Code signing the app bundle..."
# Ensure Xcode is set as active developer directory
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer 2>/dev/null || true

# Remove old signatures and sign recursively
codesign --deep --force --sign - "$APP_BUNDLE" 2>&1 | grep -i "signing\|replacing" || true

# Step 6: Verify signature
echo "Step 6: Verifying code signature..."
codesign -v "$APP_BUNDLE" 2>&1 | head -3

# Step 7: Create DMG
echo "Step 7: Creating DMG installer..."
rm -f "$DMG_FILE"
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_BUNDLE" -ov -format UDZO "$DMG_FILE"

echo "========================================="
echo "✅ Build complete!"
echo "📁 App Bundle: $APP_BUNDLE"
echo "📦 DMG File: $DMG_FILE"
echo "========================================="
