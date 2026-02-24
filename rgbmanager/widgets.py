"""
widgets.py — Cairo custom GTK3 widgets for HP OMEN RGB Manager.

Three standalone, import-safe drawing widgets:
  - CircularKnob   : arc knob with CW/CCW direction support
  - KeyboardVisual : 4-zone keyboard diagram (click = zone picker)
  - ColorCircle    : small clickable colored dot per zone
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
import cairo
import math

from .constants import (
    C_TEXT, C_MUTED, C_PRIMARY,
    KNOB_START_A, KNOB_SWEEP, KNOB_END_A, KNOB_GAP_HALF, KNOB_LINE_W,
    hex_to_rgb,
)


# ══════════════════════════════════════════════════════════════════════════════
#  CIRCULAR KNOB
# ══════════════════════════════════════════════════════════════════════════════
class CircularKnob(Gtk.DrawingArea):
    """
    Arc knob drawn with Cairo.

    - clockwise=True  : arc fills left-to-right (standard)
    - clockwise=False : arc fills right-to-left (reversed, drag inverted)
    - Observer list   : on_change() supports multiple subscribers
    - Pointer cursor  : set on realize
    """

    def __init__(self, min_val=0, max_val=255, value=100, label="",
                 arc_color=C_PRIMARY, size=110, int_only=True, clockwise=True):
        super().__init__()
        self.min_val   = min_val
        self.max_val   = max_val
        self._value    = value
        self.label     = label
        self.arc_color = arc_color
        self.size      = size
        self.int_only  = int_only
        self.clockwise = clockwise
        self._dragging  = False
        self._callbacks = []

        self.set_size_request(size, size + 24)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK   |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK         |
            Gdk.EventMask.ENTER_NOTIFY_MASK
        )
        self.connect("draw",                 self._on_draw)
        self.connect("button-press-event",   self._on_press)
        self.connect("button-release-event", self._on_release)
        self.connect("motion-notify-event",  self._on_motion)
        self.connect("scroll-event",         self._on_scroll)
        self.connect("realize",              self._on_realize)

    def _on_realize(self, widget):
        cursor = Gdk.Cursor.new_from_name(self.get_display(), "pointer")
        self.get_window().set_cursor(cursor)

    # ── Value ──────────────────────────────────────────────────────────────────
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        clamped = max(self.min_val, min(self.max_val, v))
        self._value = int(clamped) if self.int_only else clamped
        self.queue_draw()

    # ── Observer ───────────────────────────────────────────────────────────────
    def on_change(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def _emit_change(self):
        for cb in self._callbacks:
            cb(self._value)

    # ── Geometry ───────────────────────────────────────────────────────────────
    def _frac(self):
        raw = (self._value - self.min_val) / (self.max_val - self.min_val)
        return raw if self.clockwise else 1.0 - raw

    def _val_angle(self):
        return KNOB_START_A + self._frac() * KNOB_SWEEP

    # ── Drawing ────────────────────────────────────────────────────────────────
    def _on_draw(self, widget, cr):
        w  = self.get_allocated_width()
        h  = self.get_allocated_height()
        cx = w / 2
        cy = (h - 24) / 2
        r  = min(cx, cy) - 8
        val_a = self._val_angle()

        # Background track
        cr.set_line_width(KNOB_LINE_W)
        cr.set_source_rgba(0.15, 0.12, 0.25, 1)
        cr.arc(cx, cy, r, KNOB_START_A, KNOB_END_A)
        cr.stroke()

        # Value arc glow
        cr.set_line_width(KNOB_LINE_W + 6)
        cr.set_source_rgba(*self.arc_color, 0.18)
        if self.clockwise:
            cr.arc(cx, cy, r, KNOB_START_A, val_a)
        else:
            cr.arc_negative(cx, cy, r, val_a, KNOB_START_A)
        cr.stroke()

        # Value arc solid
        cr.set_line_width(KNOB_LINE_W)
        cr.set_source_rgba(*self.arc_color, 1)
        if self.clockwise:
            cr.arc(cx, cy, r, KNOB_START_A, val_a)
        else:
            cr.arc_negative(cx, cy, r, val_a, KNOB_START_A)
        cr.stroke()

        # Handle dot
        hx = cx + r * math.cos(val_a)
        hy = cy + r * math.sin(val_a)
        cr.set_source_rgba(*self.arc_color, 0.4)
        cr.arc(hx, hy, 8, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(*C_TEXT, 1)
        cr.arc(hx, hy, 5, 0, 2 * math.pi)
        cr.fill()

        # Centre value text
        val_str = str(int(self._value)) if self.int_only else f"{self._value:.1f}"
        cr.set_source_rgba(*C_TEXT, 1)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(24)
        ext = cr.text_extents(val_str)
        cr.move_to(cx - ext.width / 2, cy + ext.height / 2)
        cr.show_text(val_str)

        # Direction indicator inside arc
        indicator = "\u21bb" if self.clockwise else "\u21ba"
        cr.set_source_rgba(*self.arc_color, 0.7)
        cr.set_font_size(13)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ext2 = cr.text_extents(indicator)
        cr.move_to(cx - ext2.width / 2, cy + r * 0.45)
        cr.show_text(indicator)

        # Range label
        if self.label:
            cr.set_source_rgba(*C_MUTED, 1)
            cr.set_font_size(11)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ext = cr.text_extents(self.label)
            cr.move_to(cx - ext.width / 2, h - 5)
            cr.show_text(self.label)

    # ── Interaction ────────────────────────────────────────────────────────────
    def _get_raw_angle(self, x, y):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        cx, cy = w / 2, (h - 24) / 2
        a = math.atan2(y - cy, x - cx)
        return a + 2 * math.pi if a < 0 else a

    def _update_from_event(self, x, y):
        angle = self._get_raw_angle(x, y)
        rel = angle - KNOB_START_A
        if rel < -KNOB_GAP_HALF:
            rel += 2 * math.pi
        frac = max(0.0, min(1.0, rel / KNOB_SWEEP))
        if not self.clockwise:
            frac = 1.0 - frac
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
        delta = step if ev.direction == Gdk.ScrollDirection.UP else -step
        if not self.clockwise:
            delta = -delta
        self.value = self._value + delta
        self._emit_change()

    def toggle_direction(self):
        """Flip CW <-> CCW."""
        self.clockwise = not self.clockwise
        self.queue_draw()


# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARD VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════════
class KeyboardVisual(Gtk.DrawingArea):
    """4-zone keyboard diagram. Click a zone to invoke the color picker callback."""

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

    # ── Drawing ────────────────────────────────────────────────────────────────
    def _on_draw(self, widget, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        pad = 8
        kw = w - 2 * pad
        kh = h - 2 * pad
        zone_w = kw / 4
        corner_r = 8

        # Keyboard frame
        cr.set_source_rgba(0.12, 0.10, 0.20, 1)
        self._rounded_rect(cr, pad-2, pad-2, kw+4, kh+4, corner_r+2)
        cr.fill()

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

            # Glow overlay
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
            cr.set_source_rgba(0.05, 0.05, 0.1, 0.85) if lum > 0.55 else cr.set_source_rgba(1, 1, 1, 0.7)
            cr.set_font_size(12)
            cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ext = cr.text_extents(zone_labels[i])
            cr.move_to(x + zone_w/2 - ext.width/2, pad + kh/2 + ext.height/2)
            cr.show_text(zone_labels[i])

            # Divider
            if i < 3:
                cr.set_source_rgba(0.05, 0.05, 0.1, 0.5)
                cr.set_line_width(1)
                cr.move_to(x + zone_w, pad + 4)
                cr.line_to(x + zone_w, pad + kh - 4)
                cr.stroke()

        # Hint text
        cr.set_source_rgba(*C_MUTED, 0.6)
        cr.set_font_size(10)
        hint = "CLICK A ZONE TO CHANGE ITS COLOR"
        ext = cr.text_extents(hint)
        cr.move_to(w/2 - ext.width/2, h - 1)
        cr.show_text(hint)

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x+w-r, y+r,   r, -math.pi/2, 0)
        cr.arc(x+w-r, y+h-r, r, 0, math.pi/2)
        cr.arc(x+r,   y+h-r, r, math.pi/2, math.pi)
        cr.arc(x+r,   y+r,   r, math.pi, 3*math.pi/2)
        cr.close_path()

    def _rounded_rect_partial(self, cr, x, y, w, h, r, left=False, right=False):
        cr.new_sub_path()
        if right:
            cr.arc(x+w-r, y+r,   r, -math.pi/2, 0)
            cr.arc(x+w-r, y+h-r, r, 0, math.pi/2)
        else:
            cr.line_to(x+w, y)
            cr.line_to(x+w, y+h)
        if left:
            cr.arc(x+r, y+h-r, r, math.pi/2, math.pi)
            cr.arc(x+r, y+r,   r, math.pi, 3*math.pi/2)
        else:
            cr.line_to(x, y+h)
            cr.line_to(x, y)
        cr.close_path()

    def _on_click(self, w, ev):
        if self._click_callback and ev.button == 1:
            alloc_w = self.get_allocated_width()
            zone_w = (alloc_w - 16) / 4
            zone_idx = max(0, min(3, int((ev.x - 8) / zone_w)))
            self._click_callback(zone_idx)


# ══════════════════════════════════════════════════════════════════════════════
#  COLOR CIRCLE
# ══════════════════════════════════════════════════════════════════════════════
class ColorCircle(Gtk.DrawingArea):
    """Small clickable colored circle showing one zone's current color."""

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

        cr.set_source_rgba(*self.color, 0.3)
        cr.arc(cx, cy, r+3, 0, 2*math.pi)
        cr.fill()

        cr.set_source_rgba(*self.color, 1)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.fill()

        cr.set_source_rgba(1, 1, 1, 0.25)
        cr.set_line_width(1.5)
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.stroke()

        lum = 0.299*self.color[0] + 0.587*self.color[1] + 0.114*self.color[2]
        cr.set_source_rgba(0.05, 0.05, 0.1, 0.9) if lum > 0.55 else cr.set_source_rgba(1, 1, 1, 0.8)
        cr.set_font_size(11)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        label = str(self.idx)
        ext = cr.text_extents(label)
        cr.move_to(cx - ext.width/2, cy + ext.height/2)
        cr.show_text(label)

    def _on_click(self, w, ev):
        if self._callback and ev.button == 1:
            self._callback(self.idx)
