"""Persist the reproducible 720-degree analytic checkpoint, without claiming CAD completion."""
import hashlib
import json
import math
import subprocess
import sys
from config import ROOT, OUTPUT, load, layout
from kinematics import pose, transform_rod_point, COMPRESSION_TDC
from cam_profile import support


def run(report_name='kinematics_analytic.json'):
    result = subprocess.run([sys.executable,'-m','unittest','discover','-s','cad/sevel16',
                             '-p','test_*.py','-v'],cwd=ROOT,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    params,frame = load()
    angles = set(range(0,721,5)) | {0.001,179.999,180.001,359.999,719.999}
    for event in (143,353,365,575,254,464):
        for phase in (0,180,360,540):
            for delta in (-0.001,0,0.001):
                angles.add((event+phase+delta)%720)
    poses = [pose(a,params,frame) for a in sorted(angles)]
    length = params['moving_geometry_estimated']['value']['rod_length_mm']
    errors = [math.dist(transform_rod_point([0,0,length],c),c['piston_pin_mm'])
              for state in poses for c in state['cylinders']]
    strokes = [max(s['cylinders'][i]['crown_z_mm'] for s in poses)-
               min(s['cylinders'][i]['crown_z_mm'] for s in poses) for i in range(4)]
    rod_length_error = max(abs(math.dist(c['crankpin_mm'],c['piston_pin_mm'])-length)
                           for s in poses for c in s['cylinders'])
    pair_error = max(abs(s['cylinders'][i]['crown_z_mm']-s['cylinders'][j]['crown_z_mm'])
                     for s in poses for i,j in ((0,3),(1,2)))
    periodic_error = 0.0
    for s in poses:
        half,full = pose(s['theta_deg']+360,params,frame),pose(s['theta_deg']+720,params,frame)
        for i,c in enumerate(s['cylinders']):
            for key in ('crankpin_mm','piston_pin_mm'):
                periodic_error = max(periodic_error,math.dist(c[key],half['cylinders'][i][key]))
            for key,value in c['valve_lifts_mm'].items():
                periodic_error = max(periodic_error,abs(value-full['cylinders'][i]['valve_lifts_mm'][key]))
    phase = params['cam_profile_estimated']['value']['global_phase_deg']
    angular_error = lambda a,b: abs((a-b+180)%360-180)
    cam_error = max(angular_error(s['cam_rx_deg'],s['theta_deg']/2+phase) for s in poses)
    timing = params['timing_visual_estimated']['value']
    aux_ratio = timing['crank_teeth']/timing['aux_teeth']
    aux_error = max(angular_error(s['timing_rx_deg']['aux'],
                                 s['theta_deg']*aux_ratio+timing['aux_phase_deg']) for s in poses)
    limits = {}
    for kind in ('intake','exhaust'):
        values = [c['valve_lifts_mm'][kind] for s in poses for c in s['cylinders']]
        nominal = params['valve_timing_nominal']['value']
        limits[kind] = {'minimum_mm':min(values),'maximum_mm':max(values),
                        'maximum_allowed_mm':nominal['cam_height_mm']-nominal[kind+'_lash_mm']}
        assert min(values)>=0 and max(values)<=limits[kind]['maximum_allowed_mm']+1e-10
    assert max(errors)<1e-7 and rod_length_error<1e-7 and pair_error<1e-7
    assert periodic_error<1e-7 and cam_error<1e-9 and aux_error<1e-9
    assert all(abs(s-params['dimensions']['stroke_mm']['value'])<1e-7 for s in strokes)
    cam = [support(math.radians(i/10),params) for i in range(3600)]
    report = {'status':'PARTIAL_PASS_ANALYTIC_ONLY','reference_status':frame['status'],
              'parameter_sha256':hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest(),
              'unit':'mm, crank degrees; cam support derivatives per cam radian',
              'test_command':'python -m unittest discover -s cad/sevel16 -p test_*.py -v',
              'test_output':result.stdout+result.stderr,
              'maximum_rod_tip_error_mm':max(errors),
              'piston_strokes_mm':strokes,'maximum_rod_length_error_mm':rod_length_error,
              'maximum_paired_crown_error_mm':pair_error,
              'maximum_360_bottom_720_valve_periodicity_error_mm':periodic_error,
              'cam_ratio_to_crank':0.5,'maximum_cam_ratio_error_deg':cam_error,
              'auxiliary_ratio_to_crank':aux_ratio,'maximum_auxiliary_ratio_error_deg':aux_error,
              'valve_lift_limits':limits,'compression_tdc_deg_by_cylinder':list(COMPRESSION_TDC),
              'firing_order':[i+1 for i in sorted(range(4),key=lambda i:COMPRESSION_TDC[i])],
              'height_closure':layout(params,frame),
              'cam_minimum_curvature_radius_mm':min(h+ddh for h,dh,ddh in cam),
              'cam_maximum_flat_contact_offset_mm':max(abs(dh) for h,dh,ddh in cam),
              'pose_samples':poses,
              'pending':['CAD collisions and exports are proven only by their separate reports'],
              'warning':'Synthetic cam is not the measured OEM profile; geometric software tolerances are not manufacturing tolerances.'}
    # Keep analytic evidence separate from the combined CAD validation report.
    (OUTPUT/'reports'/report_name).write_text(json.dumps(report,indent=2)+'\n')
    (OUTPUT/'reports/analytic_tests.txt').write_text(result.stdout+result.stderr)
    print(json.dumps({k:v for k,v in report.items() if k not in ('pose_samples','test_output')}))
    return poses


if __name__=='__main__':
    run()
