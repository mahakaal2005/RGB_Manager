#!/bin/bash
# Applies the animation_direction patch to the omen-rgb-keyboard driver source
# Must be run as root (sudo)
set -e

SRC=/usr/src/omen-rgb-keyboard-1.3/src

echo "=== Patching omen_animations.h ==="
python3 - <<'PYEOF'
import re, sys

path = "/usr/src/omen-rgb-keyboard-1.3/src/include/omen_animations.h"
with open(path) as f:
    text = f.read()

OLD = """/* Device attributes for sysfs */
extern struct device_attribute animation_brightness_attr;
extern struct device_attribute animation_mode_attr;
extern struct device_attribute animation_speed_attr;"""

NEW = """/* Animation direction: 0 = left-to-right (default), 1 = right-to-left */
enum animation_direction {
\tANIMATION_DIR_LTR = 0,
\tANIMATION_DIR_RTL = 1,
};

extern enum animation_direction animation_direction;

/* Device attributes for sysfs */
extern struct device_attribute animation_brightness_attr;
extern struct device_attribute animation_mode_attr;
extern struct device_attribute animation_speed_attr;
extern struct device_attribute animation_direction_attr;"""

if "animation_direction" in text:
    print("Header already patched, skipping.")
    sys.exit(0)

if OLD not in text:
    print("ERROR: Expected text not found in header!", file=sys.stderr)
    sys.exit(1)

text = text.replace(OLD, NEW)
with open(path, 'w') as f:
    f.write(text)
print("Header patched OK.")
PYEOF

echo "=== Patching omen_animations.c ==="
python3 - <<'PYEOF'
import sys

path = "/usr/src/omen-rgb-keyboard-1.3/src/animations/omen_animations.c"
with open(path) as f:
    text = f.read()

if "animation_direction" in text:
    print("omen_animations.c already patched, skipping.")
    sys.exit(0)

# 1. Add direction global + ZONE_IDX macro after existing state vars
OLD1 = "bool animation_active = false;\n\nstatic struct timer_list animation_timer;"
NEW1 = """bool animation_active = false;
enum animation_direction animation_direction = ANIMATION_DIR_LTR;

/*
 * ZONE_IDX - Return actual zone index respecting animation_direction.
 * RTL: zone 0 <-> zone 3, zone 1 <-> zone 2.
 */
#define ZONE_IDX(z) \\
\t(animation_direction == ANIMATION_DIR_RTL ? (ZONE_COUNT - 1 - (z)) : (z))

static struct timer_list animation_timer;"""

if OLD1 not in text:
    print("ERROR: state vars block not found!", file=sys.stderr)
    sys.exit(1)
text = text.replace(OLD1, NEW1)

# 2. Patch animation_rainbow: use ZONE_IDX for hue assignment
OLD2 = """\tfor (int zone = 0; zone < ZONE_COUNT; zone++) {
\t\tint hue = (360 * cycle_pos / cycle_time + zone * 90) % 360;
\t\thsv_to_rgb(hue, 100, 100, &colors[zone]);
\t}

\tupdate_all_zones_with_colors(colors);
}

static void animation_wave"""
NEW2 = """\tfor (int zone = 0; zone < ZONE_COUNT; zone++) {
\t\tint actual = ZONE_IDX(zone);
\t\tint hue = (360 * cycle_pos / cycle_time + zone * 90) % 360;
\t\thsv_to_rgb(hue, 100, 100, &colors[actual]);
\t}

\tupdate_all_zones_with_colors(colors);
}

static void animation_wave"""
if OLD2 not in text:
    print("WARNING: rainbow block not found, skipping that hunk.")
else:
    text = text.replace(OLD2, NEW2)

# 3. Patch animation_wave: use actual = ZONE_IDX(zone)
OLD3 = """\tfor (int zone = 0; zone < ZONE_COUNT; zone++) {
\t\tint wave_pos = (cycle_pos * 4 / cycle_time + zone) % 4;
\t\tint angle = (360 * wave_pos) / 4;
\t\tint intensity = 30 + (70 * (100 + lut_sin(angle)) / 200);

\t\tcolors[zone] = original_colors[zone].colors;
\t\tcolors[zone].red = (colors[zone].red * intensity) / 100;
\t\tcolors[zone].green = (colors[zone].green * intensity) / 100;
\t\tcolors[zone].blue = (colors[zone].blue * intensity) / 100;
\t}"""
NEW3 = """\tfor (int zone = 0; zone < ZONE_COUNT; zone++) {
\t\tint actual = ZONE_IDX(zone);
\t\tint wave_pos = (cycle_pos * 4 / cycle_time + zone) % 4;
\t\tint angle = (360 * wave_pos) / 4;
\t\tint intensity = 30 + (70 * (100 + lut_sin(angle)) / 200);

\t\tcolors[actual] = original_colors[actual].colors;
\t\tcolors[actual].red   = (colors[actual].red   * intensity) / 100;
\t\tcolors[actual].green = (colors[actual].green * intensity) / 100;
\t\tcolors[actual].blue  = (colors[actual].blue  * intensity) / 100;
\t}"""
if OLD3 not in text:
    print("WARNING: wave block not found, skipping that hunk.")
else:
    text = text.replace(OLD3, NEW3)

# 4. Patch animation_chase: ZONE_IDX for active zone
OLD4 = "\tint active_zone = (cycle_pos * ZONE_COUNT) / cycle_time;"
NEW4 = "\tint logical_active = (cycle_pos * ZONE_COUNT) / cycle_time;\n\tint active_zone = ZONE_IDX(logical_active);"
if OLD4 not in text:
    print("WARNING: chase block not found, skipping that hunk.")
else:
    text = text.replace(OLD4, NEW4)

# 5. Patch animation_aurora: use actual = ZONE_IDX(zone)
OLD5 = """\tfor (int zone = 0; zone < ZONE_COUNT; zone++) {
\t\tint wave_pos = (cycle_pos * 2 + zone * 1000) % cycle_time;
\t\tint intensity = 30 + (70 * (100 + lut_sin((360 * wave_pos) / cycle_time)) / 200);

\t\t/* Aurora colors - green and blue */
\t\tcolors[zone].red = (20 * intensity) / 100;
\t\tcolors[zone].green = (200 * intensity) / 100;
\t\tcolors[zone].blue = (180 * intensity) / 100;
\t}"""
NEW5 = """\tfor (int zone = 0; zone < ZONE_COUNT; zone++) {
\t\tint actual = ZONE_IDX(zone);
\t\tint wave_pos = (cycle_pos * 2 + zone * 1000) % cycle_time;
\t\tint intensity = 30 + (70 * (100 + lut_sin((360 * wave_pos) / cycle_time)) / 200);

\t\tcolors[actual].red   = (20  * intensity) / 100;
\t\tcolors[actual].green = (200 * intensity) / 100;
\t\tcolors[actual].blue  = (180 * intensity) / 100;
\t}"""
if OLD5 not in text:
    print("WARNING: aurora block not found, skipping that hunk.")
else:
    text = text.replace(OLD5, NEW5)

# 6. Add sysfs show/set/attr before "void animation_init"
SYSFS_BLOCK = """
static ssize_t animation_direction_show(struct device *dev,
\t\t\t\t\tstruct device_attribute *attr, char *buf)
{
\treturn sprintf(buf, "%s\\n",
\t\t       animation_direction == ANIMATION_DIR_LTR
\t\t\t       ? "left_to_right" : "right_to_left");
}

static ssize_t animation_direction_set(struct device *dev,
\t\t\t\t       struct device_attribute *attr,
\t\t\t\t       const char *buf, size_t count)
{
\tif (strncmp(buf, "left_to_right", 13) == 0)
\t\tanimation_direction = ANIMATION_DIR_LTR;
\telse if (strncmp(buf, "right_to_left", 13) == 0)
\t\tanimation_direction = ANIMATION_DIR_RTL;
\telse
\t\treturn -EINVAL;

\tsave_animation_state();
\treturn count;
}

DEVICE_ATTR(animation_direction, 0644,
\t    animation_direction_show, animation_direction_set);

struct device_attribute animation_direction_attr =
\t__ATTR(animation_direction, 0644,
\t       animation_direction_show, animation_direction_set);

"""

if "void animation_init" not in text:
    print("ERROR: animation_init not found!", file=sys.stderr)
    sys.exit(1)
text = text.replace("void animation_init", SYSFS_BLOCK + "void animation_init")

with open(path, 'w') as f:
    f.write(text)
print("omen_animations.c patched OK.")
PYEOF

echo "=== Patching omen_zones.c ==="
python3 - <<'PYEOF'
import sys

path = "/usr/src/omen-rgb-keyboard-1.3/src/zones/omen_zones.c"
with open(path) as f:
    text = f.read()

if "animation_direction_attr" in text:
    print("omen_zones.c already patched, skipping.")
    sys.exit(0)

# Expand kcalloc for zone_attrs
OLD1 = "zone_attrs = kcalloc(ZONE_COUNT + 6, sizeof(struct attribute *),"
NEW1 = "zone_attrs = kcalloc(ZONE_COUNT + 7, sizeof(struct attribute *),"
if OLD1 not in text:
    print("WARNING: kcalloc line not found (might already be ZONE_COUNT+7)")
else:
    text = text.replace(OLD1, NEW1)

# Insert direction attr before NULL terminator
OLD2 = "\tzone_attrs[ZONE_COUNT + 5] = NULL; /* NULL terminate the array */"
NEW2 = "\tzone_attrs[ZONE_COUNT + 5] = &animation_direction_attr.attr;\n\tzone_attrs[ZONE_COUNT + 6] = NULL; /* NULL terminate */"
if OLD2 not in text:
    print("ERROR: NULL terminator line not found!", file=sys.stderr)
    sys.exit(1)
text = text.replace(OLD2, NEW2)

with open(path, 'w') as f:
    f.write(text)
print("omen_zones.c patched OK.")
PYEOF

echo "=== All patches applied. Rebuilding DKMS... ==="
dkms remove omen-rgb-keyboard/1.3 --all 2>/dev/null || true
dkms add /usr/src/omen-rgb-keyboard-1.3
dkms build omen-rgb-keyboard/1.3 2>&1 | tail -8
dkms install omen-rgb-keyboard/1.3 2>&1 | tail -5

echo "=== Done. Reloading module... ==="
modprobe -r omen_rgb_keyboard 2>/dev/null || true
sleep 1
modprobe omen_rgb_keyboard
sleep 1
echo "=== Sysfs nodes: ==="
ls /sys/devices/platform/omen-rgb-keyboard/rgb_zones/
echo "=== animation_direction: ==="
cat /sys/devices/platform/omen-rgb-keyboard/rgb_zones/animation_direction
