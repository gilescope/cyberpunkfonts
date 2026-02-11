#!/usr/bin/env python3
"""Diagnose unknown referenced glyphs."""
import fontforge

font = fontforge.open("Audiowide Mono-275.ufo")
for g in font.glyphs():
    state = g.validate()
    if state & 0x20:
        refs = g.references
        layer = g.layers[1]
        print(f"{g.glyphname}: validate=0x{state:x} refs={refs} contours={len(layer)}")

# Try fix: unlinkRef + correctDirection
print("\nAttempting fix...")
font.layers[1].is_quadratic = False
fixed = 0
for g in font.glyphs():
    if g.validate() & 0x20:
        g.unlinkRef()
        g.correctDirection()
font.layers[1].is_quadratic = True

for g in font.glyphs():
    state = g.validate()
    if state & 0x20:
        print(f"  STILL: {g.glyphname} (0x{state:x})")
    elif g.glyphname in [
        "Eth",
        "Ntilde",
        "asciitilde",
        "k",
        "paragraph",
        "section",
        "sterling",
        "uni0110",
        "uni0137",
        "uni0138",
        "uni0143",
        "uni0147",
        "uni0175",
        "uni017a",
        "uni017c",
        "uni1e81",
        "uni1e83",
        "uni1e85",
        "z",
        "zcaron",
    ]:
        print(f"  FIXED: {g.glyphname}")
        fixed += 1
print(f"\nFixed {fixed} unknown ref glyphs")
