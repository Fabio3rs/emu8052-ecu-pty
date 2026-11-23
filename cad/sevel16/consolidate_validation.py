"""Join measured evidence without promoting a kinematic pass to casting completion."""
import json
import hashlib
from pathlib import Path
from config import ROOT, OUTPUT, load
from proof_chain import read, sha, run as collision_chain


def run():
    params,frame = load()
    name = 'SEVEL_Carrier_A3_v001'
    model = OUTPUT/f'models/{name}.FCStd'
    digest,parameter_digest = sha(model),sha(OUTPUT/'parameters.json')
    reports = OUTPUT/'reports'
    evidence = {}
    def checked(label,path,status,source_key='source_sha256'):
        row = read(path)
        assert row['status']==status,(label,row['status'])
        if source_key:
            assert row[source_key]==digest,(label,'wrong CAD source')
        if 'parameter_sha256' in row:
            assert row['parameter_sha256']==parameter_digest,(label,'wrong parameters')
        evidence[label] = {'path':str(path.relative_to(OUTPUT)),'sha256':sha(path),'status':row['status']}
        return row
    analytic = checked('analytic',reports/'kinematics_analytic.json','PARTIAL_PASS_ANALYTIC_ONLY',None)
    dimensions = checked('dimensions',reports/f'{name}_dimensions.json','PASS')
    valves = checked('valve_dimensions',reports/f'{name}_valve_dimensions.json','PASS_DIMENSIONS_ONLY')
    contacts = checked('cam_contacts',reports/f'{name}_cam_contact.json','PASS_CAM_CONTACT_ONLY')
    rebuild = checked('rebuild',reports/f'{name}_rebuild.json','PASS')
    controller = checked('controller',reports/f'{name}_controller.json','PASS_FREECAD_CONTROLLER_ONLY')
    sections = checked('sections',reports/f'{name}_sections.json','PASS_DERIVED_CUTAWAYS')
    assert sections['theta_deg']==90 and sections['restored_theta_deg']==0
    assert {s['label'] for s in sections['sections']}=={'Longitudinal','TransverseC1'}
    for section in sections['sections']:
        assert sha(OUTPUT/section['model'])==section['sha256']
        image = Path(section['image'])
        assert image.stat().st_size>0
        metadata = read(image.with_suffix('.json'))
        assert metadata['document']==Path(section['model']).stem and metadata['theta_deg']==90
    bottom = checked('bottom_collision',reports/f'{name}_bottom_cycle_current.json','PASS')
    assert len(dimensions['parts'])==189 and all(p['valid'] and p['solids']==1 for p in dimensions['parts'])
    assert len(valves['valves'])==8 and len(valves['journals'])==5
    assert contacts['measurements']==1760 and len(contacts['angles'])==220
    assert contacts['max_support_error_mm']<contacts['profile_tolerance_mm']
    assert contacts['min_contact_margin_mm']>0 and contacts['max_active_contact_gap_mm']<0.01
    assert len(rebuild['cad_pose_angles_deg'])==145 and rebuild['baseline_parameters_unchanged']
    assert {v['kind'] for v in rebuild['variants']}=={'stroke','cosmetic'}
    assert all(v['valid'] and v['separate_copy'] for v in rebuild['variants'])
    assert controller['spring_preview_count']==16 and controller['periodic_placement_error']<1e-8
    assert controller['timer_advanced_to_deg']>0 and controller['cleanup_restored_theta_deg']==0
    assert bottom['parts']==68 and bottom['pairs']==2278 and len(bottom['pair_coverage'])==2278
    assert len(bottom['angles_deg'])==220 and not bottom['collisions']
    assert bottom['parameters_sha256']==hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()
    assert set(range(0,721,5)).issubset(bottom['angles_deg'])
    for contact in bottom['expected_contacts']:
        assert contact['volume_mm3']<=contact['limit_mm3']+bottom['volume_tolerance_mm3']
        assert {n.rsplit('_',1)[-1] for n in contact['pair']}=={'Rod','SmallBushing'}
    chain = collision_chain(params)
    folder = OUTPUT/'exports'/name
    step = checked('step',folder/'export_checks.json','PASS','source_fcstd_sha256')
    assert step['solids']==189 and step['relative_volume_error']<1e-6
    assert step['step_sha256']==sha(folder/'assembly.step')
    meshes = folder/'meshes_v001'
    mesh = checked('meshes',meshes/'mesh_checks.json','PASS_MESH_EXPORT_ONLY')
    renderer = checked('renderer',meshes/'renderer_checks.json','PASS_EXISTING_RECORDING_RENDERER_ONLY',
                       'source_fcstd_sha256')
    manifest = read(meshes/'parts_manifest.json')
    assert renderer['manifest_sha256']==sha(meshes/'parts_manifest.json')
    assert renderer['executable_sha256']==sha(OUTPUT/'check_mesh_renderer')
    assert renderer['loader_source_sha256']==sha(ROOT/'third_party/open-engine-sim/src/authored_mesh_library.cpp')
    assert manifest['source_sha256']==digest and len(manifest['parts'])==mesh['parts']==189
    assert len({p['id'] for p in manifest['parts']})==189
    assert all(p['parent_id']=='engine_root' for p in manifest['parts'])
    for value in manifest['meshes'].values():
        assert sha(meshes/value['file'])==value['sha256']
    for filename,value in renderer['pose_inputs_sha256'].items():
        assert sha(meshes/filename)==value
    assert all(p['parts']==189 for p in renderer['poses'][1:5])
    summary = {k:v for k,v in analytic.items() if k not in ('test_output','pose_samples','pending','status')}
    summary.update(status='PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING',goal_complete=False,
                   document=name,source_sha256=digest,datum_sha256=sha(OUTPUT/'datums/reference_frame.json'),
                   evidence=evidence,collision_proof_chain=chain,
                   validation_code_sha256={p.name:sha(p) for p in sorted((ROOT/'cad/sevel16').glob('*.py'))},
                   actual_cad_strokes_mm=rebuild['piston_crown_strokes_measured_in_cad_mm'],
                   actual_cad_rod_tip_error_mm=rebuild['max_freecad_rod_tip_error_mm'],
                   current_bottom_brep_tests=sum(v['brep_tested'] for v in bottom['pair_coverage'].values()),
                   cutaway_evidence=sections['sections'],
                   expected_press_fits=bottom['expected_contacts'],
                   collision_policy='220 sampled phases plus continuous envelopes for documented increments; not an all-time collision certificate',
                   pending=['Reconcile lower-head casting and broad curved block transition with user references',
                            'Complete portable metadata/source packaging and assess GLB capability',
                            'Final requirement-by-requirement delivery audit'],
                   limits=['Synthetic cam and uncalibrated casting/axial dimensions',
                           'Timing teeth, auxiliary ratio and trigger phase remain provisional',
                           'RecordingRenderer proof covers four poses; continuous playback uses FreeCAD'])
    path = reports/'kinematics_validation.json'
    archive = reports/'kinematics_validation.before_consolidation.json'
    if path.exists() and not archive.exists():
        archive.write_bytes(path.read_bytes())
    path.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'status':summary['status'],'document':name,'evidence_reports':len(evidence)}))
    return summary


if __name__=='__main__':
    run()
