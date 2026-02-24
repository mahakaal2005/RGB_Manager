"""
app.py — RGBManagerApp: GTK3 application class and all UI builder methods.

Imports only from sibling modules (one-way dependency chain):
  app -> widgets, service, styles, constants
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import threading

from .constants import (
    ANIMATION_MODES, STATIC_PRESETS, DYNAMIC_PRESETS,
    C_PRIMARY, C_ACCENT, KNOB_DEBOUNCE,
)
from .service  import RGBService
from .widgets  import CircularKnob, KeyboardVisual, ColorCircle
from .styles   import apply_css


class RGBManagerApp(Gtk.Application):
    """Main GTK application."""

    def __init__(self):
        super().__init__(application_id="dev.omen.rgb-manager")
        self.service = RGBService()
        self._brightness_timer = None
        self._speed_timer = None

        # Read live keyboard state from sysfs before building the UI
        state = self.service.read_state()
        self.zone_colors       = state["zones"]
        self.active_mode_key   = state["mode"]
        self.current_speed     = state["speed"]
        self.current_direction = state["direction"]
        self._init_brightness  = state["brightness"]
        self._mode_buttons = {}

    # ── Background tasks ───────────────────────────────────────────────────────
    def _async(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    # ── Status bar ─────────────────────────────────────────────────────────────
    def _status(self, msg, ok=True):
        GLib.idle_add(self._apply_status, msg, ok)

    def _apply_status(self, msg, ok):
        self.status_label.set_text(msg)
        ctx = self.status_label.get_style_context()
        ctx.remove_class("status-ok");  ctx.remove_class("status-err")
        ctx.add_class("status-ok" if ok else "status-err")

    # ── RGBA utility ───────────────────────────────────────────────────────────
    def _hex_to_rgba(self, h):
        rgba = Gdk.RGBA()
        rgba.parse(f"#{h.lstrip('#')}")
        return rgba

    def _rgba_to_hex(self, rgba):
        return f"{int(rgba.red*255):02X}{int(rgba.green*255):02X}{int(rgba.blue*255):02X}"

    # ── Mode highlight ─────────────────────────────────────────────────────────
    def _highlight_mode(self, key):
        self.active_mode_key = key
        for k, btn in self._mode_buttons.items():
            ctx = btn.get_style_context()
            if k == key:
                ctx.add_class("mode-active");  ctx.remove_class("mode-btn")
            else:
                ctx.remove_class("mode-active");  ctx.add_class("mode-btn")

    # ── Debounce ───────────────────────────────────────────────────────────────
    def _debounce(self, timer_attr: str, fn, *args):
        """Cancel pending sysfs write, schedule a new one after KNOB_DEBOUNCE ms."""
        existing = getattr(self, timer_attr, None)
        if existing:
            GLib.source_remove(existing)

        def _fire():
            setattr(self, timer_attr, None)
            fn(*args)
            return False

        setattr(self, timer_attr, GLib.timeout_add(KNOB_DEBOUNCE, _fire))

    # ══════════════════════════════════════════════════════════════════════════
    #  do_activate — Window construction entry point
    # ══════════════════════════════════════════════════════════════════════════
    def do_activate(self):
        apply_css()
        win = Gtk.ApplicationWindow(application=self)
        win.set_title("HP OMEN RGB Manager")
        win.set_default_size(900, 660)
        win.set_resizable(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        win.add(scroll)

        # Centering wrapper for horizontal expansion
        alignment_wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        alignment_wrapper.pack_start(Gtk.Box(), True, True, 0) # Left spring

        # Main content box (constrained width)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_size_request(880, -1)
        outer.set_margin_top(24);    outer.set_margin_bottom(24)
        alignment_wrapper.pack_start(outer, False, False, 0)

        alignment_wrapper.pack_start(Gtk.Box(), True, True, 0) # Right spring
        scroll.add(alignment_wrapper)

        outer.pack_start(self._build_header(),        False, False, 0)
        outer.pack_start(self._vspace(16),            False, False, 0)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        columns.pack_start(self._build_left_panel(),  False, False, 0)
        columns.pack_start(self._build_right_panel(), True,  True,  0)
        outer.pack_start(columns, True, True, 0)

        outer.pack_start(self._vspace(12),            False, False, 0)
        outer.pack_start(self._build_status_bar(),    False, False, 0)

        win.show_all()

    # ── Layout helpers ─────────────────────────────────────────────────────────
    def _vspace(self, px):
        b = Gtk.Box()
        b.set_size_request(-1, px)
        return b

    def _sec(self, text):
        lbl = Gtk.Label(label=text)
        lbl.set_halign(Gtk.Align.START)
        lbl.get_style_context().add_class("section-label")
        return lbl

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        box  = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,   spacing=1)
        t = Gtk.Label(label="HP OMEN RGB");           t.set_halign(Gtk.Align.START)
        t.get_style_context().add_class("header-title")
        s = Gtk.Label(label="KEYBOARD CONTROL CENTER"); s.set_halign(Gtk.Align.START)
        s.get_style_context().add_class("header-sub")
        left.pack_start(t, False, False, 0)
        left.pack_start(s, False, False, 0)
        box.pack_start(left, True, True, 0)
        return box

    # ── Left Panel ─────────────────────────────────────────────────────────────
    def _build_left_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.set_size_request(420, -1)

        # Keyboard visual
        kb_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kb_card.get_style_context().add_class("card")
        kb_card.pack_start(self._sec("KEYBOARD ZONES"), False, False, 0)
        self.keyboard_visual = KeyboardVisual(self.zone_colors)
        self.keyboard_visual.on_zone_click(self._open_zone_picker)
        kb_card.pack_start(self.keyboard_visual, False, False, 0)

        # Zone circles + Set All
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

        # Static Presets
        sp_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sp_card.get_style_context().add_class("card")
        sp_card.pack_start(self._sec("STATIC PRESETS"), False, False, 0)
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(4);  flow.set_row_spacing(4)
        flow.set_homogeneous(True)
        for name, colors in STATIC_PRESETS.items():
            btn = Gtk.Button(label=name)
            btn.get_style_context().add_class("preset-btn")
            btn.connect("clicked", self._on_static_preset, name, colors)
            flow.add(btn)
        sp_card.pack_start(flow, False, False, 0)
        panel.pack_start(sp_card, False, False, 0)

        return panel

    # ── Right Panel ────────────────────────────────────────────────────────────
    def _build_right_panel(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # ── Knobs card ──────────────────────────────────────────────────────
        knobs_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        knobs_card.get_style_context().add_class("card")
        knobs_card.set_halign(Gtk.Align.CENTER)

        def _make_knob_box(lbl_text, knob_widget):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            lbl = Gtk.Label(label=lbl_text)
            lbl.get_style_context().add_class("knob-label")
            dir_btn = Gtk.Button(label="\u21bb CW")
            dir_btn.get_style_context().add_class("dir-toggle-circle")
            dir_btn.set_halign(Gtk.Align.CENTER)
            dir_btn.set_tooltip_text("Toggle knob direction (CW <-> CCW)")

            def _on_dir_toggle(b, knob=knob_widget, btn=dir_btn):
                knob.toggle_direction()
                btn.set_label("\u21bb CW" if knob.clockwise else "\u21ba CCW")

            dir_btn.connect("clicked", _on_dir_toggle)
            box.pack_start(lbl,         False, False, 0)
            box.pack_start(knob_widget, False, False, 0)
            box.pack_start(dir_btn,     False, False, 0)
            return box

        self.brightness_knob = CircularKnob(
            min_val=0, max_val=255, value=self._init_brightness,
            label="0 - 255", arc_color=C_PRIMARY, size=110
        )
        self.brightness_knob.on_change(self._on_brightness_knob)
        knobs_card.pack_start(_make_knob_box("BRIGHTNESS", self.brightness_knob), False, False, 10)

        self.speed_knob = CircularKnob(
            min_val=1, max_val=10, value=self.current_speed,
            label="1 - 10", arc_color=C_ACCENT, size=110
        )
        self.speed_knob.on_change(self._on_speed_knob)
        knobs_card.pack_start(_make_knob_box("SPEED", self.speed_knob), False, False, 10)
        panel.pack_start(knobs_card, False, False, 0)

        # ── Animation Mode card (fixed Gtk.Grid to prevent FlowBox reflow) ──
        anim_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        anim_card.get_style_context().add_class("card")

        # Direction toggle row
        dir_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dir_row.pack_start(self._sec("ANIMATION MODE"), True, True, 0)
        dir_label = "LEFT -> RIGHT" if self.current_direction == "left_to_right" else "RIGHT -> LEFT"
        self._dir_btn = Gtk.Button(label=dir_label)
        self._dir_btn.get_style_context().add_class("dir-toggle-pill")
        self._dir_btn.set_tooltip_text("Toggle animation direction")
        self._dir_btn.connect("clicked", self._on_direction_toggle)
        dir_row.pack_start(self._dir_btn, False, False, 0)
        anim_card.pack_start(dir_row, False, False, 0)

        # Show description for the currently active mode
        current_desc = "Solid static colors"
        for key, label, desc in ANIMATION_MODES:
            if key == self.active_mode_key:
                current_desc = desc
                break
        self.mode_desc_lbl = Gtk.Label(label=current_desc)
        self.mode_desc_lbl.set_halign(Gtk.Align.START)
        self.mode_desc_lbl.get_style_context().add_class("desc-label")
        anim_card.pack_start(self.mode_desc_lbl, False, False, 0)

        COLS = 5
        grid = Gtk.Grid()
        grid.set_column_spacing(4);  grid.set_row_spacing(4)
        grid.set_column_homogeneous(True)
        for i, (key, label, desc) in enumerate(ANIMATION_MODES):
            btn = Gtk.Button(label=label)
            btn.set_hexpand(True)
            ctx = btn.get_style_context()
            ctx.add_class("mode-btn")
            if key == self.active_mode_key:   # highlight live mode, not always 'static'
                ctx.add_class("mode-active");  ctx.remove_class("mode-btn")
            btn.connect("clicked", self._on_mode_click, key, desc)
            grid.attach(btn, i % COLS, i // COLS, 1, 1)
            self._mode_buttons[key] = btn
        anim_card.pack_start(grid, False, False, 0)
        panel.pack_start(anim_card, False, False, 0)

        # ── Dynamic Presets card ─────────────────────────────────────────────
        dp_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        dp_card.get_style_context().add_class("card")
        dp_card.pack_start(self._sec("DYNAMIC PRESETS"), False, False, 0)
        flow2 = Gtk.FlowBox()
        flow2.set_max_children_per_line(3)
        flow2.set_selection_mode(Gtk.SelectionMode.NONE)
        flow2.set_column_spacing(4);  flow2.set_row_spacing(4)
        flow2.set_homogeneous(True)
        for name, (colors, mode, speed) in DYNAMIC_PRESETS.items():
            btn = Gtk.Button(label=name)
            btn.get_style_context().add_class("dpreset-btn")
            btn.connect("clicked", self._on_dynamic_preset, name, colors, mode, speed)
            flow2.add(btn)
        dp_card.pack_start(flow2, False, False, 0)
        panel.pack_start(dp_card, False, False, 0)

        return panel

    # ── Zone picking ───────────────────────────────────────────────────────────
    def _open_zone_picker(self, idx):
        dlg = Gtk.ColorChooserDialog(title=f"Zone {idx} Color",
                                     transient_for=self.get_windows()[0])
        dlg.set_use_alpha(False)
        dlg.set_rgba(self._hex_to_rgba(self.zone_colors[idx]))
        if dlg.run() == Gtk.ResponseType.OK:
            h = self._rgba_to_hex(dlg.get_rgba())
            self.zone_colors[idx] = h
            self.keyboard_visual.set_zone_color(idx, h)
            self.color_circles[idx].set_color(h)
            self._status(f"Zone {idx} -> #{h} ...")
            self._async(self._do_zone, f"zone0{idx}", h)
        dlg.destroy()

    def _on_set_all(self, btn):
        dlg = Gtk.ColorChooserDialog(title="Set All Zones",
                                     transient_for=self.get_windows()[0])
        dlg.set_use_alpha(False)
        if dlg.run() == Gtk.ResponseType.OK:
            h = self._rgba_to_hex(dlg.get_rgba())
            for i in range(4):
                self.zone_colors[i] = h
                self.keyboard_visual.set_zone_color(i, h)
                self.color_circles[i].set_color(h)
            self._status(f"All zones -> #{h} ...")
            self._async(self._do_zone, "all", h)
        dlg.destroy()

    def _do_zone(self, zone, h):
        ok, err = self.service.set_zone_color(zone, h)
        self._status(f"Zone {zone} -> #{h} OK" if ok else f"Error: {err}", ok)

    # ── Knob callbacks ─────────────────────────────────────────────────────────
    def _on_brightness_knob(self, v):
        self._status(f"Brightness -> {int(v)} ...")
        self._debounce("_brightness_timer", self._do_brightness, int(v))

    def _do_brightness(self, v):
        ok, err = self.service.set_brightness(v)
        self._status(f"Brightness -> {v} OK" if ok else f"Error: {err}", ok)

    def _on_speed_knob(self, v):
        self.current_speed = int(v)
        self._status(f"Speed -> {int(v)} ...")
        self._debounce("_speed_timer", self._do_speed, int(v))

    def _do_speed(self, v):
        ok, err = self.service.set_speed(v)
        self._status(f"Speed -> {v} OK" if ok else f"Error: {err}", ok)

    # ── Direction toggle ───────────────────────────────────────────────────────
    def _on_direction_toggle(self, btn):
        if self.current_direction == "left_to_right":
            self.current_direction = "right_to_left"
            self._dir_btn.set_label("RIGHT -> LEFT")
        else:
            self.current_direction = "left_to_right"
            self._dir_btn.set_label("LEFT -> RIGHT")
        self._status(f"Direction -> {self.current_direction} ...")
        self._async(self._do_direction, self.current_direction)

    def _do_direction(self, direction):
        ok, err = self.service.set_direction(direction)
        if ok:
            self._status(f"Direction: {direction} OK")
        elif "No such file" in err or "cannot open" in err.lower() or "Permission denied" in err:
            self._status("Direction: reboot required to load updated driver", False)
        else:
            self._status(f"Direction error: {err}", False)

    # ── Animation Mode ─────────────────────────────────────────────────────────
    def _on_mode_click(self, btn, key, desc):
        self._highlight_mode(key)
        self.mode_desc_lbl.set_text(desc)
        self._status(f"Animation -> {key} ...")
        self._async(self._do_animation, key)

    def _do_animation(self, mode):
        ok, err = self.service.set_animation(mode)
        if ok and mode != "static":
            self.service.set_speed(self.current_speed)
        self._status(f"Animation: {mode} OK" if ok else f"Error: {err}", ok)

    # ── Static Presets ─────────────────────────────────────────────────────────
    def _on_static_preset(self, btn, name, colors):
        for i, c in enumerate(colors):
            self.zone_colors[i] = c
            self.keyboard_visual.set_zone_color(i, c)
            self.color_circles[i].set_color(c)
        self._highlight_mode("static")
        self._status(f"Preset: {name} ...")
        self._async(self._do_static_preset, name, colors)

    def _do_static_preset(self, name, colors):
        ok, err = self.service.apply_preset(colors)
        if ok:
            ok2, err2 = self.service.set_animation("static")
            if ok2:
                self.service.set_speed(self.current_speed)
            ok, err = ok2, err2
        self._status(f"{name} OK" if ok else f"Error: {err}", ok)

    # ── Dynamic Presets ────────────────────────────────────────────────────────
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
        self._status(f"Dynamic: {name} ...")
        self._async(self._do_dynamic_preset, name, colors, mode, speed)

    def _do_dynamic_preset(self, name, colors, mode, speed):
        ok, err = self.service.apply_dynamic_preset(colors, mode, speed)
        self._status(f"{name} OK" if ok else f"Error: {err}", ok)

    # ── Status bar ─────────────────────────────────────────────────────────────
    def _build_status_bar(self):
        box = Gtk.Box()
        self.status_label = Gtk.Label(label="Ready - pick a zone, knob, or preset to begin.")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.get_style_context().add_class("status-bar")
        box.pack_start(self.status_label, True, True, 0)
        return box
