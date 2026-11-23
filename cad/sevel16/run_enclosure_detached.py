"""Build and validate a versioned enclosure candidate in an independent kernel."""
import json
import time
import FreeCAD as App
from config import OUTPUT, ROOT, load
from proof_chain import sha
from auxiliary_enclosure import build
from check_auxiliary_enclosure import prepare, run as validate


def run():
    started = time.monotonic()
    params,frame = load()
    index = 1
    parent = OUTPUT/'trials'
    parent.mkdir(exist_ok=True)
    while (parent/f'enclosure_v{index:03d}').exists():
        index += 1
    folder = parent/f'enclosure_v{index:03d}'
    folder.mkdir()
    baseline_path = OUTPUT/'models/SEVEL_Head_A3_v002.FCStd'
    baseline = App.openDocument(str(baseline_path))
    front = App.openDocument(str(OUTPUT/'models/SEVEL_Trigger_A4_v001.FCStd'))
    block,added,metrics = build(baseline.Block.Shape.copy(),params,frame)
    shapes = {o.Name:o.Shape.copy() for o in baseline.Objects if hasattr(o,'Shape')}
    inputs = prepare(baseline,front,added,params,frame)
    result = validate(block,added,shapes,inputs,params,frame,folder.name)
    block.exportBrep(str(folder/'block.brep'))
    added.exportBrep(str(folder/'added.brep'))
    (folder/'parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    report = {'status':result['status'],'validation':result,'metrics':metrics,
        'baseline_sha256':sha(baseline_path),'parameter_sha256':sha(OUTPUT/'parameters.json'),
        'datum_sha256':sha(OUTPUT/'datums/reference_frame.json'),
        'block_sha256':sha(folder/'block.brep'),'added_sha256':sha(folder/'added.brep'),
        'elapsed_seconds':time.monotonic()-started,
        'generator_sha256':{n:sha(ROOT/'cad/sevel16'/n) for n in
            ('auxiliary_enclosure.py','check_auxiliary_enclosure.py','run_enclosure_detached.py')}}
    (folder/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    App.closeDocument(baseline.Name); App.closeDocument(front.Name)
    print(json.dumps({'folder':str(folder),'status':result['status'],'elapsed_seconds':report['elapsed_seconds'],
                      'failures':len(result['failures'])}),flush=True)
    return report
