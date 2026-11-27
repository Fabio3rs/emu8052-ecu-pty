"""Form the flat rear walls and rounded returns seen between the spark columns."""
import FreeCAD as App
import Part

from config import layout
from head_fixing_alignment import lower_centers

V = App.Vector


def tool_for_bay(doc,params,frame,i):
    spec = params["spi_spark_bays_estimated"]["value"]
    xs = layout(params,frame)["centers"]
    x = xs[i]
    left,right,offset = spec["bay_widths_setback"][i]
    back = spec["rear_wall_y"]+offset
    front = -136
    wires = []
    for z,shift,width,depth in spec["sections_z_xshift_halfwidth_setback"]:
        a,b = x-left-width+shift,x+right+width+shift
        corners = [V(a,front,z),V(b,front,z),V(b,back+depth,z),V(a,back+depth,z)]
        wires.append(Part.makePolygon(corners+[corners[0]]))
    blank = Part.makeLoft(wires,True,True)
    # Rounding the edges of the drafted side walls leaves a broad rear face.
    # The forward edges of the tool are entirely outside the casting.
    edges = [e for e in blank.Edges if max(v.Point.y for v in e.Vertexes)>front+1]
    tool = blank.makeFillet(spec["corner_radius"],edges)
    collar = Part.makeCylinder(spec["protected_plug_radius"],100,V(0,0,-62))
    place = doc.getObject(f"C{i+1}_SparkShell").Placement
    collar.Placement = place.multiply(collar.Placement)
    fx,fy = lower_centers(xs)[i]
    pad = Part.makeCylinder(8,19,V(fx,fy,0))
    return tool.cut([collar,pad])


def third_foot(head,params,frame):
    spec = params["spi_spark_bays_estimated"]["value"]["third_foot_blend"]
    cx,cy = lower_centers(layout(params,frame)["centers"])[2]
    tip = cy+spec["y_from_fixing"]
    raw = Part.makeCylinder(spec["radius"],tip+115,V(cx+spec["offset_x"],-115,spec["z"]),V(0,1,0))
    edges = [e for e in raw.Edges if abs(e.BoundBox.YMin-tip)<1e-5]
    # Blend the low, ruled skirt into C3 without cutting the fixing annulus.
    blend = raw.makeFillet(spec["edge_radius"],edges)
    land = Part.makeCylinder(spec["land_radius"],18,V(cx,cy,0))
    result = head.Solids[0].cut(blend.cut(land)).removeSplitter()
    assert result.isValid() and len(result.Solids)==1 and 0<head.Volume-result.Volume<2500
    return result


def revise(doc,head,params,frame,indices):
    for i in indices:
        before, = head.Solids
        head = before.cut(tool_for_bay(doc,params,frame,i)).removeSplitter()
        if not head.isValid() or len(head.Solids)!=1:
            raise ValueError(f"Invalid spark bay at cylinder {i+1}")
        if abs(head.BoundBox.XLength-before.BoundBox.XLength)>.01 or not .95*before.Volume<head.Volume<before.Volume:
            raise ValueError(f"Unexpected loss of casting at cylinder {i+1}")
    return head
