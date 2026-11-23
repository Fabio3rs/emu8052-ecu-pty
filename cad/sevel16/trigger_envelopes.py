"""Rotation-invariant envelopes for the new front pulley group."""
import FreeCAD as App
from timing_parts import ring
from trigger_layout import axial_layout


def build(doc, params):
    p = params['accessory_visual_estimated']['value']
    c = params['moving_geometry_estimated']['value']
    ax = axial_layout(params)
    result = {n:doc.getObject(n).Shape.copy() for n in
              ('AccessoryPulley','CrankPulleyWasher','RotationSensor','RotationSensorBracket')}
    wheel = ring(p['wheel_tip_radius_mm'],p['hub_radius_mm']+p['fit_clearance_mm'],
                 ax['wheel_front'],p['wheel_width_mm'])
    wheel.Placement = doc.TriggerWheel.Placement
    result['TriggerWheel'] = wheel
    nut = ring(p['nut_radius_mm'],c['nose_radius_mm'],ax['nut_front'],p['nut_width_mm'])
    nut.Placement = doc.CrankPulleyNut.Placement
    result['CrankPulleyNut'] = nut
    for name,env in result.items():
        obj = doc.getObject(name)
        assert abs(obj.Shape.cut(env).Volume)<1e-5,(name,'outside envelope')
        if obj.MotionType=='crank':
            rotated = env.copy()
            rotated.rotate(obj.Placement.Base,App.Vector(1,0,0),37)
            assert abs(env.cut(rotated).Volume)+abs(rotated.cut(env).Volume)<1e-5
    return result
