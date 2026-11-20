#!/usr/bin/env python3
"""Parametric SEVEL engine meshes (v2 analysis, section 10).

Builds the parts from the numbers in include/lab/SevelGeometry.hpp (parsed, not
copied, so the meshes cannot drift from the scene geometry) and writes a
Wavefront OBJ with flat normals. Parts: piston (revolved profile), connecting
rod (I-section outline, extruded), crankshaft (5 mains, 4 pins at the crank
radius, counterweights) and the 60-2 trigger wheel (58 teeth, 2 missing).

Usage: gen_sevel_meshes.py [--out build/sevel_meshes.obj]
LLM-written (Claude); dimensions that are drawing estimates are marked.
"""
import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = ROOT / "include" / "lab" / "SevelGeometry.hpp"


def read_geometry(header=HEADER):
    """The constants the scene uses, parsed from SevelGeometry.hpp."""
    text = header.read_text()

    def value(pattern):
        found = re.search(pattern, text)
        if not found:
            raise ValueError(f"constant not found: {pattern}")
        return float(found.group(1))

    return {
        "crank_radius": value(r"crank_radius_m\s*=\s*([\d.]+)"),
        "rod_length": value(r"visual_estimate_rod_length_m\s*=\s*([\d.]+)"),
        "bore": value(r"kSevelBoreM\s*=\s*([\d.]+)"),
        "stroke": value(r"kSevelStrokeM\s*=\s*([\d.]+)"),
        "crown_above_pin": value(r"kSevelPistonCrownAbovePinM\s*=\s*([\d.]+)"),
        "skirt_below_pin": value(r"kSevelPistonSkirtBelowPinM\s*=\s*([\d.]+)"),
    }


class Mesh:
    """Triangles with flat normals; vertices are not shared across faces."""

    def __init__(self, name):
        self.name = name
        self.triangles = []  # ((x,y,z) * 3)

    def tri(self, a, b, c):
        self.triangles.append((a, b, c))

    def quad(self, a, b, c, d):
        self.tri(a, b, c)
        self.tri(a, c, d)

    def vertices(self):
        return [v for t in self.triangles for v in t]

    def bbox(self):
        vs = self.vertices()
        return tuple((min(v[i] for v in vs), max(v[i] for v in vs)) for i in range(3))


def revolve(name, profile, segments=48):
    """Surface of revolution about the Y axis from (radius, y) points."""
    mesh = Mesh(name)
    for i in range(len(profile) - 1):
        (r0, y0), (r1, y1) = profile[i], profile[i + 1]
        for s in range(segments):
            a0 = 2 * math.pi * s / segments
            a1 = 2 * math.pi * (s + 1) / segments
            p = lambda r, y, a: (r * math.cos(a), y, r * math.sin(a))
            if r0 == 0.0:
                mesh.tri(p(0, y0, a0), p(r1, y1, a0), p(r1, y1, a1))
            elif r1 == 0.0:
                mesh.tri(p(r0, y0, a0), p(0, y1, a0), p(r0, y0, a1))
            else:
                mesh.quad(p(r0, y0, a0), p(r1, y1, a0), p(r1, y1, a1), p(r0, y0, a1))
    return mesh


def extrude(name, outline, z0, z1):
    """Prism from a closed 2D outline (counter-clockwise), caps by fan."""
    mesh = Mesh(name)
    n = len(outline)
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        mesh.quad((x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1))
    cx = sum(p[0] for p in outline) / n
    cy = sum(p[1] for p in outline) / n
    for i in range(n):
        (x0, y0), (x1, y1) = outline[i], outline[(i + 1) % n]
        mesh.tri((cx, cy, z1), (x0, y0, z1), (x1, y1, z1))
        mesh.tri((cx, cy, z0), (x1, y1, z0), (x0, y0, z0))
    return mesh


def circle(cx, cy, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n))
            for k in range(n)]


CLEARANCE_M = 0.00004  # piston-to-bore running clearance, drawing estimate


def build_piston(g):
    r = g["bore"] / 2 - CLEARANCE_M / 2
    top, bottom = g["crown_above_pin"], -g["skirt_below_pin"]
    land = r * 0.93  # crown land above the rings
    profile = [(0.0, top), (land, top), (land, top - 0.011), (r, top - 0.011),
               (r, bottom + 0.004), (r * 0.97, bottom), (r * 0.80, bottom), (0.0, bottom)]
    return revolve("piston", profile)


def build_rod(g):
    big_r, small_r = 0.0285, 0.0145  # bore bosses, drawing estimates
    length = g["rod_length"]
    # Outline: big-end circle at y=0, small-end circle at y=length, tapered beam.
    big = circle(0.0, 0.0, big_r)
    small = circle(0.0, length, small_r)
    beam = [(-0.009, big_r * 0.8), (0.009, big_r * 0.8), (0.006, length - small_r * 0.8),
            (-0.006, length - small_r * 0.8)]
    parts = [extrude("rod_big_end", big, -0.011, 0.011),
             extrude("rod_small_end", small, -0.009, 0.009),
             extrude("rod_beam", beam, -0.004, 0.004)]
    merged = Mesh("rod")
    for part in parts:
        merged.triangles += part.triangles
    return merged


def build_crankshaft(g):
    """Axis along X; pitch is the cylinder pitch estimate (95 mm)."""
    pitch = 0.095
    throw = g["crank_radius"]
    mesh = Mesh("crankshaft")

    def cylinder_x(x0, x1, cy, cz, radius, n=24):
        for s in range(n):
            a0, a1 = 2 * math.pi * s / n, 2 * math.pi * (s + 1) / n
            p = lambda x, a: (x, cy + radius * math.cos(a), cz + radius * math.sin(a))
            mesh.quad(p(x0, a0), p(x1, a0), p(x1, a1), p(x0, a1))

    for k in range(5):                       # five main journals on the axis
        x = (k - 2) * pitch
        cylinder_x(x - 0.012, x + 0.012, 0.0, 0.0, 0.025)
    for cyl in range(4):                     # four pins: 1/4 up, 2/3 down
        x = (cyl - 1.5) * pitch
        offset = throw if cyl in (0, 3) else -throw
        cylinder_x(x - 0.011, x + 0.011, offset, 0.0, 0.021)
        # Counterweight opposite the pin (cheek) on the +x side of the pin.
        cheek = [(x + 0.012, -offset * 0.2), (x + 0.020, -offset * 0.2),
                 (x + 0.020, -offset * 1.6), (x + 0.012, -offset * 1.6)]
        for i in range(4):
            (xa, ya), (xb, yb) = cheek[i], cheek[(i + 1) % 4]
            mesh.quad((xa, ya, -0.03), (xb, yb, -0.03), (xb, yb, 0.03), (xa, ya, 0.03))
    return mesh


TEETH, SLOTS = 58, 60


def build_trigger_wheel(g):
    """60-2: 60 tooth positions, the last two missing. Axis along Z."""
    r_root, r_tip = 0.060, 0.066
    pitch = 2 * math.pi / SLOTS
    outline = []
    for slot in range(SLOTS):
        a0 = slot * pitch
        if slot >= SLOTS - 2:               # the two missing teeth: root radius only
            outline += [(r_root * math.cos(a0), r_root * math.sin(a0)),
                        (r_root * math.cos(a0 + pitch * 0.999), r_root * math.sin(a0 + pitch * 0.999))]
            continue
        for frac, radius in ((0.0, r_root), (0.2, r_tip), (0.7, r_tip), (0.9, r_root)):
            a = a0 + frac * pitch
            outline.append((radius * math.cos(a), radius * math.sin(a)))
    wheel = extrude("trigger_wheel", outline, -0.004, 0.004)
    return wheel


def build_all(g=None):
    g = g or read_geometry()
    return [build_piston(g), build_rod(g), build_crankshaft(g), build_trigger_wheel(g)]


def normal(tri):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def write_obj(meshes, path):
    lines = ["# SEVEL parametric meshes (tools/gen_sevel_meshes.py), metres, flat normals"]
    v_index = n_index = 1
    for mesh in meshes:
        lines.append(f"o {mesh.name}")
        for tri in mesh.triangles:
            n = normal(tri)
            for v in tri:
                lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
            lines.append(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}")
            lines.append(f"f {v_index}//{n_index} {v_index + 1}//{n_index} {v_index + 2}//{n_index}")
            v_index += 3
            n_index += 1
    Path(path).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "build" / "sevel_meshes.obj"))
    args = parser.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    meshes = build_all()
    write_obj(meshes, args.out)
    print(f"wrote {args.out}: " + ", ".join(f"{m.name}={len(m.triangles)} tris" for m in meshes))
