#!/usr/bin/env python3
"""Fix glyphs with advance width within ±5 of 750 to exactly 750."""
import glob
import xml.etree.ElementTree as ET

CELL_WIDTH = 750
TOLERANCE = 5
glyphs_dir = "Audiowide Mono-275.ufo/glyphs"
fixed = []

for path in sorted(glob.glob(f"{glyphs_dir}/*.glif")):
    tree = ET.parse(path)
    root = tree.getroot()
    advance = root.find("advance")
    if advance is None:
        continue
    width = int(advance.get("width", "0"))
    if width == 0 or width == CELL_WIDTH:
        continue
    if width % CELL_WIDTH == 0:
        continue  # already a valid multiple
    off = width - CELL_WIDTH
    if abs(off) <= TOLERANCE:
        advance.set("width", str(CELL_WIDTH))
        tree.write(path, xml_declaration=True, encoding="UTF-8")
        fixed.append(f"  {path}: {width} -> {CELL_WIDTH}")

print(f"Fixed {len(fixed)} glyphs:")
for f in fixed:
    print(f)
