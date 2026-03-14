"""
service.py — sysfs abstraction layer for HP OMEN RGB keyboard.

All hardware writes go through RGBService. Nothing in this module
imports from widgets or app layers (dependency flows one way).
"""
import subprocess
import time
from .constants import SYSFS_BASE


class RGBService:
    """Read/write interface to the omen-rgb-keyboard sysfs tree."""

    def _write(self, node: str, value: str) -> tuple[bool, str]:
        path = f"{SYSFS_BASE}/{node}"
        try:
            proc = subprocess.run(
                ["sudo", "/usr/bin/tee", path],
                input=value.strip().encode(),
                capture_output=True,
                timeout=4,
            )
            return (True, "") if proc.returncode == 0 else (False, proc.stderr.decode().strip())
        except Exception as e:
            return (False, str(e))

    def _read(self, node: str, default: str = "") -> str:
        """Read a sysfs node, returning default on any error."""
        try:
            with open(f"{SYSFS_BASE}/{node}") as f:
                return f.read().strip()
        except Exception:
            return default

    def _read_state_file(self) -> dict | None:
        """
        Parse the kernel's binary state file at /var/lib/omen-rgb-keyboard/state.
        Struct layout (little-endian):
          int   mode        (4 bytes, enum animation_mode)
          int   speed       (4 bytes)
          int   brightness  (4 bytes)
          u8[3] colors[0]   (blue, green, red — __packed)
          u8[3] colors[1]
          u8[3] colors[2]
          u8[3] colors[3]
        Total = 12 + 4*3 = 24 bytes
        """
        import struct as _struct
        STATE_PATH = "/var/lib/omen-rgb-keyboard/state"
        try:
            with open(STATE_PATH, "rb") as f:
                data = f.read()
            if len(data) < 24:
                return None
            mode_int, speed, brightness = _struct.unpack_from("<iii", data, 0)
            zones = []
            for i in range(4):
                b, g, r = _struct.unpack_from("<BBB", data, 12 + i * 3)
                zones.append(f"{r:02X}{g:02X}{b:02X}")
            return {
                "zones":      zones,
                "brightness": brightness,
                "speed":      max(1, min(10, speed)),
                "mode_int":   mode_int,
            }
        except Exception:
            return None

    def read_state(self) -> dict:
        """
        Read current keyboard state.
        Zone colors come from the kernel state file (original_colors = user base colors),
        NOT from sysfs zone nodes which return the current animated/dimmed color.
        animation_mode, animation_speed, animation_direction come from sysfs (live values).
        Falls back to safe defaults for any unreadable node.
        """
        # Animation mode names must match the kernel enum order
        MODE_NAMES = [
            "static", "breathing", "rainbow", "wave", "pulse",
            "chase", "sparkle", "candle", "aurora", "disco",
        ]

        # Prefer state file for zone colors (stores original_colors, not animated)
        sf = self._read_state_file()
        if sf:
            zones = sf["zones"]
            brightness = sf["brightness"]
            speed = sf["speed"]
        else:
            # Fallback: sysfs (may show dimmed animated color, but better than nothing)
            zones = []
            for i in range(4):
                raw = self._read(f"zone0{i}", "#FF0000")
                zones.append(raw.lstrip("#").upper() or "FF0000")
            try:
                brightness = int(self._read("brightness", "100"))
            except ValueError:
                brightness = 100
            try:
                speed = max(1, min(10, int(self._read("animation_speed", "1"))))
            except ValueError:
                speed = 1

        # Always read animation mode + direction live from sysfs (authoritative)
        mode = self._read("animation_mode", "static") or "static"

        direction = self._read("animation_direction", "left_to_right")
        if direction not in ("left_to_right", "right_to_left"):
            direction = "left_to_right"

        return {
            "zones":      zones,
            "brightness": brightness,
            "mode":       mode,
            "speed":      speed,
            "direction":  direction,
        }

    def set_zone_color(self, zone: str, hex_color: str) -> tuple[bool, str]:
        """Set a single zone color. zone = 'zone00'..'zone03' or 'all'."""
        return self._write(zone, hex_color.lstrip("#").upper())

    def set_brightness(self, value: int) -> tuple[bool, str]:
        return self._write("brightness", str(int(value)))

    def set_animation(self, mode: str) -> tuple[bool, str]:
        return self._write("animation_mode", mode)

    def set_speed(self, value: int) -> tuple[bool, str]:
        return self._write("animation_speed", str(max(1, min(10, int(value)))))

    def set_direction(self, direction: str) -> tuple[bool, str]:
        """
        Set animation direction ('left_to_right' or 'right_to_left').
        Requires kernel driver patched with animation_direction sysfs node.
        Returns (False, reason) gracefully if node doesn't exist.
        """
        return self._write("animation_direction", direction)

    def apply_preset(self, colors: list) -> tuple[bool, str]:
        """Apply a list of 4 hex color strings to zones 0-3."""
        for i, h in enumerate(colors):
            ok, err = self.set_zone_color(f"zone0{i}", h)
            if not ok:
                return (False, err)
        return (True, "")

    def apply_dynamic_preset(self, colors: list, mode: str, speed: int) -> tuple[bool, str]:
        ok, err = self.apply_preset(colors)
        if not ok:
            return (False, err)
        ok, err = self.set_animation(mode)
        if not ok:
            return (False, err)
        return self.set_speed(speed)

    # ── Module health & recovery ────────────────────────────────────────────

    def health_check(self) -> tuple[bool, str]:
        """
        Test whether sysfs writes succeed. Reads the current brightness and
        writes it back — a no-op that confirms the driver is alive.
        Returns (True, '') if healthy, (False, error_message) if stuck.
        """
        current = self._read("brightness", "100")
        return self._write("brightness", current)

    def reload_module(self) -> tuple[bool, str]:
        """
        Remove and reload the omen_rgb_keyboard kernel module.
        Requires passwordless sudo on modprobe (set up by install_sudoers.sh
        or add 'NOPASSWD: /sbin/modprobe' to the sudoers rule).
        """
        try:
            # Remove (ignore error if module was already unloaded)
            subprocess.run(
                ["sudo", "/sbin/modprobe", "-r", "omen_rgb_keyboard"],
                capture_output=True, timeout=10,
            )
            time.sleep(1)
            # Load
            proc = subprocess.run(
                ["sudo", "/sbin/modprobe", "omen_rgb_keyboard"],
                capture_output=True, timeout=10,
            )
            if proc.returncode != 0:
                return (False, proc.stderr.decode().strip() or "modprobe failed")
            time.sleep(1)  # Give the driver a moment to create sysfs nodes
            return (True, "")
        except Exception as e:
            return (False, str(e))

    def reapply_last_state(self) -> tuple[bool, str]:
        """
        Read the last known state from the kernel state file and push it
        back to hardware. Call this after reload_module() to restore settings.
        """
        state = self.read_state()
        # Restore zone colors
        ok, err = self.apply_preset(state["zones"])
        if not ok:
            return (False, err)
        # Restore brightness
        ok, err = self.set_brightness(state["brightness"])
        if not ok:
            return (False, err)
        # Restore animation mode and speed
        ok, err = self.set_animation(state["mode"])
        if not ok:
            return (False, err)
        return self.set_speed(state["speed"])
