"""Conservative continuous-rotation envelopes for the external timing checkpoint."""
import math
import FreeCAD as App
import Part
from timing_layout import wheels
from timing_parts import cylinder, ring
from config import layout


def bounds(shape):
    return shape.optimalBoundingBox(False)


def overlaps(a, b):
    aa,bb = bounds(a),bounds(b)
    return all(min(getattr(aa,k+'Max'),getattr(bb,k+'Max'))-
               max(getattr(aa,k+'Min'),getattr(bb,k+'Min'))>1e-7 for k in 'XYZ')


def build(doc, params, frame):
    p = params['timing_visual_estimated']['value']
    c = params['moving_geometry_estimated']['value']
    v = params['valvetrain_layout_estimated']['value']
    rows = {w['name']:w for w in wheels(params,frame)}
    left,width = p['pulley_center_x_mm']-p['pulley_width_mm']/2,p['pulley_width_mm']
    result = {}
    for name in ('Cam','Crank','Aux'):
        if name=='Cam':
            env = cylinder(rows[name]['tip_radius'],left,width)
            front = layout(params,frame)['supports'][0]-v['cam_journal_width_mm']/2
            j = v['cam_diagram_indices_in_positive_x'][0]
            radius = params['valvetrain_nominal']['value']['cam_journal_diameters_diagram_order_mm'][j]/2
            env = env.fuse(cylinder(radius,left+width,front-left-width))
        else:
            radius = c['nose_radius_mm'] if name=='Crank' else p['aux_nose_radius_mm']
            env = ring(rows[name]['tip_radius'],radius+p['shaft_fit_clearance_mm'],left,width)
        env.Placement.Base = App.Vector(0,*rows[name]['center'])
        result[name+'Sprocket'] = env
    for name in ('AuxiliaryFrontShaft','AuxiliaryFrontBush','TimingTensioner',
                 'TimingTensionerSupport','TimingBelt'):
        result[name] = doc.getObject(name).Shape.copy()
    for name,env in result.items():
        obj = doc.getObject(name)
        assert abs(obj.Shape.cut(env).Volume)<1e-5,(name,'not contained')
        if obj.MotionType!='fixed':
            # These envelopes contain cylinders, cones and plane end faces only.
            assert all(isinstance(f.Surface,(Part.Cylinder,Part.Plane,Part.Cone)) for f in env.Faces)
            rotated = env.copy()
            rotated.rotate(obj.Placement.Base,App.Vector(1,0,0),37)
            assert abs(rotated.cut(env).Volume)+abs(env.cut(rotated).Volume)<1e-5
    return result


def old_envelope(obj, new_shape, params, frame):
    if obj.MotionType=='fixed':
        return obj.Shape
    if obj.MotionType=='piston':
        # The auxiliary journal reaches the piston's X interval by ~0.2 mm.
        # Cover its entire Z stroke even though the transverse bounds separate it.
        q = bounds(obj.Shape)
        g = layout(params,frame)
        length = params['moving_geometry_estimated']['value']['rod_length_mm']
        low = -g['height']-g['radius']+length-obj.Placement.Base.z
        return Part.makeBox(q.XLength,q.YLength,q.ZLength+2*g['radius'],
                            App.Vector(q.XMin,q.YMin,q.ZMin+low))
    # Other moving components have disjoint X intervals in this checkpoint.
    assert obj.MotionType in ('crank','cam'), ('Unhandled old moving component',obj.Name)
    a,b = bounds(obj.Shape),bounds(new_shape)
    lo,hi = max(a.XMin,b.XMin),min(a.XMax,b.XMax)
    section = obj.Shape.common(Part.makeBox(hi-lo,1000,1000,App.Vector(lo,-500,-500)))
    if section.isNull() or section.Volume<1e-8:
        return section
    q = bounds(section)
    pivot = obj.Placement.Base
    radial = math.hypot(max(abs(q.YMin-pivot.y),abs(q.YMax-pivot.y)),
                        max(abs(q.ZMin-pivot.z),abs(q.ZMax-pivot.z)))
    return Part.makeCylinder(radial,hi-lo,App.Vector(lo,pivot.y,pivot.z),App.Vector(1,0,0))
