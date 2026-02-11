#!/usr/bin/env python3
"""Fix emdash, fi, fl, ij to single-width (750)."""
import re, os

UFO = os.path.join(
    os.path.dirname(__file__), "../audiowide-mono/Audiowide Mono-275.ufo/glyphs"
)


def transform_glif(path, transform_x, new_width):
    with open(path) as f:
        content = f.read()
    content = re.sub(
        r'<advance width="\d+"/>', f'<advance width="{new_width}"/>', content
    )

    def replace_x(m):
        x = int(m.group(2))
        return f"{m.group(1)}{transform_x(x)}{m.group(3)}"

    content = re.sub(r'(<point x=")([\-]?\d+)(")', replace_x, content)
    with open(path, "w") as f:
        f.write(content)


# emdash: scale proportionally
transform_glif(os.path.join(UFO, "emdash.glif"), lambda x: round(x * 750 / 935), 750)
print("emdash: scaled x by 750/935, width=750")

# fi: outline fits (max x=728 < 750), just change width
path = os.path.join(UFO, "fi.glif")
with open(path) as f:
    content = f.read()
content = re.sub(r'<advance width="\d+"/>', '<advance width="750"/>', content)
with open(path, "w") as f:
    f.write(content)
print("fi: width=750 (outline already fits)")

# fl: scale proportionally
transform_glif(os.path.join(UFO, "fl.glif"), lambda x: round(x * 750 / 855), 750)
print("fl: scaled x by 750/855, width=750")

# ij: center outline in 750
# x range: 223-740, span=517, center margin=(750-517)/2=116.5, shift=117-223=-106
transform_glif(os.path.join(UFO, "uni0133.glif"), lambda x: x - 106, 750)
print("ij: shifted x by -106, width=750")
