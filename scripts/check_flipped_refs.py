#!/usr/bin/env python3
"""Fix flipped references by correcting contour direction in the UFO source."""
import fontforge
import os
import xml.etree.ElementTree as ET

font = fontforge.open("Audiowide Mono-275.ufo")

# Identify flipped
flipped = []
for g in font.glyphs():
    if g.validate() & 0x8:
        print(f"  {g.glyphname}: flipped reference (0x{g.validate():x})")
        flipped.append(g.glyphname)

if not flipped:
    print("No flipped references found.")
    exit(0)

print(f"\nFixing {len(flipped)} glyphs...")

# Fix in cubic mode
font.layers[1].is_quadratic = False
for name in flipped:
    g = font[name]
    g.unlinkRef()
    g.correctDirection()
font.layers[1].is_quadratic = True

# Verify fix
for name in flipped:
    state = font[name].validate()
    print(f"  {name}: {'FIXED' if not (state & 0x8) else 'STILL BROKEN'}")

# Glyph name to filename mapping for the known flipped glyphs
mapping = {
    "Z": "Z_.glif",
    "ae": "ae.glif",
    "asciitilde": "asciitilde.glif",
    "e": "e.glif",
    "s": "s.glif",
    "scedilla": "scedilla.glif",
    "uni0119": "uni0119.glif",
    "uni014b": "uni014b.glif",
    "z": "z.glif",
}

# Extract fixed contour data and write .glif XML
os.makedirs("/out", exist_ok=True)
for name in flipped:
    g = font[name]
    layer = g.layers[1]
    fname = mapping.get(name)
    if not fname:
        print(f"  WARNING: no mapping for {name}")
        continue

    # Read original .glif to preserve metadata (unicode, note, advance)
    orig_path = f"Audiowide Mono-275.ufo/glyphs/{fname}"
    orig_tree = ET.parse(orig_path)
    orig_root = orig_tree.getroot()

    # Build new outline from FontForge's fixed contour data
    new_outline = ET.SubElement(ET.Element("dummy"), "outline")
    new_outline = ET.Element("outline")

    for contour in layer:
        c_elem = ET.SubElement(new_outline, "contour")
        points = list(contour)
        for i, pt in enumerate(points):
            attrs = {"x": str(int(round(pt.x))), "y": str(int(round(pt.y)))}
            if pt.on_curve:
                # Determine if line or qcurve
                # Look back for off-curve points since last on-curve
                has_offcurve = False
                j = i - 1
                while j >= 0 and not points[j].on_curve:
                    has_offcurve = True
                    j -= 1
                if j < 0:
                    # Wrapped around - check from end
                    j = len(points) - 1
                    while j > i and not points[j].on_curve:
                        has_offcurve = True
                        j -= 1

                if i == 0 and not has_offcurve:
                    # First point, check if preceded by off-curve at end of contour
                    for k in range(len(points) - 1, -1, -1):
                        if points[k].on_curve:
                            break
                        has_offcurve = True

                attrs["type"] = "qcurve" if has_offcurve else "line"

                # Check smoothness
                if pt.type != fontforge.splineCorner and has_offcurve:
                    attrs["smooth"] = "yes"
            # off-curve points have no type attribute
            ET.SubElement(c_elem, "point", attrs)

    # Replace outline in original
    old_outline = orig_root.find("outline")
    if old_outline is not None:
        orig_root.remove(old_outline)
    orig_root.append(new_outline)

    # Write to /out
    out_path = f"/out/{fname}"
    ET.indent(orig_root, space="    ")
    tree = ET.ElementTree(orig_root)
    tree.write(out_path, encoding="unicode", xml_declaration=True)
    # Ensure trailing newline
    with open(out_path, "a") as f:
        f.write("\n")
    print(f"  Exported {fname}")
