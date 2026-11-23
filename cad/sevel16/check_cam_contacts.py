"""Measure flat-follower contact using sections of the final fused cam B-rep."""
import json
import math
import hashlib
from pathlib import Path
import FreeCAD as App
from assembly import apply_pose
from cam_profile import support
from config import OUTPUT, load
from kinematics import COMPRESSION_TDC
from valvetrain_layout import valves


def angles(params):
    samples = set(range(0,721,5))
    timing = params['valve_timing_nominal']['value']
    phase = 2*params['cam_profile_estimated']['value']['global_phase_deg']
    for tdc in COMPRESSION_TDC:
        for kind in ('intake','exhaust'):
            opening,closing = timing[kind+'_events_deg']
            for local in (opening,closing,(opening+closing)/2,0,180,360,540):
                for delta in (-0.001,0,0.001):
                    samples.add((tdc+local-phase+delta)%720)
    return sorted(samples)


def run(doc):
    params,frame = load()
    rows = valves(params,frame)
    cam = doc.Camshaft.Shape.copy()
    cam.Placement = App.Placement()
    sections = {}
    for row in rows:
        wires = cam.slice(App.Vector(1,0,0),row['axis_origin_mm'][0])
        assert len(wires)==1, (row['id'],len(wires))
        sections[row['id']] = [v.Point for v in wires[0].Vertexes]
        assert len(sections[row['id']])>100
    original_theta = doc.Phase.ThetaDeg
    report = {'scope':'Fused cam sections and actual shim/valve placements; no full collision proof',
              'document':doc.Name, 'profile_tolerance_mm':0.01,
              'source_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
              'parameter_sha256':hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest(),
              'max_support_error_mm':0, 'max_active_contact_gap_mm':0,
              'min_contact_margin_mm':1e9, 'measurements':0, 'angles':angles(params)}
    timing = params['valve_timing_nominal']['value']
    cam_z = params['valvetrain_layout_estimated']['value']['cam_axis_z_mm']
    base = params['cam_profile_estimated']['value']['base_radius_mm']
    try:
        for theta in report['angles']:
            state = apply_pose(doc,theta,params,frame,update_springs=False)
            for row in rows:
                points = [doc.Camshaft.Placement.multVec(v) for v in sections[row['id']]]
                contact = min(points,key=lambda v:v.z)
                cylinder = state['cylinders'][row['cylinder']-1]
                phase = 2*params['cam_profile_estimated']['value']['global_phase_deg']
                alpha = math.radians((cylinder['cycle_deg']+phase-row['peak_local_crank_deg'])/2)
                h,_,_ = support(alpha,params)
                error = abs(cam_z-contact.z-h)
                assert error<0.01, (theta,row['id'],error)
                report['max_support_error_mm'] = max(report['max_support_error_mm'],error)
                shim = doc.getObject(row['id']+'_Shim')
                valve = doc.getObject(row['id']+'_Valve')
                lift = cylinder['valve_lifts_mm'][row['kind']]
                gap = contact.z-shim.Shape.BoundBox.ZMax
                expected_gap = max(0,timing[row['kind']+'_lash_mm']-(h-base))
                assert -1e-6<=gap and abs(gap-expected_gap)<0.01,(theta,row['id'],gap)
                assert abs(valve.Shape.BoundBox.ZMin-(row['axis_origin_mm'][2]-lift))<1e-6
                if lift>0:
                    radius = params['valvetrain_layout_estimated']['value']['shim_diameter_mm']/2
                    margin = radius-abs(contact.y-row['axis_origin_mm'][1])
                    assert margin>0,(theta,row['id'],margin)
                    report['min_contact_margin_mm'] = min(report['min_contact_margin_mm'],margin)
                    report['max_active_contact_gap_mm'] = max(report['max_active_contact_gap_mm'],gap)
                report['measurements'] += 1
    finally:
        apply_pose(doc,original_theta,params,frame)
    report['status'] = 'PASS_CAM_CONTACT_ONLY'
    assert report['source_sha256']==hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest()
    (OUTPUT/f'reports/{doc.Name}_cam_contact.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
