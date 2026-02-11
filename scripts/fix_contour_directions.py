#!/usr/bin/env python3
"""Fix contour direction warnings in UFO glyphs.

Two issues cause FontForge's 'wrong direction' (0x4) validation flag:

1. Degenerate zero-length segments: consecutive on-curve points at the same
   coordinates (a 'qcurve' followed by a 'line' at identical x,y). Removing
   the redundant 'line' point fixes this without changing the glyph shape.
   Affects ~354 glyphs.

2. Overlapping contours: glyphs like 'plus', 'seven', fractions, etc. have
   separate contours that overlap. FontForge flags these as wrong direction.
   We merge overlapping contours using pathops (skia-pathops) boolean union,
   then convert cubic curves back to quadratic with fontTools cu2qu.
   Affects ~10 glyphs.

Dependencies: fonttools, skia-pathops (pip install fonttools skia-pathops)
"""
import os
import glob
import xml.etree.ElementTree as ET

from fontTools.ufoLib.glifLib import readGlyphFromString, writeGlyphToString
from fontTools.pens.recordingPen import RecordingPointPen
from fontTools.pens.pointPen import (
    PointToSegmentPen,
    SegmentToPointPen,
    ReverseContourPointPen,
)
from fontTools.pens.cu2quPen import Cu2QuPointPen
from pathops import Path, union


UFO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "audiowide-mono",
    "Audiowide Mono-275.ufo",
    "glyphs",
)


class SimpleGlyph:
    """Minimal glyph object for readGlyphFromString/writeGlyphToString."""

    def __init__(self):
        self.name = None
        self.width = 0
        self.height = 0
        self.unicodes = []
        self.lib = {}
        self.image = None
        self.guidelines = None
        self.anchors = None
        self.note = None


def remove_degenerate_points(path):
    """Remove qcurve+line duplicate points. Returns (modified, points_removed)."""
    tree = ET.parse(path)
    root = tree.getroot()
    outline = root.find("outline")
    if outline is None:
        return False, 0

    modified = False
    removed = 0
    for contour in outline.findall("contour"):
        points = contour.findall("point")
        to_remove = []

        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]

            type0 = p0.get("type")
            type1 = p1.get("type")
            if not type0 or not type1:
                continue

            if p0.get("x") != p1.get("x") or p0.get("y") != p1.get("y"):
                continue

            if type0 == "qcurve" and type1 == "line":
                to_remove.append(p1)

        for p in to_remove:
            contour.remove(p)
            removed += 1
            modified = True

    if modified:
        ET.indent(tree, space="  ")
        tree.write(path, encoding="unicode", xml_declaration=True)

    return modified, removed


def remove_overlaps(path):
    """Merge overlapping contours using pathops boolean union."""
    with open(path) as f:
        data = f.read()

    glyph = SimpleGlyph()
    rec = RecordingPointPen()
    readGlyphFromString(data, glyph, rec)

    has_contours = any(m == "beginPath" for m, _, _ in rec.value)
    if not has_contours:
        return False

    # Run pathops union
    skia_path = Path()
    pen = skia_path.getPen()
    seg_pen = PointToSegmentPen(pen)
    rec.replay(seg_pen)

    result_path = Path()
    union([skia_path], result_path.getPen(), fix_winding=True)

    # Convert cubic output back to quadratic, reversing contour direction.
    # pathops fix_winding uses PostScript convention (outer=CCW); FontForge
    # expects the opposite for TrueType quadratic outlines, so we reverse.
    result_rec = RecordingPointPen()
    rev_pen = ReverseContourPointPen(result_rec)
    cu2qu_pen = Cu2QuPointPen(rev_pen, max_err=1.0, reverse_direction=False)
    adapter = SegmentToPointPen(cu2qu_pen)
    result_path.draw(adapter)

    def draw_func(pen, _rec=result_rec):
        _rec.replay(pen)

    new_data = writeGlyphToString(glyph.name, glyph, draw_func, formatVersion=2)

    with open(path, "w") as f:
        f.write(new_data)

    return True


# Phase 1: Remove degenerate duplicate points
degenerate_fixed = 0
points_removed = 0

for filepath in sorted(glob.glob(os.path.join(UFO_DIR, "*.glif"))):
    modified, removed = remove_degenerate_points(filepath)
    if modified:
        degenerate_fixed += 1
        points_removed += removed

print(
    f"Phase 1: Fixed {degenerate_fixed} glyphs ({points_removed} degenerate points removed)"
)

# Phase 2: Merge overlapping contours in specific glyphs that still trigger
# FontForge's wrong-direction flag due to overlapping contour geometry.
OVERLAP_GLYPHS = [
    "braceright.glif",
    "onequarter.glif",
    "plus.glif",
    "seven.glif",
    "threequarters.glif",
    "threesuperior.glif",
    "uni0125.glif",
    "uni0132.glif",
    "uni0140.glif",
    "uni0165.glif",
]

overlap_fixed = 0
for fname in OVERLAP_GLYPHS:
    filepath = os.path.join(UFO_DIR, fname)
    if os.path.exists(filepath) and remove_overlaps(filepath):
        overlap_fixed += 1

print(f"Phase 2: Merged overlaps in {overlap_fixed} glyphs")
print(f"Total: {degenerate_fixed + overlap_fixed} glyphs modified")
