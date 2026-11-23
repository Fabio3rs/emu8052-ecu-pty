"""Inspect the corrected support path in an actual C1 exhaust section."""
import json
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import OUTPUT, load
from capture_checkpoint import save
from check_auxiliary import sha
from valvetrain_layout import valves


def run(doc):
    params,frame = load()
    assert doc.Phase.ThetaDeg==0
    x = next(r for r in valves(params,frame) if r['id']=='C1_exhaust')['axis_origin_mm'][0]
    path = OUTPUT/f'models/{doc.Name}_SeatSection.FCStd'
    if path.exists():
        raise FileExistsError(path)
    selected = ['HeadLower']+['C1_exhaust_'+n for n in (
        'Valve','Guide','InnerSpringSeat','OuterSpringSeat','InnerSpring','OuterSpring')]
    box = Part.makeBox(2,40,35,App.Vector(x-1,-20,50))
    cut = App.newDocument(doc.Name+'_SeatSection')
    for name in selected:
        original = doc.getObject(name)
        shape = original.Shape.common(box)
        assert shape.isValid() and not shape.isNull() and shape.Volume>0,name
        obj = cut.addObject('Part::Feature',name)
        obj.Shape = shape
        obj.addProperty('App::PropertyString','SourcePartId','Provenance')
        obj.SourcePartId = original.PartId
        obj.ViewObject.ShapeColor = original.ViewObject.ShapeColor
    cut.recompute(); cut.saveAs(str(path)); App.closeDocument(cut.Name)
    cut = App.openDocument(str(path))
    assert all(o.Shape.isValid() for o in cut.Objects)
    images = [save(cut,'Right',cut.Name,0,'C1 exhaust lower seat: two touching CAD regions; no former 3 mm gap')]
    visible = {o.Name:o.ViewObject.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    try:
        for name in visible:
            doc.getObject(name).ViewObject.Visibility = name.startswith('C1_exhaust_')
        images.append(save(doc,'Isometric',doc.Name+'-exhaust-stack',0,'One valve stack with stepped lower spring support'))
    finally:
        for name,state in visible.items():
            doc.getObject(name).ViewObject.Visibility = state
        App.setActiveDocument(doc.Name); Gui.setActiveDocument(doc.Name)
    report = {'status':'CAPTURED_REVIEW_REQUIRED','source_sha256':sha(doc.FileName),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),'images':images,
              'section_path':str(path),'section_sha256':sha(path),'section_x_mm':x,'phase_deg':0}
    (OUTPUT/f'reports/{doc.Name}_seat_captures.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
