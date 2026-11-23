"""Incremental B-rep and continuous-envelope validation of external timing."""
import hashlib
import itertools
import json
from pathlib import Path
import FreeCAD as App
from config import OUTPUT, load
from assembly import apply_pose
from timing_sweeps import build, bounds, overlaps, old_envelope


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(doc, baseline):
    params,frame = load()
    previous = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:v for k,v in params.items() if k not in ('timing_visual_estimated','auxiliary_nominal')}==previous
    evidence = OUTPUT/f'reports/{baseline.Name}_flywheel_validation.json'
    proof = json.loads(evidence.read_text())
    assert proof['status']=='PASS_FLYWHEEL_INCREMENT_CONTINUOUS_CLEARANCE'
    assert proof['source_sha256']==sha(baseline.FileName)
    assert doc.Phase.ThetaDeg==baseline.Phase.ThetaDeg==0
    unchanged = {}
    for old in baseline.Objects:
        if not hasattr(old,'Shape'):
            continue
        obj = doc.getObject(old.Name)
        assert obj and obj.PartId==old.PartId and obj.MotionType==old.MotionType
        assert obj.CylinderId==old.CylinderId
        for prop in ('ValveKind','SpringKind','RestBase'):
            assert getattr(obj,prop,None)==getattr(old,prop,None)
        delta = abs(obj.Shape.cut(old.Shape).Volume)+abs(old.Shape.cut(obj.Shape).Volume)
        assert delta<1e-5,(old.Name,delta)
        unchanged[old.Name] = delta
    assert len(unchanged)==174
    envelopes = build(doc,params,frame)
    pairs = {}
    def check(name,a,b):
        volume = abs(a.common(b).Volume) if overlaps(a,b) else 0
        assert volume<1e-5,(name,volume)
        pairs[name] = volume
    for (an,a),(bn,b) in itertools.combinations(envelopes.items(),2):
        check(an+'/'+bn,a,b)
    for name,env in envelopes.items():
        obj = doc.getObject(name)
        a = bounds(env)
        for old in baseline.Objects:
            if not hasattr(old,'Shape'):
                continue
            b = bounds(old.Shape)
            if min(a.XMax,b.XMax)-max(a.XMin,b.XMin)<=1e-7:
                continue
            if obj.MotionType==old.MotionType and obj.MotionType in ('crank','cam'):
                assert (obj.Placement.Base-old.Placement.Base).Length<1e-9
                check(name+'/'+old.Name,obj.Shape,old.Shape)
            else:
                old_sweep = old_envelope(old,env,params,frame)
                if not old_sweep.isNull():
                    check(name+'/'+old.Name,env,old_sweep)
    belt_gaps = {n:env.distToShape(doc.TimingBelt.Shape)[0] for n,env in envelopes.items()
                 if n in ('CamSprocket','CrankSprocket','AuxSprocket','TimingTensioner')}
    p = params['timing_visual_estimated']['value']
    assert all(abs(g-p['belt_visual_clearance_mm'])<1e-6 for g in belt_gaps.values()),belt_gaps
    contacts = [('CamSprocket','Camshaft'),('TimingTensionerSupport','Block'),('AuxiliaryFrontBush','Block')]
    assert all(doc.getObject(a).Shape.distToShape(doc.getObject(b).Shape)[0]<1e-7 for a,b in contacts)
    worst = 0
    try:
        for theta in range(0,721,5):
            apply_pose(doc,theta,params,frame,update_springs=False)
            expected = {'CamSprocket':theta/2+params['cam_profile_estimated']['value']['global_phase_deg'],
                        'CrankSprocket':theta,
                        'AuxSprocket':theta*p['crank_teeth']/p['aux_teeth']+p['aux_phase_deg'],
                        'TimingTensioner':-theta*p['crank_teeth']*p['pitch_mm']/(2*3.141592653589793*p['tensioner_radius_mm'])+p['tensioner_phase_deg']}
            for name,angle in expected.items():
                rotation = App.Rotation(App.Vector(1,0,0),angle%360)
                actual = doc.getObject(name).Placement.Rotation
                error = (actual.multVec(App.Vector(0,0,1))-rotation.multVec(App.Vector(0,0,1))).Length
                worst = max(worst,error)
                assert error<1e-10,(name,theta,error)
    finally:
        apply_pose(doc,0,params,frame,update_springs=False)
    report = {'status':'PASS_EXTERNAL_TIMING_INCREMENT','source_sha256':sha(doc.FileName),
              'baseline_proof_sha256':sha(evidence),'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'unchanged_parts_symmetric_difference_mm3':unchanged,
              'continuous_envelope_pairs_mm3':pairs,'belt_envelope_clearance_mm':belt_gaps,
              'expected_contacts':contacts,'pose_samples':145,'max_unit_vector_rotation_error':worst,
              'scope':'External timing only; prior assembly retained by B-rep comparison and evidence hash',
              'limits':['No tooth meshing or belt material motion',
                        'Rear auxiliary journal/internal drive and trigger wheel are not included',
                        'No new valve-spring cycle scan; inherited proof and X-interval exclusion used']}
    (OUTPUT/f'reports/{doc.Name}_timing_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,dict)}))
    return report
