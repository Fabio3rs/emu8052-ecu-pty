"""Independent accessory pulley, missing-tooth ring, sensor and mounting hardware."""
import math
import FreeCAD as App
import Part
from config import layout
from timing_parts import cylinder, ring
from trigger_layout import slots, radial, axial_layout
import sensor_bracket

V = App.Vector
AXIS = V(1,0,0)


def wheel(params):
    p = params['accessory_visual_estimated']['value']
    grid = params['trigger_pattern_estimated']['value']
    ids = slots(params)
    x = axial_layout(params)['wheel_front']
    pitch,half = 360/grid['nominal_slots'],grid['tooth_width_angle_deg']/2
    root,tip = p['wheel_root_radius_mm'],p['wheel_tip_radius_mm']
    assert p['hub_radius_mm']+p['fit_clearance_mm']<root<tip
    def point(radius,angle):
        return V(x,*radial(angle,radius))
    def arc(radius,a,b):
        return Part.Arc(point(radius,a),point(radius,(a+b)/2),point(radius,b)).toShape()
    edges = []
    for k,i in enumerate(ids):
        a,b = i*pitch-half,i*pitch+half
        following = (ids[(k+1)%len(ids)]+(grid['nominal_slots'] if k==len(ids)-1 else 0))*pitch-half
        edges.extend([Part.makeLine(point(root,a),point(tip,a)),arc(tip,a,b),
                      Part.makeLine(point(tip,b),point(root,b)),arc(root,b,following)])
    outer = Part.Wire(edges)
    assert outer.isClosed()
    shape = Part.Face(outer).extrude(V(p['wheel_width_mm'],0,0))
    shape = shape.cut(cylinder(p['hub_radius_mm']+p['fit_clearance_mm'],x-1,p['wheel_width_mm']+2))
    shape.rotate(V(),AXIS,grid['wheel_phase_deg'])
    return shape


def build(params, frame):
    p = params['accessory_visual_estimated']['value']
    c = params['moving_geometry_estimated']['value']
    ax = axial_layout(params)
    x,w,r = ax['pulley_front'],p['pulley_width_mm'],p['pulley_radius_mm']
    assert 0<p['groove_width_mm']<w and 0<p['groove_depth_mm']<r-p['hub_radius_mm']
    body = cylinder(r,x,w).fuse(cylinder(p['hub_radius_mm'],x,ax['back']-x))
    center,half = x+w/2,p['groove_width_mm']/2
    points = [V(center-half,r,0),V(center,r-p['groove_depth_mm'],0),
              V(center+half,r,0),V(center+half,r+2,0),V(center-half,r+2,0)]
    groove = Part.Face(Part.makePolygon(points+[points[0]])).revolve(V(),AXIS,360)
    body = body.cut(groove).cut(cylinder(c['nose_radius_mm']+p['fit_clearance_mm'],x-1,ax['back']-x+2)).removeSplitter()
    washer = ring(p['washer_radius_mm'],c['nose_radius_mm']+p['fit_clearance_mm'],ax['washer_front'],p['washer_width_mm'])
    points = [V(ax['nut_front'],*radial(i*60,p['nut_radius_mm'])) for i in range(6)]
    nut = Part.Face(Part.makePolygon(points+[points[0]])).extrude(V(p['nut_width_mm'],0,0))
    nut = nut.cut(cylinder(c['nose_radius_mm'],ax['nut_front']-1,p['nut_width_mm']+2))
    angle = params['trigger_pattern_estimated']['value']['sensor_angle_deg']
    sy,sz = radial(angle,p['wheel_tip_radius_mm']+params['rotation_sensor_gap']['value'])
    uy,uz = radial(angle,1)
    sensor = Part.makeCylinder(p['sensor_radius_mm'],p['sensor_length_mm'],
                V(ax['sensor_x'],sy,sz-layout(params,frame)['height']),V(0,uy,uz))
    parts = {'AccessoryPulley':(body,'crank'),'TriggerWheel':(wheel(params),'crank'),
             'CrankPulleyWasher':(washer,'crank'),'CrankPulleyNut':(nut,'crank'),
             'RotationSensor':(sensor,'fixed'),'RotationSensorBracket':(sensor_bracket.build(params,frame),'fixed')}
    for shape,_ in parts.values():
        assert not shape.isNull() and shape.isValid() and len(shape.Solids)==1
    return parts
