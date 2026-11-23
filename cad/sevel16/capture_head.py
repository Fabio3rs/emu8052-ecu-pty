"""External head views and a section through the C1 exhaust valve axis."""
import json
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import OUTPUT, load
from capture_checkpoint import save
from check_auxiliary import sha
from valvetrain_layout import valves


def run(doc):
    assert doc.Phase.ThetaDeg==0
    params,frame = load()
    visible = {o.Name:o.ViewObject.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    paths = []
    try:
        for name in visible:
            doc.getObject(name).ViewObject.Visibility = name in ('HeadLower','HeadGasket','CarrierGasket')
        for view in ('Isometric','Front','Back','Top','Bottom','Right'):
            paths.append(save(doc,view,doc.Name+'-head',0,'Lower head and independent gaskets; uncalibrated casting'))
        for name in visible:
            doc.getObject(name).ViewObject.Visibility = True
        paths.append(save(doc,'Isometric',doc.Name+'-external',0,'New fixed head on the retained 189-part assembly'))
        x = next(r for r in valves(params,frame) if r['id']=='C1_exhaust')['axis_origin_mm'][0]
        box = Part.makeBox(2,400,190,App.Vector(x-1,-200,-5))
        section_path = OUTPUT/f'models/{doc.Name}_ExhaustSection.FCStd'
        if section_path.exists():
            raise FileExistsError(section_path)
        section = App.newDocument(doc.Name+'_ExhaustSection')
        for obj in doc.Objects:
            if obj.Name not in ('HeadLower','HeadGasket','CarrierGasket','CamCarrier','Camshaft') and not obj.Name.startswith('C1_exhaust_'):
                continue
            shape = obj.Shape.common(box)
            if shape.isNull() or abs(shape.Volume)<1e-7:
                continue
            assert shape.isValid(),obj.Name
            cut = section.addObject('Part::Feature',obj.Name)
            cut.Shape = shape
            cut.addProperty('App::PropertyString','SourcePartId','Provenance')
            cut.SourcePartId = obj.PartId
            cut.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
        section.recompute()
        section.saveAs(str(section_path))
        App.closeDocument(section.Name)
        section = App.openDocument(str(section_path))
        assert all(o.Shape.isValid() for o in section.Objects)
        paths.append(save(section,'Right',section.Name,0,'Static section through C1 exhaust; two millimetres wide'))
        report = {'status':'CAPTURED_REVIEW_REQUIRED','source_sha256':sha(doc.FileName),
                  'parameter_sha256':sha(OUTPUT/'parameters.json'),'images':paths,
                  'section_path':str(section_path),'section_sha256':sha(section_path),'section_x_mm':x,
                  'section_parts':len(section.Objects),'phase_deg':0}
        (OUTPUT/f'reports/{doc.Name}_head_captures.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        for name,state in visible.items():
            doc.getObject(name).ViewObject.Visibility=state
        App.setActiveDocument(doc.Name); Gui.setActiveDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric(); Gui.activeDocument().activeView().fitAll()
    return report
