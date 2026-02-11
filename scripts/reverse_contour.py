#!/usr/bin/env python3
"""Reverse a specific contour's direction in a .glif file.

Usage: python3 reverse_contour.py <glif_file> <contour_index>

Reverses the point order of the specified contour (0-indexed) to flip
its winding direction (CW <-> CCW).
"""
import sys
import xml.etree.ElementTree as ET


def reverse_contour(contour_elem):
    """Reverse point order of a UFO contour element in-place."""
    points = list(contour_elem)

    # Separate into segments: each segment is [off-curve...] + on-curve
    segments = []
    current = []
    for p in points:
        current.append(p)
        if p.get("type") in ("line", "qcurve", "curve"):
            segments.append(current)
            current = []

    if not segments:
        return

    # Reverse the segment order
    segments.reverse()

    # In reversed order, each segment's off-curve points need to be
    # associated with the on-curve point they now precede.
    # When we reverse: seg[i]'s off-curves should come from seg[i-1]
    # (the segment that was AFTER in the original order).
    #
    # Rebuild: take on-curve from each segment, but off-curves from
    # the NEXT segment in reversed order (which was the previous in original).
    n = len(segments)
    new_points = []
    for i in range(n):
        # Off-curves come from the next segment (wrapping)
        next_seg = segments[(i + 1) % n]
        off_curves = next_seg[:-1]  # all but the on-curve
        on_curve = segments[i][-1]  # the on-curve point

        # Reverse the off-curves within the group
        off_curves = list(reversed(off_curves))

        for oc in off_curves:
            new_points.append(oc)
        new_points.append(on_curve)

    # Clear and repopulate the contour element
    for p in list(contour_elem):
        contour_elem.remove(p)
    for p in new_points:
        contour_elem.append(p)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <glif_file> <contour_index>")
        sys.exit(1)

    glif_path = sys.argv[1]
    contour_idx = int(sys.argv[2])

    tree = ET.parse(glif_path)
    root = tree.getroot()
    outline = root.find("outline")
    contours = list(outline.findall("contour"))

    if contour_idx >= len(contours):
        print(f"Error: only {len(contours)} contours, index {contour_idx} out of range")
        sys.exit(1)

    print(f"Reversing contour {contour_idx} in {glif_path}")
    contour = contours[contour_idx]
    pts_before = len(list(contour))
    reverse_contour(contour)
    pts_after = len(list(contour))
    print(f"  Points: {pts_before} -> {pts_after}")

    # Write back with XML declaration
    tree.write(glif_path, xml_declaration=True, encoding="UTF-8")
    print(f"  Written to {glif_path}")


if __name__ == "__main__":
    main()
