#!/usr/bin/env python3
"""Check all glyphs have advance width that is a multiple of 750 (monospace invariant)."""
import glob
import sys
import xml.etree.ElementTree as ET

CELL_WIDTH = 750
glyphs_dir = "Audiowide Mono-275.ufo/glyphs"
errors = []

for path in sorted(glob.glob(f"{glyphs_dir}/*.glif")):
    tree = ET.parse(path)
    root = tree.getroot()
    advance = root.find("advance")
    if advance is None:
        errors.append(f"{path}: missing <advance> element")
        continue
    width = int(advance.get("width", "0"))
    if width == 0:
        continue  # null / control characters
    if width % CELL_WIDTH != 0:
        errors.append(f"{path}: width={width}, not a multiple of {CELL_WIDTH}")

if errors:
    print(f"Width issues ({len(errors)} glyphs):")
    for e in errors:
        print(f"  {e}")
    print(f"\n{len(errors)} glyphs need width fixes (see todo.md)")
else:
    print(f"All glyph widths are multiples of {CELL_WIDTH}")
