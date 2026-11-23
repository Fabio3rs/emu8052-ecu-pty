"""Add the lower head and two gaskets without replacing inherited components."""
import json
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT, load
from assembly import add_part
from check_auxiliary import sha, difference
import head_blank
import head_passages
import head_gaskets


def generate(params,frame):
    blank = head_blank.build(params,frame)
    body,metrics = head_passages.finish(blank,params,frame)
    return {'HeadLower':body,**head_gaskets.build(blank,params,frame)},metrics


def run(baseline,shapes,metrics,verification,interfaces,params):
    current,frame = load()
    assert params==current and baseline.Name=='SEVEL_Carrier_A3_v001'
    assert baseline.Phase.ThetaDeg==0
    baseline_proof = OUTPUT/'reports/kinematics_validation.json'
    baseline_report = json.loads(baseline_proof.read_text())
    if baseline_report['document']!=baseline.Name:
        inherited = baseline_report['inherited_baseline']
        baseline_proof = OUTPUT/inherited['path']
        assert sha(baseline_proof)==inherited['sha256']
        baseline_report = json.loads(baseline_proof.read_text())
    assert baseline_report['document']==baseline.Name
    assert baseline_report['source_sha256']==sha(baseline.FileName)
    prior = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:params[k] for k in prior}==prior
    assert verification['status']=='PASS_HEAD_INCREMENT_GEOMETRY'
    assert verification['pairs_checked']==570 and not verification['failures']
    assert interfaces['status']=='PASS_CONTACTS_AND_SEPARATE_VISUAL_PASSAGES_WITH_KNOWN_GAPS'
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
        obj = add_part(doc,old.Name,old.Shape.copy(),old.MotionType,old.CylinderId,old.ViewObject.ShapeColor)
        obj.Placement,obj.Label = old.Placement,old.Label
        for prop,kind in [('ValveKind','String'),('SpringKind','String'),('RestBase','Vector')]:
            if hasattr(old,prop):
                obj.addProperty('App::Property'+kind,prop,'Assembly')
                setattr(obj,prop,getattr(old,prop))
    for name,shape in shapes.items():
        add_part(doc,name,shape,color=(.72,.73,.75) if name=='HeadLower' else (.2,.21,.23))
    doc.recompute()
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(objects)==192 and len({o.PartId for o in objects})==192
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in objects)
    path = OUTPUT/f'models/{doc.Name}.FCStd'
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in doc.Objects if hasattr(o,'Shape'))
    unchanged = {o.Name:difference(o.Shape,doc.getObject(o.Name).Shape)
                 for o in baseline.Objects if hasattr(o,'Shape')}
    assert len(unchanged)==189 and max(unchanged.values())<1e-5
    assert all(difference(s,doc.getObject(n).Shape)<1e-5 for n,s in shapes.items())
    for name in unchanged:
        a,b = baseline.getObject(name),doc.getObject(name)
        for prop in ('PartId','MotionType','CylinderId','ValveKind','SpringKind','RestBase'):
            assert getattr(a,prop,None)==getattr(b,prop,None),(name,prop)
    report = dict(verification,source_sha256=sha(path),baseline_sha256=sha(baseline.FileName),
                  parameter_sha256=sha(OUTPUT/'parameters.json'),datum_sha256=sha(OUTPUT/'datums/reference_frame.json'),
                  unchanged_parts_symmetric_difference_mm3=unchanged,added_parts=list(shapes),
                  chamber_metrics=metrics,interfaces=interfaces,geometry_is_provisional=True,goal_complete=False)
    report['baseline_proof_sha256'] = sha(baseline_proof)
    report['baseline_proof_scope'] = 'Consolidated report for Carrier v001; no claim that it validates new casting geometry'
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}_head_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    App.setActiveDocument(doc.Name); Gui.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric(); Gui.activeDocument().activeView().fitAll()
    print(doc.Name,'192 valid solids; 189 inherited shapes unchanged')
    return doc,report
