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
    BLEND_MODES, BLEND_MODE_LABELS,
    C_PRIMARY, C_ACCENT, KNOB_DEBOUNCE,
)
from .service        import RGBService
from .layer_service  import LayerService, default_layer
from .compositor     import LayerCompositor
from .animator       import AnimationLoop, get_frame_colors
from .widgets        import CircularKnob, KeyboardVisual, ColorCircle
from .styles         import apply_css


class RGBManagerApp(Gtk.Application):
    """Main GTK application."""

    def __init__(self):
        super().__init__(application_id="dev.omen.rgb-manager")
        self.service     = RGBService()
        self.layer_svc   = LayerService()
        self.compositor  = LayerCompositor()
        self.anim_loop   = AnimationLoop(self.compositor, self.service)
        self._brightness_timer = None
        self._speed_timer = None

        # Read live keyboard state from sysfs before building the UI
        state = self.service.read_state()
        self.zone_colors       = state["zones"]
        self.active_mode_key   = state["mode"]
        self.current_speed     = state["speed"]
        self.current_direction = state["direction"]
        self._init_brightness  = state["brightness"]
        self._mode_buttons     = {}

        # Layer UI state
        self._layers_list_box  = None  # Gtk.ListBox ref
        self._layer_apply_btn  = None  # The composite+apply button

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

        # Start animation loop (Phase 2: replaces kernel timer)
        layers = self.layer_svc.load()
        self.anim_loop.update_layers(layers)
        self.anim_loop.start()

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

        # Layers panel
        panel.pack_start(self._build_layers_panel(), False, False, 0)

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

    # ── Application quit ───────────────────────────────────────────────────────
    def do_quit(self):
        self.anim_loop.stop()
        super().do_quit()

    # ══════════════════════════════════════════════════════════════════════════
    #  Layers panel
    # ══════════════════════════════════════════════════════════════════════════

    def _build_layers_panel(self):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("card")

        # Header row
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr.pack_start(self._sec("MY LAYERS"), True, True, 0)
        card.pack_start(hdr, False, False, 0)

        # Save row: name entry + save button
        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._layer_name_entry = Gtk.Entry()
        self._layer_name_entry.set_placeholder_text("Layer name...")
        self._layer_name_entry.set_hexpand(True)
        save_btn = Gtk.Button(label="Save Current")
        save_btn.get_style_context().add_class("layer-save-btn")
        save_btn.set_tooltip_text("Save current keyboard state as a new layer")
        save_btn.connect("clicked", self._on_layer_save)
        save_row.pack_start(self._layer_name_entry, True, True, 0)
        save_row.pack_start(save_btn, False, False, 0)
        card.pack_start(save_row, False, False, 0)

        # Scrollable layer list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(180)
        scroll.set_max_content_height(380)

        self._layers_list_box = Gtk.ListBox()
        self._layers_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._layers_list_box.get_style_context().add_class("layers-list")
        scroll.add(self._layers_list_box)
        card.pack_start(scroll, True, True, 0)
        self._refresh_layers_list()

        # Composite & Apply button
        self._layer_apply_btn = Gtk.Button(label="Composite & Apply All")
        self._layer_apply_btn.get_style_context().add_class("layer-apply-btn")
        self._layer_apply_btn.set_tooltip_text(
            "Blend all enabled layers and push the result to the keyboard")
        self._layer_apply_btn.connect("clicked", self._on_layer_composite_apply)
        card.pack_start(self._layer_apply_btn, False, False, 0)

        return card

    # ── Layers list helpers ────────────────────────────────────────────────────

    def _refresh_layers_list(self):
        """Rebuild the layer list box from disk."""
        box = self._layers_list_box
        for child in box.get_children():
            box.remove(child)

        layers = self.layer_svc.load()
        self.anim_loop.update_layers(layers)

        if not layers:
            lbl = Gtk.Label(label="No layers yet. Type a name above and click Save.")
            lbl.get_style_context().add_class("layers-empty")
            lbl.set_margin_top(8);  lbl.set_margin_bottom(8)
            box.add(lbl)
        else:
            for layer in layers:
                row = self._build_layer_row(layer)
                box.add(row)

        box.show_all()

    def _build_layer_row(self, layer: dict) -> Gtk.Widget:
        name       = layer.get("name", "?")
        enabled    = layer.get("enabled", True)
        zone_mask  = layer.get("zone_mask", [True, True, True, True])
        blend_mode = layer.get("blend_mode", "override")
        blend_amt  = int(layer.get("blend_amount", 1.0) * 100)
        mode       = layer.get("mode", "static")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.get_style_context().add_class("layer-row")
        outer.set_margin_bottom(2)

        # ── Top row: toggle | name | mode chip | reorder | delete ──────────────
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        sw = Gtk.Switch()
        sw.set_active(enabled)
        sw.set_valign(Gtk.Align.CENTER)
        sw.connect("notify::active", self._on_layer_toggle, name)
        top.pack_start(sw, False, False, 0)

        name_lbl = Gtk.Label(label=name)
        name_lbl.get_style_context().add_class("layer-name-lbl")
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        top.pack_start(name_lbl, True, True, 0)

        # Mode chip
        mode_chip = Gtk.Label(label=mode)
        mode_chip.get_style_context().add_class("desc-label")
        top.pack_start(mode_chip, False, False, 0)

        # Reorder buttons
        for arrow, direction in (("↑", "up"), ("↓", "down")):
            btn = Gtk.Button(label=arrow)
            btn.get_style_context().add_class("layer-reorder-btn")
            btn.connect("clicked", self._on_layer_reorder, name, direction)
            top.pack_start(btn, False, False, 0)

        # Delete button
        del_btn = Gtk.Button(label="✕")
        del_btn.get_style_context().add_class("layer-del-btn")
        del_btn.set_tooltip_text(f"Delete layer '{name}'")
        del_btn.connect("clicked", self._on_layer_delete, name)
        top.pack_start(del_btn, False, False, 0)

        outer.pack_start(top, False, False, 0)

        # ── Bottom row: zone mask | blend mode | opacity ───────────────────────
        bot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Zone mask toggle pills
        for i in range(4):
            z_btn = Gtk.Button(label=f"Z{i+1}")
            z_btn.get_style_context().add_class("zone-mask-btn")
            if zone_mask[i]:
                z_btn.get_style_context().add_class("zone-mask-active")
            z_btn.set_tooltip_text(f"Toggle zone {i+1} for this layer")
            z_btn.connect("clicked", self._on_zone_mask_toggle, name, i)
            bot.pack_start(z_btn, False, False, 0)

        # Blend mode combo
        combo = Gtk.ComboBoxText()
        combo.get_style_context().add_class("blend-combo")
        for m in BLEND_MODES:
            combo.append(m, BLEND_MODE_LABELS[m])
        combo.set_active_id(blend_mode)
        combo.set_tooltip_text("Blend mode for this layer")
        combo.connect("changed", self._on_blend_mode_change, name)
        bot.pack_start(combo, False, False, 0)

        # Opacity label + scale
        op_lbl = Gtk.Label(label="Opacity:")
        op_lbl.get_style_context().add_class("desc-label")
        bot.pack_start(op_lbl, False, False, 0)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        scale.set_value(blend_amt)
        scale.set_draw_value(False)
        scale.set_size_request(120, -1)
        scale.set_tooltip_text(f"Opacity: {blend_amt}%")
        scale.connect("value-changed", self._on_blend_amount_change, name)
        bot.pack_start(scale, False, False, 0)

        outer.pack_start(bot, False, False, 0)
        return outer

    # ── Layer callbacks ────────────────────────────────────────────────────────

    def _on_layer_save(self, btn):
        name = self._layer_name_entry.get_text().strip()
        if not name:
            self._status("Enter a layer name first.", False)
            return
        layer = default_layer(
            name        = name,
            zones       = list(self.zone_colors),
            mode        = self.active_mode_key,
            speed       = self.current_speed,
            brightness  = int(self.brightness_knob.value),
            direction   = self.current_direction,
        )
        self.layer_svc.upsert(layer)
        self._layer_name_entry.set_text("")
        self._refresh_layers_list()
        self._status(f"Layer '{name}' saved.")

    def _on_layer_toggle(self, sw, _param, name):
        self.layer_svc.update_field(name, "enabled", sw.get_active())
        self._refresh_layers_list()

    def _on_layer_reorder(self, btn, name, direction):
        self.layer_svc.move(name, direction)
        self._refresh_layers_list()

    def _on_layer_delete(self, btn, name):
        self.layer_svc.delete(name)
        self._refresh_layers_list()
        self._status(f"Layer '{name}' deleted.")

    def _on_zone_mask_toggle(self, btn, name, zone_idx):
        layers = self.layer_svc.load()
        for l in layers:
            if l.get("name") == name:
                mask = l.get("zone_mask", [True, True, True, True])
                mask[zone_idx] = not mask[zone_idx]
                l["zone_mask"] = mask
                break
        self.layer_svc.save(layers)
        self._refresh_layers_list()

    def _on_blend_mode_change(self, combo, name):
        mode = combo.get_active_id()
        if mode:
            self.layer_svc.update_field(name, "blend_mode", mode)
            self._refresh_layers_list()

    def _on_blend_amount_change(self, scale, name):
        amount = scale.get_value() / 100.0
        self.layer_svc.update_field(name, "blend_amount", round(amount, 2))
        self._refresh_layers_list()

    def _on_layer_composite_apply(self, btn):
        """Composite all enabled layers and push to hardware."""
        btn.set_sensitive(False)
        layers = self.layer_svc.load()
        import time as _time
        t = _time.monotonic()
        frame_colors = [get_frame_colors(l, t) for l in layers]
        final = self.compositor.composite(layers, frame_colors)
        # Update UI to reflect composed colors
        for i, c in enumerate(final):
            self.zone_colors[i] = c
            self.keyboard_visual.set_zone_color(i, c)
            self.color_circles[i].set_color(c)
        self._status("Compositing layers...")
        def _do():
            ok, err = self.service.apply_preset(final)
            GLib.idle_add(btn.set_sensitive, True)
            GLib.idle_add(self._status,
                          "Layers applied!" if ok else f"Error: {err}", ok)
        self._async(_do)
