"""Publish current evidence while retaining the hash-linked Carrier baseline."""
import json
from pathlib import Path
from config import ROOT, OUTPUT, load
from proof_chain import read, sha
from head_proof_chain import run as audit_chain


def run(name='SEVEL_Head_A3_v002'):
    params,frame = load()
    part_count = 192
    if name.startswith('SEVEL_Accessories_A5_'):
        from accessories_proof_chain import run as audit_accessories
        baseline_path,archive,baseline,chain = audit_accessories(params,name)
        part_count = 198+len(chain[-1]['added_parts'])
    elif name.startswith('SEVEL_Closures_A5_'):
        from closure_proof_chain import run as audit_closures
        baseline_path,archive,baseline,chain = audit_closures(params,name)
        part_count += len(chain[-1]['added_parts'])
    elif name.startswith('SEVEL_Casting_A4_'):
        from enclosure_proof_chain import run as audit_enclosure
        baseline_path,archive,baseline,chain = audit_enclosure(params,name)
    else:
        assert name=='SEVEL_Head_A3_v002'
        baseline_path,archive,baseline,chain = audit_chain(params)
    digest = sha(OUTPUT/f'models/{name}.FCStd')
    parameter_digest = sha(OUTPUT/'parameters.json')
    reports,folder = OUTPUT/'reports',OUTPUT/'exports'/name
    evidence = {}
    def checked(label,path,status,source_key='source_sha256'):
        row = read(path)
        assert row['status']==status,(label,row['status'])
        if source_key:
            assert row[source_key]==digest,(label,'wrong model')
        if 'parameter_sha256' in row:
            assert row['parameter_sha256']==parameter_digest,(label,'wrong parameters')
        evidence[label] = {'path':str(path.relative_to(OUTPUT)),'sha256':sha(path),'status':row['status']}
        return row
    analytic = checked('analytic',reports/f'{name}_analytic.json','PARTIAL_PASS_ANALYTIC_ONLY',None)
    dimensions = checked('dimensions',reports/f'{name}_dimensions.json','PASS')
    valves = checked('valve_dimensions',reports/f'{name}_valve_dimensions.json','PASS_DIMENSIONS_ONLY')
    rebuild = checked('rebuild',reports/f'{name}_rebuild.json','PASS')
    controller = checked('controller',reports/f'{name}_controller.json','PASS_FREECAD_CONTROLLER_ONLY')
    sections = checked('sections',reports/f'{name}_sections.json','PASS_DERIVED_CUTAWAYS')
    captures = checked('cycle_captures',reports/f'{name}_cycle_captures.json',
                       'REVIEWED_WITH_DOCUMENTED_DIFFERENCES')
    if name.startswith('SEVEL_Closures_A5_'):
        rebuilt_closures = checked('closure_rebuild',reports/f'{name}_closure_rebuild.json',
                                  'PASS_CLOSURE_REBUILD')
        assert len(rebuilt_closures['symmetric_difference_mm3'])==6
        assert max(map(abs,rebuilt_closures['symmetric_difference_mm3'].values()))<1e-5
        assert rebuilt_closures['entrypoint_sha256']==sha(ROOT/'cad/sevel16/build_closures_checkpoint.py')
    if name.startswith(('SEVEL_Closures_A5_','SEVEL_Accessories_A5_')):
        closures = checked('closure_captures',reports/f'{name}_closure_captures.json',
                           'REVIEWED_WITH_DOCUMENTED_DIFFERENCES')
        assert closures['restored_theta_deg']==0 and len(closures['images'])==7
        assert (ROOT/closures['review_document']).is_file()
        assert sha(OUTPUT/closures['exploded_model'])==closures['exploded_sha256']
        exploded = closures['exploded_parts']
        assert len(exploded)==len({p['source_part_id'] for p in exploded})==11
        assert all(p['restored_symmetric_difference_mm3']<1e-5 for p in exploded)
        assert {'Block','HeadLower','CamCarrier','ValveCover','OilPan'}.issubset(
            {p['source_object'] for p in exploded})
        for capture in closures['images']:
            path = OUTPUT/capture['path']
            assert sha(path)==capture['sha256']
            assert sha(path.with_suffix('.json'))==capture['metadata_sha256']
    if name.startswith('SEVEL_Accessories_A5_'):
        accessory_rebuild = checked('accessories_rebuild',reports/f'{name}_accessories_rebuild.json',
                                    'PASS_ACCESSORIES_REBUILD')
        deltas = accessory_rebuild['symmetric_difference_mm3']
        assert len(deltas)==20
        sampled = accessory_rebuild['sampled_reconstruction']
        assert {key for key,value in deltas.items() if value is None}==set(sampled)
        assert set(sampled).issubset({'IntakeManifold'})
        assert all(abs(value)<1e-5 for value in deltas.values() if value is not None)
        for row in sampled.values():
            assert row['surface_samples']==row['counts']['Faces']*81
            assert row['edge_samples']>0 and row['linear_tolerance_mm']==1e-7
            assert max(row[k] for k in ('maximum_surface_error_mm','maximum_edge_error_mm',
                'maximum_vertex_error_mm','maximum_parameter_range_error'))<1e-7
            assert row['maximum_face_area_error_mm2']<1e-6 and row['volume_error_mm3']<1e-5
        unchanged = accessory_rebuild['unchanged_parts_symmetric_difference_mm3']
        assert len(unchanged)==198 and max(map(abs,unchanged.values()))<1e-5
        assert accessory_rebuild['entrypoint_sha256']==sha(ROOT/'cad/sevel16/build_accessories_checkpoint.py')
        accessories = checked('accessory_captures',reports/f'{name}_accessory_captures.json',
                              'REVIEWED_WITH_DOCUMENTED_DIFFERENCES')
        assert accessories['restored_theta_deg']==0 and len(accessories['images'])==10
        assert (ROOT/accessories['review_document']).is_file()
        for capture in accessories['images']:
            path = OUTPUT/capture['path']
            assert sha(path)==capture['sha256'] and sha(path.with_suffix('.json'))==capture['metadata_sha256']
    assert captures['restored_theta_deg']==0 and len(captures['images'])==13
    assert (ROOT/captures['review_document']).is_file()
    phases = set()
    for capture in captures['images']:
        path = OUTPUT/capture['path']
        assert sha(path)==capture['sha256']
        assert sha(path.with_suffix('.json'))==capture['metadata_sha256']
        metadata = read(path.with_suffix('.json'))
        assert metadata['document']==name
        if '-pose' in path.name:
            phases.add(metadata['theta_deg'])
    assert phases=={0,90,180,270,359,360,450,540,630,720}
    assert len(dimensions['parts'])==part_count and len({p['id'] for p in dimensions['parts']})==part_count
    assert all(p['valid'] and p['solids']==1 and p['volume_mm3']>0 for p in dimensions['parts'])
    assert dimensions['seal_maximum_boundary_distance_mm']<1e-6
    assert len(valves['valves'])==8 and len(valves['journals'])==5
    assert rebuild['cad_pose_angles_deg']==list(range(0,721,5))
    assert rebuild['baseline_parameters_unchanged'] and rebuild['max_freecad_rod_tip_error_mm']<1e-7
    assert len(rebuild['rebuild_symmetric_difference_mm3'])==13
    assert max(map(abs,rebuild['rebuild_symmetric_difference_mm3'].values()))<1e-5
    assert {r['kind'] for r in rebuild['variants']}=={'stroke','cosmetic'}
    assert all(r['valid'] and r['separate_copy'] for r in rebuild['variants'])
    assert controller['spring_preview_count']==16 and controller['periodic_placement_error']<1e-8
    assert controller['timer_advanced_to_deg']>0 and controller['cleanup_restored_theta_deg']==0
    assert {0,90,180,270,359,360,450,540,630,720}.issubset(controller['tested_theta_deg'])
    assert sections['head_included'] and sections['theta_deg']==90 and sections['restored_theta_deg']==0
    assert {s['label'] for s in sections['sections']}=={'Longitudinal','TransverseC1'}
    for section in sections['sections']:
        assert sha(OUTPUT/section['model'])==section['sha256']
        assert any(p['source_object']=='HeadLower' for p in section['parts'])
        image = Path(section['image'])
        assert image.stat().st_size>0
        metadata = read(image.with_suffix('.json'))
        assert metadata['document']==Path(section['model']).stem and metadata['theta_deg']==90
    step = checked('step',folder/'export_checks.json','PASS','source_fcstd_sha256')
    assert step['solids']==part_count and step['relative_volume_error']<1e-6
    assert step['step_sha256']==sha(folder/'assembly.step')
    meshes = folder/'meshes_v001'
    mesh = checked('meshes',meshes/'mesh_checks.json','PASS_MESH_EXPORT_ONLY')
    renderer = checked('renderer',meshes/'renderer_checks.json','PASS_EXISTING_RECORDING_RENDERER_ONLY',
                       'source_fcstd_sha256')
    manifest = read(meshes/'parts_manifest.json')
    assert sha(meshes/'parts_manifest.json')==renderer['manifest_sha256']
    assert manifest['source_sha256']==digest and len(manifest['parts'])==mesh['parts']==part_count
    if name.startswith(('SEVEL_Casting_A4_','SEVEL_Closures_A5_','SEVEL_Accessories_A5_')):
        assert renderer['parts_with_primitive_materials']==part_count
        assert manifest['material_bindings']=={p['id']:p['material_bindings'] for p in manifest['parts']}
        assert all(set(p['material_bindings'])==set(p['mesh_batches']) for p in manifest['parts'])
        casting_rows = [r for r in mesh['checks'] if r['id'] in
                        ('sevel.block','sevel.headlower','sevel.camcarrier')]
        assert len(casting_rows)==3 and all(set(r['material_triangles'])==
            {'cast_surface','machined_surface'} and min(r['material_triangles'].values())>0 for r in casting_rows)
    assert {p['id'] for p in manifest['parts']}=={p['id'] for p in dimensions['parts']}
    assert renderer['executable_sha256']==sha(OUTPUT/'check_mesh_renderer')
    assert renderer['loader_source_sha256']==sha(ROOT/'third_party/open-engine-sim/src/authored_mesh_library.cpp')
    for value in manifest['meshes'].values():
        assert sha(meshes/value['file'])==value['sha256']
    for filename,value in renderer['pose_inputs_sha256'].items():
        assert sha(meshes/filename)==value
    rendered = {Path(p['pose']).name:p for p in renderer['poses']}
    expected_counts = {'calibration_pose.txt':2,'pose_000.txt':part_count,'pose_090.txt':part_count,
                       'pose_359.txt':part_count,'pose_720.txt':part_count,
                       'pose_000_periodic.txt':part_count-1,'pose_720_periodic.txt':part_count-1}
    assert set(rendered)==set(expected_counts) and len(rendered)==len(renderer['poses'])
    for filename,count in expected_counts.items():
        assert rendered[filename]['parts']==count
        assert rendered[filename]['status']=='PASS_RENDERER_POSE_ONLY'
    assert renderer['independent_period_checks']['sevel.timingtensioner']['matrix_error']<1e-8
    generator = manifest['generator']
    assert generator['parameter_sha256']==parameter_digest
    assert generator['entrypoint_sha256']==sha(ROOT/generator['entrypoint'])
    summary = {k:v for k,v in analytic.items() if k not in ('test_output','pose_samples','pending','status')}
    summary.update(status='PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING',goal_complete=False,
        document=name,source_sha256=digest,datum_sha256=sha(OUTPUT/'datums/reference_frame.json'),
        evidence=evidence,collision_proof_chain=chain,
        inherited_baseline={'path':str(archive.relative_to(OUTPUT)),'sha256':sha(baseline_path),
            'scope':'Unchanged moving parts: bottom collisions and cam contacts inherited through checked B-rep identities'},
        actual_cad_strokes_mm=rebuild['piston_crown_strokes_measured_in_cad_mm'],
        actual_cad_rod_tip_error_mm=rebuild['max_freecad_rod_tip_error_mm'],
        inherited_bottom_brep_tests=baseline.get('inherited_bottom_brep_tests',baseline.get('current_bottom_brep_tests')),
        current_increment_pairs=sum(r.get('pairs_checked',0) for r in chain),
        expected_press_fits=baseline['expected_press_fits'],
        cutaway_evidence=sections['sections'],collision_policy=baseline['collision_policy'],
        validation_code_sha256={p.name:sha(p) for p in sorted((ROOT/'cad/sevel16').glob('*.py'))},
        pending=['Refine block side casting and complete remaining requested visual components',
                 'Package the final checkpoint after remaining visual refinements',
                 'Final requirement-by-requirement delivery audit'],
        limits=baseline['limits']+['Head chambers remain below the manual volume; coolant recesses are blind',
                                 'Native GLB calibration failed; validated STEP/OBJ remain available'])
    if name.startswith('SEVEL_Accessories_A5_'):
        summary['status'] = 'PASS_CURRENT_VISUAL_KINEMATICS'
        summary['pending'] = ['Verify portable delivery and publish final requirement audit']
        summary['completion_record'] = 'reports/final_delivery.json, published only after package verification'
        summary['limits'] += ['Accessory water pump remains static; drive ratio unknown',
            'Intake rebuild uses measured surface/trim equivalence after an OCC Boolean failure']
    if not archive.exists():
        archive.write_bytes(baseline_path.read_bytes())
    assert sha(archive)==summary['inherited_baseline']['sha256']
    target = reports/'kinematics_validation.json'
    if target.exists() and read(target).get('document')!=name:
        previous = read(target)
        previous_name = previous['document']
        assert Path(previous_name).name==previous_name
        history = reports/f'kinematics_validation.{previous_name}.{sha(target)[:12]}.json'
        if not history.exists():
            history.write_bytes(target.read_bytes())
        assert sha(history)==sha(target)
    target.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'status':summary['status'],'document':name,'reports':len(evidence),'stages':len(chain)}))
    return summary


if __name__=='__main__':
    run()
