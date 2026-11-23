"""External timing drive; exact tangent belt envelope with simplified pulley teeth."""
import math
import FreeCAD as App
import Part
from config import layout
from timing_layout import wheels, path

V = App.Vector
AXIS = V(1,0,0)


def cylinder(radius, x, width):
    return Part.makeCylinder(radius,width,V(x,0,0),AXIS)


def ring(outer, inner, x, width):
    return cylinder(outer,x,width).cut(cylinder(inner,x-1,width+2))


def sprocket(row, p, left, width):
    root = row['pitch_radius']-p['tooth_root_below_pitch_mm']
    points = []
    for i in range(row['teeth']):
        for fraction,radius in [(0,root),(.18,root),(.34,row['tip_radius']),
                                (.66,row['tip_radius']),(.82,root)]:
            a = 2*math.pi*(i+fraction)/row['teeth']
            points.append(V(left,radius*math.cos(a),radius*math.sin(a)))
    return Part.Face(Part.makePolygon(points+[points[0]])).extrude(V(width,0,0))


def belt(params, frame):
    p = params['timing_visual_estimated']['value']
    x = p['pulley_center_x_mm']-p['belt_width_mm']/2
    def boundary(offset):
        edges = []
        for segment in path(params,frame):
            if segment['kind']=='line':
                points = [V(x,q[0]+offset*segment['normal'][0],q[1]+offset*segment['normal'][1])
                          for q in segment['points']]
                edges.append(Part.makeLine(*points))
            else:
                radius = segment['radius']+segment['sign']*offset
                assert radius>0
                cy,cz = segment['center']
                angles = [segment['start']+f*segment['sweep'] for f in (0,.5,1)]
                points = [V(x,cy+radius*math.cos(a),cz+radius*math.sin(a)) for a in angles]
                edges.append(Part.Arc(*points).toShape())
        wire = Part.Wire(edges)
        assert wire.isClosed()
        return Part.Face(wire)
    section = boundary(p['belt_thickness_mm']/2).cut(boundary(-p['belt_thickness_mm']/2))
    return section.extrude(V(p['belt_width_mm'],0,0))


def build(params, frame):
    p = params['timing_visual_estimated']['value']
    n = params['auxiliary_nominal']['value']
    c = params['moving_geometry_estimated']['value']
    v = params['valvetrain_layout_estimated']['value']
    rows = {w['name']:w for w in wheels(params,frame)}
    left,width = p['pulley_center_x_mm']-p['pulley_width_mm']/2,p['pulley_width_mm']
    right = left+width
    parts = {}
    for name in ('Cam','Crank','Aux'):
        shape = sprocket(rows[name],p,left,width)
        if name=='Cam':
            front = layout(params,frame)['supports'][0]-v['cam_journal_width_mm']/2
            j = v['cam_diagram_indices_in_positive_x'][0]
            radius = params['valvetrain_nominal']['value']['cam_journal_diameters_diagram_order_mm'][j]/2
            shape = shape.fuse(cylinder(radius,right,front-right))
            holes = []
            for i in range(p['cam_window_count']):
                a = 2*math.pi*i/p['cam_window_count']
                hole = cylinder(p['cam_window_radius_mm'],left-1,width+2)
                r = rows[name]['pitch_radius']*p['cam_window_circle_fraction']
                hole.translate(V(0,r*math.cos(a),r*math.sin(a)))
                holes.append(hole)
            shape = shape.cut(Part.makeCompound(holes))
        else:
            radius = c['nose_radius_mm'] if name=='Crank' else p['aux_nose_radius_mm']
            shape = shape.cut(cylinder(radius+p['shaft_fit_clearance_mm'],left-1,width+2))
        parts[name+'Sprocket'] = (shape.removeSplitter(),name.lower())
    jx,jw = p['aux_front_journal_x_mm'],p['aux_front_journal_width_mm']
    nose = cylinder(p['aux_nose_radius_mm'],left,jx-left)
    nose = nose.fuse(cylinder(n['journal_diameters_mm'][0]/2,jx,jw)).removeSplitter()
    parts['AuxiliaryFrontShaft'] = (nose,'aux')
    parts['AuxiliaryFrontBush'] = (ring(n['block_seat_diameters_mm'][0]/2,n['bush_inner_diameters_mm'][0]/2,jx,jw),'aux_fixed')
    parts['TimingTensioner'] = (ring(p['tensioner_radius_mm'],p['tensioner_bore_radius_mm']+p['shaft_fit_clearance_mm'],left,width),'tensioner')
    pin = cylinder(p['tensioner_bore_radius_mm'],left,right-left)
    pin = pin.fuse(cylinder(p['tensioner_pedestal_radius_mm'],right,p['tensioner_support_end_x_mm']-right)).removeSplitter()
    parts['TimingTensionerSupport'] = (pin,'tensioner_fixed')
    parts['TimingBelt'] = (belt(params,frame),'fixed')
    for shape,_ in parts.values():
        assert not shape.isNull() and shape.isValid() and len(shape.Solids)==1
    return parts
