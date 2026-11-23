"""Publish completion only after a concrete package and its checks exist."""
import json
from pathlib import Path
import sys
from config import ROOT, OUTPUT, load
from proof_chain import read, sha
from accessories_proof_chain import run as audit_chain


def run(package,relocation):
    package,relocation = Path(package).resolve(),Path(relocation).resolve()
    assert package.is_relative_to(ROOT) and relocation.is_relative_to(ROOT)
    index = read(package/'delivery.json')
    name = index['document']
    current_path = OUTPUT/'reports/kinematics_validation.json'
    current = read(current_path)
    assert current['document']==name and current['status']=='PASS_CURRENT_VISUAL_KINEMATICS'
    assert current['source_sha256']==index['source_sha256']
    params,_ = load()
    _,_,_,chain = audit_chain(params,name)
    assert chain==current['collision_proof_chain'] and len(chain)==12
    assert len(current['evidence'])==13
    for row in current['evidence'].values():
        assert sha(OUTPUT/row['path'])==row['sha256']
    for relative,digest in index['files'].items():
        path = (package/relative).resolve()
        assert path.is_relative_to(package) and sha(path)==digest,relative
    native_path = package/'verification/native_cad.json'
    native,relocated = read(native_path),read(relocation)
    assert native['status']=='PASS_RELOCATED_NATIVE_CAD'
    assert relocated['status']=='PASS_RELOCATED_SOURCES_AND_RENDERER'
    for proof in (native,relocated):
        assert proof['delivery_index_sha256']==sha(package/'delivery.json')
        assert proof['source_sha256']==current['source_sha256']
        assert proof['parameter_sha256']==current['parameter_sha256']
    assert native['valid_solids']==218 and native['chain_stages']==12
    assert relocated['renderer_recompiled'] and relocated['transforms_and_materials_preserved']
    assert sha(relocation.parent/'analytic_tests.txt')==relocated['unit_test_output_sha256']
    assert len(relocated['poses'])==7 and all(p['status']=='PASS_RENDERER_POSE_ONLY'
                                             for p in relocated['poses'])
    assert sha(package/'verification/moving_rebuild.json')==native['moving_rebuild_sha256']
    assert sha(package/'verification/accessory_rebuild.json')==native['accessory_rebuild_sha256']
    manifest = read(package/index['mesh_folder']/'parts_manifest.json')
    names = {p['source_object'] for p in manifest['parts']}
    required = {'Block','HeadLower','HeadGasket','CamCarrier','ValveCover','OilPan',
                'IntakeManifold','ExhaustManifold','WaterPumpBody','WaterPumpPulley'}
    required.update(f'C{i}_Spark{part}' for i in range(1,5) for part in ('Shell','Ceramic','Electrode'))
    assert len(names)==218 and required.issubset(names)
    audit = ROOT/'cad/sevel16/FINAL_DELIVERY_AUDIT.md'
    assert audit.is_file() and (package/'cad/sevel16/FINAL_DELIVERY_AUDIT.md').read_bytes()==audit.read_bytes()
    result = {'status':'PASS_VISUAL_KINEMATIC_DELIVERY','goal_complete':True,
        'document':name,'source_sha256':current['source_sha256'],
        'parameter_sha256':current['parameter_sha256'],
        'kinematics_validation_sha256':sha(current_path),
        'package':str(package.relative_to(ROOT)),'delivery_index_sha256':sha(package/'delivery.json'),
        'relocation_report':str(relocation.relative_to(ROOT)),'relocation_sha256':sha(relocation),
        'native_report':str(native_path.relative_to(ROOT)),'native_sha256':sha(native_path),
        'audit':'cad/sevel16/FINAL_DELIVERY_AUDIT.md','audit_sha256':sha(audit),
        'scope':'Parametric visual engine and deterministic 720-degree mechanism; not certified manufacturing geometry',
        'limits':current['limits']}
    target = OUTPUT/'reports/final_delivery.json'
    assert not target.exists(), 'Preserve the published completion record'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'report':str(target)}))
    return result


if __name__=='__main__':
    run(*sys.argv[1:])
