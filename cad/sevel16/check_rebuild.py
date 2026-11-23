"""Rebuild, perturb structural/cosmetic inputs in copies, and verify CAD placements."""
import copy
import hashlib
import json
from pathlib import Path
import FreeCAD as App
import Part
from config import OUTPUT, load, layout
from assembly import apply_pose
import crankshaft
import piston
import connecting_rod


def run(doc, report_path=None):
    params,frame = load()
    original_hash = hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest()
    rebuilt = {'Crankshaft':crankshaft.build(params,frame)[0]}
    rebuilt.update({'C1_'+k:v for k,v in piston.build(params,frame).items()})
    rebuilt.update({'C1_'+k:v for k,v in connecting_rod.build(params,frame).items()})
    errors = {}
    for name, shape in rebuilt.items():
        saved = doc.getObject(name).Shape.copy()
        saved.Placement = App.Placement()
        delta = shape.cut(saved).Volume+saved.cut(shape).Volume
        assert abs(delta)<1e-5,(name,delta)
        errors[name] = delta
    variations = []
    for kind in ('stroke','cosmetic'):
        p = copy.deepcopy(params)
        if kind=='stroke':
            p['dimensions']['stroke_mm']['value'] = 70
        else:
            p['moving_geometry_estimated']['value']['counterweight_half_angle_deg'] = 48
        crank,_ = crankshaft.build(p,frame)
        pistons = piston.build(p,frame)
        assert crank.isValid() and len(crank.Solids)==1
        assert abs(crank.Volume-rebuilt['Crankshaft'].Volume)>1
        if kind=='stroke':
            r = p['moving_nominal']['crankpin_diameter_mm']['value']/2
            surfaces = [f.Surface for f in crank.Faces if isinstance(f.Surface,Part.Cylinder)
                        and abs(f.Surface.Radius-r)<1e-7]
            assert len(surfaces)==4
            assert all(abs((s.Center.y**2+s.Center.z**2)**0.5-35)<1e-7 for s in surfaces)
            assert abs(pistons['Piston'].BoundBox.ZMax-layout(p,frame)['compression_height'])<1e-7
        variations.append({'kind':kind,'crank_volume_mm3':crank.Volume,
                           'compression_height_mm':layout(p,frame)['compression_height'],
                           'valid':True,'separate_copy':True})
    maximum_tip_error = 0
    crowns = [[] for _ in range(4)]
    original_theta = doc.Phase.ThetaDeg
    length = params['moving_geometry_estimated']['value']['rod_length_mm']
    try:
        for theta in range(0,721,5):
            state = apply_pose(doc,theta,params,frame,update_springs=False)
            for c in state['cylinders']:
                obj = doc.getObject(f'C{c["cylinder"]}_Rod')
                tip = obj.Placement.multVec(App.Vector(0,0,length))
                error = (tip-App.Vector(*c['piston_pin_mm'])).Length
                assert error<1e-7
                maximum_tip_error = max(maximum_tip_error,error)
                crown = doc.getObject(f'C{c["cylinder"]}_Piston').Shape.BoundBox.ZMax
                assert abs(crown-c['crown_z_mm'])<1e-7
                crowns[c['cylinder']-1].append(crown)
    finally:
        apply_pose(doc,original_theta,params,frame)
    assert original_hash==hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest()
    strokes = [max(values)-min(values) for values in crowns]
    assert all(abs(stroke-params['dimensions']['stroke_mm']['value'])<1e-7 for stroke in strokes)
    report = {'status':'PASS','document':doc.Name,'parameter_sha256':original_hash,
              'source_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
              'rebuild_symmetric_difference_mm3':errors,'variants':variations,
              'cad_pose_angles_deg':list(range(0,721,5)),
              'max_freecad_rod_tip_error_mm':maximum_tip_error,
              'piston_crown_strokes_measured_in_cad_mm':strokes,
              'baseline_parameters_unchanged':True,
              'scope':'Bottom-end prototype rebuilds and actual FreeCAD placements; spring deformation and upper assemblies checked separately'}
    target = Path(report_path) if report_path else OUTPUT/f'reports/{doc.Name}_rebuild.json'
    if report_path:
        assert not target.exists(), 'Preserve previous relocation evidence'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cad_pose_angles_deg'}))
    return report
