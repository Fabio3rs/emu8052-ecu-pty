"""Build and validate external accessories against the frozen closure assembly."""
import json
import time
import FreeCAD as App
import MeshPart
import Part
from config import ROOT, OUTPUT, load
from proof_chain import read, sha
import external_accessories
import check_external_accessories

GENERATORS = ('spark_plugs.py','manifold_profiles.py','intake_manifold.py',
              'exhaust_manifold.py','water_pump.py','external_accessories.py',
              'check_external_accessories.py','run_accessories_trial.py')


def run():
    started = time.monotonic()
    params,frame = load()
    name = 'SEVEL_Closures_A5_v001'
    source = OUTPUT/f'models/{name}.FCStd'
    proof_path = OUTPUT/'reports/kinematics_validation.json'
    baseline = read(proof_path)
    visited = set()
    while baseline['document']!=name:
        assert proof_path not in visited
        visited.add(proof_path)
        inherited = baseline['inherited_baseline']
        proof_path = (OUTPUT/inherited['path']).resolve()
        assert proof_path.is_relative_to((OUTPUT/'reports').resolve())
        assert sha(proof_path)==inherited['sha256']
        baseline = read(proof_path)
    assert baseline['source_sha256']==sha(source)
    assert baseline['status']=='PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING'
    prior = read(OUTPUT/f'reports/{name}.parameters.json')
    assert {k:params[k] for k in prior}==prior
    archive = OUTPUT/f'reports/kinematics_validation.{name}.{sha(proof_path)[:12]}.json'
    if not archive.exists():
        archive.write_bytes(proof_path.read_bytes())
    assert sha(archive)==sha(proof_path)
    index = 1
    while (OUTPUT/f'trials/accessories_v{index:03d}').exists():
        index += 1
    folder = OUTPUT/f'trials/accessories_v{index:03d}'
    folder.mkdir()
    shapes,contacts,metrics = external_accessories.build(params,frame)
    files, export_preflight = {},{}
    for label,shape in shapes.items():
        path = folder/f'{label}.brep'
        shape.exportBrep(str(path))
        files[label] = {'file':path.name,'sha256':sha(path),'volume_mm3':shape.Volume}
        mesh = MeshPart.meshFromShape(Shape=shape,LinearDeflection=0.08,
                                     AngularDeflection=0.2,Relative=False)
        assert mesh.isSolid(),('open accessory mesh',label)
        export_preflight[label] = {'closed_mesh':True,'facets':mesh.CountFacets}
        if label.endswith('Manifold'):
            step_path = folder/f'{label}.step'
            shape.exportStep(str(step_path))
            restored = Part.read(str(step_path))
            error = abs(restored.Volume-shape.Volume)/shape.Volume
            assert restored.isValid() and len(restored.Solids)==1 and error<1e-6,(label,error)
            export_preflight[label]['step_relative_volume_error'] = error
    (folder/'parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    doc = App.openDocument(str(source))
    validation = check_external_accessories.run(doc,shapes,contacts,params,frame,folder.name)
    report = {'status':validation['status'],'validation':validation,'parts':files,'interfaces':metrics,
        'export_preflight':export_preflight,
        'baseline_document':name,'baseline_sha256':sha(source),
        'baseline_proof_path':str(archive.relative_to(OUTPUT)),'baseline_proof_sha256':sha(archive),
        'parameter_sha256':sha(OUTPUT/'parameters.json'),'datum_sha256':sha(OUTPUT/'datums/reference_frame.json'),
        'elapsed_seconds':time.monotonic()-started,
        'generator_sha256':{n:sha(ROOT/'cad/sevel16'/n) for n in GENERATORS}}
    (folder/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    App.closeDocument(doc.Name)
    print(json.dumps({'folder':str(folder),'status':validation['status'],
                      'failures':validation['failures'][:20],'elapsed_seconds':report['elapsed_seconds']}),flush=True)
    return report
