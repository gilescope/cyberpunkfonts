#!/usr/bin/env python3
"""Build Audiowide Mono TTF from UFO source using FontForge."""
import fontforge

font = fontforge.open("Audiowide Mono-275.ufo")

# Fix contour directions: convert to cubic, fix, convert back to quadratic.
# The UFO stores quadratic curves but FontForge's correctDirection() needs
# cubic mode to apply PostScript winding rules correctly.
font.layers[1].is_quadratic = False
for g in font.glyphs():
    g.unlinkRef()
    g.removeOverlap()
    g.correctDirection()

# Second pass: some glyphs have overlapping contours that removeOverlap()
# merges incorrectly. Re-open the source and fix those without removeOverlap().
font.generate("pass1.ttf")
font2 = fontforge.open("pass1.ttf")
still_wrong = [g.glyphname for g in font2.glyphs() if g.validate() & 0x4]
font2.close()

if still_wrong:
    font3 = fontforge.open("Audiowide Mono-275.ufo")
    font3.layers[1].is_quadratic = False
    for name in still_wrong:
        g = font3[name]
        g.unlinkRef()
        g.correctDirection()
    font3.layers[1].is_quadratic = True
    font3.generate("pass2.ttf")

    # Copy fixed glyphs from pass2 into the main font
    font4 = fontforge.open("pass1.ttf")
    font5 = fontforge.open("pass2.ttf")
    for name in still_wrong:
        font4.selection.select(name)
        font5.selection.select(name)
        font5.copy()
        font4.paste()
    font4.generate("Audiowide-Mono-Latest.ttf")
else:
    import os

    os.rename("pass1.ttf", "Audiowide-Mono-Latest.ttf")

font.layers[1].is_quadratic = True
print("Generated Audiowide-Mono-Latest.ttf")
