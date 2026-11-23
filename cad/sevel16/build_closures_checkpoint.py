"""Integrate validated external closures while preserving every inherited part."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import ROOT, OUTPUT, load
from proof_chain import read, sha
from check_auxiliary import difference
from assembly import add_part
import valve_cover
import oil_pan


def baseline_proof(trial,source):
    path = OUTPUT/'reports/kinematics_validation.json'
    if sha(path)!=trial['baseline_proof_sha256']:
        path = OUTPUT/'reports'/(
            f'kinematics_validation.{source.stem}.{trial["baseline_proof_sha256"][:12]}.json')
    assert sha(path)==trial['baseline_proof_sha256']
    proof = read(path)
    assert proof['document']==source.stem and proof['source_sha256']==sha(source)
    return path


def run(folder):
    folder = Path(folder)
    trial = read(folder/'validation.json')
    assert trial['status']=='PASS_CLOSURES_INCREMENT' and not trial['validation']['failures']
    params,frame = load()
    assert trial['parameter_sha256']==sha(OUTPUT/'parameters.json')
    assert read(folder/'parameters.json')==params
    assert trial['datum_sha256']==sha(OUTPUT/'datums/reference_frame.json')
    for filename,digest in trial['generator_sha256'].items():
        assert sha(ROOT/'cad/sevel16'/filename)==digest
    source = OUTPUT/'models'/f'{trial["baseline_document"]}.FCStd'
    assert sha(source)==trial['baseline_sha256']
    proof_path = baseline_proof(trial,source)
    archive = OUTPUT/'reports'/f'kinematics_validation.{source.stem}.{sha(proof_path)[:12]}.json'
    if not archive.exists():
        archive.write_bytes(proof_path.read_bytes())
    assert sha(archive)==sha(proof_path)
    baseline = App.listDocuments().get(source.stem) or App.openDocument(str(source))
    assert baseline.Phase.ThetaDeg==0
    shapes = {**valve_cover.build(params,frame),**oil_pan.build(params,frame)}
    rebuilt = {}
    for name,shape in shapes.items():
        row = trial['parts'][name]
        assert sha(folder/row['file'])==row['sha256']
        rebuilt[name] = difference(shape,Part.read(str(folder/row['file'])))
        assert rebuilt[name]<1e-5,name
    index = 1
    while (OUTPUT/f'models/SEVEL_Closures_A5_v{index:03d}.FCStd').exists():
        index += 1
    doc = App.newDocument(f'SEVEL_Closures_A5_v{index:03d}')
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
        color = (.17,.18,.20) if 'Gasket' not in name else (.35,.31,.25)
        if name=='OilDrainPlug':
            color = (.62,.63,.65)
        add_part(doc,name,shape,color=color)
    doc.recompute()
    path = OUTPUT/f'models/{doc.Name}.FCStd'
    doc.saveAs(str(path)); App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(objects)==198 and len({o.PartId for o in objects})==198
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in objects)
    unchanged = {o.Name:difference(o.Shape,doc.getObject(o.Name).Shape)
                 for o in baseline.Objects if hasattr(o,'Shape')}
    assert len(unchanged)==192 and max(unchanged.values())<1e-5
    for name in unchanged:
        a,b = baseline.getObject(name),doc.getObject(name)
        for prop in ('PartId','MotionType','CylinderId','ValveKind','SpringKind','RestBase'):
            assert getattr(a,prop,None)==getattr(b,prop,None),(name,prop)
    report = dict(trial['validation'],source_sha256=sha(path),baseline_sha256=sha(source),
        parameter_sha256=sha(OUTPUT/'parameters.json'),datum_sha256=trial['datum_sha256'],
        baseline_proof_path=str(archive.relative_to(OUTPUT)),baseline_proof_sha256=sha(archive),
        unchanged_parts_symmetric_difference_mm3=unchanged,rebuild_symmetric_difference_mm3=rebuilt,
        trial_validation_sha256=sha(folder/'validation.json'),goal_complete=False)
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}_closures_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    Gui.activeDocument().activeView().viewIsometric(); Gui.activeDocument().activeView().fitAll()
    print(doc.Name,'198 valid solids; 192 unchanged; six closures rebuilt and reopened')
    return doc,report
