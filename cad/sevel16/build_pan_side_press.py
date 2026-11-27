"""Paired inside/outside draw profiles on the long side of the pressed-steel pan."""
from pathlib import Path

import FreeCAD as App
import Part

from config import load

V = App.Vector


def draw_die(a, b, radius):
    direction = (b - a).normalize()
    barrel = Part.makeCylinder(radius, (b-a).Length + 4*radius,
                               a-direction*2*radius, direction)
    # The shop die has a rounded cross section and sloping runouts.
    # Planar end trims preserve analytic ellipses through STEP exchange.
    yz = [(a.y, a.z-radius), (a.y-radius-1, a.z),
          (b.y-radius-1, b.z), (b.y, b.z+radius),
          (b.y+2*radius, b.z+radius), (a.y+2*radius, a.z-radius)]
    pts = [V(a.x-radius-1, y, z) for y, z in yz]
    clip = Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(2*radius+2,0,0))
    return barrel.common(clip)


def wall_y(shape, x, z):
    line = Part.makeLine(V(x, 40, z), V(x, 110, z))
    inner, outer = sorted(v.Point.y for v in shape.section(line).Vertexes)
    return inner, outer


def press(pan, params):
    profile = params["pan_side_press_estimated"]["value"]
    r, depth = profile["radius"], profile["penetration"]
    stock, tools = [], []
    for x, bottom, top in profile["stations"]:
        ends = [wall_y(pan, x, z) for z in (bottom, top)]
        outer = [V(x, side + r - depth, z)
                 for (_, side), z in zip(ends, (bottom, top))]
        tool = draw_die(*outer, r)
        inner_ends = [V(x, side + r - depth, z)
                      for (side, _), z in zip(ends, (bottom, top))]
        inner = draw_die(*inner_ends, r)
        # Retain only the inboard half of the die in the wall stock. Its
        # translated twin shapes the outside and preserves the sheet gauge.
        lo, hi = bottom - r - 2, top + r + 2
        slope = (ends[1][1] - ends[0][1]) / (top - bottom)
        def face_y(z):
            return ends[0][1] + slope * (z - bottom)
        points = [V(x-r-1, 30, lo), V(x-r-1, face_y(lo)-.2, lo),
                  V(x-r-1, face_y(hi)-.2, hi), V(x-r-1, 30, hi)]
        clip = Part.Face(Part.makePolygon(points + [points[0]])).extrude(V(2*r+2, 0, 0))
        stock.append(inner.common(clip))
        tools.append(tool)
    result = pan.fuse(stock).cut(tools).removeSplitter()
    assert result.isValid() and len(result.Solids) == 1 and result.Solids[0].isClosed()
    for x, bottom, top in profile["stations"]:
        z = (bottom + top) / 2
        before, after = wall_y(pan, x, z), wall_y(result, x, z)
        assert before[1] - after[1] > .9 * depth
        assert abs((after[1] - after[0]) - (before[1] - before[0])) < .03, (x, before, after)
    return result


def run(source, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    params, _ = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        pan, = doc.OilPan.Shape.Solids
        doc.OilPan.Shape = press(pan, params)
        doc.Label = destination.stem
        doc.recompute()
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
