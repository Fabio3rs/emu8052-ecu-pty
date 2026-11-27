"""Trim the lower plug-side casting against the surveyed chamber-face perimeter."""
import hashlib
import json

import FreeCAD as App
import Part

from build_head_main_row import centers
from config import OUTPUT, layout
from head_fixing_alignment import lower_centers

V = App.Vector


def cutter(params,frame):
    spec = params["spi_head_front_rim_estimated"]["value"]
    data = (OUTPUT/spec["registration"]).read_bytes()
    if hashlib.sha256(data).hexdigest()!=spec["sha256"]:
        raise ValueError("Unexpected spark-side rim registration")
    surveyed = json.loads(data)["deck_view"]["lower_rim_xy_mm"]
    # The two end faces carry their own machined interfaces. Let the tool
    # recede beyond the casting at both ends of the photographed side.
    lo,start,stop,hi = spec["end_blend_x"]
    points = [(lo-4,-108)]
    for x,y in surveyed:
        if lo<x<hi:
            t = min(1,(x-lo)/(start-lo),(hi-x)/(hi-stop))
            weight = t*t*(3-2*t)
            points.append((x,-108+weight*(108+y-spec["edge_allowance"])))
    points.append((hi+4,-108))
    rows = []
    for z,dy in spec["height_y_offsets"]:
        curve = Part.BSplineCurve()
        rim = [V(x,y+dy,z) for x,y in points]
        curve.interpolate(rim)
        outer = [rim[-1],V(rim[-1].x,-170,z),V(rim[0].x,-170,z),rim[0]]
        rows.append(Part.Wire([curve.toShape()]+[Part.makeLine(a,b) for a,b in zip(outer,outer[1:])]))
    tool = Part.makeLoft(rows,True,False)
    xs = layout(params,frame)["centers"]
    pads = [Part.makeCylinder(7.85,11,V(x,y,0)) for x,y in lower_centers(xs)]
    pads += [Part.makeCylinder(10,68,V(x,y,0)) for x,y in centers(xs)]
    return tool.cut(pads)


def trim(head,params,frame):
    result = head.cut(cutter(params,frame)).removeSplitter()
    assert result.isValid() and len(result.Solids)==1 and result.Solids[0].isClosed()
    if not .94*head.Volume<result.Volume<head.Volume or abs(result.BoundBox.XLength-head.BoundBox.XLength)>.01:
        raise ValueError("Lower-rim cut removed more than the local plug-side casting")
    return result
