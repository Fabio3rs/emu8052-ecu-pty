"""Hollow removable cover aligned to the existing inclined carrier interface."""
import math
import FreeCAD as App
import Part
from config import layout
from cam_carrier import rounded_prism

V = App.Vector


def build(params,frame):
    p = params['external_closures_estimated']['value']
    c = params['cam_carrier_outline_estimated']['value']
    v = params['valvetrain_layout_estimated']['value']
    angle = params['carrier_section_estimated']['value']['top_slope_y_deg']
    stations = layout(params,frame)['supports']
    lo,hi = stations[0]-v['cam_journal_width_mm']/2,stations[-1]+v['cam_journal_width_mm']/2
    half = v['carrier_half_width_mm']/math.cos(math.radians(angle))
    radius = c['outer_corner_radius_mm']
    gasket,flange,wall,height = [p[k] for k in
        ('cover_gasket_mm','cover_flange_mm','cover_wall_mm','cover_height_mm')]
    assert 0<wall<flange+wall<height and 0<p['cover_roof_radius_mm']<wall
    def prism(z,h,inset=0):
        return rounded_prism(lo+inset,-half+inset,z,hi-lo-2*inset,2*(half-inset),h,radius-inset)
    def rim(z,h):
        shape = prism(z,h)
        for fraction in c['cover_boss_fractions']:
            for y in (-half,half):
                shape = shape.fuse(Part.makeCylinder(c['cover_boss_radius_mm'],h,V(lo+fraction*(hi-lo),y,z)))
        return shape
    seal = rim(0,gasket)
    inner = prism(-1,height+gasket+2,c['side_rail_width_mm'])
    seal = seal.cut(inner)
    body = prism(gasket+flange,height-flange)
    roof = gasket+height
    edges = [e for e in body.Edges if abs(e.BoundBox.ZMin-roof)<1e-7 and abs(e.BoundBox.ZMax-roof)<1e-7]
    body = body.makeFillet(p['cover_roof_radius_mm'],edges).fuse(rim(gasket,flange))
    cavity = prism(gasket-1,height-wall+1,wall)
    body = body.cut(cavity)
    holes = []
    for fraction in c['cover_boss_fractions']:
        for y in (-half,half):
            holes.append(Part.makeCylinder(c['cover_hole_radius_mm'],gasket+height+2,
                                          V(lo+fraction*(hi-lo),y,-1)))
    seal = seal.cut(Part.makeCompound(holes)).removeSplitter()
    body = body.cut(Part.makeCompound(holes))
    x = lo+p['filler_x_fraction']*(hi-lo)
    neck = p['filler_neck_height_mm']
    body = body.fuse(Part.makeCylinder(p['filler_outer_radius_mm'],neck+wall,V(x,0,roof-wall)))
    body = body.cut(Part.makeCylinder(p['filler_inner_radius_mm'],neck+wall+2,V(x,0,roof-wall-1)))
    cap = Part.makeCylinder(p['filler_cap_radius_mm'],p['filler_cap_height_mm'],V(x,0,roof+neck))
    transform = App.Placement(V(0,0,v['carrier_cap_top_z_mm']),App.Rotation(V(1,0,0),angle))
    result = {'ValveCover':body.removeSplitter(),'ValveCoverGasket':seal,'OilFillerCap':cap}
    for shape in result.values():
        shape.Placement = transform
        assert shape.isValid() and len(shape.Solids)==1 and shape.Volume>0
    return result
