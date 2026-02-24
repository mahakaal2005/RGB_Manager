# HP OMEN 16-xd0xxx Linux RGB Keyboard Control Guide

This document outlines the steps taken on February 24, 2026, to enable RGB keyboard control for your HP OMEN 16-xd0xxx (Board 8BCD) under Linux (Ubuntu 24.04).

## 1. Background
Official HP Omen Gaming Hub software is unavailable for Linux. Standard tools like OpenRGB often fail to detect the internal keyboard of the 16-xd0xxx series because the hardware interface is proprietary.

## 2. Solution Implemented
We installed the community-developed `omen-rgb-keyboard` kernel module, which interfaces directly with the keyboard controller via WMI.

### Installation Steps Taken:
1.  **Dependencies:** Installed `build-essential`, `linux-headers`, and `dkms`.
2.  **Driver Source:** Cloned from `https://github.com/alessandromrc/omen-rgb-keyboard.git`.
3.  **Deployment:** Installed via DKMS (Dynamic Kernel Module Support) to ensure the driver remains active even after kernel updates.
4.  **Activation:** Loaded the module using `sudo modprobe omen_rgb_keyboard`.

## 3. How to Control Your RGB
The driver exposes control files in the `/sys` filesystem. You can change colors by writing Hex values (`RRGGBB`) to these files.

### Common Commands:
*   **Set All Zones to a Color (e.g., Sky Blue):**
    ```bash
    sudo bash -c 'echo 00FFFF > /sys/devices/platform/omen-rgb-keyboard/rgb_zones/all'
    ```
*   **Set Specific Zones (00, 01, 02, 03):**
    ```bash
    sudo bash -c 'echo FF0000 > /sys/devices/platform/omen-rgb-keyboard/rgb_zones/zone00'
    ```
*   **Change Brightness (0-255):**
    ```bash
    sudo bash -c 'echo 255 > /sys/devices/platform/omen-rgb-keyboard/rgb_zones/brightness'
    ```
*   **Toggle Mute LED:**
    ```bash
    sudo bash -c 'echo 1 > /sys/devices/platform/omen-rgb-keyboard/rgb_zones/mute_led' # 1 for ON, 0 for OFF
    ```

## 4. Troubleshooting
If the RGB stops responding or the files disappear:
1.  **Reload Driver:** `sudo modprobe omen_rgb_keyboard`
2.  **Hard Reset:** If the lights freeze, shut down the laptop, unplug the power, hold the power button for 30 seconds, and restart.

---
*Created by Gemini CLI*
