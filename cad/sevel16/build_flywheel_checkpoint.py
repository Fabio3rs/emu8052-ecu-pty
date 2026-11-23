"""A4 flywheel checkpoint; preserve the saved A3 baseline and all part IDs."""
import hashlib
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT, load
from assembly import add_part, apply_pose
import flywheel


def run():
    params,frame = load()
    source = OUTPUT/'models/SEVEL_ValveTrain_A3_v003.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName==str(source)),None)
    old = old or App.openDocument(str(source))
    assert old.Phase.ThetaDeg==0
    previous = json.loads((OUTPUT/f'reports/{old.Name}.parameters.json').read_text())
    assert {k:params[k] for k in previous}==previous
    index = 1
    while (OUTPUT/f'models/SEVEL_Flywheel_A4_v{index:03d}.FCStd').exists():
        index += 1
    name = f'SEVEL_Flywheel_A4_v{index:03d}'
    parts = flywheel.build(params,frame)
    doc = App.newDocument(name)
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
    for name,shape in parts.items():
        color = (0.49,0.48,0.44) if name=='Flywheel' else (0.32,0.34,0.36)
        add_part(doc,name,shape,'crank',color=color)
    apply_pose(doc,0,params,frame,update_springs=False)
    solids = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(solids)==174 and len({o.PartId for o in solids})==174
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
    report = {'status':'BUILT_FLYWHEEL_VALIDATION_PENDING','document':doc.Name,
              'source_a3':str(source),'source_a3_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'solids':174,'added_parts':list(parts),'mount_face_x_mm':flywheel.mount_x(params,frame),
              'scope':'Flywheel, starter ring and six bolts only; remaining A4 distribution absent',
              'limits':['uncalibrated dimensions and visual teeth',
                        'A3 cage inclinations still pending; inherits provisional valve axes']}
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return doc


if __name__=='__main__':
    run()
