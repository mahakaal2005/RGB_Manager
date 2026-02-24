"""
compositor.py — Layer compositor for HP OMEN RGB Manager.

Pure-Python color blending engine.  No GTK dependency.
Given a stack of layers (bottom → top) and their resolved frame
colors, produces the final 4-zone hex output that gets sent to hardware.
"""

# ── Blend kernels (all operate on per-channel 0-255 ints) ──────────────────

def _clamp(v: float) -> int:
    return max(0, min(255, int(v)))


def _blend_channels(bottom: tuple, top: tuple, alpha: float,
                    mode: str) -> tuple:
    """Blend two (R,G,B) tuples according to mode and opacity alpha ∈ [0,1]."""
    r0, g0, b0 = bottom
    r1, g1, b1 = top

    if mode == "override":
        # Top fully replaces bottom weighted by alpha
        r = r0 * (1 - alpha) + r1 * alpha
        g = g0 * (1 - alpha) + g1 * alpha
        b = b0 * (1 - alpha) + b1 * alpha

    elif mode == "blend":
        # 50/50 average, weighted by alpha
        a = alpha * 0.5
        r = r0 * (1 - a) + r1 * a
        g = g0 * (1 - a) + g1 * a
        b = b0 * (1 - a) + b1 * a

    elif mode == "add":
        # Additive — gets brighter, clamped at 255
        r = r0 + r1 * alpha
        g = g0 + g1 * alpha
        b = b0 + b1 * alpha

    elif mode == "multiply":
        # Darkening blend
        mr = r0 * r1 / 255
        mg = g0 * g1 / 255
        mb = b0 * b1 / 255
        r = r0 * (1 - alpha) + mr * alpha
        g = g0 * (1 - alpha) + mg * alpha
        b = b0 * (1 - alpha) + mb * alpha

    elif mode == "screen":
        # Lightening blend
        sr = 255 - (255 - r0) * (255 - r1) / 255
        sg = 255 - (255 - g0) * (255 - g1) / 255
        sb = 255 - (255 - b0) * (255 - b1) / 255
        r = r0 * (1 - alpha) + sr * alpha
        g = g0 * (1 - alpha) + sg * alpha
        b = b0 * (1 - alpha) + sb * alpha

    else:
        # Unknown mode — treat as override
        r = r0 * (1 - alpha) + r1 * alpha
        g = g0 * (1 - alpha) + g1 * alpha
        b = b0 * (1 - alpha) + b1 * alpha

    return (_clamp(r), _clamp(g), _clamp(b))


def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#").upper()
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"{r:02X}{g:02X}{b:02X}"


# ── Compositor ─────────────────────────────────────────────────────────────

class LayerCompositor:
    """
    Composites a stack of layers bottom-to-top.

    frame_colors: list[list[str]] — pre-resolved per-layer zone colors
                  (4 hex strings per layer, already animated/dimmed if needed)
                  Must be in the same order and length as `layers`.
    """

    VALID_MODES = frozenset(["override", "blend", "add", "multiply", "screen"])

    def composite(self, layers: list, frame_colors: list) -> list:
        """
        Returns a list of 4 hex color strings for zones 0-3.

        layers:       ordered list of layer dicts (bottom first)
        frame_colors: list[list[str]] — 4 hex-strings per layer
        """
        # Start with a black base for every zone
        result = [(0, 0, 0)] * 4

        for layer, colors in zip(layers, frame_colors):
            if not layer.get("enabled", True):
                continue

            zone_mask  = layer.get("zone_mask",   [True, True, True, True])
            blend_mode = layer.get("blend_mode",  "override")
            blend_amt  = float(layer.get("blend_amount", 1.0))
            blend_amt  = max(0.0, min(1.0, blend_amt))

            if blend_mode not in self.VALID_MODES:
                blend_mode = "override"

            for i in range(4):
                if zone_mask[i]:
                    top_rgb = _hex_to_rgb(colors[i])
                    result[i] = _blend_channels(result[i], top_rgb,
                                                blend_amt, blend_mode)

        return [_rgb_to_hex(*c) for c in result]
