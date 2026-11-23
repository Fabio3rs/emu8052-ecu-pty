"""Audit the six closures against their frozen casting checkpoint."""
import itertools
from config import OUTPUT
from proof_chain import read, sha
from enclosure_proof_chain import run as enclosure_chain


def run(params,name,parameter_digest=None):
    reports = OUTPUT/'reports'
    path = reports/f'{name}_closures_validation.json'
    report = read(path)
    assert report['status']=='PASS_CLOSURES_INCREMENT' and not report['failures']
    assert report['source_sha256']==sha(OUTPUT/f'models/{name}.FCStd')
    assert report['parameter_sha256']==(parameter_digest or sha(OUTPUT/'parameters.json'))
    assert report['datum_sha256']==sha(OUTPUT/'datums/reference_frame.json')
    assert read(reports/f'{name}.parameters.json')==params
    archive = OUTPUT/report['baseline_proof_path']
    assert sha(archive)==report['baseline_proof_sha256']
    baseline = read(archive)
    old_name = baseline['document']
    assert old_name=='SEVEL_Casting_A4_v002'
    assert baseline['source_sha256']==report['baseline_sha256']==sha(OUTPUT/f'models/{old_name}.FCStd')
    old_params = read(reports/f'{old_name}.parameters.json')
    assert {k:params[k] for k in old_params}==old_params
    _,_,_,chain = enclosure_chain(old_params,old_name,baseline['parameter_sha256'])
    assert chain==baseline['collision_proof_chain']
    for row in baseline['evidence'].values():
        assert sha(OUTPUT/row['path'])==row['sha256']
    renderer = read(OUTPUT/baseline['evidence']['renderer']['path'])
    manifest = OUTPUT/f'exports/{old_name}/meshes_v001/parts_manifest.json'
    assert sha(manifest)==renderer['manifest_sha256']
    parts = {p['source_object']:p for p in read(manifest)['parts']}
    unchanged = report['unchanged_parts_symmetric_difference_mm3']
    assert set(unchanged)==set(parts) and len(parts)==report['baseline_parts']==192
    assert max(map(abs,unchanged.values()))<1e-5
    added = report['added_parts']
    assert len(added)==len(set(added))==6 and not set(added)&set(parts)
    rebuilt = report['rebuild_symmetric_difference_mm3']
    assert set(rebuilt)==set(added) and max(map(abs,rebuilt.values()))<1e-5
    assert len(report['contacts_mm'])==6 and max(report['contacts_mm'].values())<1e-6
    samples = report['angles_deg']
    assert len(samples)==len(set(samples))==220 and set(range(0,721,5)).issubset(samples)
    covered = report['pair_coverage']
    expected = {a+' / '+b:(len(samples) if p['motion_type'] in ('crank','rod','piston') else 1)
                for a in added for b,p in parts.items()}
    expected.update({a+' / '+b:1 for a,b in itertools.combinations(added,2)})
    assert set(expected)==set(covered) and len(covered)==1167
    for pair,count in expected.items():
        row = covered[pair]
        assert row['bbox_filtered']>=0 and row['brep_tested']>=0
        assert row['bbox_filtered']+row['brep_tested']==count
    assert set(report['continuous_envelope_parts'])=={
        n for n,p in parts.items() if p['motion_type'] not in ('crank','rod','piston')}
    chain.append({'document':name,'status':report['status'],'report':str(path.relative_to(OUTPUT)),
        'report_sha256':sha(path),'model_sha256':report['source_sha256'],
        'parameter_snapshot_sha256':sha(reports/f'{name}.parameters.json'),
        'parameter_comparison':'Parsed snapshots; inherited inputs unchanged',
        'unchanged_parts':192,'added_parts':added,'pairs_checked':len(covered),
        'scope':report['scope'],'limits':report['limits']})
    return archive,archive,baseline,chain
