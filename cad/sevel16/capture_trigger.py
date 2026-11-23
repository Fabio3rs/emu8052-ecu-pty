"""Capture pulley/ring separation and the actual sensor facing the missing region."""
import FreeCAD as App
import FreeCADGui as Gui
from assembly import apply_pose
from config import load
from capture_checkpoint import save
import capture_timing


def run(doc):
    params,frame = load()
    assert doc.Phase.ThetaDeg==0
    App.setActiveDocument(doc.Name)
    Gui.setActiveDocument(doc.Name)
    visible = {o.Name:o.ViewObject.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    paths = capture_timing.run(doc)
    group = {'AccessoryPulley','TriggerWheel','RotationSensor','RotationSensorBracket',
             'CrankPulleyWasher','CrankPulleyNut'}
    try:
        for name in visible:
            doc.getObject(name).ViewObject.Visibility=name in group
        for view in ('Left','Isometric'):
            paths.append(save(doc,view,doc.Name+'-pulley-sensor',0,
                              'Independent 60-2 ring; uncalibrated phase and accessory dimensions'))
        p = params['trigger_pattern_estimated']['value']
        start = next(i for i in p['missing_slots'] if (i-1)%p['nominal_slots'] not in p['missing_slots'])
        midpoint = (start+(len(p['missing_slots'])-1)/2)*360/p['nominal_slots']
        theta = (p['sensor_angle_deg']-p['wheel_phase_deg']-midpoint)%360
        apply_pose(doc,theta,params,frame)
        for name in visible:
            doc.getObject(name).ViewObject.Visibility=name in ('TriggerWheel','RotationSensor')
        paths.append(save(doc,'Right',doc.Name+'-missing-gap',theta,
                          'Sensor centered on missing region; wheel alone for visual clarity'))
    finally:
        apply_pose(doc,0,params,frame)
        for name,state in visible.items():
            doc.getObject(name).ViewObject.Visibility=state
    print('\n'.join(paths[-3:]))
    return paths
