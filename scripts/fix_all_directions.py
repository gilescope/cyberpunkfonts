#!/usr/bin/env python3
"""Fix contour winding direction in all UFO glyphs for TrueType convention.

TrueType expects outer contours to be CW on screen (= CCW in y-up font coords = positive area).
Inner contours should be the opposite (CW in y-up = negative area).

Uses largest absolute area to identify the outer contour. If the outer contour
has wrong winding, ALL contours in the glyph are reversed (since a consistently-
wound glyph has all contours wrong together).
"""
import os, glob, re
import xml.etree.ElementTree as ET


def signed_area(points):
    """Signed area via shoelace. Positive = CCW (y-up), negative = CW (y-up)."""
    a = 0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return a / 2


def reverse_contour(contour_elem):
    """Reverse contour point order with correct type attribute shifting.

    When reversing, each on-curve point gets the type of the NEXT on-curve
    point in the ORIGINAL order (because the incoming segment to a reversed
    point corresponds to the outgoing segment from it in the original).
    """
    points = list(contour_elem.findall("point"))
    if len(points) < 3:
        return

    data = []
    for p in points:
        data.append(
            {
                "x": p.get("x"),
                "y": p.get("y"),
                "type": p.get("type"),
                "smooth": p.get("smooth"),
            }
        )

    oncurve = [(i, d["type"]) for i, d in enumerate(data) if d["type"]]
    if len(oncurve) < 2:
        return

    # Each on-curve gets the type of the NEXT on-curve in original order
    new_types = {}
    for j in range(len(oncurve)):
        curr_idx = oncurve[j][0]
        next_type = oncurve[(j + 1) % len(oncurve)][1]
        new_types[curr_idx] = next_type

    data.reverse()
    n = len(data)

    for orig_idx, new_type in new_types.items():
        rev_idx = n - 1 - orig_idx
        data[rev_idx]["type"] = new_type

    for p, d in zip(points, data):
        p.set("x", d["x"])
        p.set("y", d["y"])
        if d["type"]:
            p.set("type", d["type"])
        elif "type" in p.attrib:
            del p.attrib["type"]
        if d["smooth"]:
            p.set("smooth", d["smooth"])
        elif "smooth" in p.attrib:
            del p.attrib["smooth"]


UFO = os.path.join(
    os.path.dirname(__file__), "../audiowide-mono/Audiowide Mono-275.ufo/glyphs"
)

fixed = 0
for path in sorted(glob.glob(os.path.join(UFO, "*.glif"))):
    tree = ET.parse(path)
    root = tree.getroot()
    outline = root.find("outline")
    if outline is None:
        continue

    contours = outline.findall("contour")
    if not contours:
        continue

    # Compute areas, find outer contour (largest absolute area)
    contour_data = []
    for c in contours:
        pts = [(int(p.get("x")), int(p.get("y"))) for p in c.findall("point")]
        area = signed_area(pts) if len(pts) >= 3 else 0
        contour_data.append((pts, area))

    valid_areas = [(abs(a), a) for _, a in contour_data if abs(a) > 0]
    if not valid_areas:
        continue

    # Outer contour = largest absolute area
    valid_areas.sort(reverse=True)
    outer_area = valid_areas[0][1]

    # TrueType: outer should be positive (CCW in y-up = CW on screen)
    if outer_area > 0:
        continue  # Already correct

    # Outer is negative (CW in y-up) = wrong for TrueType → reverse ALL contours
    for c in contours:
        reverse_contour(c)

    # Write back preserving original XML formatting
    fname = os.path.basename(path)
    with open(path) as f:
        content = f.read()

    contour_pattern = re.compile(r"<contour>\s*\n(.*?)</contour>", re.DOTALL)

    new_contours = []
    for c in contours:
        lines = []
        for p in c.findall("point"):
            attrs = [f'x="{p.get("x")}"', f'y="{p.get("y")}"']
            if p.get("type"):
                attrs.append(f'type="{p.get("type")}"')
            if p.get("smooth"):
                attrs.append(f'smooth="{p.get("smooth")}"')
            lines.append(f'      <point {" ".join(attrs)}/>')
        new_contours.append("\n".join(lines) + "\n")

    counter = [0]

    def replace_contour(m):
        result = new_contours[counter[0]]
        counter[0] += 1
        return f"<contour>\n{result}    </contour>"

    content = contour_pattern.sub(replace_contour, content)
    with open(path, "w") as f:
        f.write(content)

    fixed += 1

print(f"Fixed contour directions in {fixed} glyphs")
