"""Absolute FreeCAD adapter. All moving parts are root children (no double rotation)."""
import FreeCAD as App
from kinematics import pose


def apply_pose(doc, theta_deg, params, frame, update_springs=True):
    state = pose(theta_deg,params,frame)
    for obj in doc.Objects:
        kind = getattr(obj,'MotionType','fixed')
        if kind == 'fixed':
            continue
        if kind == 'crank':
            translation, angle = state['crank_pivot_mm'], state['crank_rx_deg']
        elif kind == 'cam':
            translation = [0,0,params['valvetrain_layout_estimated']['value']['cam_axis_z_mm']]
            angle = state['cam_rx_deg']
        elif kind in ('aux','tensioner'):
            angle = state['timing_rx_deg'][kind]
            if kind=='aux':
                p = params['casting_visual_estimated']['value']
                translation = [0,p['aux_y'],p['aux_z']]
            else:
                p = params['timing_visual_estimated']['value']
                translation = [0,p['tensioner_y_mm'],p['tensioner_z_mm']]
        elif kind in ('valve','spring'):
            lift = state['cylinders'][obj.CylinderId-1]['valve_lifts_mm'][obj.ValveKind]
            if kind=='spring':
                if update_springs:
                    import valve_springs
                    obj.Shape = valve_springs.build(params,obj.SpringKind,lift)
                obj.Placement = App.Placement(obj.RestBase,App.Rotation())
                continue
            translation = list(obj.RestBase-App.Vector(0,0,lift))
            angle = 0
        else:
            cylinder = state['cylinders'][obj.CylinderId-1]
            translation = cylinder['crankpin_mm'] if kind == 'rod' else cylinder['piston_pin_mm']
            angle = cylinder['rod_rx_deg'] if kind == 'rod' else 0
        obj.Placement = App.Placement(App.Vector(*translation),App.Rotation(App.Vector(1,0,0),angle))
    doc.Phase.ThetaDeg = theta_deg
    doc.recompute()
    return state


def add_part(doc, name, shape, kind='fixed', cylinder=0, color=(0.65,0.67,0.7)):
    obj = doc.addObject('Part::Feature',name)
    obj.Shape = shape
    for prop in ['PartId','MotionType']:
        obj.addProperty('App::PropertyString',prop,'Assembly')
    obj.PartId = 'sevel.'+name.lower()
    obj.MotionType = kind
    obj.addProperty('App::PropertyInteger','CylinderId','Assembly')
    obj.CylinderId = cylinder
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.LineColor = (0.12,0.13,0.15)
    return obj
