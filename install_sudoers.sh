#!/bin/bash
# One-time setup: allows the RGB Manager to write to sysfs without a password prompt.
# Grants passwordless sudo for:
#   - tee to sysfs rgb_zones (color writes)
#   - modprobe to reload the omen_rgb_keyboard module (auto-recovery after sleep)


REAL_USER=${SUDO_USER:-$USER}
TEE_RULE="${REAL_USER} ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/devices/platform/omen-rgb-keyboard/rgb_zones/*"
MODPROBE_RM_RULE="${REAL_USER} ALL=(ALL) NOPASSWD: /sbin/modprobe -r omen_rgb_keyboard"
MODPROBE_ADD_RULE="${REAL_USER} ALL=(ALL) NOPASSWD: /sbin/modprobe omen_rgb_keyboard"
DEST='/etc/sudoers.d/rgb-keyboard'

echo "Installing sudoers rules to $DEST ..."
printf '%s\n%s\n%s\n' "$TEE_RULE" "$MODPROBE_RM_RULE" "$MODPROBE_ADD_RULE" | sudo tee "$DEST" > /dev/null
sudo chmod 0440 "$DEST"

# Validate the sudoers file is syntactically correct
if sudo visudo -c -f "$DEST" 2>&1; then
    echo "✅ Done! The RGB Manager will no longer ask for your password."
else
    echo "❌ Syntax error in sudoers rule — removing broken file."
    sudo rm "$DEST"
    exit 1
fi
