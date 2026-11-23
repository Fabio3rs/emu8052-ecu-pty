"""Audit accessory coverage and the identity of the inherited closure assembly."""
import itertools
from config import ROOT, OUTPUT
from proof_chain import read, sha
from closure_proof_chain import run as closure_chain


def run(params,name):
    reports = OUTPUT/'reports'
    path = reports/f'{name}_accessories_validation.json'
    report = read(path)
    assert report['status']=='PASS_ACCESSORIES_INCREMENT' and not report['failures']
    assert report['source_sha256']==sha(OUTPUT/f'models/{name}.FCStd')
    assert report['parameter_sha256']==sha(OUTPUT/'parameters.json')
    assert report['datum_sha256']==sha(OUTPUT/'datums/reference_frame.json')
    assert read(reports/f'{name}.parameters.json')==params
    archive = OUTPUT/report['baseline_proof_path']
    assert sha(archive)==report['baseline_proof_sha256']
    baseline = read(archive)
    old_name = baseline['document']
    assert old_name=='SEVEL_Closures_A5_v001'
    assert baseline['source_sha256']==report['baseline_sha256']==sha(OUTPUT/f'models/{old_name}.FCStd')
    old_params = read(reports/f'{old_name}.parameters.json')
    assert {k:params[k] for k in old_params}==old_params
    _,_,_,chain = closure_chain(old_params,old_name,baseline['parameter_sha256'])
    assert chain==baseline['collision_proof_chain']
    for row in baseline['evidence'].values():
        assert sha(OUTPUT/row['path'])==row['sha256']
    renderer = read(OUTPUT/baseline['evidence']['renderer']['path'])
    manifest = OUTPUT/f'exports/{old_name}/meshes_v001/parts_manifest.json'
    assert sha(manifest)==renderer['manifest_sha256']
    parts = {p['source_object']:p for p in read(manifest)['parts']}
    unchanged = report['unchanged_parts_symmetric_difference_mm3']
    assert set(unchanged)==set(parts) and len(parts)==report['baseline_parts']==198
    assert max(map(abs,unchanged.values()))<1e-5
    added = report['added_parts']
    assert len(added)==len(set(added))==20 and not set(added)&set(parts)
    rebuilt = report['rebuild_symmetric_difference_mm3']
    assert set(rebuilt)==set(added) and max(map(abs,rebuilt.values()))<1e-5
    assert len(report['contacts_mm'])==22 and max(report['contacts_mm'].values())<1e-6
    samples = report['angles_deg']
    assert len(samples)==len(set(samples))==220 and set(range(0,721,5)).issubset(samples)
    covered = report['pair_coverage']
    expected = {a+' / '+b:(len(samples) if p['motion_type'] in ('crank','rod','piston') else 1)
                for a in added for b,p in parts.items()}
    expected.update({a+' / '+b:1 for a,b in itertools.combinations(added,2)})
    assert set(expected)==set(covered) and len(covered)==4150
    for pair,count in expected.items():
        row = covered[pair]
        assert row['bbox_filtered']>=0 and row['brep_tested']>=0
        assert row['bbox_filtered']+row['brep_tested']==count
    interface = report['interfaces']
    assert len(interface['ports'])==len({p['id'] for p in interface['ports']})==8
    assert all(p['side']=='+Y' and p['obstruction_mm3']<1e-5 and p['missing_passage_mm3']<1e-5
               for p in interface['ports'])
    assert {p['cylinder'] for p in interface['spark_tips']}=={1,2,3,4}
    assert all(p['outside_chamber_mm3']<1e-7 for p in interface['spark_tips'])
    assert interface['intake_air_water_separation_mm']>0.1
    assert interface['intake_air_solids']==interface['intake_water_solids']==interface['exhaust_gas_solids']==1
    assert interface['exhaust_runner_probe_margin_mm']==0.1
    assert len(interface['exhaust_runner_probe_missing_mm3'])==4
    assert max(map(abs,interface['exhaust_runner_probe_missing_mm3']))<1e-5
    assert interface['accessory_pulley_alignment_mm']<1e-7
    trial_path = OUTPUT/report['trial_path']/'validation.json'
    assert sha(trial_path)==report['trial_validation_sha256']
    trial = read(trial_path)
    assert trial['status']==report['status'] and trial['interfaces']==interface
    preflight = trial['export_preflight']
    assert set(preflight)==set(added) and all(row['closed_mesh'] and row['facets']>0
                                             for row in preflight.values())
    for part in ('IntakeManifold','ExhaustManifold'):
        assert preflight[part]['step_relative_volume_error']<1e-6
    for filename,digest in trial['generator_sha256'].items():
        assert sha(ROOT/'cad/sevel16'/filename)==digest
    chain.append({'document':name,'status':report['status'],'report':str(path.relative_to(OUTPUT)),
        'report_sha256':sha(path),'model_sha256':report['source_sha256'],
        'parameter_snapshot_sha256':sha(reports/f'{name}.parameters.json'),
        'parameter_comparison':'Parsed snapshots; inherited inputs unchanged',
        'unchanged_parts':198,'added_parts':added,'pairs_checked':len(covered),
        'scope':report['scope'],'limits':report['limits']})
    return archive,archive,baseline,chain
