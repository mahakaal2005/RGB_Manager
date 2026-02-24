#!/bin/bash
# HP OMEN RGB Manager — Launcher
# Uses the system Python3 which has python3-gi (GTK3 bindings)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Launch as Python package (modular layout under rgbmanager/)
cd "$SCRIPT_DIR" && /usr/bin/python3 -m rgbmanager
