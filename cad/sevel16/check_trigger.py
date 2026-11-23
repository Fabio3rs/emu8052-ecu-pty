"""Validate the nose extension, accessory group, actual tooth grid and sensor gap."""
import hashlib
import itertools
import json
from pathlib import Path
import FreeCAD as App
import Part
from config import OUTPUT, load
from build_trigger_checkpoint import compatible_parameters
from timing_sweeps import bounds, overlaps, old_envelope, build as timing_envelopes
from trigger_envelopes import build as trigger_envelopes
from trigger_checks import grid, poses


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(doc, baseline):
    params,frame = load()
    previous = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    compatible_parameters(params,previous)
    evidence = OUTPUT/f'reports/{baseline.Name}_timing_validation.json'
    proof = json.loads(evidence.read_text())
    assert proof['status']=='PASS_EXTERNAL_TIMING_INCREMENT'
    assert proof['source_sha256']==sha(baseline.FileName)
    assert doc.Phase.ThetaDeg==baseline.Phase.ThetaDeg==0
    unchanged = {}
    for old in baseline.Objects:
        if not hasattr(old,'Shape') or old.Name=='Crankshaft':
            continue
        obj = doc.getObject(old.Name)
        assert obj and obj.PartId==old.PartId and obj.MotionType==old.MotionType
        assert obj.CylinderId==old.CylinderId
        for prop in ('ValveKind','SpringKind','RestBase'):
            assert getattr(obj,prop,None)==getattr(old,prop,None)
        delta = abs(obj.Shape.cut(old.Shape).Volume)+abs(old.Shape.cut(obj.Shape).Volume)
        assert delta<1e-5,(old.Name,delta)
        unchanged[old.Name] = delta
    assert len(unchanged)==181
    new,old = doc.Crankshaft.Shape,baseline.Crankshaft.Shape
    added,removed = new.cut(old),old.cut(new)
    p = params['moving_geometry_estimated']['value']
    extra = p['nose_length_mm']-previous['moving_geometry_estimated']['value']['nose_length_mm']
    pivot = doc.Crankshaft.Placement.Base
    expected = Part.makeCylinder(p['nose_radius_mm'],extra,
                    App.Vector(bounds(new).XMin,pivot.y,pivot.z),App.Vector(1,0,0))
    assert abs(removed.Volume)<1e-5
    assert abs(added.cut(expected).Volume)+abs(expected.cut(added).Volume)<1e-5
    separation = min(bounds(doc.getObject(n).Shape).XMin for n in unchanged)-bounds(added).XMax
    assert separation>0
    envs = trigger_envelopes(doc,params)
    old_timing = timing_envelopes(baseline,previous,frame)
    pairs = {}
    def check(name,a,b):
        volume = abs(a.common(b).Volume) if overlaps(a,b) else 0
        assert volume<1e-5,(name,volume)
        pairs[name] = volume
    for (an,a),(bn,b) in itertools.combinations(envs.items(),2):
        check(an+'/'+bn,a,b)
    for name,env in envs.items():
        obj = doc.getObject(name)
        if obj.MotionType=='crank':
            check(name+'/Crankshaft',obj.Shape,doc.Crankshaft.Shape)
        else:
            check(name+'/Crankshaft',env,old_envelope(doc.Crankshaft,env,params,frame))
        a = bounds(env)
        for old in baseline.Objects:
            if not hasattr(old,'Shape') or old.Name=='Crankshaft':
                continue
            b = bounds(old.Shape)
            if min(a.XMax,b.XMax)-max(a.XMin,b.XMin)<=1e-7:
                continue
            envelope = old_timing.get(old.Name)
            if envelope is None:
                envelope = old_envelope(old,env,previous,frame)
            if not envelope.isNull():
                check(name+'/'+old.Name,env,envelope)
    gap = envs['TriggerWheel'].distToShape(doc.RotationSensor.Shape)[0]
    assert abs(gap-params['rotation_sensor_gap']['value'])<1e-7
    contacts = [('AccessoryPulley','CrankSprocket'),('TriggerWheel','AccessoryPulley'),
                ('CrankPulleyWasher','AccessoryPulley'),('CrankPulleyNut','CrankPulleyWasher'),
                ('RotationSensorBracket','Block'),('CrankPulleyNut','Crankshaft')]
    assert all(doc.getObject(a).Shape.distToShape(doc.getObject(b).Shape)[0]<1e-7 for a,b in contacts)
    measured_grid = grid(doc,params)
    measured_poses = poses(doc,params,frame)
    report = {'status':'PASS_TRIGGER_INCREMENT','source_sha256':sha(doc.FileName),
              'baseline_proof_sha256':sha(evidence),'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'unchanged_parts_symmetric_difference_mm3':unchanged,
              'crank_added_volume_mm3':added.Volume,'crank_removed_volume_mm3':removed.Volume,
              'nose_extension_axial_clearance_to_old_parts_mm':separation,
              'continuous_envelope_pairs_mm3':pairs,'expected_contacts':contacts,
              'full_rotation_sensor_gap_mm':gap,'actual_grid':measured_grid,'pose_checks':measured_poses,
              'scope':'Accessory/trigger increment and isolated nose extension; previous assembly proof retained',
              'limits':['60-2 and mounting phase not independently confirmed on target',
                        'No ECU electrical signal or manufacturing thread validation',
                        'Auxiliary rear shaft and casting inclination corrections remain pending']}
    (OUTPUT/f'reports/{doc.Name}_trigger_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,dict)}))
    return report
