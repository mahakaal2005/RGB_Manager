"""
fan_service.py — sysfs abstraction layer for HP OMEN fan control.

Mirrors service.py's pattern exactly: all hardware writes go through
FanService, using sudo tee for writes and plain reads for status.
Nothing in this module imports from widgets or app layers.
"""
import subprocess
from .constants import FAN_SYSFS_BASE, FAN_CURVE_MIN_POINTS, FAN_CURVE_MAX_POINTS


def parse_curve(raw: str) -> list[tuple[int, int]]:
    """
    Parse a driver curve string ("30:20 40:28 50:38") into
    [(temp, percent), ...] sorted by temperature. Skips malformed pairs.
    """
    points = []
    for pair in raw.split():
        if ":" not in pair:
            continue
        temp_s, pct_s = pair.split(":", 1)
        try:
            points.append((int(temp_s), int(pct_s)))
        except ValueError:
            continue
    points.sort(key=lambda p: p[0])
    return points


def serialize_curve(points: list[tuple[int, int]]) -> str:
    """Serialize [(temp, percent), ...] into the driver's space-separated format."""
    ordered = sorted(points, key=lambda p: p[0])
    return " ".join(f"{int(t)}:{int(p)}" for t, p in ordered)


def validate_curve(points: list[tuple[int, int]]) -> tuple[bool, str]:
    """Check point count and value ranges before writing to hardware."""
    if len(points) < FAN_CURVE_MIN_POINTS:
        return False, f"Need at least {FAN_CURVE_MIN_POINTS} points."
    if len(points) > FAN_CURVE_MAX_POINTS:
        return False, f"At most {FAN_CURVE_MAX_POINTS} points allowed."
    for t, p in points:
        if not (0 <= p <= 100):
            return False, f"Fan percent {p} out of range 0-100."
    return True, ""


class FanService:
    """Read/write interface to the omen-rgb-keyboard fan sysfs tree."""

    def _write(self, node: str, value: str) -> tuple[bool, str]:
        path = f"{FAN_SYSFS_BASE}/{node}"
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
        try:
            with open(f"{FAN_SYSFS_BASE}/{node}") as f:
                return f.read().strip()
        except Exception:
            return default

    def read_state(self) -> dict:
        """Read current fan state. Falls back to safe defaults for any unreadable node."""
        try:
            cpu_rpm = int(self._read("cpu_fan_rpm", "0") or "0")
        except ValueError:
            cpu_rpm = 0
        try:
            gpu_rpm = int(self._read("gpu_fan_rpm", "0") or "0")
        except ValueError:
            gpu_rpm = 0

        curve_enable = self._read("fan_curve_enable", "0") == "1"
        thermal_profile = self._read("thermal_profile", "normal") or "normal"
        curve = parse_curve(self._read("fan_curve", ""))

        return {
            "cpu_rpm":         cpu_rpm,
            "gpu_rpm":         gpu_rpm,
            "curve_enable":    curve_enable,
            "thermal_profile": thermal_profile,
            "curve":           curve,
        }

    def read_rpm(self) -> tuple[int, int]:
        """Lightweight poll for just CPU/GPU RPM (used by the live-refresh timer)."""
        try:
            cpu_rpm = int(self._read("cpu_fan_rpm", "0") or "0")
        except ValueError:
            cpu_rpm = 0
        try:
            gpu_rpm = int(self._read("gpu_fan_rpm", "0") or "0")
        except ValueError:
            gpu_rpm = 0
        return cpu_rpm, gpu_rpm

    def set_thermal_profile(self, profile: str) -> tuple[bool, str]:
        return self._write("thermal_profile", profile)

    def set_curve(self, points: list[tuple[int, int]]) -> tuple[bool, str]:
        ok, err = validate_curve(points)
        if not ok:
            return False, err
        return self._write("fan_curve", serialize_curve(points))

    def set_curve_enable(self, enabled: bool) -> tuple[bool, str]:
        """
        KNOWN BROKEN on this hardware/driver/kernel combination: writing 1
        here unconditionally fails with ENODEV, regardless of curve content
        (verified with 2-point, 5-point, flat, non-flat, and the driver's
        own auto-generated curves — all fail identically). Left in place
        for when this is fixed upstream; the UI disables the controls that
        would call it. See fan_curve_enable investigation, 2026-08-14.
        """
        return self._write("fan_curve_enable", "1" if enabled else "0")

    def set_max_fan(self, enabled: bool) -> tuple[bool, str]:
        """The one proven-reliable lever for commanding real fan speed changes."""
        return self._write("max_fan", "1" if enabled else "0")
