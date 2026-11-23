"""Nonparallel casting interfaces; bearing/valve datums remain independently defined."""
import math
import FreeCAD as App
import Part
from config import layout
from valvetrain_layout import valves
from cam_carrier import rounded_prism

V = App.Vector


def section_prism(lo, hi, points):
    vertices = [V(lo,y,z) for y,z in points]
    return Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(V(hi-lo,0,0))


def build(params, frame):
    p = params['valvetrain_layout_estimated']['value']
    n = params['valvetrain_nominal']['value']
    c = params['cam_carrier_outline_estimated']['value']
    s = params['carrier_section_estimated']['value']
    xs = layout(params,frame)['supports']
    w = p['cam_journal_width_mm']
    lo,hi = xs[0]-w/2,xs[-1]+w/2
    base,top = p['carrier_base_z_mm'],p['carrier_cap_top_z_mm']
    b,y = s['base_half_width_mm'],p['carrier_half_width_mm']
    m0,m1 = math.tan(math.radians(s['base_slope_y_deg'])),math.tan(math.radians(s['top_slope_y_deg']))
    assert b>y>0 and base+abs(b*m0)<p['carrier_split_z_mm']<top-abs(y*m1)
    zmin,zmax = base-abs(b*m0),top+abs((y+c['cover_boss_radius_mm'])*m1)
    cage = section_prism(lo,hi,[(-b,base-b*m0),(b,base+b*m0),
                              (y,top+y*m1),(-y,top-y*m1)])
    outline = rounded_prism(lo,-b,zmin-1,hi-lo,2*b,zmax-zmin+2,c['outer_corner_radius_mm'])
    cage = cage.common(outline)
    normal = V(0,-m1,1); normal.normalize()
    holes = []
    for fraction in c['cover_boss_fractions']:
        x = lo+fraction*(hi-lo)
        for yy in (-y,y):
            center = V(x,yy,top+yy*m1)
            depth = s['cover_ear_depth_mm']
            cage = cage.fuse(Part.makeCylinder(c['cover_boss_radius_mm'],depth,center-normal*depth,normal))
            holes.append(Part.makeCylinder(c['cover_hole_radius_mm'],depth+2,center-normal*(depth+1),normal))
    inner_y = y-c['side_rail_width_mm']
    for a,bx in zip(xs,xs[1:]):
        holes.append(rounded_prism(a+w/2,-inner_y,p['carrier_split_z_mm'],bx-a-w,2*inner_y,
                                  zmax-p['carrier_split_z_mm']+2,c['window_corner_radius_mm']))
    # Drill the exact documented interfaces after shaping the casting; do not
    # rotate or shear cam bearings or tappet bores with the outer planes.
    holes.append(Part.makeCylinder(p['cam_core_radius_mm']+p['cam_relief_radial_clearance_mm'],
                                  hi-lo+2,V(lo-1,0,p['cam_axis_z_mm']),V(1,0,0)))
    for i,x in enumerate(xs):
        j = p['cam_diagram_indices_in_positive_x'][i]
        holes.append(Part.makeCylinder(n['cam_housing_diameters_diagram_order_mm'][j]/2,w+2,
                                      V(x-w/2-1,0,p['cam_axis_z_mm']),V(1,0,0)))
    for row in valves(params,frame):
        x,yy,_ = row['axis_origin_mm']
        holes.append(Part.makeCylinder(n['tappet_housing_mm']/2,zmax-zmin+2,V(x,yy,zmin-1)))
        width = p['cam_lobe_width_mm']+2*p['cam_relief_axial_clearance_mm']
        radius = params['cam_profile_estimated']['value']['base_radius_mm']
        radius += params['valve_timing_nominal']['value']['cam_height_mm']+p['cam_relief_radial_clearance_mm']
        holes.append(Part.makeCylinder(radius,width,V(x-width/2,0,p['cam_axis_z_mm']),V(1,0,0)))
    flange = s['lower_flange_height_mm']
    band = section_prism(lo-1,hi+1,[(-b-1,base+(-b-1)*m0-1),(b+1,base+(b+1)*m0-1),
                                   (b+1,base+(b+1)*m0+flange),(-b-1,base+(-b-1)*m0+flange)])
    for x in xs[1:-1]:
        notch = Part.makeCylinder(s['scallop_radius_mm'],zmax-zmin+2,V(x,-b,zmin-1))
        holes.append(notch.common(band))
    cage = cage.cut(Part.makeCompound(holes)).removeSplitter()
    assert cage.isValid() and len(cage.Solids)==1
    return cage
