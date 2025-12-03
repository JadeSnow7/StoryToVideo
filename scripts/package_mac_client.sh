#!/usr/bin/env bash
set -euo pipefail

# Build and package the StoryToVideo Qt client into a macOS .app and .dmg bundle.
# Usage: ./scripts/package_mac_client.sh [build-dir]

ROOT_DIR=$(cd -- "$(dirname -- "$0")/.." && pwd)
BUILD_DIR=${1:-"$ROOT_DIR/build-macos"}

mkdir -p "$BUILD_DIR"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required to locate Qt for macOS. Install from https://brew.sh." >&2
  exit 1
fi

QT_PREFIX=${QT_PREFIX:-$(brew --prefix qt 2>/dev/null || true)}
if [[ -z "$QT_PREFIX" ]]; then
  echo "Unable to find Qt via Homebrew. Set QT_PREFIX to your Qt install prefix." >&2
  exit 1
fi

echo "Using Qt from: $QT_PREFIX"

cmake -S "$ROOT_DIR/client" -B "$BUILD_DIR" -G "Ninja" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$QT_PREFIX"

cmake --build "$BUILD_DIR" --config Release

INSTALL_DIR="$BUILD_DIR/install"
cmake --install "$BUILD_DIR" --config Release --prefix "$INSTALL_DIR"

APP_BUNDLE="$INSTALL_DIR/StoryToVideo.app"
QT_DEPLOY_TOOL="$QT_PREFIX/bin/macdeployqt"

if [[ ! -x "$QT_DEPLOY_TOOL" ]]; then
  echo "macdeployqt not found at $QT_DEPLOY_TOOL" >&2
  exit 1
fi

"$QT_DEPLOY_TOOL" "$APP_BUNDLE" -qmldir="$ROOT_DIR/client/qml" -verbose=1

pushd "$INSTALL_DIR" >/dev/null
DMG_NAME="StoryToVideo-macOS.dmg"
hdiutil create -format UDZO -srcfolder "$(basename "$APP_BUNDLE")" "$DMG_NAME" -ov
popd >/dev/null

echo "Packaged app: $APP_BUNDLE"
echo "Disk image: $INSTALL_DIR/$DMG_NAME"
