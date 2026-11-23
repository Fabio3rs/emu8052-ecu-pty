"""Persist distribution and assembled poses using the actual CAD spring geometry."""
import FreeCAD as App
import FreeCADGui as Gui
import json
from pathlib import Path
from config import OUTPUT, load
from proof_chain import sha
from assembly import apply_pose
from capture_checkpoint import save

TIMING_PARTS = {'CamSprocket','CrankSprocket','AuxSprocket','AuxiliaryFrontShaft',
                'AuxiliaryFrontBush','AuxiliaryRearBush','TimingTensioner','TimingTensionerSupport','TimingBelt'}


def run(doc):
    params,frame = load()
    assert doc.Phase.ThetaDeg==0
    App.setActiveDocument(doc.Name)
    Gui.setActiveDocument(doc.Name)
    visible = {o.Name:o.ViewObject.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    paths = []
    try:
        for o in doc.Objects:
            if hasattr(o,'Shape'):
                o.ViewObject.Visibility=(o.Name not in (
                    'Block','CamCarrier','HeadLower','HeadGasket','CarrierGasket',
                    'ValveCover','ValveCoverGasket','OilFillerCap',
                    'OilPan','OilPanGasket','OilDrainPlug')
                    and 'Spark' not in o.Name and 'Manifold' not in o.Name
                    and not o.Name.startswith('WaterPump'))
        for theta in (0,90,180,270,359,360,450,540,630,720):
            apply_pose(doc,theta,params,frame)
            note = ('Timing and moving assembly; auxiliary rear journal pending'
                    if doc.getObject('TriggerWheel') else
                    'Timing and moving assembly; auxiliary rear journal and trigger wheel pending')
            if doc.getObject('AuxiliaryRearBush'):
                note = 'Timing and complete auxiliary shaft; provisional axial dimensions and gear profile'
            paths.append(save(doc,'Isometric',doc.Name+f'-pose{theta:03d}',theta,
                              note))
        apply_pose(doc,0,params,frame)
        for o in doc.Objects:
            if hasattr(o,'Shape'):
                o.ViewObject.Visibility=o.Name in TIMING_PARTS
        for view in ('Left','Isometric'):
            paths.append(save(doc,view,doc.Name+'-distribution',0,
                              'External timing; smooth belt, provisional teeth and axial offsets'))
        for o in doc.Objects:
            if hasattr(o,'Shape'):
                o.ViewObject.Visibility=True
        paths.append(save(doc,'Isometric',doc.Name+'-external',0,
                          'Current casting and timing; lower head '+
                          ('included' if doc.getObject('HeadLower') else 'absent')))
    finally:
        apply_pose(doc,0,params,frame)
        for name,state in visible.items():
            doc.getObject(name).ViewObject.Visibility=state
    report = {'status':'CAPTURED_AWAITING_VISUAL_REVIEW','document':doc.Name,
              'source_sha256':sha(Path(doc.FileName)),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'restored_theta_deg':doc.Phase.ThetaDeg,
              'images':[{'path':str(Path(p).relative_to(OUTPUT)),'sha256':sha(Path(p)),
                         'metadata_sha256':sha(Path(p).with_suffix('.json'))} for p in paths]}
    (OUTPUT/f'reports/{doc.Name}_cycle_captures.json').write_text(json.dumps(report,indent=2)+'\n')
    print('\n'.join(paths))
    return paths
