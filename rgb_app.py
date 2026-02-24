#!/usr/bin/env python3
"""
HP OMEN RGB Manager v3 — Redesigned UI
GTK3 + Cairo desktop app for HP OMEN 16 keyboard RGB control.

Two-column layout with circular knobs, keyboard visualization,
and retro-futurism gaming aesthetic.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

import cairo
import math
import subprocess
import threading

SYSFS_BASE = "/sys/devices/platform/omen-rgb-keyboard/rgb_zones"

# ── Animation modes (from kernel source) ──────────────────────────────────────
ANIMATION_MODES = [
    ("static",    "Static",     "Solid static colors"),
    ("breathing", "Breathing",  "Zones pulse in and out"),
    ("rainbow",   "Rainbow",    "Full spectrum cycle"),
    ("wave",      "Wave",       "Colors ripple across zones"),
    ("pulse",     "Pulse",      "Sharp pulse of zone colors"),
    ("chase",     "Chase",      "Lit zone sweeps across"),
    ("sparkle",   "Sparkle",    "White sparks flash"),
    ("candle",    "Candle",     "Warm amber flicker"),
    ("aurora",    "Aurora",     "Green-blue aurora sweep"),
    ("disco",     "Disco",      "Fast RGB strobe"),
]

STATIC_PRESETS = {
    "Gaming":    ["FF0000", "FF0000", "FF0000", "FF0000"],
    "Ocean":     ["0033FF", "0099FF", "00CCFF", "00FFFF"],
    "Synthwave": ["FF00FF", "AA00FF", "FF0066", "AA00FF"],
    "Matrix":    ["00FF00", "00CC00", "009900", "006600"],
    "Sunset":    ["FF6600", "FF3300", "FF6600", "FFAA00"],
    "White":     ["FFFFFF", "FFFFFF", "FFFFFF", "FFFFFF"],
    "Off":       ["000000", "000000", "000000", "000000"],
}

DYNAMIC_PRESETS = {
    "Breathe Blue":  (["0055FF", "0055FF", "0055FF", "0055FF"], "breathing", 2),
    "Rainbow Rush":  (["FF0000", "00FF00", "0000FF", "FF00FF"], "rainbow",   6),
    "Ocean Wave":    (["0033FF", "0099FF", "00CCFF", "00FFFF"], "wave",      3),
    "Sparkle Red":   (["FF0000", "FF0000", "FF0000", "FF0000"], "sparkle",   4),
    "Candlelight":   (["FF6600", "FF3300", "FF6600", "FFAA00"], "candle",    5),
    "Aurora":        (["00FF88", "00CCAA", "00FFCC", "009966"], "aurora",    2),
    "Disco Fever":   (["FF0000", "00FF00", "0000FF", "FF00FF"], "disco",     8),
    "Heartbeat":     (["FF0000", "FF0000", "FF0000", "FF0000"], "pulse",     7),
    "Blue Chase":    (["0055FF", "0055FF", "0055FF", "0055FF"], "chase",     5),
}

# ── Color Palette (Retro-Futurism / Gaming) ───────────────────────────────────
C_BG       = (0.059, 0.059, 0.137)   # #0F0F23
C_CARD     = (0.086, 0.071, 0.157)   # #161228
C_CARD_B   = (0.188, 0.212, 0.239)   # #30363D  (border)
C_PRIMARY  = (0.486, 0.227, 0.929)   # #7C3AED
C_SECOND   = (0.655, 0.545, 0.980)   # #A78BFA
C_ACCENT   = (0.957, 0.247, 0.369)   # #F43F5E
C_TEXT     = (0.886, 0.910, 0.941)   # #E2E8F0
C_MUTED    = (0.392, 0.455, 0.545)   # #64748B
C_GLOW_P   = (0.486, 0.227, 0.929, 0.35)
C_GLOW_A   = (0.957, 0.247, 0.369, 0.35)

def hex_to_rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255)

def rgb_to_hex(r, g, b):
    return f"{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"

CSS = b"""
window { background-color: #0F0F23; }

.header-title {
    font-size: 18px;
    font-weight: bold;
    color: #E2E8F0;
    letter-spacing: 1px;
}
.header-sub {
    font-size: 9px;
    color: #64748B;
    letter-spacing: 3px;
}
.section-label {
    font-size: 9px;
    font-weight: bold;
    color: #7C3AED;
    letter-spacing: 2px;
}
.card {
    background-color: #161228;
    border-radius: 10px;
    padding: 12px;
    border: 1px solid #2A2545;
}
.mode-btn {
    border-radius: 6px;
    font-size: 10px;
    font-weight: 600;
    color: #E2E8F0;
    padding: 6px 4px;
    background-color: #1E1840;
    border: 1px solid #2A2545;
}
.mode-btn:hover {
    background-color: #2A2545;
    border-color: #7C3AED;
}
.mode-active {
    background-color: #2D1B69;
    border: 1px solid #7C3AED;
    color: #A78BFA;
}
.preset-btn {
    border-radius: 6px;
    font-size: 9px;
    font-weight: 600;
    color: #E2E8F0;
    padding: 5px 4px;
    background-color: #1E1840;
    border: 1px solid #2A2545;
}
.preset-btn:hover {
    background-color: #2A2545;
    border-color: #A78BFA;
}
.dpreset-btn {
    border-radius: 6px;
    font-size: 9px;
    font-weight: 600;
    color: #E2E8F0;
    padding: 5px 4px;
    background-color: #1E1840;
    border: 1px solid #2A2545;
}
.dpreset-btn:hover {
    background-color: #2A2545;
    border-color: #F43F5E;
}
.set-all-btn {
    border-radius: 6px;
    font-size: 10px;
    font-weight: bold;
    color: #0F0F23;
    padding: 6px 10px;
    background-color: #7C3AED;
    border: none;
}
.set-all-btn:hover {
    background-color: #A78BFA;
}
.status-bar {
    font-size: 10px;
    color: #64748B;
}
.status-ok  { color: #34D399; }
.status-err { color: #F43F5E; }
.desc-label {
    font-size: 9px;
    color: #64748B;
    font-style: italic;
}
.knob-label {
    font-size: 9px;
    font-weight: bold;
    color: #A78BFA;
    letter-spacing: 2px;
}
"""


# ══════════════════════════════════════════════════════════════════════════════
#  SERVICE LAYER (unchanged)
# ══════════════════════════════════════════════════════════════════════════════
class RGBService:
    def _write(self, node, value):
        path = f"{SYSFS_BASE}/{node}"
        try:
            proc = subprocess.run(
                ["sudo", "/usr/bin/tee", path],
                input=value.strip().encode(),
                capture_output=True, timeout=4,
            )
            return (True, "") if proc.returncode == 0 else (False, proc.stderr.decode().strip())
        except Exception as e:
            return (False, str(e))

    def set_zone_color(self, zone, hex_color):
        return self._write(zone, hex_color.lstrip("#").upper())

    def set_brightness(self, value):
        return self._write("brightness", str(int(value)))

    def set_mute_led(self, state):
        return self._write("mute_led", "1" if state else "0")

    def set_animation(self, mode):
        return self._write("animation_mode", mode)

    def set_speed(self, value):
        return self._write("animation_speed", str(max(1, min(10, int(value)))))

    def apply_preset(self, colors):
        for i, h in enumerate(colors):
            ok, err = self.set_zone_color(f"zone0{i}", h)
            if not ok:
                return (False, err)
        return (True, "")

    def apply_dynamic_preset(self, colors, mode, speed):
        ok, err = self.apply_preset(colors)
        if not ok: return (False, err)
        ok, err = self.set_animation(mode)
        if not ok: return (False, err)
        return self.set_speed(speed)


# ══════════════════════════════════════════════════════════════════════════════
#  CIRCULAR KNOB WIDGET (Cairo)
# ══════════════════════════════════════════════════════════════════════════════
class CircularKnob(Gtk.DrawingArea):
    """A circular arc knob drawn with Cairo. Click-and-drag to adjust value."""

    def __init__(self, min_val=0, max_val=255, value=100, label="",
                 arc_color=C_PRIMARY, size=110, int_only=True):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        self._value = value
        self.label = label
        self.arc_color = arc_color
        self.size = size
        self.int_only = int_only
        self._dragging = False
        self._callback = None

        self.set_size_request(size, size + 18)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK
        )
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_press)
        self.connect("button-release-event", self._on_release)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("scroll-event", self._on_scroll)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = max(self.min_val, min(self.max_val, v))
        if self.int_only:
            self._value = int(self._value)
        self.queue_draw()

    def on_change(self, callback):
        self._callback = callback

    def _emit_change(self):
        if self._callback:
            self._callback(self._value)

    def _angle_from_value(self, v):
        frac = (v - self.min_val) / (self.max_val - self.min_val)
        return -0.75 * math.pi + frac * 1.5 * math.pi  # 225° sweep from bottom-left

    def _value_from_angle(self, angle):
        # Normalize angle to our arc range
        start = -0.75 * math.pi
        frac = (angle - start) / (1.5 * math.pi)
        frac = max(0, min(1, frac))
        return self.min_val + frac * (self.max_val - self.min_val)

    def _on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        cx = w / 2
        cy = (h - 18) / 2
        r = min(cx, cy) - 8

        line_w = 6
        start_a = 0.75 * math.pi  # 135° (bottom-left)
        end_a = 2.25 * math.pi    # 405° (bottom-right, wrapping)
        val_a = start_a + ((self._value - self.min_val) / (self.max_val - self.min_val)) * 1.5 * math.pi

        # Background track
        cr.set_line_width(line_w)
        cr.set_source_rgba(0.15, 0.12, 0.25, 1)
        cr.arc(cx, cy, r, start_a, end_a)
        cr.stroke()

        # Value arc (with glow)
        # Glow
        cr.set_line_width(line_w + 6)
        cr.set_source_rgba(*self.arc_color, 0.2)
        cr.arc(cx, cy, r, start_a, val_a)
        cr.stroke()
        # Main arc
        cr.set_line_width(line_w)
        cr.set_source_rgba(*self.arc_color, 1)
        cr.arc(cx, cy, r, start_a, val_a)
        cr.stroke()

        # Handle dot
        hx = cx + r * math.cos(val_a)
        hy = cy + r * math.sin(val_a)
        # Glow
        cr.set_source_rgba(*self.arc_color, 0.4)
        cr.arc(hx, hy, 8, 0, 2 * math.pi)
        cr.fill()
        # Dot
        cr.set_source_rgba(*C_TEXT, 1)
        cr.arc(hx, hy, 5, 0, 2 * math.pi)
        cr.fill()

        # Value text in center
        val_str = str(int(self._value)) if self.int_only else f"{self._value:.1f}"
        cr.set_source_rgba(*C_TEXT, 1)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(18)
        ext = cr.text_extents(val_str)
        cr.move_to(cx - ext.width/2, cy + ext.height/2)
        cr.show_text(val_str)

        # Label below
        if self.label:
            cr.set_source_rgba(*C_MUTED, 1)
            cr.set_font_size(9)
            ext = cr.text_extents(self.label)
            cr.move_to(cx - ext.width/2, h - 4)
            cr.show_text(self.label)

    def _get_angle(self, x, y):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        cx = w / 2
        cy = (h - 18) / 2
        angle = math.atan2(y - cy, x - cx)
        # Normalize to 0..2pi
        if angle < 0:
            angle += 2 * math.pi
        return angle

    def _update_from_event(self, x, y):
        angle = self._get_angle(x, y)
        start_a = 0.75 * math.pi
        # Map angle into [start_a, start_a + 1.5pi]
        rel = angle - start_a
        if rel < -0.25 * math.pi:
            rel += 2 * math.pi
        frac = rel / (1.5 * math.pi)
        frac = max(0, min(1, frac))
        self.value = self.min_val + frac * (self.max_val - self.min_val)
        self._emit_change()

    def _on_press(self, w, ev):
        if ev.button == 1:
            self._dragging = True
            self._update_from_event(ev.x, ev.y)

    def _on_release(self, w, ev):
        self._dragging = False

    def _on_motion(self, w, ev):
        if self._dragging:
            self._update_from_event(ev.x, ev.y)

    def _on_scroll(self, w, ev):
        step = 1 if self.int_only else 0.5
        if ev.direction == Gdk.ScrollDirection.UP:
            self.value = self._value + step
        elif ev.direction == Gdk.ScrollDirection.DOWN:
            self.value = self._value - step
        self._emit_change()


# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARD VISUALIZATION WIDGET (Cairo)
# ══════════════════════════════════════════════════════════════════════════════
class KeyboardVisual(Gtk.DrawingArea):
    """Draws a 4-zone keyboard layout with colored zones. Click to pick color."""

    def __init__(self, zone_colors):
        super().__init__()
        self.zone_colors = [hex_to_rgb(c) for c in zone_colors]
        self._click_callback = None
        self.set_size_request(380, 130)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_click)

    def on_zone_click(self, callback):
        self._click_callback = callback

    def set_zone_color(self, idx, hex_color):
        self.zone_colors[idx] = hex_to_rgb(hex_color)
        self.queue_draw()

    def _on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()

        pad = 8
        kw = w - 2*pad
        kh = h - 2*pad
        zone_w = kw / 4
        corner_r = 8

        # Outer keyboard frame
        cr.set_source_rgba(0.12, 0.10, 0.20, 1)
        self._rounded_rect(cr, pad-2, pad-2, kw+4, kh+4, corner_r+2)
        cr.fill()

        # Draw 4 zones
        zone_labels = ["ZONE 0", "ZONE 1", "ZONE 2", "ZONE 3"]
        for i in range(4):
            x = pad + i * zone_w
            r, g, b = self.zone_colors[i]

            # Zone fill
            cr.set_source_rgba(r, g, b, 0.8)
            if i == 0:
                self._rounded_rect_partial(cr, x+1, pad, zone_w-2, kh, corner_r, left=True)
            elif i == 3:
                self._rounded_rect_partial(cr, x+1, pad, zone_w-2, kh, corner_r, right=True)
            else:
                cr.rectangle(x+1, pad, zone_w-2, kh)
            cr.fill()

            # Glow overlay at top
            grad = cairo.LinearGradient(x, pad, x, pad + kh*0.4)
            grad.add_color_stop_rgba(0, r, g, b, 0.6)
            grad.add_color_stop_rgba(1, r, g, b, 0.0)
            cr.set_source(grad)
            if i == 0:
                self._rounded_rect_partial(cr, x+1, pad, zone_w-2, kh*0.4, corner_r, left=True)
            elif i == 3:
                self._rounded_rect_partial(cr, x+1, pad, zone_w-2, kh*0.4, corner_r, right=True)
            else:
                cr.rectangle(x+1, pad, zone_w-2, kh*0.4)
            cr.fill()

            # Zone label
            lum = 0.299*r + 0.587*g + 0.114*b
            if lum > 0.55:
                cr.set_source_rgba(0.05, 0.05, 0.1, 0.85)
            else:
                cr.set_source_rgba(1, 1, 1, 0.7)
            cr.set_font_size(10)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ext = cr.text_extents(zone_labels[i])
            cr.move_to(x + zone_w/2 - ext.width/2, pad + kh/2 + ext.height/2)
            cr.show_text(zone_labels[i])

            # Divider line
            if i < 3:
                cr.set_source_rgba(0.05, 0.05, 0.1, 0.5)
                cr.set_line_width(1)
                cr.move_to(x + zone_w, pad + 4)
                cr.line_to(x + zone_w, pad + kh - 4)
                cr.stroke()

        # "Click a zone to change color" hint
        cr.set_source_rgba(*C_MUTED, 0.6)
        cr.set_font_size(8)
        hint = "CLICK A ZONE TO CHANGE ITS COLOR"
        ext = cr.text_extents(hint)
        cr.move_to(w/2 - ext.width/2, h - 1)
        cr.show_text(hint)

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x+w-r, y+r, r, -math.pi/2, 0)
        cr.arc(x+w-r, y+h-r, r, 0, math.pi/2)
        cr.arc(x+r, y+h-r, r, math.pi/2, math.pi)
        cr.arc(x+r, y+r, r, math.pi, 3*math.pi/2)
        cr.close_path()

    def _rounded_rect_partial(self, cr, x, y, w, h, r, left=False, right=False):
        cr.new_sub_path()
        if right:
            cr.arc(x+w-r, y+r, r, -math.pi/2, 0)
            cr.arc(x+w-r, y+h-r, r, 0, math.pi/2)
        else:
            cr.line_to(x+w, y)
            cr.line_to(x+w, y+h)
        if left:
            cr.arc(x+r, y+h-r, r, math.pi/2, math.pi)
            cr.arc(x+r, y+r, r, math.pi, 3*math.pi/2)
        else:
            cr.line_to(x, y+h)
            cr.line_to(x, y)
        cr.close_path()

    def _on_click(self, w, ev):
        if self._click_callback and ev.button == 1:
            alloc_w = self.get_allocated_width()
            pad = 8
            zone_w = (alloc_w - 2*pad) / 4
            zone_idx = int((ev.x - pad) / zone_w)
            zone_idx = max(0, min(3, zone_idx))
            self._click_callback(zone_idx)


# ══════════════════════════════════════════════════════════════════════════════
#  ZONE COLOR CIRCLE
# ══════════════════════════════════════════════════════════════════════════════
class ColorCircle(Gtk.DrawingArea):
    """A small clickable colored circle representing a zone."""

    def __init__(self, hex_color, idx):
        super().__init__()
        self.color = hex_to_rgb(hex_color)
        self.idx = idx
        self._callback = None
        self.set_size_request(36, 36)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_click)

    def set_color(self, hex_color):
        self.color = hex_to_rgb(hex_color)
        self.queue_draw()

    def on_click(self, callback):
        self._callback = callback

    def _on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        r = min(w, h) / 2 - 3
        cx, cy = w/2, h/2

        # Glow
        cr.set_source_rgba(*self.color, 0.3)
        cr.arc(cx, cy, r+3, 0, 2*math.pi)
        cr.fill()

        # Fill
        cr.set_source_rgba(*self.color, 1)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.fill()

        # Border
        cr.set_source_rgba(1, 1, 1, 0.25)
        cr.set_line_width(1.5)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()

        # Label
        lum = 0.299*self.color[0] + 0.587*self.color[1] + 0.114*self.color[2]
        if lum > 0.55:
            cr.set_source_rgba(0.05, 0.05, 0.1, 0.9)
        else:
            cr.set_source_rgba(1, 1, 1, 0.8)
        cr.set_font_size(9)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        label = str(self.idx)
        ext = cr.text_extents(label)
        cr.move_to(cx - ext.width/2, cy + ext.height/2)
        cr.show_text(label)

    def _on_click(self, w, ev):
        if self._callback and ev.button == 1:
            self._callback(self.idx)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class RGBManagerApp(Gtk.Application):

    def __init__(self):
        super().__init__(application_id="dev.omen.rgb-manager")
        self.service = RGBService()
        self._brightness_timer = None
        self._speed_timer = None
        self.zone_colors = ["FF0000", "FF0000", "FF0000", "FF0000"]
        self.active_mode_key = "static"
        self.current_speed = 1
        self._mode_buttons = {}

    def _async(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _status(self, msg, ok=True):
        GLib.idle_add(self._apply_status, msg, ok)

    def _apply_status(self, msg, ok):
        self.status_label.set_text(msg)
        ctx = self.status_label.get_style_context()
        ctx.remove_class("status-ok")
        ctx.remove_class("status-err")
        ctx.add_class("status-ok" if ok else "status-err")

    def _hex_to_rgba(self, h):
        rgba = Gdk.RGBA()
        rgba.parse(f"#{h.lstrip('#')}")
        return rgba

    def _rgba_to_hex(self, rgba):
        return f"{int(rgba.red*255):02X}{int(rgba.green*255):02X}{int(rgba.blue*255):02X}"

    def _highlight_mode(self, key):
        self.active_mode_key = key
        for k, btn in self._mode_buttons.items():
            ctx = btn.get_style_context()
            if k == key:
                ctx.add_class("mode-active")
                ctx.remove_class("mode-btn")
            else:
                ctx.remove_class("mode-active")
                ctx.add_class("mode-btn")

    # ── Build UI ──────────────────────────────────────────────────────────────
    def do_activate(self):
        self._apply_css()
        win = Gtk.ApplicationWindow(application=self)
        win.set_title("HP OMEN RGB Manager")
        win.set_default_size(860, 620)
        win.set_resizable(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(16)
        outer.set_margin_bottom(12)
        outer.set_margin_start(16)
        outer.set_margin_end(16)
        win.add(outer)

        # Header
        outer.pack_start(self._build_header(), False, False, 0)
        outer.pack_start(self._vspace(12), False, False, 0)

        # Main two-column layout
        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        columns.pack_start(self._build_left_panel(), True, True, 0)
        columns.pack_start(self._build_right_panel(), True, True, 0)
        outer.pack_start(columns, True, True, 0)

        # Status bar
        outer.pack_start(self._vspace(8), False, False, 0)
        outer.pack_start(self._build_status_bar(), False, False, 0)

        win.show_all()

    def _apply_css(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)

    def _vspace(self, px):
        b = Gtk.Box()
        b.set_size_request(-1, px)
        return b

    def _sec(self, text):
        lbl = Gtk.Label(label=text)
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("section-label")
        return lbl

    # ── Header ──────────────────────────────────────────────────────────────
    def _build_header(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        t = Gtk.Label(label="HP OMEN RGB")
        t.set_halign(Gtk.Align.START)
        t.get_style_context().add_class("header-title")
        s = Gtk.Label(label="KEYBOARD CONTROL CENTER")
        s.set_halign(Gtk.Align.START)
        s.get_style_context().add_class("header-sub")
        left.pack_start(t, False, False, 0)
        left.pack_start(s, False, False, 0)
        box.pack_start(left, True, True, 0)
        return box

    # ── Left Panel ────────────────────────────────────────────────────────────
    def _build_left_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.set_size_request(420, -1)

        # Keyboard visual card
        kb_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kb_card.get_style_context().add_class("card")
        kb_card.pack_start(self._sec("KEYBOARD ZONES"), False, False, 0)

        self.keyboard_visual = KeyboardVisual(self.zone_colors)
        self.keyboard_visual.on_zone_click(self._open_zone_picker)
        kb_card.pack_start(self.keyboard_visual, False, False, 0)

        # Zone circles + Set All row
        zone_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        zone_row.set_halign(Gtk.Align.CENTER)
        self.color_circles = []
        for i in range(4):
            circle = ColorCircle(self.zone_colors[i], i)
            circle.on_click(self._open_zone_picker)
            zone_row.pack_start(circle, False, False, 0)
            self.color_circles.append(circle)

        set_all = Gtk.Button(label="SET ALL")
        set_all.get_style_context().add_class("set-all-btn")
        set_all.connect("clicked", self._on_set_all)
        zone_row.pack_start(set_all, False, False, 4)
        kb_card.pack_start(zone_row, False, False, 0)

        panel.pack_start(kb_card, False, False, 0)

        # Static Presets card
        sp_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sp_card.get_style_context().add_class("card")
        sp_card.pack_start(self._sec("STATIC PRESETS"), False, False, 0)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(4)
        flow.set_row_spacing(4)
        flow.set_homogeneous(True)
        for name, colors in STATIC_PRESETS.items():
            btn = Gtk.Button(label=name)
            btn.get_style_context().add_class("preset-btn")
            btn.connect("clicked", self._on_static_preset, name, colors)
            flow.add(btn)
        sp_card.pack_start(flow, False, False, 0)
        panel.pack_start(sp_card, False, False, 0)

        return panel

    # ── Right Panel ───────────────────────────────────────────────────────────
    def _build_right_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Knobs row
        knobs_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        knobs_card.get_style_context().add_class("card")
        knobs_card.set_halign(Gtk.Align.CENTER)

        # Brightness knob
        bright_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        bright_lbl = Gtk.Label(label="BRIGHTNESS")
        bright_lbl.get_style_context().add_class("knob-label")
        self.brightness_knob = CircularKnob(
            min_val=0, max_val=255, value=100,
            label="0 — 255", arc_color=C_PRIMARY, size=110
        )
        self.brightness_knob.on_change(self._on_brightness_knob)
        bright_box.pack_start(bright_lbl, False, False, 0)
        bright_box.pack_start(self.brightness_knob, False, False, 0)
        knobs_card.pack_start(bright_box, False, False, 10)

        # Speed knob
        speed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        speed_lbl = Gtk.Label(label="SPEED")
        speed_lbl.get_style_context().add_class("knob-label")
        self.speed_knob = CircularKnob(
            min_val=1, max_val=10, value=1,
            label="1 — 10", arc_color=C_ACCENT, size=110
        )
        self.speed_knob.on_change(self._on_speed_knob)
        speed_box.pack_start(speed_lbl, False, False, 0)
        speed_box.pack_start(self.speed_knob, False, False, 0)
        knobs_card.pack_start(speed_box, False, False, 10)

        panel.pack_start(knobs_card, False, False, 0)

        # Animation Mode card
        anim_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        anim_card.get_style_context().add_class("card")
        anim_card.pack_start(self._sec("ANIMATION MODE"), False, False, 0)

        self.mode_desc_lbl = Gtk.Label(label="Solid static colors")
        self.mode_desc_lbl.set_halign(Gtk.Align.START)
        self.mode_desc_lbl.get_style_context().add_class("desc-label")
        anim_card.pack_start(self.mode_desc_lbl, False, False, 0)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(5)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(4)
        flow.set_row_spacing(4)
        flow.set_homogeneous(True)
        for key, label, desc in ANIMATION_MODES:
            btn = Gtk.Button(label=label)
            ctx = btn.get_style_context()
            ctx.add_class("mode-btn")
            if key == "static":
                ctx.add_class("mode-active")
                ctx.remove_class("mode-btn")
            btn.connect("clicked", self._on_mode_click, key, desc)
            flow.add(btn)
            self._mode_buttons[key] = btn
        anim_card.pack_start(flow, False, False, 0)
        panel.pack_start(anim_card, False, False, 0)

        # Dynamic Presets card
        dp_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        dp_card.get_style_context().add_class("card")
        dp_card.pack_start(self._sec("DYNAMIC PRESETS"), False, False, 0)

        flow2 = Gtk.FlowBox()
        flow2.set_max_children_per_line(3)
        flow2.set_selection_mode(Gtk.SelectionMode.NONE)
        flow2.set_column_spacing(4)
        flow2.set_row_spacing(4)
        flow2.set_homogeneous(True)
        for name, (colors, mode, speed) in DYNAMIC_PRESETS.items():
            btn = Gtk.Button(label=name)
            btn.get_style_context().add_class("dpreset-btn")
            btn.connect("clicked", self._on_dynamic_preset, name, colors, mode, speed)
            flow2.add(btn)
        dp_card.pack_start(flow2, False, False, 0)
        panel.pack_start(dp_card, False, False, 0)

        return panel

    # ── Zone color picking ────────────────────────────────────────────────────
    def _open_zone_picker(self, idx):
        dlg = Gtk.ColorChooserDialog(
            title=f"Zone {idx} Color",
            transient_for=self.get_windows()[0]
        )
        dlg.set_use_alpha(False)
        dlg.set_rgba(self._hex_to_rgba(self.zone_colors[idx]))
        if dlg.run() == Gtk.ResponseType.OK:
            h = self._rgba_to_hex(dlg.get_rgba())
            self.zone_colors[idx] = h
            self.keyboard_visual.set_zone_color(idx, h)
            self.color_circles[idx].set_color(h)
            self._status(f"Zone {idx} → #{h} …")
            self._async(self._do_zone, f"zone0{idx}", h)
        dlg.destroy()

    def _on_set_all(self, btn):
        dlg = Gtk.ColorChooserDialog(
            title="Set All Zones",
            transient_for=self.get_windows()[0]
        )
        dlg.set_use_alpha(False)
        if dlg.run() == Gtk.ResponseType.OK:
            h = self._rgba_to_hex(dlg.get_rgba())
            for i in range(4):
                self.zone_colors[i] = h
                self.keyboard_visual.set_zone_color(i, h)
                self.color_circles[i].set_color(h)
            self._status(f"All zones → #{h} …")
            self._async(self._do_zone, "all", h)
        dlg.destroy()

    def _do_zone(self, zone, h):
        ok, err = self.service.set_zone_color(zone, h)
        self._status(f"Zone {zone} → #{h} ✓" if ok else f"Error: {err}", ok)

    # ── Knob callbacks ────────────────────────────────────────────────────────
    def _on_brightness_knob(self, v):
        if self._brightness_timer:
            GLib.source_remove(self._brightness_timer)
        self._brightness_timer = GLib.timeout_add(300, self._fire_brightness, int(v))

    def _fire_brightness(self, v):
        self._brightness_timer = None
        self._status(f"Brightness → {v} …")
        self._async(self._do_brightness, v)
        return False

    def _do_brightness(self, v):
        ok, err = self.service.set_brightness(v)
        self._status(f"Brightness → {v} ✓" if ok else f"Error: {err}", ok)

    def _on_speed_knob(self, v):
        self.current_speed = int(v)
        if self._speed_timer:
            GLib.source_remove(self._speed_timer)
        self._speed_timer = GLib.timeout_add(300, self._fire_speed, int(v))

    def _fire_speed(self, v):
        self._speed_timer = None
        self._status(f"Speed → {v} …")
        self._async(self._do_speed, v)
        return False

    def _do_speed(self, v):
        ok, err = self.service.set_speed(v)
        self._status(f"Speed → {v} ✓" if ok else f"Error: {err}", ok)

    # ── Animation Mode ────────────────────────────────────────────────────────
    def _on_mode_click(self, btn, key, desc):
        self._highlight_mode(key)
        self.mode_desc_lbl.set_text(desc)
        self._status(f"Animation → {key} …")
        self._async(self._do_animation, key)

    def _do_animation(self, mode):
        ok, err = self.service.set_animation(mode)
        if ok and mode != "static":
            self.service.set_speed(self.current_speed)
        self._status(f"Animation: {mode} ✓" if ok else f"Error: {err}", ok)

    # ── Static Presets ────────────────────────────────────────────────────────
    def _on_static_preset(self, btn, name, colors):
        for i, c in enumerate(colors):
            self.zone_colors[i] = c
            self.keyboard_visual.set_zone_color(i, c)
            self.color_circles[i].set_color(c)
        self._highlight_mode("static")
        self._status(f"Preset: {name} …")
        self._async(self._do_static_preset, name, colors)

    def _do_static_preset(self, name, colors):
        ok, err = self.service.apply_preset(colors)
        if ok:
            ok2, err2 = self.service.set_animation("static")
            if ok2:
                self.service.set_speed(self.current_speed)
            ok, err = ok2, err2
        self._status(f"{name} ✓" if ok else f"Error: {err}", ok)

    # ── Dynamic Presets ───────────────────────────────────────────────────────
    def _on_dynamic_preset(self, btn, name, colors, mode, speed):
        for i, c in enumerate(colors):
            self.zone_colors[i] = c
            self.keyboard_visual.set_zone_color(i, c)
            self.color_circles[i].set_color(c)
        self._highlight_mode(mode)
        self.current_speed = speed
        self.speed_knob.value = speed

        for key, label, desc in ANIMATION_MODES:
            if key == mode:
                self.mode_desc_lbl.set_text(desc)
                break

        self._status(f"Dynamic: {name} …")
        self._async(self._do_dynamic_preset, name, colors, mode, speed)

    def _do_dynamic_preset(self, name, colors, mode, speed):
        ok, err = self.service.apply_dynamic_preset(colors, mode, speed)
        self._status(f"{name} ✓" if ok else f"Error: {err}", ok)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_status_bar(self):
        box = Gtk.Box()
        self.status_label = Gtk.Label(label="Ready — pick a zone, knob, or preset to begin.")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.get_style_context().add_class("status-bar")
        box.pack_start(self.status_label, True, True, 0)
        return box


if __name__ == "__main__":
    app = RGBManagerApp()
    app.run(None)
