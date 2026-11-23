"""Continuous four-window cage; dimensions beyond bearing interfaces estimated."""
import FreeCAD as App
import Part
from config import layout
from valvetrain_layout import valves


def build_interfaces(params, frame):
    """Legacy A3 v002 interfaces, retained for geometric change verification."""
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    v = App.Vector
    xs = layout(params,frame)['supports']
    w = p['cam_journal_width_mm']
    lo,hi = xs[0]-w/2,xs[-1]+w/2
    y,z0,z1 = p['carrier_half_width_mm'],p['carrier_base_z_mm'],p['carrier_split_z_mm']
    zcam = p['cam_axis_z_mm']
    body = Part.makeBox(hi-lo,2*y,z1-z0,v(lo,-y,z0))
    core = Part.makeCylinder(p['cam_core_radius_mm']+p['cam_relief_radial_clearance_mm'],
                            hi-lo+2,v(lo-1,0,zcam),v(1,0,0))
    tools,caps = [core],[]
    for i,x in enumerate(xs):
        index = p['cam_diagram_indices_in_positive_x'][i]
        radius = n['cam_housing_diameters_diagram_order_mm'][index]/2
        hole = Part.makeCylinder(radius,w+2,v(x-w/2-1,0,zcam),v(1,0,0))
        tools.append(hole)
        cap = Part.makeBox(w,2*y,p['carrier_cap_top_z_mm']-z1,v(x-w/2,-y,z1))
        caps.append(cap.cut(hole).removeSplitter())
    for row in valves(params,frame):
        x,yy,_ = row['axis_origin_mm']
        tools.append(Part.makeCylinder(n['tappet_housing_mm']/2,z1-z0+2,v(x,yy,z0-1)))
        clearance = p['cam_relief_axial_clearance_mm']
        width = p['cam_lobe_width_mm']+2*clearance
        radius = params['cam_profile_estimated']['value']['base_radius_mm']
        radius += params['valve_timing_nominal']['value']['cam_height_mm']+p['cam_relief_radial_clearance_mm']
        tools.append(Part.makeCylinder(radius,width,v(x-width/2,0,zcam),v(1,0,0)))
    body = body.cut(Part.makeCompound(tools)).removeSplitter()
    for shape in [body,*caps]:
        assert shape.isValid() and len(shape.Solids)==1
    return {'CamCarrier':body,**{f'CamCap{i+1}':s for i,s in enumerate(caps)}}


def rounded_prism(x, y, z, length, width, height, radius):
    shape = Part.makeBox(length,width,height,App.Vector(x,y,z))
    edges = [e for e in shape.Edges if e.BoundBox.ZLength>height-1e-7
             and e.BoundBox.XLength<1e-7 and e.BoundBox.YLength<1e-7]
    assert len(edges)==4 and 0<radius<min(length,width)/2
    return shape.makeFillet(radius,edges)


def build(params, frame):
    p = params['valvetrain_layout_estimated']['value']
    n = params['valvetrain_nominal']['value']
    c = params['cam_carrier_outline_estimated']['value']
    xs = layout(params,frame)['supports']
    w,y = p['cam_journal_width_mm'],p['carrier_half_width_mm']
    lo,hi = xs[0]-w/2,xs[-1]+w/2
    z0,z1,top = p['carrier_base_z_mm'],p['carrier_split_z_mm'],p['carrier_cap_top_z_mm']
    cage = rounded_prism(lo,-y,z0,hi-lo,2*y,top-z0,c['outer_corner_radius_mm'])
    holes = []
    for fraction in c['cover_boss_fractions']:
        x = lo+fraction*(hi-lo)
        for yy in (-y,y):
            boss = Part.makeCylinder(c['cover_boss_radius_mm'],top-z0,App.Vector(x,yy,z0))
            cage = cage.fuse(boss)
            holes.append(Part.makeCylinder(c['cover_hole_radius_mm'],top-z0+2,
                                          App.Vector(x,yy,z0-1)))
    # Retain the proven lower tappet/core reliefs, while rounding the exterior.
    old = build_interfaces(params,frame)
    lower_box = Part.makeBox(hi-lo,2*y,z1-z0,App.Vector(lo,-y,z0))
    holes.append(lower_box.cut(old['CamCarrier']))
    inner_y = y-c['side_rail_width_mm']
    for a,b in zip(xs,xs[1:]):
        holes.append(rounded_prism(a+w/2,-inner_y,z1,b-a-w,2*inner_y,top-z1+1,
                                   c['window_corner_radius_mm']))
    for i,x in enumerate(xs):
        index = p['cam_diagram_indices_in_positive_x'][i]
        radius = n['cam_housing_diameters_diagram_order_mm'][index]/2
        holes.append(Part.makeCylinder(radius,w+2,App.Vector(x-w/2-1,0,p['cam_axis_z_mm']),
                                       App.Vector(1,0,0)))
    cage = cage.cut(Part.makeCompound(holes)).removeSplitter()
    assert cage.isValid() and len(cage.Solids)==1
    return {'CamCarrier':cage}
