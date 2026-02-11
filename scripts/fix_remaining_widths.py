#!/usr/bin/env python3
"""Fix all remaining single-width glyphs to exactly 750.
Narrow glyphs are centered, wide glyphs are scaled proportionally."""
import re, os, glob
import xml.etree.ElementTree as ET

UFO = os.path.join(
    os.path.dirname(__file__), "../audiowide-mono/Audiowide Mono-275.ufo/glyphs"
)
TARGET = 750
fixed = 0

for path in sorted(glob.glob(os.path.join(UFO, "*.glif"))):
    tree = ET.parse(path)
    root = tree.getroot()
    adv = root.find("advance")
    if adv is None:
        continue
    width = int(adv.get("width", "0"))
    if width == 0 or width % TARGET == 0:
        continue

    fname = os.path.basename(path)

    # Read raw content for regex replacement (preserves formatting)
    with open(path) as f:
        content = f.read()

    if width < TARGET:
        # Center: shift all x by (750 - width) / 2
        shift = (TARGET - width + 1) // 2

        def replace_x(m):
            x = int(m.group(2))
            return f"{m.group(1)}{x + shift}{m.group(3)}"

        mode = f"shift +{shift}"
    else:
        # Scale: compress x proportionally
        factor = TARGET / width

        def replace_x(m):
            x = int(m.group(2))
            return f"{m.group(1)}{round(x * factor)}{m.group(3)}"

        mode = f"scale {factor:.3f}"

    content = re.sub(
        r'<advance width="\d+"\s*/>', f'<advance width="{TARGET}"/>', content
    )
    content = re.sub(r'<advance width="\d+">', f'<advance width="{TARGET}">', content)
    content = re.sub(r'(<point x=")([\-]?\d+)(")', replace_x, content)

    with open(path, "w") as f:
        f.write(content)
    print(f"  {fname}: {width} -> {TARGET} ({mode})")
    fixed += 1

print(f"\nFixed {fixed} glyphs")
