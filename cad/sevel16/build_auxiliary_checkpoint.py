"""Extend the auxiliary shaft and provide its second supported journal in a new CAD."""
import hashlib
import json
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT, load
from assembly import add_part, apply_pose
import auxiliary


def run():
    params,frame = load()
    source = OUTPUT/'models/SEVEL_Trigger_A4_v001.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName==str(source)),None)
    old = old or App.openDocument(str(source))
    assert old.Phase.ThetaDeg==0
    previous = json.loads((OUTPUT/f'reports/{old.Name}.parameters.json').read_text())
    assert {k:params[k] for k in previous}==previous
    front = old.AuxiliaryFrontShaft.Shape.copy()
    front.Placement = App.Placement()
    shaft,bush,envelope = auxiliary.build(params,front)
    housing,cutter = auxiliary.casting_tools(params)
    # Keep the Boolean result's splits: refining these intersecting seat faces
    # made the old-minus-new comparison fail in OCCT although isValid() passed.
    block = old.Block.Shape.fuse(housing).cut(cutter)
    assert block.isValid() and len(block.Solids)==1
    assert old.Block.Shape.cut(block).isValid()
    index = 1
    while (OUTPUT/f'models/SEVEL_Auxiliary_A4_v{index:03d}.FCStd').exists():
        index += 1
    doc = App.newDocument(f'SEVEL_Auxiliary_A4_v{index:03d}')
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
        if obj.Name=='AuxiliaryFrontShaft':
            obj.Shape = shaft
            obj.Placement = App.Placement()
            obj.Label = 'Auxiliary shaft — both journals, eccentric and visual gear'
        elif obj.Name=='Block':
            obj.Shape = block
    p = params['casting_visual_estimated']['value']
    obj = add_part(doc,'AuxiliaryRearBush',bush,color=(.66,.55,.30))
    obj.Placement.Base = App.Vector(0,p['aux_y'],p['aux_z'])
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
    report = {'status':'BUILT_AUXILIARY_CHECKS_PENDING','document':doc.Name,'solids':189,
              'source_baseline':str(source),'source_baseline_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'changed_parts':['Block','AuxiliaryFrontShaft'],'added_parts':['AuxiliaryRearBush'],
              'limits':['Axial dimensions and twisted gear profile are estimates',
                        'No mating oil-pump gear or functional gear-contact validation',
                        'Inherited cage/head inclinations and broad block contour remain provisional']}
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return doc


if __name__=='__main__':
    run()
