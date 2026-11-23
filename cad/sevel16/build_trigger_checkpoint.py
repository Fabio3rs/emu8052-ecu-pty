"""Versioned pulley/sensor checkpoint; the sole inherited geometry change is the nose."""
import copy
import hashlib
import json
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT, load
from assembly import add_part, apply_pose
import crankshaft
import trigger_parts


def compatible_parameters(params, previous):
    comparison = copy.deepcopy(params)
    before = previous['moving_geometry_estimated']['value']['nose_length_mm']
    assert params['moving_geometry_estimated']['value']['nose_length_mm']>before
    comparison['moving_geometry_estimated']['value']['nose_length_mm'] = before
    assert {k:comparison[k] for k in previous}==previous


def run():
    params,frame = load()
    source = OUTPUT/'models/SEVEL_Timing_A4_v002.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName==str(source)),None)
    old = old or App.openDocument(str(source))
    assert old.Phase.ThetaDeg==0
    previous = json.loads((OUTPUT/f'reports/{old.Name}.parameters.json').read_text())
    compatible_parameters(params,previous)
    index = 1
    while (OUTPUT/f'models/SEVEL_Trigger_A4_v{index:03d}.FCStd').exists():
        index += 1
    parts = trigger_parts.build(params,frame)
    crank,_ = crankshaft.build(params,frame)
    doc = App.newDocument(f'SEVEL_Trigger_A4_v{index:03d}')
    phase = doc.addObject('App::FeaturePython','Phase')
    phase.addProperty('App::PropertyFloat','ThetaDeg','Kinematics')
    phase.addProperty('App::PropertyString','EvidenceStatus','Provenance')
    phase.EvidenceStatus = frame['status']
    for original in old.Objects:
        if not hasattr(original,'Shape'):
            continue
        obj = add_part(doc,original.Name,original.Shape.copy(),original.MotionType,
                       original.CylinderId,original.ViewObject.ShapeColor)
        obj.Placement = original.Placement
        for prop,kind in [('ValveKind','String'),('SpringKind','String'),('RestBase','Vector')]:
            if hasattr(original,prop):
                obj.addProperty('App::Property'+kind,prop,'Assembly')
                setattr(obj,prop,getattr(original,prop))
        obj.ViewObject.Visibility = obj.Name not in ('Block','CamCarrier')
        if obj.Name=='Crankshaft':
            obj.Shape = crank
            obj.Placement = App.Placement()
    for name,(shape,motion) in parts.items():
        color = (0.18,0.20,0.22) if name=='RotationSensor' else (0.48,0.50,0.53)
        add_part(doc,name,shape,motion,color=color)
    apply_pose(doc,0,params,frame,update_springs=False)
    solids = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(solids)==188 and len({o.PartId for o in solids})==188
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in solids)
    App.setActiveDocument(doc.Name)
    Gui.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    path = OUTPUT/f'models/{doc.Name}.FCStd'
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    assert all(o.Shape.isValid() for o in doc.Objects if hasattr(o,'Shape'))
    report = {'status':'BUILT_TRIGGER_CHECKS_PENDING','document':doc.Name,'solids':188,
              'source_baseline':str(source),'source_baseline_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'added_parts':list(parts),
              'changed_inherited_part':'Crankshaft: nose length only, 35 to 52 mm',
              'limits':['60-2 is project-context only; mounting and sensor phase uncalibrated',
                        'sensor bracket and accessory dimensions are estimates; nut threads simplified',
                        'rear auxiliary shaft, accessory belt and water-pump drive pending',
                        'inherits provisional A3 valve and cage inclinations']}
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return doc


if __name__=='__main__':
    run()
