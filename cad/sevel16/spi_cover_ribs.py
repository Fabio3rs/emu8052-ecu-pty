"""Registered inner stiffening pattern and shoulder lengths of the SPI cover."""
import hashlib
import json

import FreeCAD as App
import Part

from config import OUTPUT

V = App.Vector


def profile(params):
    spec = params["spi_cover_relief_estimated"]["value"]
    data = (OUTPUT/spec["registration"]).read_bytes()
    if hashlib.sha256(data).hexdigest()!=spec["sha256"]:
        raise ValueError("Unexpected cover registration")
    photo = json.loads(data)
    lo,hi = photo["base_x_limits"]
    filler,opposite = [row[0] for row in photo["top"]["feature_local_mm"]]
    braces = sorted(row[0] for row in photo["underside"]["feature_local_mm"])
    assert all(min(abs(x-y) for y in braces)<1.5 for x in (filler,opposite))
    return {**spec,"shoulder_lengths":[opposite-lo,hi-filler],"brace_x":braces}


def add_ribs(body,lo,hi,half,ceiling,spec):
    inside = max((face for face in body.Faces if face.BoundBox.ZLength<1e-6 and
                  abs(face.BoundBox.ZMax-ceiling)<1e-5),key=lambda face:face.Area)
    drop = spec["rib_drop"]
    def strip(start,end,side):
        a,b = side*(spec["rib_tip_width"]/2),side*(spec["rib_root_width"]/2)
        tip,root = V(0,0,ceiling-drop),V(0,0,ceiling+.1)
        corners = [start-a+tip,start+a+tip,start+b+root,start-b+root]
        return Part.Face(Part.makePolygon(corners+[corners[0]])).extrude(end-start)
    xs = spec["brace_x"]
    long = strip(V(lo,0,0),V(xs[-1]+1,0,0),V(0,1,0))
    cross = [strip(V(x,-half,0),V(x,half,0),V(1,0,0)) for x in xs]
    cast = long.fuse(cross).removeSplitter()
    # The shadowed filler opening in the underside photo interrupts the grid.
    # Project the actual inner ceiling, including its opening, through the grid.
    mask = inside.copy()
    mask.translate(V(0,0,.2))
    cast = cast.common(mask.extrude(V(0,0,-drop-.4)))
    result = body.fuse(cast).removeSplitter()
    assert result.isValid() and len(result.Solids)==1 and result.Volume>body.Volume
    return result
