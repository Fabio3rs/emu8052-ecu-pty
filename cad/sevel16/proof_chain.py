"""Audit saved CAD identity and the scope of each incremental collision proof."""
import hashlib
import json
from config import OUTPUT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


STAGES = [
    ('SEVEL_ValveTrain_A3_v002','valvetrain_cycle','PASS_A3_COLLISIONS',None,None,None),
    ('SEVEL_ValveTrain_A3_v003','carrier_change','PASS_CARRIER_CHANGE_CONTINUOUS_ENVELOPES',165,
     'added_against_full_cycle_envelopes_mm3',9),
    ('SEVEL_Flywheel_A4_v001','flywheel_validation','PASS_FLYWHEEL_INCREMENT_CONTINUOUS_CLEARANCE',166,
     'rigid_group_pair_intersections_mm3',36),
    ('SEVEL_Timing_A4_v002','timing_validation','PASS_EXTERNAL_TIMING_INCREMENT',174,
     'continuous_envelope_pairs_mm3',64),
    ('SEVEL_Trigger_A4_v001','trigger_validation','PASS_TRIGGER_INCREMENT',181,
     'continuous_envelope_pairs_mm3',36),
    ('SEVEL_Auxiliary_A4_v002','auxiliary_validation','PASS_AUXILIARY_INCREMENT',186,None,None),
    ('SEVEL_Carrier_A3_v001','carrier_validation','PASS_INCLINED_CARRIER_INCREMENT',188,
     'full_cycle_envelope_intersections_mm3',98)]


def run(params):
    rows,previous = [],None
    for name,suffix,status,count,field,pair_count in STAGES:
        path = OUTPUT/f'reports/{name}_{suffix}.json'
        model = OUTPUT/f'models/{name}.FCStd'
        report = read(path)
        assert report['status']==status and report['source_sha256']==sha(model),name
        snapshot_path = OUTPUT/f'reports/{name}.parameters.json'
        snapshot = read(snapshot_path)
        for key,value in snapshot.items():
            if key=='moving_geometry_estimated':
                # The documented trigger increment extends only the crank nose.
                old,new = value['value'],params[key]['value']
                assert {k:v for k,v in old.items() if k!='nose_length_mm'}=={
                    k:v for k,v in new.items() if k!='nose_length_mm'}
                assert old['nose_length_mm'] in (35,52) and new['nose_length_mm']==52
            else:
                assert value==params[key],(name,key,'changed inherited input')
        if previous:
            key = 'baseline_cycle_report_sha256' if suffix=='carrier_change' else 'baseline_proof_sha256'
            assert report[key]==previous['report_sha256'],(name,'broken proof link')
            if 'baseline_sha256' in report:
                assert report['baseline_sha256']==previous['model_sha256']
            differences = report['unchanged_parts_symmetric_difference_mm3']
            assert len(differences)==count and max(map(abs,differences.values()))<1e-5
        if field:
            values = report[field]
            assert len(values)==pair_count and max(map(abs,values.values()))<1e-5
        if suffix=='valvetrain_cycle':
            assert not report['collisions'] and report['completed_angles']==report['target_angles']
            assert len(report['target_angles'])==220
            assert set(range(0,721,5)).issubset(report['target_angles'])
        if suffix=='auxiliary_validation':
            assert len(report['angles_deg'])==220 and len(report['pair_coverage'])==363
            assert min(report['continuous_auxiliary_gaps_mm'].values())>0
            assert min(report['continuous_upper_stack_z_separation_mm'].values())>0
            assert abs(report['rear_bush_block_overlap_mm3'])<1e-5
        if suffix=='carrier_validation':
            assert len(report['continuous_separations'])+pair_count==188
            assert all(r.get('gap_mm',r.get('full_cycle_x_gap_mm',0))>0
                       for r in report['continuous_separations'].values())
        row = {'document':name,'status':status,'report':str(path.relative_to(OUTPUT)),
               'report_sha256':sha(path),'model_sha256':sha(model),
               'parameter_snapshot_sha256':sha(snapshot_path),
               'parameter_comparison':'Parsed snapshots; historical raw parameter-file formatting not reconstructed',
               'unchanged_parts':count,'scope':report.get('scope',report.get('collision_scope')),
               'limits':report.get('limits',[])}
        rows.append(row)
        previous = row
    return rows
