#!/bin/bash
# One-time setup: allows the RGB Manager to write to sysfs without a password prompt.
# Adds a sudoers rule so 'sudo /usr/bin/tee /sys/.../rgb_zones/*' requires no password.

RULE='mahakaal ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/devices/platform/omen-rgb-keyboard/rgb_zones/*'
DEST='/etc/sudoers.d/rgb-keyboard'

echo "Installing sudoers rule to $DEST ..."
echo "$RULE" | sudo tee "$DEST" > /dev/null
sudo chmod 0440 "$DEST"

# Validate the sudoers file is correct
if sudo visudo -c -f "$DEST" 2>&1; then
    echo "✅ Done! The RGB Manager will no longer ask for your password."
else
    echo "❌ Syntax error in sudoers rule — removing broken file."
    sudo rm "$DEST"
    exit 1
fi
