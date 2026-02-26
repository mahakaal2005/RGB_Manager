# HP OMEN RGB Manager for Linux

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This desktop application controls the 4-zone RGB keyboard on HP OMEN 16 laptops running Linux. It provides a native GTK3 graphical interface to manage keyboard lighting, replacing the Windows-only Omen Gaming Hub.

![HP OMEN RGB Manager](icon.png)

## Features

This tool interfaces directly with the `omen-rgb-keyboard` kernel module via `/sys/`. It includes:

- **Graphical Interface:** GTK3/Cairo application with rotary dials and an interactive keyboard map to pick zone colors.
- **Layer Compositor:** A software engine stacks multiple lighting effects (e.g., a static base color underneath a breathing highlight) and streams updates to the hardware.
- **Hardware Controls:** Rotary dials control brightness and animation speed. A toggle button manages the mute LED indicator.
- **Presets:** Pre-configured themes for both static colors and dynamic animations (Rainbow, Wave, Aurora, etc.).

## Hardware Compatibility

Tested on:
- HP OMEN 16 (Model 16-xd0xxx / Board 8BCD)
- Models equipped with a 4-zone RGB keyboard

## Prerequisites

You must install the `omen-rgb-keyboard` kernel module before using this application.

1. Install build dependencies (Ubuntu/Debian example):
   ```bash
   sudo apt update
   sudo apt install build-essential linux-headers-$(uname -r) dkms
   ```

2. Clone and install the kernel module:
   ```bash
   git clone https://github.com/alessandromrc/omen-rgb-keyboard.git
   cd omen-rgb-keyboard
   sudo make dkms-install
   sudo modprobe omen_rgb_keyboard
   ```
   *Verify the installation by checking if `/sys/devices/platform/omen-rgb-keyboard/rgb_zones/` exists.*

3. Install Python dependencies:
   ```bash
   sudo apt install python3-gi gir1.2-gtk-3.0 python3-cairo
   ```

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/mahakaal/HP-Omen-RGB-Manager-Linux.git
   cd HP-Omen-RGB-Manager-Linux
   ```

2. Make the scripts executable:
   ```bash
   chmod +x run.sh install.sh install_sudoers.sh install_desktop.sh
   ```

3. **Install the Application**
   Run the unified installer. The script first verifies your hardware compatibility. If supported, it creates a desktop icon and adds a `sudoers` rule so the app can control the keyboard without requiring your password on every launch.
   ```bash
   ./install.sh
   ```

## Usage

Launch the app from your application menu (search for "HP OMEN RGB Manager") or run it directly from the terminal:
```bash
./run.sh
```

## Advanced: Animation Direction Patch (Experimental)

The official kernel module does not support reversing the direction of animations (e.g., right-to-left waves). This repository includes a patch script (`apply_direction_patch.sh`) to add this feature.

> [!CAUTION]
> **Use at your own risk.** 
> This script searches for the `omen-rgb-keyboard-1.3` source code on your hard drive, injects new C code using Python, and recompiles the kernel module using DKMS. If the original author updates the module, this script may break your keyboard driver.

If you understand the risks and want to enable direction toggling, run:
```bash
sudo ./apply_direction_patch.sh
```

## Troubleshooting

- **Lights Freeze / Missing File Error:** The kernel module sometimes stops responding. Reload it using `sudo modprobe -r omen_rgb_keyboard && sudo modprobe omen_rgb_keyboard`. If the hardware completely locks, shut down the laptop, unplug the power, hold the power button for 30 seconds, and restart.
- **Permission Denied:** Ensure you ran `./install_sudoers.sh` successfully and have not moved the installation folder.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file.
