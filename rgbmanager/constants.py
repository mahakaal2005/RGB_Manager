"""
constants.py — all data constants for HP OMEN RGB Manager.

Centralises: sysfs path, animation modes, presets, color palette,
and knob geometry. Nothing here should have side effects.
"""
import math

# ── Hardware path ──────────────────────────────────────────────────────────────
SYSFS_BASE = "/sys/devices/platform/omen-rgb-keyboard/rgb_zones"

# ── Animation modes (from kernel source: omen_animations.c) ───────────────────
# Each entry: (sysfs_key, display_label, description)
ANIMATION_MODES = [
    ("static",    "Static",    "Solid static colors"),
    ("breathing", "Breathing", "Zones pulse in and out"),
    ("rainbow",   "Rainbow",   "Full spectrum cycle"),
    ("wave",      "Wave",      "Colors ripple across zones"),
    ("pulse",     "Pulse",     "Sharp pulse of zone colors"),
    ("chase",     "Chase",     "Lit zone sweeps across"),
    ("sparkle",   "Sparkle",   "White sparks flash"),
    ("candle",    "Candle",    "Warm amber flicker"),
    ("aurora",    "Aurora",    "Green-blue aurora sweep"),
    ("disco",     "Disco",     "Fast RGB strobe"),
]

# ── Blend modes for the layer compositor ──────────────────────────────────────
BLEND_MODES = ["override", "blend", "add", "multiply", "screen"]
BLEND_MODE_LABELS = {
    "override": "Override",
    "blend":    "Blend",
    "add":      "Add",
    "multiply": "Multiply",
    "screen":   "Screen",
}

# ── Presets ────────────────────────────────────────────────────────────────────
STATIC_PRESETS = {
    "Gaming":     ["FF0000", "FF0000", "FF0000", "FF0000"],
    "Ocean":      ["0033FF", "0099FF", "00CCFF", "00FFFF"],
    "Synthwave":  ["FF00FF", "AA00FF", "FF0066", "AA00FF"],
    "Matrix":     ["00FF00", "00CC00", "009900", "006600"],
    "Sunset":     ["FF6600", "FF3300", "FF6600", "FFAA00"],
    "White":      ["FFFFFF", "FFFFFF", "FFFFFF", "FFFFFF"],
    "Off":        ["000000", "000000", "000000", "000000"],
    "Synth Soft": ["C45BAA", "9555C4", "C45B82", "9555C4"],  # Pastel synthwave
    "Aura Green": ["33B585", "1F9975", "187A5E", "166952"],  # Eye's most sensitive wavelength
    "Nightshift": ["D9751E", "B44E14", "99330D", "D9751E"],  # Amber/Orange (cuts blue light)
    "Melatonin":  ["8B0000", "5C0000", "8B0000", "5C0000"],  # Deep red (preserves night vision)
}

DYNAMIC_PRESETS = {
    "Breathe Blue": (["0055FF", "0055FF", "0055FF", "0055FF"], "breathing", 2),
    "Rainbow Rush": (["FF0000", "00FF00", "0000FF", "FF00FF"], "rainbow",   6),
    "Ocean Wave":   (["0033FF", "0099FF", "00CCFF", "00FFFF"], "wave",      3),
    "Sparkle Red":  (["FF0000", "FF0000", "FF0000", "FF0000"], "sparkle",   4),
    "Candlelight":  (["FF6600", "FF3300", "FF6600", "FFAA00"], "candle",    5),
    "Aurora":       (["00FF88", "00CCAA", "00FFCC", "009966"], "aurora",    2),
    "Disco Fever":  (["FF0000", "00FF00", "0000FF", "FF00FF"], "disco",     8),
    "Heartbeat":    (["FF0000", "FF0000", "FF0000", "FF0000"], "pulse",     7),
    "Blue Chase":   (["0055FF", "0055FF", "0055FF", "0055FF"], "chase",     5),
    "Deep Focus":   (["33B585", "33B585", "33B585", "33B585"], "breathing", 1), # Slow soft green
    "Sleep Well":   (["B44E14", "B44E14", "B44E14", "B44E14"], "breathing", 1), # Slow amber
}

# ── Color palette (Retro-Futurism) ─────────────────────────────────────────────
C_BG      = (0.059, 0.059, 0.137)  # #0F0F23
C_CARD    = (0.086, 0.071, 0.157)  # #161228
C_CARD_B  = (0.188, 0.212, 0.239)  # #30363D
C_PRIMARY = (0.486, 0.227, 0.929)  # #7C3AED
C_SECOND  = (0.655, 0.545, 0.980)  # #A78BFA
C_ACCENT  = (0.957, 0.247, 0.369)  # #F43F5E
C_TEXT    = (0.886, 0.910, 0.941)  # #E2E8F0
C_MUTED   = (0.392, 0.455, 0.545)  # #64748B

# ── Knob geometry ──────────────────────────────────────────────────────────────
# Arc sweeps clockwise from bottom-left (135deg) through 270deg to bottom-right.
KNOB_START_A  = 0.75 * math.pi   # 135 deg  -- arc start
KNOB_SWEEP    = 1.5  * math.pi   # 270 deg  -- total sweep
KNOB_END_A    = KNOB_START_A + KNOB_SWEEP
KNOB_GAP_HALF = 0.25 * math.pi   # dead-zone half-width near gap
KNOB_LINE_W   = 6                 # arc stroke width (px)
KNOB_DEBOUNCE = 300               # ms delay before sysfs write

# ── Utility ────────────────────────────────────────────────────────────────────
def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)

def rgb_to_hex(r: float, g: float, b: float) -> str:
    return f"{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
