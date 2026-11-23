"""Review a validated block candidate against the preceding saved casting."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import OUTPUT
from proof_chain import read, sha
from capture_checkpoint import save


def run(folder, baseline_name='SEVEL_Casting_A4_v001'):
    folder = Path(folder)
    trial = read(folder/'validation.json')
    assert trial['status']=='PASS_AUXILIARY_ENCLOSURE'
    assert sha(folder/'block.brep')==trial['block_sha256']
    source = OUTPUT/'models'/f'{baseline_name}.FCStd'
    baseline = App.listDocuments().get(baseline_name) or App.openDocument(str(source))
    assert baseline.Phase.ThetaDeg==0
    name = 'SEVEL_Root_Review_'+folder.name
    path = OUTPUT/'models'/f'{name}.FCStd'
    assert not path.exists() and name not in App.listDocuments()
    doc = App.newDocument(name)
    shapes = {'Before':baseline.Block.Shape.copy(),'After':Part.read(str(folder/'block.brep'))}
    for label,shape in shapes.items():
        assert shape.isValid() and len(shape.Solids)==1
        obj = doc.addObject('Part::Feature',label)
        obj.Shape = shape
        obj.ViewObject.ShapeColor = baseline.Block.ViewObject.ShapeColor
        obj.Visibility = False
    images = []
    for label in shapes:
        doc.getObject(label).Visibility = True
        for view in ('Front','Isometric'):
            image = Path(save(doc,view,name+'-'+label.lower(),0,
                'Estimated root blend comparison; baseline and candidate, same master datum'))
            images.append({'state':label,'view':view,'path':str(image.relative_to(OUTPUT)),
                           'sha256':sha(image),'metadata_sha256':sha(image.with_suffix('.json'))})
        doc.getObject(label).Visibility = False
    doc.After.Visibility = True
    doc.recompute()
    doc.saveAs(str(path))
    App.closeDocument(name)
    doc = App.openDocument(str(path))
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in doc.Objects)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    report = {'status':'CAPTURED_AWAITING_VISUAL_REVIEW','trial':str(folder.relative_to(OUTPUT)),
              'baseline_model':str(source.relative_to(OUTPUT)),'baseline_sha256':sha(source),
              'candidate_brep_sha256':trial['block_sha256'],'parameter_sha256':trial['parameter_sha256'],
              'review_model':str(path.relative_to(OUTPUT)),'review_model_sha256':sha(path),
              'images':images,'limits':'Visual profile estimate; only the separate collision proof validates clearance'}
    (folder/'root_visual_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return doc,report
