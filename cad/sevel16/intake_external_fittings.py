"""Removable fittings on the front of the SPI intake, photos 713001 and 628178."""
import math

import FreeCAD as App
import Part

from config import layout

V = App.Vector
FRONT = V(0, 1, 0)


def hex_base(center, dims):
    radius = dims["hex_radius"]
    corners = [center + V(radius * math.cos(i * math.pi / 3), 0,
                          radius * math.sin(i * math.pi / 3)) for i in range(6)]
    nut = Part.Face(Part.makePolygon(corners + corners[:1])).extrude(FRONT * dims["hex_length"])
    # The existing pilot in each alloy boss receives the locating stem.
    stem = Part.makeCylinder(4.2, 5, center - FRONT * 4, FRONT)
    return nut.fuse(stem).removeSplitter()


def fittings(params, frame):
    dims = params["intake_external_fittings_estimated"]["value"]
    first, last = layout(params, frame)["supports"][1::2]
    # Both boss faces on the heat jacket are at Y=235, Z=52 in manifold_intake_casting.
    brass = (.69, .52, .28)
    hose_seat, plug_seat = V(last, 235, 52), V(first, 235, 52)
    root = hose_seat + FRONT * dims["hex_length"]
    radius, length = dims["tail_radius"], dims["tail_length"]
    tail = Part.makeCylinder(radius, length, root, FRONT)
    lip = Part.makeCone(radius + 1, radius, 3.5, root + FRONT * (length - 4.5), FRONT)
    nipple = hex_base(hose_seat, dims).fuse([tail, lip])
    bore = Part.makeCylinder(2.8, length + dims["hex_length"] + 6, hose_seat - FRONT * 5, FRONT)
    nipple = nipple.cut(bore).removeSplitter()
    nut = hex_base(plug_seat, dims)
    top = plug_seat + FRONT * dims["hex_length"]
    w, h, depth = dims["socket_width"], dims["socket_height"], dims["socket_length"]
    corner = top - V(w / 2, 0, h / 2)
    case = Part.makeBox(w, depth, h, corner)
    corners = [e for e in case.Edges if e.BoundBox.YLength > depth - 1e-6]
    case = case.makeFillet(1.4, corners)
    cavity = Part.makeBox(w - 3, depth - 2, h - 3, corner + V(1.5, 3, 1.5))
    case = case.cut(cavity)
    return [("IntakeManifoldHoseTail", nipple, brass),
            ("IntakeManifoldPlugBase", nut, brass),
            ("IntakeManifoldSocket", case, (.07, .30, .27))]
