"""Build a detached, reproducible closure candidate without changing the GUI."""
import json
import time
import FreeCAD as App
from config import ROOT, OUTPUT, load
from proof_chain import sha, read
import valve_cover
import oil_pan
import check_closures


def run():
    started = time.monotonic()
    params,frame = load()
    name = 'SEVEL_Casting_A4_v002'
    source = OUTPUT/'models'/f'{name}.FCStd'
    baseline = read(OUTPUT/'reports/kinematics_validation.json')
    assert baseline['document']==name and baseline['source_sha256']==sha(source)
    assert baseline['status']=='PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING'
    prior = read(OUTPUT/'reports'/f'{name}.parameters.json')
    assert {k:params[k] for k in prior}==prior
    parent,index = OUTPUT/'trials',1
    while (parent/f'closures_v{index:03d}').exists():
        index += 1
    folder = parent/f'closures_v{index:03d}'
    folder.mkdir()
    doc = App.openDocument(str(source))
    shapes = {**valve_cover.build(params,frame),**oil_pan.build(params,frame)}
    assert len(shapes)==6
    files = {}
    for label,shape in shapes.items():
        path = folder/f'{label}.brep'
        shape.exportBrep(str(path))
        files[label] = {'file':path.name,'sha256':sha(path),'volume_mm3':shape.Volume}
    (folder/'parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    validation = check_closures.run(doc,shapes,params,frame,folder.name)
    report = {'status':validation['status'],'validation':validation,'parts':files,
              'baseline_document':name,'baseline_sha256':sha(source),
              'baseline_proof_sha256':sha(OUTPUT/'reports/kinematics_validation.json'),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'datum_sha256':sha(OUTPUT/'datums/reference_frame.json'),
              'elapsed_seconds':time.monotonic()-started,
              'generator_sha256':{n:sha(ROOT/'cad/sevel16'/n) for n in
                  ('valve_cover.py','oil_pan.py','check_closures.py','run_closures_trial.py')}}
    (folder/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    App.closeDocument(doc.Name)
    print(json.dumps({'folder':str(folder),'status':validation['status'],
                      'failures':validation['failures'][:12],'elapsed_seconds':report['elapsed_seconds']}),flush=True)
    return report
