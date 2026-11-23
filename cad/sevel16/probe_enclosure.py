"""Independent headless diagnostic for failed enclosure poses; no GUI changes."""
import json
import time
import FreeCAD as App
from config import OUTPUT, load
from auxiliary_enclosure import build
from check_moving import snapshot, placed
from check_auxiliary import volume, sha
from check_crank import overlap
from kinematics import pose


def run(angles=(65,90)):
    params,frame = load()
    path = OUTPUT/'models/SEVEL_Head_A3_v002.FCStd'
    doc = App.openDocument(str(path))
    block,added,metrics = build(doc.Block.Shape.copy(),params,frame)
    parts = [p for p in snapshot(doc) if p['kind'] in ('crank','rod','piston')]
    box = added.BoundBox
    results = []
    for theta in angles:
        start = time.monotonic()
        state = pose(theta,params,frame)
        collisions,tests = [],0
        for part in parts:
            shape = placed(part,state)
            if not overlap(box,shape.BoundBox):
                continue
            tests += 1
            amount = volume(added.common(shape))
            if amount>1e-5:
                collisions.append({'part':part['name'],'intersection_mm3':amount})
        row = {'theta_deg':theta,'tests':tests,'seconds':time.monotonic()-start,'collisions':collisions}
        results.append(row)
        print(json.dumps(row),flush=True)
    report = {'status':'DIAGNOSTIC_ONLY','baseline_sha256':sha(path),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),'metrics':metrics,'poses':results}
    index = 1
    while (OUTPUT/f'reports/enclosure_diagnostic_v{index:03d}.json').exists():
        index += 1
    (OUTPUT/f'reports/enclosure_diagnostic_v{index:03d}.json').write_text(json.dumps(report,indent=2)+'\n')
    App.closeDocument(doc.Name)
    return report
