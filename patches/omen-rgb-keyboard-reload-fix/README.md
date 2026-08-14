# omen-rgb-keyboard: Reload Driver persistence fix

Fixes a bug in the upstream [`omen-rgb-keyboard`](https://github.com/alessandromrc/omen-rgb-keyboard)
kernel driver (tested against v1.4/v1.5, commit `171e1dc`) that made RGB_Manager's
**"🔄 Reload Driver"** button (and any `modprobe -r omen_rgb_keyboard && modprobe omen_rgb_keyboard`
cycle) wipe your saved color/brightness instead of restoring it.

## Root cause

On `modprobe -r`, `platform_device_unregister()` triggers the devm-managed LED
classdev's automatic unregister. The Linux LED core turns the LED off as part
of that teardown by calling the driver's `brightness_set` callback with `0`.
The driver's callback (`omen_apply_brightness`) unconditionally persisted
whatever brightness it was called with to `/var/lib/omen-rgb-keyboard/state`
— so this transient shutdown value permanently overwrote the real saved state,
seconds before the module even finished unloading.

Separately, on load, `hp_wmi_bios_setup()` called `fourzone_setup()` (which
reads the *live* hardware color into `original_colors[]`) **before**
`load_animation_state()` — but since the LEDs were just forced off, this
live read is black, and nothing afterward pushed the correctly-loaded
color/brightness back out to the hardware anyway.

## Fix

1. Add a `driver_unloading` flag, set at the start of `hp_wmi_exit()`, that
   suppresses the disk save inside `omen_apply_brightness()` during teardown.
2. Reorder init so `load_animation_state()` runs *after* `fourzone_setup()`
   (so its readback can't clobber the restored colors), and explicitly call
   `omen_apply_brightness(global_brightness)` afterward to push the restored
   color/brightness out to hardware.

See `reload-persistence-fix.patch` for the exact diff (3 files:
`src/core/omen_rgb_keyboard_main.c`, `src/include/omen_zones.h`,
`src/zones/omen_zones.c`).

## Applying

```bash
git clone https://github.com/alessandromrc/omen-rgb-keyboard.git
cd omen-rgb-keyboard
git apply /path/to/RGB_Manager/patches/omen-rgb-keyboard-reload-fix/reload-persistence-fix.patch
sudo make install
sudo modprobe -r omen_rgb_keyboard
sudo modprobe omen_rgb_keyboard
```

If you already have the driver installed via DKMS, sync the patched source
into the DKMS tree instead of a fresh clone:

```bash
sudo rsync -a --delete /path/to/patched/omen-rgb-keyboard/ /usr/src/omen-rgb-keyboard-<version>/
sudo dkms remove omen-rgb-keyboard/<version> --all
cd /usr/src/omen-rgb-keyboard-<version>
sudo make install
sudo modprobe -r omen_rgb_keyboard && sudo modprobe omen_rgb_keyboard
```

Verified: set a color/brightness, reload, and both the `rgb_zones/all` and
`rgb_zones/brightness` sysfs values — and the physical keyboard — now come
back exactly as they were before the reload.

## Not fixed here

There's also a pre-existing kernel `WARNING` at `workqueue.c:4302` inside
`omen_hda_led_cleanup()` on every unload (a `__flush_work` call from a bad
context). It's noisy in `dmesg`/`journalctl -k` but harmless — the module
still unloads and reloads correctly despite it. Out of scope for this patch.
