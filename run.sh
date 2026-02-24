#!/bin/bash
# HP OMEN RGB Manager — Launcher
# Uses the system Python3 which has python3-gi (GTK3 bindings)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

/usr/bin/python3 "$SCRIPT_DIR/rgb_app.py"
