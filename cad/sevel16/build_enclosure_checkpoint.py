"""Save a separately versioned assembly with only its block casting changed."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import ROOT, OUTPUT, load
from assembly import add_part
from check_auxiliary import difference, sha
from auxiliary_enclosure import build


def from_trial(folder):
    """Import only a validated detached result whose inputs still match."""
    folder = Path(folder)
    report = json.loads((folder/'validation.json').read_text())
    params,frame = load()
    assert report['status']=='PASS_AUXILIARY_ENCLOSURE'
    assert report['parameter_sha256']==sha(OUTPUT/'parameters.json')
    assert json.loads((folder/'parameters.json').read_text())==params
    assert report['datum_sha256']==sha(OUTPUT/'datums/reference_frame.json')
    assert report['block_sha256']==sha(folder/'block.brep')
    assert report['added_sha256']==sha(folder/'added.brep')
    for name,digest in report['generator_sha256'].items():
        assert sha(ROOT/'cad/sevel16'/name)==digest
    source = OUTPUT/'models/SEVEL_Head_A3_v002.FCStd'
    assert report['baseline_sha256']==sha(source)
    baseline = App.listDocuments().get(source.stem) or App.openDocument(str(source))
    return run(baseline,Part.read(str(folder/'block.brep')),report['metrics'],report['validation'],params)


def run(baseline,block,metrics,verification,params):
    current,frame = load()
    assert current==params and baseline.Name=='SEVEL_Head_A3_v002'
    assert baseline.Phase.ThetaDeg==0
    previous = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:params[k] for k in previous}==previous
    proof_path = OUTPUT/'reports/kinematics_validation.json'
    proof = json.loads(proof_path.read_text())
    visited = set()
    while proof['document']!=baseline.Name:
        assert proof_path not in visited, 'Cyclic baseline evidence'
        visited.add(proof_path)
        inherited = proof['inherited_baseline']
        proof_path = (OUTPUT/inherited['path']).resolve()
        assert proof_path.is_relative_to((OUTPUT/'reports').resolve())
        assert sha(proof_path)==inherited['sha256']
        proof = json.loads(proof_path.read_text())
    assert proof['document']==baseline.Name and proof['source_sha256']==sha(baseline.FileName)
    assert proof['status']=='PASS_CURRENT_KINEMATICS_VISUAL_WORK_PENDING'
    assert verification['status']=='PASS_AUXILIARY_ENCLOSURE' and not verification['failures']
    assert len(verification['pair_coverage'])+len(verification['continuous_upper_separations_mm'])==191
    assert len(verification['angles_deg'])==220
    regenerated,_,rebuilt_metrics = build(baseline.Block.Shape.copy(),params,frame)
    assert difference(regenerated,block)<1e-5
    assert abs(rebuilt_metrics['added_volume_mm3']-metrics['added_volume_mm3'])<1e-5
    proof_digest = sha(proof_path)
    archive = OUTPUT/f'reports/kinematics_validation.head_v002.{proof_digest[:12]}.json'
    if not archive.exists():
        archive.write_bytes(proof_path.read_bytes())
    assert sha(archive)==proof_digest
    index = 1
    while (OUTPUT/f'models/SEVEL_Casting_A4_v{index:03d}.FCStd').exists():
        index += 1
    doc = App.newDocument(f'SEVEL_Casting_A4_v{index:03d}')
    phase = doc.addObject('App::FeaturePython','Phase')
    phase.addProperty('App::PropertyFloat','ThetaDeg','Kinematics')
    phase.addProperty('App::PropertyString','EvidenceStatus','Provenance')
    phase.EvidenceStatus = frame['status']
    for old in baseline.Objects:
        if not hasattr(old,'Shape'):
            continue
        shape = block if old.Name=='Block' else old.Shape.copy()
        obj = add_part(doc,old.Name,shape,old.MotionType,old.CylinderId,old.ViewObject.ShapeColor)
        obj.Placement,obj.Label = old.Placement,old.Label
        for prop,kind in [('ValveKind','String'),('SpringKind','String'),('RestBase','Vector')]:
            if hasattr(old,prop):
                obj.addProperty('App::Property'+kind,prop,'Assembly')
                setattr(obj,prop,getattr(old,prop))
    doc.recompute()
    path = OUTPUT/f'models/{doc.Name}.FCStd'
    doc.saveAs(str(path)); App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(objects)==192 and len({o.PartId for o in objects})==192
    unchanged = {}
    for obj in objects:
        old = baseline.getObject(obj.Name)
        assert obj.Shape.isValid() and len(obj.Shape.Solids)==1
        for prop in ('PartId','MotionType','CylinderId','ValveKind','SpringKind','RestBase'):
            assert getattr(obj,prop,None)==getattr(old,prop,None),(obj.Name,prop)
        if obj.Name!='Block':
            unchanged[obj.Name] = difference(obj.Shape,old.Shape)
    assert len(unchanged)==191 and max(unchanged.values())<1e-5
    assert difference(doc.Block.Shape,regenerated)<1e-5
    assert sha(baseline.FileName)==proof['source_sha256']
    report = dict(verification,source_sha256=sha(path),baseline_sha256=sha(baseline.FileName),
        baseline_proof_sha256=proof_digest,baseline_proof_path=str(archive.relative_to(OUTPUT)),
        parameter_sha256=sha(OUTPUT/'parameters.json'),datum_sha256=sha(OUTPUT/'datums/reference_frame.json'),
        unchanged_parts_symmetric_difference_mm3=unchanged,changed_parts=['Block'],
        added_parts=[],casting_metrics=metrics,rebuild_verified=True,goal_complete=False)
    (OUTPUT/f'reports/{doc.Name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{doc.Name}_enclosure_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    App.setActiveDocument(doc.Name); Gui.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric(); Gui.activeDocument().activeView().fitAll()
    print(doc.Name,'192 valid solids; 191 unchanged; block enclosure rebuilt and reopened')
    return doc,report
