#!/usr/bin/env python3
"""Fix remaining double-width ligatures to 1500 width by centering outlines."""
import re, os

UFO = os.path.join(
    os.path.dirname(__file__), "../audiowide-mono/Audiowide Mono-275.ufo/glyphs"
)

# Each entry: (filename, old_width) — shift = (1500 - old_width) // 2
FIXES = [
    ("O_E_.glif", 1398),
    ("ae.glif", 1116),
    ("oe.glif", 1142),
    ("uni0132.glif", 1005),
    ("perthousand.glif", 1260),
    ("uni01fc.glif", 1350),
    ("uni01fd.glif", 1116),
]

for filename, old_width in FIXES:
    shift = (1500 - old_width + 1) // 2  # round to nearest
    path = os.path.join(UFO, filename)
    with open(path) as f:
        content = f.read()

    # Update width
    content = re.sub(r'<advance width="\d+"\s*/>', '<advance width="1500"/>', content)

    # Shift all x coordinates
    def replace_x(m):
        x = int(m.group(2))
        return f"{m.group(1)}{x + shift}{m.group(3)}"

    content = re.sub(r'(<point x=")([\-]?\d+)(")', replace_x, content)

    with open(path, "w") as f:
        f.write(content)
    print(f"{filename}: width {old_width} -> 1500 (x shifted +{shift})")
