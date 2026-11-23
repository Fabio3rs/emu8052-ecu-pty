"""Independent reconstruction and on-disk predecessor identity verification."""
import json
from pathlib import Path
import FreeCAD as App
from config import ROOT, OUTPUT, load
from proof_chain import read, sha
from geometry_identity import difference, sampled_equivalence
import external_accessories


def run(name='SEVEL_Accessories_A5_v002', report_path=None):
    params,frame = load()
    proof = read(OUTPUT/f'reports/{name}_accessories_validation.json')
    assert proof['parameter_sha256']==sha(OUTPUT/'parameters.json')
    path = OUTPUT/f'models/{name}.FCStd'
    assert proof['source_sha256']==sha(path)
    old_path = OUTPUT/'models/SEVEL_Closures_A5_v001.FCStd'
    assert proof['baseline_sha256']==sha(old_path)
    baseline,doc = App.openDocument(str(old_path)),App.openDocument(str(path))
    try:
        shapes,contacts,metrics = external_accessories.build(params,frame)
        rebuilt, sampled = {},{}
        for n,s in shapes.items():
            saved = doc.getObject(n).Shape
            try:
                rebuilt[n] = difference(s,saved)
                assert abs(rebuilt[n])<1e-5
            except ValueError as error:
                if n!='IntakeManifold' or str(error)!='Null shape':
                    raise
                sampled[n] = sampled_equivalence(s,saved)
                rebuilt[n] = None
        assert len(rebuilt)==20
        unchanged = {}
        for old in baseline.Objects:
            if not hasattr(old,'Shape'):
                continue
            obj = doc.getObject(old.Name)
            unchanged[old.Name] = difference(old.Shape,obj.Shape)
            for prop in ('PartId','MotionType','CylinderId','ValveKind','SpringKind','RestBase'):
                assert getattr(old,prop,None)==getattr(obj,prop,None),(old.Name,prop)
        assert len(unchanged)==198 and max(map(abs,unchanged.values()))<1e-5
        assert metrics==proof['interfaces']
        assert {a+' / '+b for a,b in contacts}==set(proof['contacts_mm'])
        result = {'status':'PASS_ACCESSORIES_REBUILD','source_sha256':sha(path),
            'parameter_sha256':sha(OUTPUT/'parameters.json'),'baseline_sha256':sha(old_path),
            'symmetric_difference_mm3':rebuilt,'unchanged_parts_symmetric_difference_mm3':unchanged,
            'sampled_reconstruction':sampled,'interfaces':metrics,
            'identity_method':'Canonical B-rep or Boolean; explicit surface sampling for a failed intake Boolean',
            'entrypoint_sha256':sha(ROOT/'cad/sevel16/build_accessories_checkpoint.py')}
        target = Path(report_path) if report_path else OUTPUT/f'reports/{name}_accessories_rebuild.json'
        if report_path:
            assert not target.exists(), 'Preserve previous relocation evidence'
        target.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'rebuilt':len(rebuilt),'preserved':len(unchanged)}))
        return result
    finally:
        App.closeDocument(doc.Name)
        App.closeDocument(baseline.Name)
