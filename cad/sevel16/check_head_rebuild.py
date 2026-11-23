"""Rebuild the three fixed additions from parameters, independently of the GUI."""
import json
from config import OUTPUT
from build_head_checkpoint import generate
from check_auxiliary import difference, sha


def run(saved_shapes,params,frame,source_path):
    rebuilt,metrics = generate(params,frame)
    differences = {name:difference(saved_shapes[name],shape) for name,shape in rebuilt.items()}
    assert set(differences)=={'HeadLower','HeadGasket','CarrierGasket'}
    assert max(differences.values())<1e-5
    report = {'status':'PASS_HEAD_REBUILD','source_sha256':sha(source_path),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'datum_sha256':sha(OUTPUT/'datums/reference_frame.json'),
              'symmetric_differences_mm3':differences,'chamber_metrics':metrics,
              'scope':'Rebuilt lower head and both gaskets; inherited components covered by baseline proof'}
    name = source_path.stem
    (OUTPUT/f'reports/{name}_head_rebuild.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
