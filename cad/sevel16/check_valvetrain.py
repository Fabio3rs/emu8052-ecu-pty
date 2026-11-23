"""B-rep checks for A3 against itself and the already checked bottom end."""
import json
import time
from itertools import combinations
from config import OUTPUT


def snapshot(doc):
    """Copy on the GUI thread; the checker only reads independent shapes."""
    return [{'name':o.Name, 'shape':o.Shape.copy(), 'motion':o.MotionType,
             'valve':getattr(o,'ValveKind',None), 'cylinder':o.CylinderId}
            for o in doc.Objects if hasattr(o,'Shape')]


def is_new(part):
    return part['valve'] is not None or part['name'].startswith(('Camshaft','CamCarrier','CamCap'))


def scan(parts, theta, report_name, cache=None):
    start = time.monotonic()
    report = {'status':'RUNNING', 'theta_deg':theta,
              'scope':'All pairs involving A3; bottom-end-only pairs excluded',
              'volume_threshold_mm3':1e-5, 'bbox_candidates':0,
              'brep_checks':0, 'cached_checks':0, 'collisions':[], 'elapsed_seconds':0}
    path = OUTPUT/'reports'/report_name
    pairs = [(a,b) for a,b in combinations(parts,2) if is_new(a) or is_new(b)]
    report['pair_count'] = len(pairs)
    def save():
        report['elapsed_seconds'] = time.monotonic()-start
        path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for a,b in pairs:
        aa,bb = a['shape'].BoundBox,b['shape'].BoundBox
        if not all(min(getattr(aa,k+'Max'),getattr(bb,k+'Max'))-
                   max(getattr(aa,k+'Min'),getattr(bb,k+'Min'))>1e-7 for k in 'XYZ'):
            continue
        report['bbox_candidates'] += 1
        # A rigid pair's intersection is invariant under their shared motion.
        # Springs also need installed height in the key because their B-rep deforms.
        relative = a['shape'].Placement.inverse().multiply(b['shape'].Placement)
        key = (a['name'],b['name'],tuple(round(v,9) for v in relative.toMatrix().A),
               round(aa.ZLength,9) if a['motion']=='spring' else None,
               round(bb.ZLength,9) if b['motion']=='spring' else None)
        if cache is not None and key in cache:
            volume = cache[key]
            report['cached_checks'] += 1
        else:
            volume = abs(a['shape'].common(b['shape']).Volume)
            report['brep_checks'] += 1
            if cache is not None:
                cache[key] = volume
        if volume>report['volume_threshold_mm3']:
            report['collisions'].append({'a':a['name'],'b':b['name'],'volume_mm3':volume})
        save()
    report['status'] = 'FAIL' if report['collisions'] else 'PASS_STATIC_POSE_ONLY'
    save()
    return report


def run_cycle(doc):
    """Headless document adapter: GUI documents must not be passed from async."""
    import hashlib
    from pathlib import Path
    from assembly import apply_pose
    from check_cam_contacts import angles
    from config import load
    params,frame = load()
    cache = {}
    result = {'status':'RUNNING','document':doc.Name,
              'source_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
              'scope':'A3 pairs and their contacts with A2; bottom-end-only pairs excluded',
              'cache':'Same named pair, relative placement rounded to 1e-9, spring height included',
              'completed_angles':[], 'brep_checks':0,'cached_checks':0,'collisions':[]}
    path = OUTPUT/f'reports/{doc.Name}_valvetrain_cycle.json'
    target = angles(params)
    result['target_angles'] = target
    original_theta = doc.Phase.ThetaDeg
    try:
        for theta in target:
            apply_pose(doc,theta,params,frame)
            parts = snapshot(doc)
            assert all(p['shape'].isValid() and len(p['shape'].Solids)==1 for p in parts)
            row = scan(parts,theta,doc.Name+'_cycle_current_pose.json',cache)
            result['completed_angles'].append(theta)
            for name in ('brep_checks','cached_checks'):
                result[name] += row[name]
            result['collisions'].extend(dict(c,theta_deg=theta) for c in row['collisions'])
            path.write_text(json.dumps(result,indent=2)+'\n')
        result['status'] = 'FAIL' if result['collisions'] else 'PASS_A3_COLLISIONS'
    finally:
        apply_pose(doc,original_theta,params,frame)
        path.write_text(json.dumps(result,indent=2)+'\n')
    return result
