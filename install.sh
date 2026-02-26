#!/bin/bash
# HP OMEN RGB Manager Unified Installer

echo "=== HP OMEN RGB Manager Installation ==="

# 1. Hardware Verification
SYSFS_DIR="/sys/devices/platform/omen-rgb-keyboard/rgb_zones"
if [ ! -d "$SYSFS_DIR" ]; then
    echo "❌ Sorry, but this app is not supported by your system."
    echo "   Could not find the omen-rgb-keyboard hardware interface at $SYSFS_DIR."
    echo "   Ensure you installed and loaded the 'omen-rgb-keyboard' kernel module."
    exit 1
fi

echo "🎉 Congratulations! You are lucky, this app can be used on your system!"
echo ""

# 2. Execute Sub-Scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Step 1: Installing Sudoers Rule"
sudo bash "$SCRIPT_DIR/install_sudoers.sh"

echo ""
echo "Step 2: Creating Desktop Entry"
bash "$SCRIPT_DIR/install_desktop.sh"

echo ""
echo "✅ Installation Complete! You can now launch the app from your application menu."
echo ""
echo "⚠️  NOTE: Animation Direction Patch"
echo "If you want to support changing the direction of RGB animations,"
echo "you can optionally run: sudo ./apply_direction_patch.sh"
echo "WARNING: This modifies and recompiles the C-source of the kernel module."
echo "Use this entirely AT YOUR OWN RISK!"
