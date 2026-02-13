#!/usr/bin/env python3
"""Lossless simplification of UFO glyph outlines.

Applies shape-preserving transformations:
1. Remove degenerate contours (zero/near-zero area)
2. Remove consecutive duplicate points (same x,y)
3. Convert straight qcurve segments to lines (off-curve is colinear)
4. Snap 1-unit jitter on near-straight segments

Outputs before/after stats and generates glyph-preview.html for visual diff.
"""
import os, glob, json, re
import xml.etree.ElementTree as ET

UFO = os.path.join(
    os.path.dirname(__file__), "../audiowide-mono/Audiowide Mono-275.ufo/glyphs"
)
COLINEAR_TOLERANCE = 1.5  # max distance from line to count as colinear


def signed_area(points):
    """Shoelace formula. Returns 0 for degenerate contours."""
    a = 0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return a / 2


def point_to_line_dist(px, py, ax, ay, bx, by):
    """Distance from point (px,py) to line through (ax,ay)-(bx,by)."""
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    cross = abs(dx * (py - ay) - dy * (px - ax))
    return cross / (len_sq**0.5)


def parse_contour(contour_elem):
    """Parse contour element into list of point dicts."""
    pts = []
    for p in contour_elem.findall("point"):
        pts.append(
            {
                "x": int(p.get("x")),
                "y": int(p.get("y")),
                "type": p.get("type"),  # None for off-curve
                "smooth": p.get("smooth"),
            }
        )
    return pts


def find_oncurve_before(pts, idx):
    """Find the previous on-curve point index (wrapping)."""
    n = len(pts)
    j = (idx - 1) % n
    while j != idx:
        if pts[j]["type"] is not None:
            return j
        j = (j - 1) % n
    return idx


def remove_degenerate_contours(contours_pts):
    """Remove contours with near-zero area (< 100 sq units)."""
    kept = []
    removed = 0
    for pts in contours_pts:
        coords = [(p["x"], p["y"]) for p in pts]
        if len(coords) < 3 or abs(signed_area(coords)) < 100:
            removed += 1
        else:
            kept.append(pts)
    return kept, removed


def remove_duplicate_points(pts):
    """Remove consecutive points at identical coordinates."""
    if len(pts) <= 1:
        return pts, 0
    result = [pts[0]]
    removed = 0
    for i in range(1, len(pts)):
        if pts[i]["x"] == pts[i - 1]["x"] and pts[i]["y"] == pts[i - 1]["y"]:
            # Keep the one with a type attribute if possible
            if pts[i]["type"] and not result[-1]["type"]:
                result[-1] = pts[i]
            elif pts[i]["type"] and result[-1]["type"]:
                # Both have types — keep the more specific one
                result[-1] = pts[i]
            removed += 1
        else:
            result.append(pts[i])
    # Check wrap-around: first and last
    if (
        len(result) > 1
        and result[0]["x"] == result[-1]["x"]
        and result[0]["y"] == result[-1]["y"]
    ):
        t0 = result[0]["type"]
        t1 = result[-1]["type"]
        # Only merge if they have the same type, or one is off-curve.
        # Different on-curve types (line vs qcurve) define distinct segments.
        if t0 == t1 or not t0 or not t1:
            if t1 and not t0:
                result[0] = result[-1]
            result.pop()
            removed += 1
    return result, removed


def convert_straight_qcurves(pts):
    """Convert qcurve segments where off-curves are colinear to lines.

    Two-pass: first identify all off-curves to remove, then build result.
    """
    if len(pts) < 3:
        return pts, 0
    n = len(pts)
    skip = set()  # indices of off-curve points to remove
    convert = {}  # qcurve index -> "line" (type conversion)

    # Pass 1: identify straight qcurve segments
    for i in range(n):
        p = pts[i]
        if p["type"] != "qcurve":
            continue

        # Collect preceding off-curve points
        off_indices = []
        j = (i - 1) % n
        while pts[j]["type"] is None:
            off_indices.insert(0, j)
            j = (j - 1) % n
            if j == i:
                break

        if not off_indices:
            continue

        # Previous on-curve
        prev_on = pts[j]
        if prev_on["type"] is None:
            continue

        ax, ay = prev_on["x"], prev_on["y"]
        bx, by = p["x"], p["y"]

        # Check colinearity
        all_colinear = True
        for oidx in off_indices:
            dist = point_to_line_dist(pts[oidx]["x"], pts[oidx]["y"], ax, ay, bx, by)
            if dist > COLINEAR_TOLERANCE:
                all_colinear = False
                break

        if all_colinear:
            for oidx in off_indices:
                skip.add(oidx)
            convert[i] = "line"

    # Pass 2: build result
    result = []
    for i in range(n):
        if i in skip:
            continue
        p = dict(pts[i])
        if i in convert:
            p["type"] = convert[i]
        result.append(p)

    return result, len(skip)


def snap_jitter(pts):
    """Snap 1-unit coordinate jitter on line segments to exact alignment."""
    if len(pts) < 2:
        return pts, 0
    snapped = 0
    n = len(pts)
    for i in range(n):
        p = pts[i]
        if p["type"] != "line":
            continue
        # Find previous on-curve
        j = (i - 1) % n
        while j != i and pts[j]["type"] is None:
            j = (j - 1) % n
        if j == i:
            continue
        prev = pts[j]
        # Near-vertical: snap x
        if abs(p["x"] - prev["x"]) == 1 and abs(p["y"] - prev["y"]) > 10:
            p["x"] = prev["x"]
            snapped += 1
        # Near-horizontal: snap y
        elif abs(p["y"] - prev["y"]) == 1 and abs(p["x"] - prev["x"]) > 10:
            p["y"] = prev["y"]
            snapped += 1
    return pts, snapped


def pts_to_xml_lines(pts, indent="\t\t\t"):
    """Convert point list back to XML string lines."""
    lines = []
    for p in pts:
        attrs = [f'x="{p["x"]}"', f'y="{p["y"]}"']
        if p["type"]:
            attrs.append(f'type="{p["type"]}"')
        if p["smooth"]:
            attrs.append(f'smooth="{p["smooth"]}"')
        lines.append(f'{indent}<point {" ".join(attrs)}/>')
    return lines


def rebuild_glif_xml(original_xml, new_contours_pts):
    """Rebuild .glif XML with new contour data, preserving non-outline content."""
    # Parse to get structure
    tree = ET.fromstring(original_xml)
    outline = tree.find("outline")
    if outline is None:
        return original_xml

    # Rebuild using regex to preserve formatting outside contours
    # First, remove all contours from outline
    contour_pattern = re.compile(
        r"(\t\t<contour>)\s*\n(.*?)\t\t(</contour>)", re.DOTALL
    )

    matches = list(contour_pattern.finditer(original_xml))

    if len(matches) != len(new_contours_pts) + (len(matches) - len(new_contours_pts)):
        # Fallback: rebuild from scratch
        pass

    # Build new contour blocks
    new_blocks = []
    for pts in new_contours_pts:
        lines = pts_to_xml_lines(pts)
        block = "\t\t<contour>\n" + "\n".join(lines) + "\n\t\t</contour>"
        new_blocks.append(block)

    # Replace the outline section
    outline_pattern = re.compile(r"(\t<outline>\s*\n)(.*?)(\t</outline>)", re.DOTALL)
    m = outline_pattern.search(original_xml)
    if m:
        new_outline = m.group(1) + "\n".join(new_blocks) + "\n" + m.group(3)
        return original_xml[: m.start()] + new_outline + original_xml[m.end() :]

    return original_xml


# === Main ===

changes = []  # (filename, before_xml, after_xml, stats)
total_pts_before = 0
total_pts_after = 0

for path in sorted(glob.glob(os.path.join(UFO, "*.glif"))):
    with open(path) as f:
        original_xml = f.read()

    tree = ET.parse(path)
    root = tree.getroot()
    outline = root.find("outline")
    if outline is None:
        continue

    contours = outline.findall("contour")
    if not contours:
        continue

    # Parse all contours
    all_pts = [parse_contour(c) for c in contours]
    pts_before = sum(len(p) for p in all_pts)
    total_pts_before += pts_before

    stats = {"degenerate": 0, "duplicates": 0, "straight": 0, "jitter": 0}

    # Step 1: Remove degenerate contours
    all_pts, n = remove_degenerate_contours(all_pts)
    stats["degenerate"] = n

    # Step 2-4: Per-contour simplification (loop until stable)
    simplified = []
    for pts in all_pts:
        prev_len = -1
        while len(pts) != prev_len:
            prev_len = len(pts)
            pts, n = remove_duplicate_points(pts)
            stats["duplicates"] += n
            pts, n = convert_straight_qcurves(pts)
            stats["straight"] += n
            pts, n = snap_jitter(pts)
            stats["jitter"] += n

        if len(pts) >= 3:
            simplified.append(pts)
        else:
            stats["degenerate"] += 1

    pts_after = sum(len(p) for p in simplified)
    total_pts_after += pts_after
    removed = pts_before - pts_after

    if removed == 0 and stats["jitter"] == 0:
        continue

    # Rebuild XML
    new_xml = rebuild_glif_xml(original_xml, simplified)

    fname = os.path.basename(path)
    changes.append((fname, original_xml, new_xml, stats, pts_before, pts_after))

    # Write the simplified file
    with open(path, "w") as f:
        f.write(new_xml)

# Report
print(f"Total glyphs modified: {len(changes)}")
print(
    f"Total points: {total_pts_before} -> {total_pts_after} "
    f"(removed {total_pts_before - total_pts_after})"
)
print()
for fname, _, _, stats, before, after in sorted(
    changes, key=lambda x: x[4] - x[5], reverse=True
):
    removed = before - after
    detail = []
    if stats["degenerate"]:
        detail.append(f'{stats["degenerate"]} degen')
    if stats["duplicates"]:
        detail.append(f'{stats["duplicates"]} dup')
    if stats["straight"]:
        detail.append(f'{stats["straight"]} straight')
    if stats["jitter"]:
        detail.append(f'{stats["jitter"]} jitter')
    print(f"  {fname}: {before} -> {after} pts (-{removed}) [{', '.join(detail)}]")

# Generate glyph-preview.html
preview_path = os.path.join(os.path.dirname(__file__), "../glyph-preview.html")
preview_data = []
for fname, before_xml, after_xml, stats, pts_before, pts_after in changes:
    preview_data.append(
        {
            "name": fname.replace(".glif", ""),
            "before": before_xml,
            "after": after_xml,
            "ptsBefore": pts_before,
            "ptsAfter": pts_after,
        }
    )

html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Glyph Simplification — Before / After</title>
<style>
  body { font-family: system-ui; background: #1a1a2e; color: #eee; margin: 2em; }
  h1 { color: #0ff; font-size: 1.5em; }
  h2 { color: #e94560; margin-top: 0; font-size: 1.1em; }
  .summary { background: #16213e; padding: 1em; border-radius: 8px; margin-bottom: 2em; }
  .summary h2 { color: #0ff; }
  .row { display: flex; gap: 1.5em; flex-wrap: wrap; align-items: flex-start; margin-bottom: 2em; border-bottom: 1px solid #333; padding-bottom: 1.5em; }
  .card { background: #16213e; border-radius: 8px; padding: 0.8em; }
  svg { background: #0a0a1a; border-radius: 4px; }
  .meta { font-size: 0.8em; color: #aaa; margin-top: 0.4em; }
  .cell-line { stroke: #333; stroke-width: 1; stroke-dasharray: 4,4; }
  .baseline { stroke: #555; stroke-width: 1; }
  .glyph-fill { fill: #0ff; fill-opacity: 0.15; fill-rule: nonzero; }
  .contour-0 { fill: none; stroke: #f44; stroke-width: 2; }
  .contour-1 { fill: none; stroke: #0ff; stroke-width: 1.5; }
  .contour-2 { fill: none; stroke: #0f0; stroke-width: 1.5; }
  .contour-3 { fill: none; stroke: #ff0; stroke-width: 1.5; }
  .point-on { fill: #ff0; }
  .point-off { fill: #f0f; }
  .delta { color: #0f0; font-weight: bold; }
  .glyph-name { color: #0ff; font-size: 1.2em; margin: 0 0 0.3em 0; }
</style>
</head>
<body>
<div class="summary">
  <h2>Glyph Simplification Results</h2>
  <p>TOTAL_SUMMARY</p>
  <p style="font-size:0.85em;color:#aaa">Showing all GLYPH_COUNT modified glyphs. Scroll down to compare before/after.</p>
</div>

<div id="glyphs"></div>

<script>
const DATA = GLYPH_DATA;

function parseGlif(xml) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, 'text/xml');
  const adv = doc.querySelector('advance');
  const width = adv ? +adv.getAttribute('width') : 750;
  const contours = [];
  for (const c of doc.querySelectorAll('contour')) {
    const pts = [];
    for (const p of c.querySelectorAll('point')) {
      pts.push({
        x: +p.getAttribute('x'), y: +p.getAttribute('y'),
        type: p.getAttribute('type') || 'offcurve',
        smooth: p.getAttribute('smooth') === 'yes'
      });
    }
    contours.push(pts);
  }
  return { width, contours };
}

function contourToPath(pts) {
  if (pts.length === 0) return '';
  let startIdx = pts.findIndex(p => p.type === 'line' || p.type === 'qcurve');
  if (startIdx < 0) return '';
  const start = pts[startIdx];
  let d = `M ${start.x} ${start.y} `;
  let i = (startIdx + 1) % pts.length;
  while (i !== startIdx) {
    const p = pts[i];
    if (p.type === 'line') {
      d += `L ${p.x} ${p.y} `;
    } else if (p.type === 'qcurve') {
      const offCurve = [];
      let j = (i - 1 + pts.length) % pts.length;
      while (pts[j].type === 'offcurve' && j !== startIdx) {
        offCurve.unshift(pts[j]);
        const prev = (j - 1 + pts.length) % pts.length;
        if (pts[prev].type !== 'offcurve') break;
        j = prev;
      }
      if (offCurve.length === 0) {
        d += `L ${p.x} ${p.y} `;
      } else if (offCurve.length === 1) {
        d += `Q ${offCurve[0].x} ${offCurve[0].y} ${p.x} ${p.y} `;
      } else {
        for (let k = 0; k < offCurve.length; k++) {
          let endX, endY;
          if (k < offCurve.length - 1) {
            endX = (offCurve[k].x + offCurve[k+1].x) / 2;
            endY = (offCurve[k].y + offCurve[k+1].y) / 2;
          } else { endX = p.x; endY = p.y; }
          d += `Q ${offCurve[k].x} ${offCurve[k].y} ${endX} ${endY} `;
        }
      }
    }
    i = (i + 1) % pts.length;
  }
  d += 'Z ';
  return d;
}

function renderCard(title, xml, subtitle) {
  const g = parseGlif(xml);
  const card = document.createElement('div');
  card.className = 'card';
  const scale = 0.45;
  const pad = 30;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const pts of g.contours) {
    for (const p of pts) {
      minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
    }
  }
  if (minX === Infinity) { minX = 0; maxX = g.width; minY = -100; maxY = 800; }
  const boundsW = Math.max(g.width, maxX - minX + 40);
  const boundsH = maxY - minY + 40;
  const svgW = (boundsW + pad * 2) * scale;
  const svgH = (boundsH + pad * 2) * scale;
  const yOff = maxY + 20 + pad;
  let svg = '';
  for (let cx = 0; cx <= g.width; cx += 750)
    svg += `<line class="cell-line" x1="${cx+pad}" y1="0" x2="${cx+pad}" y2="${boundsH+pad*2}"/>`;
  svg += `<line class="baseline" x1="0" y1="${yOff}" x2="${boundsW+pad*2}" y2="${yOff}"/>`;
  svg += `<g transform="translate(${pad}, ${yOff}) scale(1, -1)">`;
  const allPath = g.contours.map(contourToPath).join('');
  svg += `<path class="glyph-fill" d="${allPath}"/>`;
  g.contours.forEach((pts, ci) => {
    svg += `<path class="contour-${ci}" d="${contourToPath(pts)}"/>`;
  });
  for (const pts of g.contours)
    for (const p of pts) {
      const cls = p.type === 'offcurve' ? 'point-off' : 'point-on';
      const r = p.type === 'offcurve' ? 2 : 3;
      svg += `<circle class="${cls}" cx="${p.x}" cy="${p.y}" r="${r}"/>`;
    }
  svg += '</g>';
  const totalPts = g.contours.reduce((s, c) => s + c.length, 0);
  card.innerHTML = `<h2>${title}</h2>
    <svg width="${svgW}" height="${svgH}" viewBox="0 0 ${boundsW+pad*2} ${boundsH+pad*2}">${svg}</svg>
    <div class="meta">${subtitle} | ${totalPts} pts, ${g.contours.length} contour(s)</div>`;
  return card;
}

const container = document.getElementById('glyphs');
for (const g of DATA) {
  const section = document.createElement('div');
  section.className = 'row';
  const delta = g.ptsBefore - g.ptsAfter;
  const label = document.createElement('div');
  label.style.width = '100%';
  label.innerHTML = `<p class="glyph-name">${g.name} <span class="delta">-${delta} pts</span> <span style="color:#aaa;font-size:0.8em">(${g.ptsBefore} → ${g.ptsAfter})</span></p>`;
  section.appendChild(label);
  section.appendChild(renderCard('Before', g.before, ''));
  section.appendChild(renderCard('After', g.after, ''));
  container.appendChild(section);
}
</script>
</body>
</html>"""

total_removed = total_pts_before - total_pts_after
html = html.replace(
    "TOTAL_SUMMARY",
    f"{len(changes)} glyphs simplified: {total_pts_before} → {total_pts_after} points "
    f"(<span class='delta'>-{total_removed}</span>)",
)
html = html.replace("GLYPH_COUNT", str(len(changes)))
html = html.replace("GLYPH_DATA", json.dumps(preview_data, ensure_ascii=False))

with open(preview_path, "w") as f:
    f.write(html)
print(f"\nPreview written to {preview_path}")
