"""Continuous envelopes resolved by component and height, for the inclined cage."""
import math
import FreeCAD as App
import Part
from config import layout
from timing_sweeps import bounds
from carrier_swept_envelopes import build as legacy_envelopes
from timing_layout import wheels
from timing_parts import cylinder


def build(doc, params, frame, minimum_z):
    result = {'Camshaft':legacy_envelopes(doc,params,frame)['Camshaft']}
    p = params['valvetrain_layout_estimated']['value']
    t = params['timing_visual_estimated']['value']
    wheel = next(w for w in wheels(params,frame) if w['name']=='Cam')
    left,width = t['pulley_center_x_mm']-t['pulley_width_mm']/2,t['pulley_width_mm']
    front = layout(params,frame)['supports'][0]-p['cam_journal_width_mm']/2
    j = p['cam_diagram_indices_in_positive_x'][0]
    radius = params['valvetrain_nominal']['value']['cam_journal_diameters_diagram_order_mm'][j]/2
    sprocket = cylinder(wheel['tip_radius'],left,width)
    sprocket = sprocket.fuse(cylinder(radius,left+width,front-left-width))
    sprocket.Placement.Base = App.Vector(0,*wheel['center'])
    assert abs(doc.CamSprocket.Shape.cut(sprocket).Volume)<1e-5
    result['CamSprocket'] = sprocket
    timing = params['valve_timing_nominal']['value']
    clip = Part.makeBox(2000,2000,2000,App.Vector(-1000,-1000,minimum_z-1e-6))
    for obj in doc.Objects:
        if not hasattr(obj,'ValveKind'):
            continue
        if obj.MotionType=='fixed':
            result[obj.Name] = obj.Shape.copy()
            continue
        if obj.MotionType=='spring':
            kind = obj.SpringKind
            radius = p[kind+'_spring_mean_radius_mm']+p[kind+'_spring_wire_radius_mm']
            low,high = p[kind+'_spring_seat_z_mm'],p['retainer_bottom_z_mm']
        else:
            assert obj.MotionType=='valve'
            # Remove current lift to recover closed geometry. Material below
            # the casting can only move further downward during the cycle.
            closed = obj.Shape.copy()
            closed.Placement = App.Placement()
            relevant = closed.common(clip)
            if relevant.isNull() or relevant.Volume<1e-9:
                continue
            q = bounds(relevant)
            radius = max(abs(q.XMin),abs(q.XMax),abs(q.YMin),abs(q.YMax))
            low = q.ZMin-(timing['cam_height_mm']-timing[obj.ValveKind+'_lash_mm'])
            high = q.ZMax
            local = Part.makeCylinder(radius+1e-6,high-low+2e-6,App.Vector(0,0,low-1e-6))
            assert relevant.cut(local).Volume<1e-5,obj.Name
        origin = obj.RestBase
        result[obj.Name] = Part.makeCylinder(radius+1e-6,high-low+2e-6,
                                            App.Vector(origin.x,origin.y,low-1e-6))
    return result


def lower_bound(obj, params, frame):
    """Upper Z for a full cycle; stationary geometry is already in world space."""
    if obj.MotionType=='fixed':
        return bounds(obj.Shape).ZMax
    g = layout(params,frame)
    shape = obj.Shape.copy(); shape.Placement = App.Placement()
    q = bounds(shape)
    radius = math.hypot(max(abs(q.YMin),abs(q.YMax)),max(abs(q.ZMin),abs(q.ZMax)))
    kind = obj.MotionType
    if kind=='crank':
        return -g['height']+radius
    if kind=='rod':
        return -g['height']+g['radius']+radius
    if kind=='piston':
        return -g['height']+g['radius']+params['moving_geometry_estimated']['value']['rod_length_mm']+q.ZMax
    if kind=='aux':
        return params['casting_visual_estimated']['value']['aux_z']+radius
    if kind=='tensioner':
        return params['timing_visual_estimated']['value']['tensioner_z_mm']+radius
    raise ValueError(('Unhandled motion',obj.Name,kind))
