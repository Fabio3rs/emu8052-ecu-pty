"""Audit the additive block enclosure against the frozen Head v002 assembly."""
from config import OUTPUT
from proof_chain import read, sha
from head_proof_chain import run as head_chain


def run(params,name,parameter_digest=None):
    reports = OUTPUT/'reports'
    path = reports/f'{name}_enclosure_validation.json'
    report = read(path)
    assert report['status']=='PASS_AUXILIARY_ENCLOSURE' and not report['failures']
    assert report['source_sha256']==sha(OUTPUT/f'models/{name}.FCStd')
    assert report['parameter_sha256']==(parameter_digest or sha(OUTPUT/'parameters.json'))
    assert report['datum_sha256']==sha(OUTPUT/'datums/reference_frame.json')
    archive = OUTPUT/report['baseline_proof_path']
    assert sha(archive)==report['baseline_proof_sha256']
    baseline = read(archive)
    assert baseline['document']=='SEVEL_Head_A3_v002'
    assert baseline['source_sha256']==report['baseline_sha256']==sha(OUTPUT/'models/SEVEL_Head_A3_v002.FCStd')
    old_params = read(reports/'SEVEL_Head_A3_v002.parameters.json')
    assert {k:params[k] for k in old_params}==old_params
    assert read(reports/f'{name}.parameters.json')==params
    _,_,_,chain = head_chain(old_params)
    assert chain==baseline['collision_proof_chain']
    for row in baseline['evidence'].values():
        assert sha(OUTPUT/row['path'])==row['sha256']
    manifest_path = OUTPUT/'exports/SEVEL_Head_A3_v002/meshes_v001/parts_manifest.json'
    renderer = read(OUTPUT/baseline['evidence']['renderer']['path'])
    assert sha(manifest_path)==renderer['manifest_sha256']
    parts = {p['source_object']:p for p in read(manifest_path)['parts']}
    unchanged = report['unchanged_parts_symmetric_difference_mm3']
    assert set(unchanged)==set(parts)-{'Block'} and len(unchanged)==191
    assert max(map(abs,unchanged.values()))<1e-5
    assert report['changed_parts']==['Block'] and not report['added_parts']
    assert report['rebuild_verified']
    metrics = report['casting_metrics']
    assert metrics['added_volume_mm3']>0 and metrics['removed_volume_mm3']<1e-5
    assert metrics['bore_plane_y_clearance_mm']>0 and metrics['seal_plane_z_clearance_mm']>0
    assert set(metrics['service_openings_preserved'])=={'breather','oil_filter'}
    samples = report['angles_deg']
    assert len(samples)==220 and set(range(0,721,5)).issubset(samples)
    covered,separated = report['pair_coverage'],report['continuous_upper_separations_mm']
    assert set(covered).isdisjoint(separated) and set(covered)|set(separated)==set(unchanged)
    for part,row in covered.items():
        moving = parts[part]['motion_type'] in ('crank','rod','piston')
        assert row['bbox_filtered']+row['brep_tested']==(len(samples) if moving else 1)
    for part,gap in separated.items():
        assert parts[part]['motion_type'] in ('cam','valve','spring') and gap>0
    assert report['continuous_auxiliary_gap_mm']>=params['auxiliary_internal_estimated']['value']['running_clearance_mm']-1e-6
    assert max(report['bush_contacts_mm'].values())<1e-7
    assert len(report['outward_wall_ray_lengths_mm'])==40
    assert min(report['outward_wall_ray_lengths_mm'].values())>2
    chain.append({'document':name,'status':report['status'],'report':str(path.relative_to(OUTPUT)),
        'report_sha256':sha(path),'model_sha256':report['source_sha256'],
        'parameter_snapshot_sha256':sha(reports/f'{name}.parameters.json'),
        'parameter_comparison':'Parsed snapshots; inherited inputs unchanged',
        'unchanged_parts':191,'pairs_checked':191,'scope':report['scope'],'limits':report['limits']})
    return archive,archive,baseline,chain
