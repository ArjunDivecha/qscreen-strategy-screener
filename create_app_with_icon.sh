#!/bin/bash

# Script to create an app bundle with a custom icon
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating Investment Strategies app with custom icon..."

# Create app bundle directory structure
APP_DIR="$SCRIPT_DIR/InvestmentStrategies.app"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create Info.plist file
cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>InvestmentStrategiesLauncher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.investmentstrategies.app</string>
    <key>CFBundleName</key>
    <string>InvestmentStrategies</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>This app needs to control Terminal to launch the Investment Strategies application.</string>
</dict>
</plist>
EOF

# Compile the AppleScript
osacompile -o "$APP_DIR/Contents/Resources/launcher.scpt" InvestmentStrategies.applescript

# Create the launcher shell script
cat > "$APP_DIR/Contents/MacOS/InvestmentStrategiesLauncher" << EOF
#!/bin/bash
cd "\$(dirname "\$(dirname "\$(dirname "\$0")")")"
osascript "\$PWD/Contents/Resources/launcher.scpt"
EOF

chmod +x "$APP_DIR/Contents/MacOS/InvestmentStrategiesLauncher"

# Copy the icon
cp icons/InvestmentStrategies.icns "$APP_DIR/Contents/Resources/AppIcon.icns"

# Copy to Desktop
cp -R "$APP_DIR" ~/Desktop/

echo "App created at ~/Desktop/InvestmentStrategies.app with custom icon"
echo "You may need to refresh the Finder view to see the icon change:"
echo "1. Open a Terminal window"
echo "2. Run: killall Finder"
echo "3. The Finder will restart and the icon should be visible" 