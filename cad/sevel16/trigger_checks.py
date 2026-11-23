"""Measure the actual B-rep tooth grid and exercise rigid poses and sensor passages."""
import math
import FreeCAD as App
import Part
from assembly import apply_pose
from trigger_layout import slots, crossing_angles


def grid(doc, params):
    p = params['accessory_visual_estimated']['value']
    pattern = params['trigger_pattern_estimated']['value']
    pivot = doc.Crankshaft.Placement.Base
    top,root = [],[]
    for face in doc.TriggerWheel.Shape.Faces:
        surface = face.Surface
        if not isinstance(surface,Part.Cylinder):
            continue
        if abs(surface.Radius-p['wheel_tip_radius_mm'])<1e-7:
            point = face.CenterOfMass-pivot
            angle = math.degrees(math.atan2(-point.y,point.z))%360
            top.append(round(angle,8)%360)
        elif abs(surface.Radius-p['wheel_root_radius_mm'])<1e-7:
            root.append(math.degrees(face.Area/(surface.Radius*p['wheel_width_mm'])))
    expected = sorted((i*360/pattern['nominal_slots']+pattern['wheel_phase_deg'])%360 for i in slots(params))
    assert len(top)==len(expected)==len(root)
    for actual,target in zip(sorted(top),expected):
        assert abs((actual-target+180)%360-180)<1e-6,(actual,target)
    pitch = 360/pattern['nominal_slots']
    largest = (len(pattern['missing_slots'])+1)*pitch-pattern['tooth_width_angle_deg']
    assert abs(max(root)-largest)<1e-6
    return {'actual_tooth_count':len(top),'actual_centers_deg':sorted(top),
            'largest_root_arc_deg':max(root),'nominal_pitch_deg':pitch}


def poses(doc, params, frame):
    moving = [doc.getObject(n) for n in ('AccessoryPulley','TriggerWheel','CrankPulleyWasher','CrankPulleyNut')]
    fixed = {o.Name:list(o.Placement.toMatrix().A) for o in (doc.RotationSensor,doc.RotationSensorBracket)}
    required_gap = params['rotation_sensor_gap']['value']
    crossing_gaps = []
    try:
        for theta in range(0,721,5):
            apply_pose(doc,theta,params,frame,update_springs=False)
            for obj in moving:
                assert (obj.Placement.Base-doc.Crankshaft.Placement.Base).Length<1e-9
                assert obj.Placement.Rotation.isSame(doc.Crankshaft.Placement.Rotation,1e-9)
            for name,matrix in fixed.items():
                assert list(doc.getObject(name).Placement.toMatrix().A)==matrix
        for theta in crossing_angles(params):
            apply_pose(doc,theta,params,frame,update_springs=False)
            gap = doc.RotationSensor.Shape.distToShape(doc.TriggerWheel.Shape)[0]
            assert abs(gap-required_gap)<1e-6,(theta,gap)
            crossing_gaps.append(gap)
        p = params['trigger_pattern_estimated']['value']
        start = next(i for i in p['missing_slots'] if (i-1)%p['nominal_slots'] not in p['missing_slots'])
        midpoint = (start+(len(p['missing_slots'])-1)/2)*360/p['nominal_slots']
        theta = (p['sensor_angle_deg']-p['wheel_phase_deg']-midpoint)%360
        apply_pose(doc,theta,params,frame,update_springs=False)
        gap = doc.RotationSensor.Shape.distToShape(doc.TriggerWheel.Shape)[0]
        assert gap>required_gap+1e-3
    finally:
        apply_pose(doc,0,params,frame,update_springs=False)
    return {'rigid_pose_samples':145,'sensor_tooth_center_samples':len(crossing_gaps),
            'center_crossing_gaps_mm':crossing_gaps,'missing_gap_midpoint_theta_deg':theta,
            'sensor_gap_at_missing_region_mm':gap}
