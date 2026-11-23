"""Version a casting-only revision while preserving every moving component and datum."""
import hashlib
import json
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT, load
from assembly import add_part, apply_pose
import inclined_carrier


def run():
    params,frame = load()
    source = OUTPUT/'models/SEVEL_Auxiliary_A4_v002.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName==str(source)),None)
    old = old or App.openDocument(str(source))
    assert old.Phase.ThetaDeg==0
    previous = json.loads((OUTPUT/f'reports/{old.Name}.parameters.json').read_text())
    assert {k:params[k] for k in previous}==previous
    cage = inclined_carrier.build(params,frame)
    index = 1
    while (OUTPUT/f'models/SEVEL_Carrier_A3_v{index:03d}.FCStd').exists():
        index += 1
    doc = App.newDocument(f'SEVEL_Carrier_A3_v{index:03d}')
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
        obj.Label = original.Label
        for prop,kind in [('ValveKind','String'),('SpringKind','String'),('RestBase','Vector')]:
            if hasattr(original,prop):
                obj.addProperty('App::Property'+kind,prop,'Assembly')
                setattr(obj,prop,getattr(original,prop))
        obj.ViewObject.Visibility = obj.Name!='Block'
        if obj.Name=='CamCarrier':
            obj.Shape = cage
    apply_pose(doc,0,params,frame,update_springs=False)
    solids = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(solids)==189 and len({o.PartId for o in solids})==189
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
    report = {'status':'BUILT_CARRIER_CHECKS_PENDING','document':doc.Name,'solids':189,
              'source_baseline':str(source),'source_baseline_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'changed_parts':['CamCarrier'],'added_parts':[],
              'limits':['Casting plane angles and scallop side are provisional',
                        'Valve axes are not inferred from casting-plane slopes',
                        'Head lower body and broad block curvature remain to reconcile']}
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return doc


if __name__=='__main__':
    run()
