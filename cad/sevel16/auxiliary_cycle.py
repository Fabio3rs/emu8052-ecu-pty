"""Detached-shape scan: continuous auxiliary envelope against the lower moving parts."""
import itertools
import json
from config import OUTPUT
from kinematics import pose
from check_moving import snapshot, placed
from check_auxiliary import volume
from timing_sweeps import bounds, overlaps, build as timing_envelopes


def inputs(doc, baseline, params, frame, targets):
    old_timing = timing_envelopes(baseline,params,frame)
    moving = [p for p in snapshot(baseline) if p['kind'] in ('crank','rod','piston')]
    fixed,excluded = {},{}
    zmax = max(bounds(s).ZMax for s in targets.values())
    for obj in baseline.Objects:
        if not hasattr(obj,'Shape') or obj.Name in ('Block','AuxiliaryFrontShaft'):
            continue
        motion = obj.MotionType
        if motion in ('crank','rod','piston'):
            continue
        if motion in ('cam','valve','spring'):
            # Rotation about X can change cam Y/Z bounds, while the valve stack
            # only moves downward by at most the declared maximum cam lift.
            if motion=='cam':
                q,pivot = bounds(obj.Shape),obj.Placement.Base
                radius = ((max(abs(q.YMin-pivot.y),abs(q.YMax-pivot.y)))**2+
                          (max(abs(q.ZMin-pivot.z),abs(q.ZMax-pivot.z)))**2)**.5
                low = pivot.z-radius
            else:
                low = bounds(obj.Shape).ZMin-params['valve_timing_nominal']['value']['cam_height_mm']
            assert low>zmax,(obj.Name,low,zmax)
            excluded[obj.Name] = low-zmax
        elif motion in ('aux','tensioner'):
            fixed[obj.Name] = old_timing[obj.Name].copy()
        else:
            assert motion=='fixed',obj.Name
            fixed[obj.Name] = obj.Shape.copy()
    return moving,fixed,excluded


def run(name, report, targets, moving, fixed, excluded, params, frame, angles):
    pairs,tests = {},0
    def check(label,a,b):
        nonlocal tests
        row = pairs.setdefault(label,{'bbox_filtered':0,'brep_tested':0})
        if not overlaps(a,b):
            row['bbox_filtered'] += 1
            return
        overlap = volume(a.common(b))
        row['brep_tested'] += 1
        tests += 1
        assert overlap<1e-5,(label,overlap)
    for (an,a),(bn,b) in itertools.combinations(targets.items(),2):
        check(an+'/'+bn,a,b)
    for tn,target in targets.items():
        for old,shape in fixed.items():
            check(tn+'/'+old,target,shape)
    progress = OUTPUT/f'reports/{name}_auxiliary_cycle.progress.json'
    for i,theta in enumerate(angles):
        state = pose(theta,params,frame)
        for part in moving:
            shape = placed(part,state)
            for tn,target in targets.items():
                check(tn+'/'+part['name'],target,shape)
        progress.write_text(json.dumps({'theta':theta,'completed':i+1,'total':len(angles),
                                        'brep_tests':tests})+'\n')
    report.update(status='PASS_AUXILIARY_INCREMENT',angles_deg=list(angles),
                  brep_tests=tests,pair_coverage=pairs,
                  continuous_upper_stack_z_separation_mm=excluded,
                  collision_scope='Auxiliary full-rotation envelope, bush and added casting against inherited parts; lower assembly sampled at listed phases')
    path = OUTPUT/f'reports/{name}_auxiliary_validation.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'phases':len(angles),'pairs':len(pairs),'brep_tests':tests}))
    return report
