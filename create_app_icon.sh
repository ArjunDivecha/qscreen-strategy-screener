#!/bin/bash

# Script to create an ICNS icon file for the Investment Strategies app
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating icon for Investment Strategies app..."

# Create icons directory if it doesn't exist
mkdir -p icons/AppIcon.iconset

# Download a suitable investment/finance icon
# This is a placeholder icon - replace with your preferred icon
echo "Downloading investment icon..."
curl -s "https://cdn-icons-png.flaticon.com/512/2620/2620084.png" -o icons/investment_icon.png

# Check if download was successful
if [ ! -f icons/investment_icon.png ]; then
    echo "Failed to download icon. Please try again or use a different icon."
    exit 1
fi

echo "Creating icon set for macOS..."

# Create iconset directory
mkdir -p icons/AppIcon.iconset

# Generate different sizes of the icon
sips -z 16 16 icons/investment_icon.png --out icons/AppIcon.iconset/icon_16x16.png
sips -z 32 32 icons/investment_icon.png --out icons/AppIcon.iconset/icon_16x16@2x.png
sips -z 32 32 icons/investment_icon.png --out icons/AppIcon.iconset/icon_32x32.png
sips -z 64 64 icons/investment_icon.png --out icons/AppIcon.iconset/icon_32x32@2x.png
sips -z 128 128 icons/investment_icon.png --out icons/AppIcon.iconset/icon_128x128.png
sips -z 256 256 icons/investment_icon.png --out icons/AppIcon.iconset/icon_128x128@2x.png
sips -z 256 256 icons/investment_icon.png --out icons/AppIcon.iconset/icon_256x256.png
sips -z 512 512 icons/investment_icon.png --out icons/AppIcon.iconset/icon_256x256@2x.png
sips -z 512 512 icons/investment_icon.png --out icons/AppIcon.iconset/icon_512x512.png
sips -z 1024 1024 icons/investment_icon.png --out icons/AppIcon.iconset/icon_512x512@2x.png

# Convert the iconset to icns
iconutil -c icns icons/AppIcon.iconset -o icons/InvestmentStrategies.icns

# Clean up
rm -rf icons/AppIcon.iconset

echo "Icon created: $SCRIPT_DIR/icons/InvestmentStrategies.icns"
echo "To attach this icon to your app:"
echo "1. Right-click on ~/Desktop/InvestmentStrategies.app in Finder"
echo "2. Select 'Get Info'"
echo "3. Drag the icon file onto the small icon in the top-left corner"
echo "   of the Get Info window"
echo ""
echo "Alternatively, you can run: fileicon set ~/Desktop/InvestmentStrategies.app $SCRIPT_DIR/icons/InvestmentStrategies.icns"
echo "if you have the fileicon utility installed (brew install fileicon)" 