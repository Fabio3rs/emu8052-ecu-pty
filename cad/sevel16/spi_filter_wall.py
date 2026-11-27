"""Cast the filter-side upright, its foot and the ledge above the recessed skirt."""
import math

import FreeCAD as App
import Part

from build_core_plug_wall import cubic_knots
from config import layout

V = App.Vector


def casting_stock(params, frame):
    dims = params["spi_filter_wall_estimated"]["value"]
    columns = []
    for x,m,f,l,ledge_z in zip(dims["x_mm"],dims["column_weight"],dims["foot_weight"],
                               dims["ledge_weight"],dims["ledge_z_mm"],strict=True):
        col = [V(x,y-m*mc-f*fc-l*lc,z) for z,y,mc,fc,lc in dims["upper_z_y_column_foot_ledge"]]
        col.extend(V(x,y-d*l,ledge_z+dz) for dz,y,d in dims["ledge_dz_y_depth"])
        bottom = dims["bottom_z_mm"]
        col += [V(x,-72-7*l,(col[-1].z+bottom)/2),V(x,dims["bottom_y_mm"],bottom)]
        assert all(a.z>b.z for a,b in zip(col,col[1:]))
        columns.append(col)
    surface = Part.BSplineSurface()
    um,uk = cubic_knots(len(columns))
    vm,vk = cubic_knots(len(columns[0]))
    surface.buildFromPolesMultsKnots(columns,um,vm,uk,vk,False,False,3,3)
    sections = []
    for i in range(dims["intervals"]+1):
        curve = surface.uIso(uk[-1]*i/dims["intervals"])
        a,b = curve.value(curve.FirstParameter),curve.value(curve.LastParameter)
        c,d = V(b.x,dims["inside_y_mm"],b.z),V(a.x,dims["inside_y_mm"],a.z)
        sections.append(Part.Wire([curve.toShape(),Part.makeLine(b,c),Part.makeLine(c,d),Part.makeLine(d,a)]))
    stock = Part.makeLoft(sections,True,True)
    moving = params["moving_geometry_estimated"]["value"]
    rod = params["piston_rod_visual_estimated"]["value"]
    g = layout(params,frame)
    swing = g["radius"]+math.hypot(rod["rod_bolt_y_mm"]+rod["rod_bolt_head_radius_mm"],
                                  rod["rod_bolt_half_length_mm"]+4)
    radius = max(moving["counterweight_radius_mm"],swing)+moving["crankcase_clearance_mm"]
    crank = Part.makeCylinder(radius+.05,220,V(136,0,-g["height"]),V(1,0,0))
    visual = params["casting_visual_estimated"]["value"]
    auxiliary = Part.makeCylinder(26,240,V(-65,visual["aux_y"],visual["aux_z"]),V(1,0,0))
    return stock.cut([crank,auxiliary])


def build(original, params, frame):
    stock = casting_stock(params,frame)
    solid = original.Solids[0].fuse(stock).removeSplitter()
    assert len(solid.Solids)==1 and solid.isValid() and solid.Solids[0].isClosed()
    assert len(solid.Shells)==len(original.Shells) and 1<solid.Volume/original.Volume<1.08
    return solid
