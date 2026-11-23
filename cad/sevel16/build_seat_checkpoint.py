"""Close the lower-seat support gap while preserving all motion and source IDs."""
import json
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT, load
from assembly import add_part
from check_auxiliary import difference, sha
from valvetrain_layout import valves
import valve_parts


def generate(params,frame):
    replacements = {}
    for row in valves(params,frame):
        shape = valve_parts.build(params,row)['InnerSpringSeat'][0]
        shape.translate(App.Vector(*row['axis_origin_mm'][:2],0))
        replacements[row['id']+'_InnerSpringSeat'] = shape
    return replacements


def run(baseline,replacements,verification,params):
    current,frame = load()
    assert current==params and baseline.Name=='SEVEL_Head_A3_v001'
    assert baseline.Phase.ThetaDeg==0
    prior = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:params[k] for k in prior}==prior
    proof_path = OUTPUT/f'reports/{baseline.Name}_head_validation.json'
    proof = json.loads(proof_path.read_text())
    assert proof['status']=='PASS_HEAD_INCREMENT_GEOMETRY'
    assert proof['source_sha256']==sha(baseline.FileName)
    assert verification['status']=='PASS_STEPPED_SPRING_SEATS' and verification['pairs_checked']==1500
    rebuilt = generate(params,frame)
    assert all(difference(s,replacements[n])<1e-5 for n,s in rebuilt.items())
    index = 1
    while (OUTPUT/f'models/SEVEL_Head_A3_v{index:03d}.FCStd').exists():
        index += 1
    doc = App.newDocument(f'SEVEL_Head_A3_v{index:03d}')
    phase = doc.addObject('App::FeaturePython','Phase')
    phase.addProperty('App::PropertyFloat','ThetaDeg','Kinematics')
    phase.addProperty('App::PropertyString','EvidenceStatus','Provenance')
    phase.EvidenceStatus = frame['status']
    for old in baseline.Objects:
        if not hasattr(old,'Shape'):
            continue
        shape = replacements.get(old.Name,old.Shape).copy()
        obj = add_part(doc,old.Name,shape,old.MotionType,old.CylinderId,old.ViewObject.ShapeColor)
        obj.Placement,obj.Label = old.Placement,old.Label
        for prop,kind in [('ValveKind','String'),('SpringKind','String'),('RestBase','Vector')]:
            if hasattr(old,prop):
                obj.addProperty('App::Property'+kind,prop,'Assembly')
                setattr(obj,prop,getattr(old,prop))
        if old.Name in replacements:
            obj.Label = old.Name+' — upper region of stepped lower spring seat'
    doc.recompute()
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(objects)==192 and len({o.PartId for o in objects})==192
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in objects)
    path = OUTPUT/f'models/{doc.Name}.FCStd'
    doc.saveAs(str(path)); App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    unchanged = {}
    for old in baseline.Objects:
        if not hasattr(old,'Shape'):
            continue
        obj = doc.getObject(old.Name)
        assert obj.Shape.isValid() and len(obj.Shape.Solids)==1
        for prop in ('PartId','MotionType','CylinderId','ValveKind','SpringKind','RestBase'):
            assert getattr(obj,prop,None)==getattr(old,prop,None),(old.Name,prop)
        if old.Name not in replacements:
            unchanged[old.Name] = difference(old.Shape,obj.Shape)
        else:
            assert difference(rebuilt[old.Name],obj.Shape)<1e-5
    assert len(unchanged)==184 and max(unchanged.values())<1e-5
    report = dict(verification,source_sha256=sha(path),baseline_sha256=sha(baseline.FileName),
                  baseline_proof_sha256=sha(proof_path),parameter_sha256=sha(OUTPUT/'parameters.json'),
                  datum_sha256=sha(OUTPUT/'datums/reference_frame.json'),changed_parts=list(replacements),
                  unchanged_parts_symmetric_difference_mm3=unchanged,rebuild_verified=True,goal_complete=False)
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}_seat_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    App.setActiveDocument(doc.Name); Gui.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric(); Gui.activeDocument().activeView().fitAll()
    print(doc.Name,'192 valid solids; 184 unchanged; eight lower seats supported')
    return doc,report
