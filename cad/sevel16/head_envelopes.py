"""Continuous spatial bounds for testing newly added fixed head components."""
import math
import FreeCAD as App
import Part
from valvetrain_layout import valves
from carrier_interface_envelopes import lower_bound
from timing_sweeps import bounds
from timing_layout import wheels
from timing_parts import cylinder
from config import layout

V = App.Vector


def prepare(doc,params,frame):
    """Snapshot on the GUI thread before any asynchronous intersection work."""
    rows = {r['id']:r for r in valves(params,frame)}
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    timing = params['valve_timing_nominal']['value']
    result = {}
    pulley = params['timing_visual_estimated']['value']
    wheel = next(w for w in wheels(params,frame) if w['name']=='Cam')
    left,width = pulley['pulley_center_x_mm']-pulley['pulley_width_mm']/2,pulley['pulley_width_mm']
    front = layout(params,frame)['supports'][0]-p['cam_journal_width_mm']/2
    radius = n['cam_journal_diameters_diagram_order_mm'][p['cam_diagram_indices_in_positive_x'][0]]/2
    cam_sprocket = cylinder(wheel['tip_radius'],left,width).fuse(cylinder(radius,left+width,front-left-width))
    cam_sprocket.Placement.Base = V(0,*wheel['center'])
    assert abs(doc.CamSprocket.Shape.cut(cam_sprocket).Volume)<1e-5
    for obj in doc.Objects:
        if not hasattr(obj,'Shape'):
            continue
        shape = obj.Shape.copy()
        kind = obj.MotionType
        if kind=='fixed':
            result[obj.Name] = {'shape':shape,'method':'fixed B-rep'}
        elif hasattr(obj,'ValveKind'):
            lift = timing['cam_height_mm']-timing[obj.ValveKind+'_lash_mm']
            local = shape.copy(); local.Placement=App.Placement()
            b = bounds(local)
            if obj.Name.endswith('_Valve'):
                row = rows[obj.Name.removesuffix('_Valve')]
                z = p['valve_face_closed_z_mm']
                r = n[row['kind']+'_head_mm']/2
                stem_z = z+p['valve_margin_mm']+p['valve_face_height_mm']+p['valve_neck_height_mm']
                # After filling the keeper groove the radial profile decreases
                # monotonically with Z. Downward translation adds only the
                # full-head-radius extension below its maximum-radius band.
                env = local.fuse(Part.makeCylinder(n['stem_mm']/2,b.ZMax-stem_z,V(0,0,stem_z)))
                env = env.fuse(Part.makeCylinder(r,lift+p['valve_margin_mm'],V(0,0,z-lift)))
            else:
                radius = max(abs(b.XMin),abs(b.XMax),abs(b.YMin),abs(b.YMax))
                low,high = b.ZMin-lift,b.ZMax
                if kind=='spring':
                    radius = p[obj.SpringKind+'_spring_mean_radius_mm']+p[obj.SpringKind+'_spring_wire_radius_mm']
                    low,high = p[obj.SpringKind+'_spring_seat_z_mm'],p['retainer_bottom_z_mm']
                # Avoid coincident cylindrical/BSpline faces in helical-wire
                # booleans. This expands the test envelope, never the part.
                pad = 1e-4
                if kind=='spring':
                    inner = p[obj.SpringKind+'_spring_mean_radius_mm']-p[obj.SpringKind+'_spring_wire_radius_mm']-pad
                    env = Part.makeCylinder(radius+pad,high-low,V(0,0,low)).cut(
                        Part.makeCylinder(inner,high-low+2,V(0,0,low-1)))
                else:
                    env = Part.makeCylinder(radius+pad,high-low+2*pad,V(0,0,low-pad))
            assert env.isValid() and abs(local.cut(env).Volume)<1e-5,obj.Name
            env.translate(obj.RestBase)
            result[obj.Name] = {'shape':env,'method':'continuous valve/spring envelope'}
        elif obj.Name=='CamSprocket':
            result[obj.Name] = {'shape':cam_sprocket,'method':'axisymmetric pulley and shaft envelope'}
        elif kind=='cam':
            b = bounds(shape); pivot = obj.Placement.Base
            radial = math.hypot(max(abs(b.YMin-pivot.y),abs(b.YMax-pivot.y)),
                                max(abs(b.ZMin-pivot.z),abs(b.ZMax-pivot.z)))
            result[obj.Name] = {'minimum_z':pivot.z-radial,'method':'full rotation lower Z bound'}
        else:
            result[obj.Name] = {'maximum_z':lower_bound(obj,params,frame),
                                'method':'full cycle upper Z bound'}
    assert len(result)==len([o for o in doc.Objects if hasattr(o,'Shape')])
    return result
