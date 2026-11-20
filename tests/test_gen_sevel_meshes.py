#!/usr/bin/env python3
"""GenSevelMeshes (v2 doc, section 10): the generated parts have the right sizes.

Acceptance: piston diameter = bore - clearance, crank throw radius = 33.7 mm,
58 teeth plus 2 missing on the trigger wheel; rod 127 mm centre to centre;
normals filled and unit length.
"""
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import gen_sevel_meshes as gen  # noqa: E402

g = gen.read_geometry()
meshes = {m.name: m for m in gen.build_all(g)}


def span(mesh, axis):
    lo, hi = mesh.bbox()[axis]
    return hi - lo


# The geometry is read from the header the scene uses, not duplicated.
assert abs(g["bore"] - 0.0864) < 1e-9 and abs(g["crank_radius"] - 0.0337) < 1e-9
assert abs(g["rod_length"] - 0.127) < 1e-9

# Piston: diameter = bore - running clearance; height = crown + skirt.
piston = meshes["piston"]
assert abs(span(piston, 0) - (g["bore"] - gen.CLEARANCE_M)) < 1e-6, span(piston, 0)
assert abs(span(piston, 2) - span(piston, 0)) < 1e-4          # round
assert abs(span(piston, 1) - (g["crown_above_pin"] + g["skirt_below_pin"])) < 1e-9

# Rod: centre-to-centre = 127 mm (small-end circle centre at y=length).
rod = meshes["rod"]
lo, hi = rod.bbox()[1]
small_r, big_r = 0.0145, 0.0285
assert abs((hi - small_r) - g["rod_length"]) < 1e-3, hi
assert abs(lo + big_r) < 1e-3, lo

# Crankshaft: four pins, centre offset = crank radius, 1/4 opposed to 2/3.
crank = meshes["crankshaft"]
ys = sorted({round(v[1], 4) for v in crank.vertices()})
assert max(ys) > g["crank_radius"], "pin surface reaches beyond the throw radius"
pin_offsets = set()
for tri in crank.triangles:
    for v in tri:
        if abs(abs(v[1]) - (g["crank_radius"] + 0.021)) < 1e-6:   # pin top / bottom surface
            pin_offsets.add(round(v[1] - math.copysign(0.021, v[1]), 6))
assert pin_offsets == {round(g["crank_radius"], 6), round(-g["crank_radius"], 6)}, pin_offsets
xs = sorted({round(v[0], 4) for v in crank.vertices()})
assert len({x for x in xs if abs(x) < 0.2}) >= 10               # 5 mains + 4 pins span the block

# Trigger wheel: 58 teeth + 2 missing.
wheel = meshes["trigger_wheel"]
tip = 0.066
tip_angles = sorted({round(math.degrees(math.atan2(v[1], v[0])) % 360, 3)
                     for v in wheel.vertices() if abs(math.hypot(v[0], v[1]) - tip) < 1e-5})
pitch_deg = 360.0 / gen.SLOTS
teeth = {int((a + 1e-6) // pitch_deg) for a in tip_angles}
assert len(teeth) == gen.TEETH == 58, len(teeth)
missing = set(range(gen.SLOTS)) - teeth
assert missing == {58, 59}, missing

# OBJ output: filled unit normals, every face references them.
with tempfile.TemporaryDirectory() as work:
    obj = Path(work) / "m.obj"
    gen.write_obj(list(meshes.values()), obj)
    lines = obj.read_text().splitlines()
vn = [l for l in lines if l.startswith("vn ")]
faces = [l for l in lines if l.startswith("f ")]
assert vn and len(vn) == len(faces) == sum(len(m.triangles) for m in meshes.values())
for line in vn:
    x, y, z = map(float, line.split()[1:])
    assert abs(math.sqrt(x * x + y * y + z * z) - 1.0) < 1e-4, line
assert [l for l in lines if l.startswith("o ")] == [
    "o piston", "o rod", "o crankshaft", "o trigger_wheel"]
print("meshes ok:", {n: len(m.triangles) for n, m in meshes.items()})
