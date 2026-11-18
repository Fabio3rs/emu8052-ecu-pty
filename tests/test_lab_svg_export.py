#!/usr/bin/env python3
"""RecordingRenderer::save_svg: one <path> per draw call, alpha preserved."""

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
paths = root.findall(ns + "path")
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
