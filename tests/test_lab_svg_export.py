#!/usr/bin/env python3
"""RecordingRenderer::save_svg: one <path> per draw call, alpha preserved, pieces
grouped by id (<g id="cyl1-piston">...), and a geometry check on the groups.
"""

import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

binary, rom, output_dir = sys.argv[1:]
svg = pathlib.Path(output_dir) / "sevel-svg-export.svg"
svg.unlink(missing_ok=True)
result = subprocess.run(
    [binary, rom, "--headless", "--capture-tick", "1485000", "--capture-svg", str(svg)],
    capture_output=True, text=True, timeout=60)
assert result.returncode == 0, result.stdout[-1500:] + result.stderr[-1500:]
log = re.search(r"\[LAB-CAPTURE\].*draw_calls=(\d+) triangles=(\d+).*drawn_calls=(\d+)",
                result.stdout)
assert log, result.stdout[-1500:]
draw_calls, triangles, drawn_calls = map(int, log.groups())

# The SVG re-opens as well-formed XML.
root = ET.parse(svg).getroot()
ns = "{http://www.w3.org/2000/svg}"
assert root.tag == ns + "svg"
paths = list(root.iter(ns + "path"))
assert not root.findall(ns + "polygon"), "per-triangle polygons are gone"
# Draw-call count matches: one path per call that emitted triangles.
assert len(paths) == drawn_calls and 0 < drawn_calls <= draw_calls, (
    len(paths), drawn_calls, draw_calls)
# Every triangle is present as one subpath.
subpaths = sum(path.get("d").count("M") for path in paths)
assert subpaths == triangles, (subpaths, triangles)
for path in paths:
    assert path.get("d").count("M") == path.get("d").count("Z") > 0
    assert re.fullmatch(r"#[0-9A-F]{6}", path.get("fill"))
    opacity = path.get("fill-opacity")
    if opacity is None:
        assert path.get("shape-rendering") == "crispEdges"  # opaque, seam-free
    else:
        assert 0.0 <= float(opacity) < 1.0
print(f"paths={len(paths)} draw_calls={draw_calls} triangles={triangles}")


# --- Groups with ids and geometry (v2 doc, section 2) -----------------------
CRANK_R, ROD = 0.0337, 0.127
CROWN, SKIRT, MARGIN = 0.023, 0.040, 0.003
CHAMBER = 0.0674 / (9.2 - 1.0)
HEAD_FACE = CRANK_R + ROD + CROWN + CHAMBER
LINER_BOTTOM = ROD - CRANK_R - SKIRT - MARGIN
BORE = 0.0864

groups = {g.get("id"): g for g in root.iter(ns + "g")}
expected = {"crankshaft", "head", "camshaft"}
for cylinder in range(1, 5):
    expected |= {f"cyl{cylinder}-{part}"
                 for part in ("liner", "crank", "rod", "piston", "valves", "web")}
assert expected <= set(groups), sorted(expected - set(groups))
assert all(path in sum((list(g.iter(ns + "path")) for g in groups.values()), [])
           for path in paths), "ungrouped path in the scene export"


def bbox(group):
    xs, ys = [], []
    for path in group.iter(ns + "path"):
        for x, y in re.findall(r"[ML]([-\d.]+),([-\d.]+)", path.get("d")):
            xs.append(float(x))
            ys.append(float(y))
    return min(xs), min(ys), max(xs), max(ys)


head = bbox(groups["head"])
crankshaft = bbox(groups["crankshaft"])
for cylinder in range(1, 5):
    liner = bbox(groups[f"cyl{cylinder}-liner"])
    piston = bbox(groups[f"cyl{cylinder}-piston"])
    crank = bbox(groups[f"cyl{cylinder}-crank"])
    liner_w, liner_h = liner[2] - liner[0], liner[3] - liner[1]
    # Isotropic scale: the liner's height/width ratio is the physical one
    # (3 mm walls add to the bore width).
    expected_ratio = (HEAD_FACE - LINER_BOTTOM) / (BORE + 0.003)
    assert abs(liner_h / liner_w / expected_ratio - 1.0) < 0.02, (
        cylinder, liner_h / liner_w, expected_ratio)
    # The piston sits inside the liner and never touches the head (y is down).
    assert liner[0] <= piston[0] and piston[2] <= liner[2], cylinder
    assert piston[1] > head[3], (cylinder, piston[1], head[3])
    # The liner ends above the crank circle: it does not cross the crankshaft.
    assert liner[3] < crank[1] or liner[3] < crankshaft[1], cylinder
    assert liner[3] < crankshaft[1], (cylinder, liner[3], crankshaft[1])
print(f"groups={len(groups)} geometry ok")

# M2: each counterweight web is scene geometry below the crank axis line of its
# cylinder (y is down in the SVG), centred on the cylinder axis.
for cylinder in range(1, 5):
    web = bbox(groups[f"cyl{cylinder}-web"])
    liner = bbox(groups[f"cyl{cylinder}-liner"])
    centre = 0.5 * (liner[0] + liner[2])
    assert abs(0.5 * (web[0] + web[2]) - centre) < 0.5, (cylinder, web, liner)
    assert web[2] - web[0] > 0 and web[3] - web[1] > 0, (cylinder, web)
print("webs ok")
