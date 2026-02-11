#!/usr/bin/env python3
"""Validate font glyphs using FontForge's built-in validator."""
import sys
import fontforge

# Hard errors - these fail the build
ERRORS = [
    (0x1, "open contour"),
    (0x2, "self-intersecting"),
    (0x80, "non-integral coordinates"),
    (0x200, "duplicate name"),
    (0x400, "duplicate unicode"),
]

# Warnings - reported but don't fail the build
WARNINGS = [
    (0x4, "wrong direction"),
    (0x8, "flipped reference"),
    (0x10, "missing points at extrema"),
    (0x20, "unknown referenced glyph"),
    (0x40, "hints with invalid layer"),
    (0x100, "missing anchor"),
    (0x800, "overlapping hints"),
]

font = fontforge.open("Audiowide Mono-275.ufo")

errors = []
warnings = []
for glyph in font.glyphs():
    state = glyph.validate()
    if state == 0:
        continue
    errs = [desc for mask, desc in ERRORS if state & mask]
    warns = [desc for mask, desc in WARNINGS if state & mask]
    if errs:
        errors.append(f"  {glyph.glyphname}: {', '.join(errs)}")
    if warns:
        warnings.append(f"  {glyph.glyphname}: {', '.join(warns)}")

if warnings:
    print(f"Warnings ({len(warnings)} glyphs):")
    for w in warnings:
        print(w)

if errors:
    print(f"Errors ({len(errors)} glyphs):", file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(1)

print("Validation passed (no hard errors)")
