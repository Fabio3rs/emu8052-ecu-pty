"""Derive two cutaway documents from the current assembled CAD at mid-stroke."""
import json
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import OUTPUT, load
from assembly import apply_pose
from capture_checkpoint import save
from proof_chain import sha
from timing_sweeps import overlaps


def run(doc):
    params,frame = load()
    initial = doc.Phase.ThetaDeg
    source_hash = sha(OUTPUT/'models'/f'{doc.Name}.FCStd')
    has_head = doc.getObject('HeadLower') is not None
    scope = 'Derived static section of current assembly; lower head '+('included' if has_head else 'absent')
    boxes = [('Longitudinal',Part.makeBox(1000,500,1000,App.Vector(-300,0,-500)),'Front'),
             ('TransverseC1',Part.makeBox(2,1000,1000,App.Vector(-1,-500,-500)),'Right')]
    records = []
    try:
        apply_pose(doc,90,params,frame)
        for label,box,view in boxes:
            name = doc.Name+'_'+label
            target = OUTPUT/f'models/{name}.FCStd'
            assert not target.exists() and name not in App.listDocuments(),name
            cut = App.newDocument(name)
            parts = []
            for original in doc.Objects:
                if not hasattr(original,'Shape') or not overlaps(original.Shape,box):
                    continue
                shape = original.Shape.common(box)
                if shape.isNull() or abs(shape.Volume)<1e-7:
                    continue
                assert shape.isValid(),original.Name
                obj = cut.addObject('Part::Feature',original.Name)
                obj.Shape = shape
                obj.addProperty('App::PropertyString','SourcePartId','Provenance')
                obj.SourcePartId = original.PartId
                obj.ViewObject.ShapeColor = original.ViewObject.ShapeColor
                parts.append({'source_part_id':original.PartId,'source_object':original.Name,
                              'cut_solids':len(shape.Solids),'volume_mm3':shape.Volume})
            assert parts
            cut.recompute()
            App.setActiveDocument(name)
            Gui.setActiveDocument(name)
            if has_head:
                assert any(p['source_object']=='HeadLower' for p in parts),label
            image = save(cut,view,name,90,scope)
            cut.saveAs(str(target))
            App.closeDocument(name)
            reopened = App.openDocument(str(target))
            assert all(o.Shape.isValid() for o in reopened.Objects if hasattr(o,'Shape'))
            records.append({'label':label,'model':str(target.relative_to(OUTPUT)),
                            'sha256':sha(target),'image':image,'parts':parts})
    finally:
        apply_pose(doc,initial,params,frame)
        App.setActiveDocument(doc.Name)
        Gui.setActiveDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.activeDocument().activeView().fitAll()
    assert sha(OUTPUT/'models'/f'{doc.Name}.FCStd')==source_hash
    report = {'status':'PASS_DERIVED_CUTAWAYS','source_sha256':source_hash,
              'parameter_sha256':sha(OUTPUT/'parameters.json'),'theta_deg':90,
              'sections':records,'restored_theta_deg':initial,
              'head_included':has_head,
              'limits':'Static B-rep cuts for inspection; collision validation is separate'}
    (OUTPUT/f'reports/{doc.Name}_sections.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'parts_per_section':[len(r['parts']) for r in records]}))
    return report
