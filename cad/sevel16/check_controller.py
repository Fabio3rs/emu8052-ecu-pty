"""Exercise the actual GUI controller, including deforming spring previews."""
import json
import time
import hashlib
from pathlib import Path
import FreeCADGui as Gui
from config import OUTPUT


def run(controller):
    doc = controller.doc
    original_ids = {o.PartId for o in doc.Objects if hasattr(o,'PartId')}
    original_solids = len([o for o in doc.Objects if hasattr(o,'Shape')])
    own_periods = set()
    timing = controller.params.get('timing_visual_estimated',{}).get('value')
    if timing:
        if abs((720*timing['crank_teeth']/timing['aux_teeth'])%360)>1e-9:
            own_periods.add('aux')
        # A smooth idler has its own angular period, determined by its radius.
        own_periods.add('tensioner')
    poses,times = {},[]
    for theta in (0,90,180,270,359,360,450,540,630,720,90):
        start = time.monotonic()
        controller.set_phase(theta)
        times.append(time.monotonic()-start)
        placement = {o.Name:list(o.Placement.toMatrix().A) for o in doc.Objects if hasattr(o,'MotionType')}
        assert doc.Phase.ThetaDeg==theta
        assert all(p.Mesh.isSolid() and p.Mesh.CountFacets>0 for p in controller.previews)
        for spring,preview in zip(controller.springs,controller.previews):
            assert not spring.Visibility
            lower = doc.getObject(spring.Name.removesuffix('Spring')+'SpringSeat').Shape.BoundBox.ZMax
            retainer_name = spring.Name.rsplit('_',1)[0]+'_Retainer'
            upper = doc.getObject(retainer_name).Shape.BoundBox.ZMin
            assert preview.Mesh.BoundBox.ZMin>=lower-1e-7
            assert preview.Mesh.BoundBox.ZMax<=upper+1e-7
        if theta in poses:
            assert placement==poses[theta], 'Repeated absolute phase drifted'
        poses[theta] = placement
    separate = [o.Name for o in doc.Objects if getattr(o,'MotionType','fixed') in own_periods]
    maximum = max(abs(a-b) for name,row in poses[0].items() if name not in separate
                  for a,b in zip(row,poses[720][name]))
    assert maximum<1e-8
    controller.set_phase(0)
    controller.play.setChecked(True)
    until = time.monotonic()+0.6
    while time.monotonic()<until:
        Gui.updateGui()
        time.sleep(0.01)
    controller.play.setChecked(False)
    animated_theta = doc.Phase.ThetaDeg
    assert 0<animated_theta<90
    controller.close()
    Gui.updateGui()
    assert len([o for o in doc.Objects if hasattr(o,'Shape')])==original_solids
    assert {o.PartId for o in doc.Objects if hasattr(o,'PartId')}==original_ids
    assert not any(o.Name.endswith('_AnimationPreview') for o in doc.Objects)
    assert doc.Phase.ThetaDeg==controller.initial_theta
    report = {'status':'PASS_FREECAD_CONTROLLER_ONLY','document':doc.Name,
              'source_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
              'parameter_sha256':hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest(),
              'tested_theta_deg':list(poses),'periodic_placement_error':maximum,
              'max_pose_update_seconds':max(times),'timer_advanced_to_deg':animated_theta,
              'spring_preview_count':16,'solid_meshes':True,
              'parts_with_independent_angular_period':separate,
              'cleanup_restored_theta_deg':doc.Phase.ThetaDeg,
              'limits':'FreeCAD preview only; repository viewer integration remains pending'}
    (OUTPUT/f'reports/{doc.Name}_controller.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
