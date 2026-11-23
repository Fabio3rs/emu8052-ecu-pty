"""Shared manifold interfaces derived from the existing eight head ports."""
import FreeCAD as App
import Part
from config import layout
from valvetrain_layout import valves
from head_profiles import capsule
from head_passages import circle

V = App.Vector


def sweep(points,radius):
    poles = [V(*p) for p in points]
    curve = Part.BezierCurve()
    curve.setPoles(poles)
    section = circle(points[0],tuple(poles[1]-poles[0]),radius)
    shape = Part.Wire([curve.toShape()]).makePipeShell([section],True,False)
    assert shape.isValid() and len(shape.Solids)==1
    return shape


def flange(rows,params,y,depth,extra):
    h = params['head_lower_casting_estimated']['value']
    def center(row):
        return row['axis_origin_mm'][0],h[row['kind']+'_port_z_mm']
    def radius(row):
        return h[row['kind']+'_port_radius_mm']+extra
    if len(rows)==1:
        x,z = center(rows[0])
        return Part.makeCylinder(radius(rows[0]),depth,V(x,y,z),V(0,1,0))
    shapes = []
    for a,b in zip(rows,rows[1:]):
        shape = Part.Face(capsule(center(a),center(b),radius(a),radius(b))).extrude(V(0,0,depth))
        shape.rotate(V(),V(1,0,0),90)
        shape.translate(V(0,y+depth,0))
        shapes.append(shape)
    return shapes[0].multiFuse(shapes[1:]).removeSplitter() if len(shapes)>1 else shapes[0]


def gaskets(params,frame):
    h,p = params['head_lower_casting_estimated']['value'],params['manifold_visual_estimated']['value']
    rows = valves(params,frame)
    result = {}
    for i in range(2):
        group = rows[i*4:i*4+4]
        y,depth = h['manifold_face_y_mm'],p['gasket_mm']
        shape = flange(group,params,y,depth,5)
        x = layout(params,frame)['supports'][1+2*i]
        coolant = Part.makeCylinder(h['coolant_port_radius_mm']+2,depth,
                                   V(x,y,h['coolant_port_z_mm']),V(0,1,0))
        shape = shape.fuse(coolant)
        holes = [Part.makeCylinder(h[r['kind']+'_port_radius_mm'],depth+2,
                    V(r['axis_origin_mm'][0],y-1,h[r['kind']+'_port_z_mm']),V(0,1,0)) for r in group]
        holes.append(Part.makeCylinder(h['coolant_port_radius_mm'],depth+2,
                     V(x,y-1,h['coolant_port_z_mm']),V(0,1,0)))
        shape = shape.cut(Part.makeCompound(holes)).removeSplitter()
        assert shape.isValid() and len(shape.Solids)==1
        result[f'ManifoldGasket{i+1}'] = shape
    return result
