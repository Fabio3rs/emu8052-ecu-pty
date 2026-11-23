"""Native FreeCAD verification in a fresh process rooted in the copied package."""
import json
import FreeCAD as App
from config import ROOT, OUTPUT, load
from proof_chain import read, sha
import check_accessories_rebuild
import check_rebuild
from accessories_proof_chain import run as audit_chain


def run():
    index = read(ROOT/'delivery.json')
    assert index['document'].startswith('SEVEL_Accessories_A5_')
    def verify_files():
        for relative,digest in index['files'].items():
            path = (ROOT/relative).resolve()
            assert path.is_relative_to(ROOT) and sha(path)==digest,relative
    verify_files()
    folder = ROOT/'verification'
    folder.mkdir(exist_ok=True)
    target = folder/'native_cad.json'
    assert not target.exists()
    params,frame = load()
    name = index['document']
    _,_,_,chain = audit_chain(params,name)
    current = read(OUTPUT/'reports/kinematics_validation.json')
    assert current['document']==name and current['collision_proof_chain']==chain
    for row in current['evidence'].values():
        assert sha(OUTPUT/row['path'])==row['sha256']
    accessory = check_accessories_rebuild.run(name,folder/'accessory_rebuild.json')
    path = OUTPUT/f'models/{name}.FCStd'
    assert sha(path)==index['source_sha256']==current['source_sha256']
    doc = App.openDocument(str(path))
    try:
        parts = [o for o in doc.Objects if hasattr(o,'Shape')]
        assert len(parts)==len({o.PartId for o in parts})==218
        assert all(not o.Shape.isNull() and o.Shape.isValid()
                   and len(o.Shape.Solids)==1 and o.Shape.Volume>0 for o in parts)
        check_rebuild.run(doc,folder/'moving_rebuild.json')
        assert doc.Phase.ThetaDeg==0
        report = {'status':'PASS_RELOCATED_NATIVE_CAD','document':name,
            'freecad_version':App.Version(),
            'source_sha256':sha(path),'parameter_sha256':sha(OUTPUT/'parameters.json'),
            'delivery_index_sha256':sha(ROOT/'delivery.json'),'valid_solids':len(parts),
            'chain_stages':len(chain),'direct_evidence':len(current['evidence']),
            'moving_rebuild_sha256':sha(folder/'moving_rebuild.json'),
            'accessory_rebuild_sha256':sha(folder/'accessory_rebuild.json'),
            'accessory_sampled_reconstruction':accessory['sampled_reconstruction'],
            'scope':'Reopen, regenerate 13 moving prototypes and 20 accessories, 145 CAD poses; audit inherited collision evidence',
            'limits':'No new full collision sweep; intake comparison uses explicit surface/trim sampling'}
        verify_files()
        target.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='accessory_sampled_reconstruction'}))
        return report
    finally:
        App.closeDocument(doc.Name)
