"""Regenerate closures after publication, using the frozen predecessor proof."""
import json
import FreeCAD as App
from config import ROOT, OUTPUT, load
from proof_chain import read, sha
from check_auxiliary import difference
from build_closures_checkpoint import baseline_proof
import valve_cover
import oil_pan


def run(name='SEVEL_Closures_A5_v001',trial_name='closures_v004'):
    params,frame = load()
    trial = read(OUTPUT/f'trials/{trial_name}/validation.json')
    assert trial['status']=='PASS_CLOSURES_INCREMENT'
    assert trial['parameter_sha256']==sha(OUTPUT/'parameters.json')
    for filename,digest in trial['generator_sha256'].items():
        assert sha(ROOT/'cad/sevel16'/filename)==digest
    source = OUTPUT/f'models/{trial["baseline_document"]}.FCStd'
    proof = baseline_proof(trial,source)
    path = OUTPUT/f'models/{name}.FCStd'
    doc = App.openDocument(str(path))
    try:
        shapes = {**valve_cover.build(params,frame),**oil_pan.build(params,frame)}
        errors = {n:difference(s,doc.getObject(n).Shape) for n,s in shapes.items()}
        assert len(errors)==6 and max(map(abs,errors.values()))<1e-5
        result = {'status':'PASS_CLOSURE_REBUILD','source_sha256':sha(path),
            'parameter_sha256':sha(OUTPUT/'parameters.json'),
            'baseline_proof_path':str(proof.relative_to(OUTPUT)),
            'baseline_proof_sha256':sha(proof),'symmetric_difference_mm3':errors,
            'entrypoint_sha256':sha(ROOT/'cad/sevel16/build_closures_checkpoint.py')}
        (OUTPUT/f'reports/{name}_closure_rebuild.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
        return result
    finally:
        App.closeDocument(doc.Name)
