"""Flywheel in crank-local coordinates; photo proportions, not manufacturing CAD."""
import math
import FreeCAD as App
import Part
from config import layout

V = App.Vector
AXIS = V(1,0,0)


def mount_x(params, frame):
    p = params['moving_geometry_estimated']['value']
    return (layout(params,frame)['supports'][-1]+p['main_journal_width_mm']/2
            +p['rear_hub_length_mm']+p['rear_flange_width_mm'])


def cylinder(radius, x, width, y=0, z=0):
    return Part.makeCylinder(radius,width,V(x,y,z),AXIS)


def prism(points, width):
    return Part.Face(Part.Wire(Part.makePolygon(points+[points[0]]).Edges)).extrude(V(width,0,0))


def build(params, frame):
    p = params['flywheel_visual_estimated']['value']
    c = params['moving_geometry_estimated']['value']
    x,t,r = mount_x(params,frame),p['thickness_mm'],p['body_radius_mm']
    assert 0<p['front_recess_depth_mm']<t and 0<p['back_relief_depth_mm']<t
    assert p['back_relief_inner_radius_mm']>c['rear_flange_radius_mm']
    assert p['back_relief_outer_radius_mm']<p['outer_fixing_circle_radius_mm']+p['outer_fixing_hole_radius_mm']<r
    body = cylinder(r,x,t)
    front = x+t-p['front_recess_depth_mm']
    holes = [cylinder(p['center_bore_radius_mm'],x-1,t+2),
             cylinder(p['front_recess_radius_mm'],front,p['front_recess_depth_mm']+1)]
    relief = cylinder(p['back_relief_outer_radius_mm'],x-1,p['back_relief_depth_mm']+1)
    relief = relief.cut(cylinder(p['back_relief_inner_radius_mm'],x-1,p['back_relief_depth_mm']+1))
    holes.append(relief)
    bolts = {}
    for i in range(6):
        a = math.radians(60*i)
        y,z = c['rear_bolt_circle_radius_mm']*math.sin(a),c['rear_bolt_circle_radius_mm']*math.cos(a)
        holes.append(cylinder(c['rear_bolt_hole_radius_mm'],x-1,t+2,y,z))
        start = x-c['rear_flange_width_mm']+p['bolt_end_inset_mm']
        shank = cylinder(p['bolt_shank_radius_mm'],start,front-start,y,z)
        pts = [V(front,y+p['bolt_head_radius_mm']*math.sin(math.radians(j*60)),
                 z+p['bolt_head_radius_mm']*math.cos(math.radians(j*60))) for j in range(6)]
        bolts[f'FlywheelBolt{i+1}'] = shank.fuse(prism(pts,p['bolt_head_height_mm'])).removeSplitter()
    for i in range(p['outer_fixing_count']):
        a = math.radians(i*360/p['outer_fixing_count']+30)
        holes.append(cylinder(p['outer_fixing_hole_radius_mm'],x-1,t+2,
                     p['outer_fixing_circle_radius_mm']*math.sin(a),
                     p['outer_fixing_circle_radius_mm']*math.cos(a)))
    body = body.cut(Part.makeCompound(holes)).removeSplitter()
    # A continuous ring with trapezoidal visual teeth, explicitly not involutes.
    n = p['ring_teeth_visual_count']
    assert isinstance(n,int) and n>=12 and r<p['ring_root_radius_mm']<p['ring_tip_radius_mm']
    assert 0<=p['ring_offset_mm'] and p['ring_offset_mm']+p['ring_width_mm']<=t
    rx = x+p['ring_offset_mm']
    points = []
    for i in range(n):
        for f,rad in [(0,p['ring_root_radius_mm']),(.2,p['ring_root_radius_mm']),
                      (.35,p['ring_tip_radius_mm']),(.65,p['ring_tip_radius_mm']),
                      (.8,p['ring_root_radius_mm'])]:
            a = 2*math.pi*(i+f)/n
            points.append(V(rx,rad*math.sin(a),rad*math.cos(a)))
    ring = prism(points,p['ring_width_mm']).cut(cylinder(r,rx-1,p['ring_width_mm']+2))
    parts = {'Flywheel':body,'StarterRing':ring,**bolts}
    for shape in parts.values():
        shape.rotate(V(),AXIS,p['mount_phase_deg'])
        assert not shape.isNull() and shape.isValid() and len(shape.Solids)==1
    assert abs(p['mount_phase_deg']%60)<1e-9, 'Mount phase must preserve six-hole registration'
    return parts
