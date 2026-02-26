#!/bin/bash
# Desktop Entry Installer for HP OMEN RGB Manager


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/omen-rgb.desktop"

echo "Creating desktop entry for HP OMEN RGB Manager..."

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=HP OMEN RGB Manager
Comment=Control HP OMEN 16 keyboard RGB zones
Exec=/bin/bash $SCRIPT_DIR/run.sh
Icon=$SCRIPT_DIR/icon.png
Terminal=false
Categories=Utility;HardwareSettings;
Keywords=RGB;keyboard;OMEN;HP;lighting;
EOF

chmod +x "$DESKTOP_FILE"
update-desktop-database "$DESKTOP_DIR"

echo "✅ Desktop entry installed successfully at $DESKTOP_FILE"
echo "You can now launch 'HP OMEN RGB Manager' from your application menu."
