"""All-pairs B-rep bottom-end scan with rigid-pair cache and explicit press fit."""
import itertools
import hashlib
import json
import math
import FreeCAD as App
from config import OUTPUT
from kinematics import pose
from check_crank import overlap


def snapshot(doc):
    parts = []
    for o in doc.Objects:
        if not hasattr(o,'Shape'):
            continue
        shape = o.Shape.copy()
        kind, cylinder = getattr(o,'MotionType','fixed'), getattr(o,'CylinderId',0)
        if kind != 'fixed':
            shape.Placement = App.Placement()
        parts.append({'name':o.Name,'kind':kind,'cylinder':cylinder,'shape':shape})
    return parts


def placed(part, state):
    shape = part['shape'].copy()
    kind = part['kind']
    if kind == 'fixed':
        return shape
    if kind == 'crank':
        xyz, angle = state['crank_pivot_mm'], state['crank_rx_deg']
    else:
        c = state['cylinders'][part['cylinder']-1]
        xyz = c['crankpin_mm'] if kind=='rod' else c['piston_pin_mm']
        angle = c['rod_rx_deg'] if kind=='rod' else 0
    shape.Placement = App.Placement(App.Vector(*xyz),App.Rotation(App.Vector(1,0,0),angle))
    return shape


def scan(parts, params, frame, angles, report_name, progress=None, source_sha256=None):
    path = OUTPUT/f'reports/{report_name}.json'
    if path.exists():
        raise FileExistsError(path)
    progress_path = path.with_suffix('.progress.json')
    pairs = list(itertools.combinations(range(len(parts)),2))
    collisions, exceptions, counts, cached = [], [], {}, set()
    periodic, reused = {}, {}
    if any(p['kind'] not in {'fixed','crank','rod','piston'} for p in parts):
        raise ValueError('360-degree cache applies only to the bottom end')
    tolerance = 1e-5
    n = params['piston_rod_nominal']['value']
    sw = params['piston_rod_visual_estimated']['value']['rod_small_width_mm']
    press_limit = math.pi/4*(n['small_bushing_outer_mm']**2-n['small_bushing_seat_mm']**2)*sw
    angles = list(angles)
    for step,theta in enumerate(angles):
        state = pose(theta,params,frame)
        shapes = [placed(p,state) for p in parts]
        matrices = [list(s.Placement.toMatrix().A) for s in shapes]
        key = theta % 360
        if key in periodic:
            previous, old_matrices = periodic[key]
            assert max(abs(a-b) for old,new in zip(old_matrices,matrices)
                       for a,b in zip(old,new)) < 1e-10
            reused[str(theta)] = previous
            continue
        periodic[key] = (theta,matrices)
        for i,j in pairs:
            a,b = parts[i],parts[j]
            pair_id = a['name']+' / '+b['name']
            group_a, group_b = (a['kind'],a['cylinder']),(b['kind'],b['cylinder'])
            if group_a==group_b and pair_id in cached:
                continue
            if group_a==group_b:
                cached.add(pair_id)
            count = counts.setdefault(pair_id,{'bbox_filtered':0,'brep_tested':0})
            if not overlap(shapes[i].BoundBox,shapes[j].BoundBox):
                count['bbox_filtered'] += 1
                continue
            common = shapes[i].common(shapes[j])
            count['brep_tested'] += 1
            volume = 0 if common.isNull() else common.Volume
            if volume<=tolerance:
                continue
            row = {'theta_deg':theta,'pair':[a['name'],b['name']],'volume_mm3':volume}
            labels = {a['name'].split('_')[-1],b['name'].split('_')[-1]}
            if labels=={'Rod','SmallBushing'} and a['cylinder']==b['cylinder'] and volume<=press_limit+tolerance:
                row['exception'] = 'Manual nominal bushing press fit; bounded by annular overlap'
                row['limit_mm3'] = press_limit
                exceptions.append(row)
            else:
                collisions.append(row)
        if progress is not None:
            progress.update({'theta_deg':theta,'completed':step+1,'total':len(angles),
                             'collisions':len(collisions)})
            progress_path.write_text(json.dumps(progress)+'\n')
    report = {'status':'FAIL' if collisions else 'PASS','angles_deg':angles,
              'source_sha256':source_sha256,
              'parameters_sha256':hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest(),
              'parts':len(parts),'pairs':len(pairs),'pair_coverage':counts,
              'rigid_pair_cache':'Same motion kind and cylinder checked once; common rigid transform preserves overlap',
              'periodic_angle_reuse':reused,
              'periodic_cache_proof':'All part placement matrices equal within 1e-10; unchanged local B-reps',
              'collisions':collisions,'expected_contacts':exceptions,'volume_tolerance_mm3':tolerance,
              'scope':'All supplied bottom-end parts including block, caps, rings, bolts and bearings; head/valves excluded',
              'part_names':[p['name'] for p in parts]}
    path.write_text(json.dumps(report,indent=2)+'\n')
    progress_path.write_text(json.dumps({'state':'done','status':report['status'],
                                        'completed':len(angles),'total':len(angles)})+'\n')
    return report
