#!/bin/bash
# Build dist/Falcos.app (the game in its own window, see Falcos.swift) and a zip of it beside it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
APP="$ROOT/dist/Falcos.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O -o "$APP/Contents/MacOS/Falcos" "$ROOT/tools/highpeaks/app/Falcos.swift" -framework Cocoa -framework WebKit
# the app's icon: the game's own (art/highpeaks/cover or frontend/assets), when one is found
ICON_SRC=""
for f in "$ROOT/frontend/assets/menu/logo_falcos.webp" "$ROOT/frontend/assets/icon.png" "$ROOT/frontend/favicon.png"; do
  [ -f "$f" ] && ICON_SRC="$f" && break
done
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Falcos</string>
  <key>CFBundleDisplayName</key><string>Falcos</string>
  <key>CFBundleIdentifier</key><string>com.smukiez.falcos.local</string>
  <key>CFBundleExecutable</key><string>Falcos</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleIconFile</key><string>Falcos</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST
if [ -n "${ICON_PNG:-}" ] && [ -f "$ICON_PNG" ]; then
  SET="$ROOT/dist/Falcos.iconset"; rm -rf "$SET"; mkdir -p "$SET"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$ICON_PNG" --out "$SET/icon_${s}x${s}.png" >/dev/null
    sips -z $((s*2)) $((s*2)) "$ICON_PNG" --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$SET" -o "$APP/Contents/Resources/Falcos.icns" && rm -rf "$SET"
fi
codesign --force -s - "$APP" >/dev/null 2>&1 || true
(cd "$ROOT/dist" && rm -f Falcos.zip && ditto -c -k --keepParent Falcos.app Falcos.zip)
echo "built $APP"
