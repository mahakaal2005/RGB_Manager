"""
styles.py — GTK3 CSS for HP OMEN RGB Manager.

Pure data — import and call apply_css() from do_activate().
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

CSS: bytes = b"""
window { background-color: #0F0F23; }

.header-title {
    font-size: 22px;
    font-weight: bold;
    color: #E2E8F0;
    letter-spacing: 1px;
}
.header-sub {
    font-size: 11px;
    color: #64748B;
    letter-spacing: 2.5px;
}
.section-label {
    font-size: 11px;
    font-weight: bold;
    color: #7C3AED;
    letter-spacing: 1.5px;
}
.card {
    background-color: #161228;
    border-radius: 12px;
    padding: 18px;
    border: 1px solid #2A2545;
}
.mode-btn {
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    color: #E2E8F0;
    padding: 8px 12px;
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
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #E2E8F0;
    padding: 7px 10px;
    background-color: #1E1840;
    border: 1px solid #2A2545;
}
.preset-btn:hover {
    background-color: #2A2545;
    border-color: #A78BFA;
}
.dpreset-btn {
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #E2E8F0;
    padding: 7px 10px;
    background-color: #1E1840;
    border: 1px solid #2A2545;
}
.dpreset-btn:hover {
    background-color: #2A2545;
    border-color: #F43F5E;
}
.set-all-btn {
    border-radius: 8px;
    font-size: 12px;
    font-weight: bold;
    color: #0F0F23;
    padding: 8px 16px;
    background-color: #7C3AED;
    border: none;
}
.set-all-btn:hover { background-color: #A78BFA; }
.reload-btn {
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    padding: 7px 16px;
    background-color: #1C1500;
    border: 1px solid #D97706;
    color: #FBBF24;
}
.reload-btn:hover { background-color: #D97706; color: #0F0F23; }
.reload-btn:disabled { opacity: 0.4; }
.status-bar {
    font-size: 11px;
    color: #94A3B8;
}
.status-ok  { color: #34D399; }
.status-err { color: #F85149; }
.desc-label {
    font-size: 12px;
    color: #64748B;
    font-style: normal;
}
.knob-label {
    font-size: 11px;
    font-weight: bold;
    color: #A78BFA;
    letter-spacing: 1.5px;
}
.dir-toggle-circle {
    border-radius: 50%;
    font-size: 13px;
    padding: 6px;
    background-color: #1E1840;
    border: 1px solid #2A2545;
    color: #64748B;
    min-width: 34px;
    min-height: 34px;
}
.dir-toggle-circle:hover {
    border-color: #7C3AED;
    color: #E2E8F0;
}
.dir-toggle-pill {
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    padding: 8px 14px;
    background-color: #1E1840;
    border: 1px solid #2A2545;
    color: #94A3B8;
}
.dir-toggle-pill:hover {
    border-color: #7C3AED;
    color: #E2E8F0;
}

/* ============ Layers panel ============ */
.layer-row {
    background-color: #1A1338;
    border-radius: 10px;
    padding: 12px 14px;
    border: 1px solid #2A2545;
    margin-bottom: 6px;
}
.layer-row:hover {
    border-color: #7C3AED;
}
.layer-name-lbl {
    font-size: 13px;
    font-weight: 600;
    color: #E2E8F0;
}
.zone-mask-btn {
    border-radius: 6px;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 8px;
    min-width: 34px;
    min-height: 28px;
    background-color: #2A2545;
    border: 1px solid #3A3560;
    color: #64748B;
}
.zone-mask-btn:hover { border-color: #7C3AED; }
.zone-mask-active {
    background-color: #2D1B69;
    border-color: #7C3AED;
    color: #A78BFA;
}
.layer-apply-btn {
    border-radius: 8px;
    font-size: 11px;
    font-weight: bold;
    padding: 7px 16px;
    background-color: #1B4D35;
    border: 1px solid #22C55E;
    color: #22C55E;
}
.layer-apply-btn:hover { background-color: #22C55E; color: #0F0F23; }
.layer-apply-btn:disabled { opacity: 0.4; }
.layer-del-btn {
    border-radius: 6px;
    font-size: 13px;
    padding: 4px 10px;
    min-height: 30px;
    background-color: transparent;
    border: 1px solid #3A2030;
    color: #64748B;
}
.layer-del-btn:hover { border-color: #F85149; color: #F85149; }
.layer-reorder-btn {
    border-radius: 6px;
    font-size: 13px;
    padding: 4px 9px;
    min-height: 30px;
    background-color: transparent;
    border: 1px solid #2A2545;
    color: #64748B;
    min-width: 32px;
}
.layer-reorder-btn:hover { border-color: #7C3AED; color: #A78BFA; }
.layers-empty {
    font-size: 12px;
    color: #394157;
    font-style: italic;
}
.blend-combo {
    font-size: 11px;
    color: #94A3B8;
    border-radius: 6px;
}
.layer-save-btn {
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    padding: 7px 14px;
    background-color: #2D1B69;
    border: 1px solid #7C3AED;
    color: #A78BFA;
}
.layer-save-btn:hover { background-color: #7C3AED; color: #fff; }
"""


def apply_css() -> None:
    """Load CSS into GTK global stylesheet. Call once from do_activate()."""
    prov = Gtk.CssProvider()
    prov.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
