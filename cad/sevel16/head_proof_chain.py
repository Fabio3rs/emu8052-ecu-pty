"""Extend the frozen Carrier evidence with complete head/seat pair coverage."""
from itertools import combinations
from config import OUTPUT
from proof_chain import read, sha, run as earlier_chain


def run(params):
    reports = OUTPUT/'reports'
    head_path = reports/'SEVEL_Head_A3_v001_head_validation.json'
    head = read(head_path)
    baseline_hash = head['baseline_proof_sha256']
    archive = reports/f'kinematics_validation.carrier.{baseline_hash[:12]}.json'
    baseline_path = archive if archive.exists() else reports/'kinematics_validation.json'
    assert sha(baseline_path)==baseline_hash,'Missing immutable Carrier consolidation'
    baseline = read(baseline_path)
    assert baseline['document']=='SEVEL_Carrier_A3_v001'
    assert baseline['status']=='PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING'
    assert baseline['source_sha256']==sha(OUTPUT/'models/SEVEL_Carrier_A3_v001.FCStd')
    for label,row in baseline['evidence'].items():
        assert sha(OUTPUT/row['path'])==row['sha256'],(label,'changed historical evidence')
    chain = earlier_chain(params)
    assert chain==baseline['collision_proof_chain'],'Changed historical collision chain'
    previous_model,previous_proof = baseline['source_sha256'],baseline_hash
    previous_params = read(reports/'SEVEL_Carrier_A3_v001.parameters.json')
    manifest_path = OUTPUT/'exports/SEVEL_Carrier_A3_v001/meshes_v001/parts_manifest.json'
    renderer = read(OUTPUT/baseline['evidence']['renderer']['path'])
    assert sha(manifest_path)==renderer['manifest_sha256']
    parts = read(manifest_path)['parts']
    assert {p['id'] for p in parts}=={
        p['id'] for p in read(OUTPUT/baseline['evidence']['dimensions']['path'])['parts']}
    previous_names = {p['source_object'] for p in parts}
    assert len(previous_names)==len(parts)==189
    for name,suffix,status,count in [
        ('SEVEL_Head_A3_v001','head_validation','PASS_HEAD_INCREMENT_GEOMETRY',570),
        ('SEVEL_Head_A3_v002','seat_validation','PASS_STEPPED_SPRING_SEATS',1500)]:
        path = reports/f'{name}_{suffix}.json'
        report = read(path)
        snapshot_path = reports/f'{name}.parameters.json'
        snapshot = read(snapshot_path)
        assert {k:snapshot[k] for k in previous_params}==previous_params
        assert {k:params[k] for k in snapshot}==snapshot
        assert report['status']==status and not report['failures']
        assert report['source_sha256']==sha(OUTPUT/f'models/{name}.FCStd')
        assert report['baseline_sha256']==previous_model
        assert report['baseline_proof_sha256']==previous_proof
        assert report['datum_sha256']==baseline['datum_sha256']==sha(OUTPUT/'datums/reference_frame.json')
        retained = report['unchanged_parts_symmetric_difference_mm3']
        changed = set(report.get('added_parts',report.get('changed_parts',[])))
        assert len(changed)==(3 if suffix=='head_validation' else 8)
        assert set(retained)==previous_names-changed
        assert max(map(abs,retained.values()))<1e-5
        expected = {frozenset((a,b)) for a in changed for b in retained}
        expected.update(frozenset(pair) for pair in combinations(changed,2))
        checks = report['checks']
        actual = {frozenset(row['pair']) for row in checks}
        assert actual==expected and len(actual)==len(checks)==report['pairs_checked']==count
        assert report['tolerance_mm3']<=1e-5
        for row in checks:
            if 'intersection_mm3' in row:
                assert abs(row['intersection_mm3'])<=report['tolerance_mm3']
            else:
                assert row['gap_mm']>0
        if suffix=='seat_validation':
            assert report['rebuild_verified'] and len(report['load_path_contacts'])==8
            for contact in report['load_path_contacts'].values():
                assert contact['united_seat_solids']==1
                assert max(contact['outer_region_to_head_mm'],contact['inner_region_to_outer_region_mm'])<1e-7
                assert contact['outer_spring_radial_gap_mm']>0
        chain.append({'document':name,'status':status,'report':str(path.relative_to(OUTPUT)),
                      'report_sha256':sha(path),'model_sha256':report['source_sha256'],
                      'parameter_snapshot_sha256':sha(snapshot_path),
                      'parameter_comparison':'Parsed snapshots; inherited parameters unchanged',
                      'unchanged_parts':len(retained),'pairs_checked':count,'scope':report['scope']})
        previous_model,previous_proof = report['source_sha256'],sha(path)
        previous_params,previous_names = snapshot,set(retained)|changed
    assert previous_params==params and len(previous_names)==192
    return baseline_path,archive,baseline,chain
