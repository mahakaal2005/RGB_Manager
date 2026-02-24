"""Entry point: python3 -m rgbmanager"""
import gi
gi.require_version("Gtk", "3.0")
import cairo  # noqa: F401 — must import early to register cairo.Context converter

from .app import RGBManagerApp

app = RGBManagerApp()
app.run(None)
