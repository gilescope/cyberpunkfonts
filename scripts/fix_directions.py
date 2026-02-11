#!/usr/bin/env python3
"""Diagnostic: check contour direction status before and after build fix."""
import fontforge

font = fontforge.open("Audiowide Mono-275.ufo")
ufo_wrong = sum(1 for g in font.glyphs() if g.validate() & 0x4)
print(f"UFO source: {ufo_wrong} glyphs with wrong direction")

# Apply same fix as build_font.py: 2-pass approach
font.layers[1].is_quadratic = False
for g in font.glyphs():
    g.unlinkRef()
    g.removeOverlap()
    g.correctDirection()
font.generate("pass1.ttf")

font2 = fontforge.open("pass1.ttf")
still_wrong = [g.glyphname for g in font2.glyphs() if g.validate() & 0x4]
font2.close()
print(f"After pass 1: {len(still_wrong)} wrong")

if still_wrong:
    print(f"  {', '.join(still_wrong)}")
    font3 = fontforge.open("Audiowide Mono-275.ufo")
    font3.layers[1].is_quadratic = False
    for name in still_wrong:
        g = font3[name]
        g.unlinkRef()
        g.correctDirection()
    font3.layers[1].is_quadratic = True
    font3.generate("pass2.ttf")

    font4 = fontforge.open("pass1.ttf")
    font5 = fontforge.open("pass2.ttf")
    for name in still_wrong:
        font4.selection.select(name)
        font5.selection.select(name)
        font5.copy()
        font4.paste()
    font4.generate("test.ttf")
else:
    import shutil

    shutil.copy("pass1.ttf", "test.ttf")

font.layers[1].is_quadratic = True

font6 = fontforge.open("test.ttf")
remaining = [g.glyphname for g in font6.glyphs() if g.validate() & 0x4]
print(f"Built TTF: {len(remaining)} glyphs with wrong direction")
if remaining:
    print("Remaining:", ", ".join(remaining))
