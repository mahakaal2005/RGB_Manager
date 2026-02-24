"""
animator.py — Software animation engine for HP OMEN RGB Manager.

Phase 1:  Acts as a pass-through — returns the layer's static base colors.
Phase 2:  Full per-animation-mode time-based frame rendering so all 10
          animation types work in Python and blend modes apply to animated
          layers too.  The kernel's animation_mode is kept at 'static' so
          the kernel timer never fires, eliminating the ACPI interrupt storm
          that caused overheating.

No GTK dependency.
"""
import math
import time
import threading

from .constants import SYSFS_BASE


# ── Colour helpers ──────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#").upper()
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"{max(0,min(255,int(r))):02X}{max(0,min(255,int(g))):02X}{max(0,min(255,int(b))):02X}"


def _scale(rgb: tuple, factor: float) -> tuple:
    r, g, b = rgb
    return (int(r * factor), int(g * factor), int(b * factor))


# ── Sin look-up (avoids repeated math.sin calls inside the hot loop) ────────

def _sin01(phase: float) -> float:
    """Return sin mapped to [0, 1] for a phase in [0, 1]."""
    return 0.5 + 0.5 * math.sin(2 * math.pi * phase - math.pi / 2)


# ── Per-mode frame functions ────────────────────────────────────────────────
# Each takes (t, speed, brightness, base_colors) and returns list[tuple(R,G,B)]

def _frame_static(t, speed, brightness, base_colors):
    factor = brightness / 100
    return [_scale(_hex_to_rgb(c), factor) for c in base_colors]


def _frame_breathing(t, speed, brightness, base_colors):
    cycle = 3.0 / max(1, speed)
    phase = (t % cycle) / cycle
    intensity = 0.08 + 0.92 * _sin01(phase)
    factor = intensity * brightness / 100
    return [_scale(_hex_to_rgb(c), factor) for c in base_colors]


def _frame_wave(t, speed, brightness, base_colors):
    cycle = 3.0 / max(1, speed)
    result = []
    for i, c in enumerate(base_colors):
        phase = ((t % cycle) / cycle + i / 4) % 1.0
        intensity = 0.3 + 0.7 * _sin01(phase)
        result.append(_scale(_hex_to_rgb(c), intensity * brightness / 100))
    return result


def _frame_rainbow(t, speed, brightness, base_colors):
    cycle = 2.0 / max(1, speed)
    phase = (t % cycle) / cycle
    result = []
    for i in range(4):
        hue = (phase * 360 + i * 90) % 360
        r, g, b = _hsv_to_rgb(hue, 100, brightness)
        result.append((r, g, b))
    return result


def _frame_pulse(t, speed, brightness, base_colors):
    cycle = 1.5 / max(1, speed)
    phase = (t % cycle) / cycle
    # Sharp attack, fast decay
    intensity = max(0.0, 1.0 - phase * 4) if phase < 0.25 else 0.05
    factor = intensity * brightness / 100
    return [_scale(_hex_to_rgb(c), factor) for c in base_colors]


def _frame_chase(t, speed, brightness, base_colors):
    cycle = 1.5 / max(1, speed)
    active = int((t % cycle) / cycle * 4)
    result = []
    for i, c in enumerate(base_colors):
        factor = (brightness / 100) if i == active else 0.05
        result.append(_scale(_hex_to_rgb(c), factor))
    return result


def _frame_aurora(t, speed, brightness, base_colors):
    cycle = 4.0 / max(1, speed)
    result = []
    for i in range(4):
        phase = ((t % cycle + i * 0.3) / cycle) % 1.0
        intensity = 0.3 + 0.7 * _sin01(phase)
        r = int(20  * intensity * brightness / 100)
        g = int(200 * intensity * brightness / 100)
        b = int(180 * intensity * brightness / 100)
        result.append((r, g, b))
    return result


# Defer sparkle / candle / disco — they need per-tick randomness and
# matching the kernel is tricky.  Fall back to static for now.


def _hsv_to_rgb(h, s, v):
    """Simple HSV→RGB. h∈[0,360], s∈[0,100], v∈[0,100]. Returns int tuple."""
    h, s, v = h % 360, s / 100, v / 100
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if   h < 60:   r, g, b = c, x, 0
    elif h < 120:  r, g, b = x, c, 0
    elif h < 180:  r, g, b = 0, c, x
    elif h < 240:  r, g, b = 0, x, c
    elif h < 300:  r, g, b = x, 0, c
    else:          r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


_FRAME_FN = {
    "static":    _frame_static,
    "breathing": _frame_breathing,
    "wave":      _frame_wave,
    "rainbow":   _frame_rainbow,
    "pulse":     _frame_pulse,
    "chase":     _frame_chase,
    "aurora":    _frame_aurora,
    # fallback for modes not yet ported
}


def get_frame_colors(layer: dict, t: float) -> list:
    """Return list of 4 hex strings for this layer at time t."""
    mode      = layer.get("mode", "static")
    speed     = layer.get("speed", 1)
    bright    = layer.get("brightness", 100)
    base      = layer.get("zones", ["000000"] * 4)
    fn        = _FRAME_FN.get(mode, _frame_static)
    rgb_list  = fn(t, speed, bright, base)
    return [_rgb_to_hex(*rgb) for rgb in rgb_list]


# ── Animation loop (Phase 2) ────────────────────────────────────────────────

class AnimationLoop:
    """
    Runs a 10 FPS daemon thread that composites the layer stack and writes
    the result to sysfs as a stream of 'static' color frames.

    The kernel animation_mode is held at 'static', so the ACPI interrupt
    storm that causes overheating is completely eliminated.
    """

    FPS       = 10
    INTERVAL  = 1.0 / FPS

    def __init__(self, compositor, service):
        self._compositor  = compositor
        self._service     = service
        self._running     = False
        self._thread      = None
        self._layers: list = []
        self._lock        = threading.Lock()
        self._start_t     = 0.0

    def start(self):
        if self._running:
            return
        # NOTE: Do NOT set animation_mode=static here. The kernel runs freely
        # until the user has enabled animated layers for compositing.
        self._running = True
        self._start_t = time.monotonic()
        self._thread  = threading.Thread(target=self._loop, daemon=True,
                                         name="rgb-animator")
        self._thread.start()

    def stop(self):
        self._running = False

    def update_layers(self, layers: list):
        with self._lock:
            self._layers = list(layers)

    def _loop(self):
        _kernel_taken_over = False  # Did we already set kernel to 'static'?

        while self._running:
            tick_start = time.monotonic()
            t = tick_start - self._start_t

            with self._lock:
                layers = list(self._layers)

            # Only enabled layers matter
            active = [l for l in layers if l.get("enabled", True)]

            if active:
                # If any active layer has a non-static animation, we need to
                # own the kernel (set it to static so it doesn't interfere).
                has_anim = any(l.get("mode", "static") != "static" for l in active)
                if has_anim and not _kernel_taken_over:
                    self._service.set_animation("static")
                    _kernel_taken_over = True

                frame_colors = [get_frame_colors(l, t) for l in layers]
                final = self._compositor.composite(layers, frame_colors)
                self._service.apply_preset(final)
            else:
                # No active layers — release the kernel back to user control
                _kernel_taken_over = False

            elapsed = time.monotonic() - tick_start
            sleep_t = max(0.0, self.INTERVAL - elapsed)
            time.sleep(sleep_t)
