"""
layer_service.py — JSON-backed layer persistence for HP OMEN RGB Manager.

Stores layers as an ordered list (not a dict) so compositor priority order
is defined and stable.  All file I/O is atomic (write to temp → os.replace).
"""
import json
import os
import tempfile
from pathlib import Path


CONFIG_DIR  = Path.home() / ".config" / "omen-rgb-manager"
LAYERS_FILE = CONFIG_DIR / "layers.json"

# ── Default layer template ─────────────────────────────────────────────────

def default_layer(name: str, zones: list, mode: str = "static",
                  speed: int = 1, brightness: int = 100,
                  direction: str = "left_to_right") -> dict:
    return {
        "name":         name,
        "zones":        zones,          # list of 4 hex strings
        "zone_mask":    [True, True, True, True],
        "mode":         mode,
        "speed":        speed,
        "brightness":   brightness,
        "direction":    direction,
        "blend_mode":   "override",
        "blend_amount": 1.0,
        "enabled":      True,
    }


# ── Service ────────────────────────────────────────────────────────────────

class LayerService:
    """Manages the ordered list of layers stored in layers.json."""

    def __init__(self, path: Path = LAYERS_FILE):
        self.path = path
        os.makedirs(self.path.parent, exist_ok=True)

    # ── Read ───────────────────────────────────────────────────────────────

    def load(self) -> list:
        """Return the layer list. Gracefully returns [] on missing/corrupt JSON."""
        try:
            with open(self.path) as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Expected a list")
            return data
        except Exception:
            return []

    # ── Write ──────────────────────────────────────────────────────────────

    def save(self, layers: list) -> None:
        """Atomically write the full layer list to disk."""
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, suffix=".json")
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(layers, f, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ── Mutation helpers ───────────────────────────────────────────────────

    def upsert(self, layer: dict) -> list:
        """Insert or replace a layer by name. Appends if name is new."""
        layers = self.load()
        for i, l in enumerate(layers):
            if l.get("name") == layer["name"]:
                layers[i] = layer
                break
        else:
            layers.append(layer)
        self.save(layers)
        return layers

    def delete(self, name: str) -> list:
        """Remove a layer by name. No-op if not found."""
        layers = [l for l in self.load() if l.get("name") != name]
        self.save(layers)
        return layers

    def rename(self, old_name: str, new_name: str) -> list:
        """Rename a layer. No-op if old_name not found or new_name already taken."""
        layers = self.load()
        existing_names = {l.get("name") for l in layers}
        if new_name in existing_names:
            return layers  # Conflict — don't rename
        for l in layers:
            if l.get("name") == old_name:
                l["name"] = new_name
                break
        self.save(layers)
        return layers

    def move(self, name: str, direction: str) -> list:
        """Move a layer 'up' (toward index 0 = bottom) or 'down' (toward top)."""
        layers = self.load()
        for i, l in enumerate(layers):
            if l.get("name") == name:
                if direction == "up" and i > 0:
                    layers[i], layers[i - 1] = layers[i - 1], layers[i]
                elif direction == "down" and i < len(layers) - 1:
                    layers[i], layers[i + 1] = layers[i + 1], layers[i]
                break
        self.save(layers)
        return layers

    def update_field(self, name: str, field: str, value) -> list:
        """Update a single field on a named layer."""
        layers = self.load()
        for l in layers:
            if l.get("name") == name:
                l[field] = value
                break
        self.save(layers)
        return layers
