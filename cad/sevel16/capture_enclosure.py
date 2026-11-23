"""Compare the lateral casting and expose the auxiliary tunnel in a saved cut."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import OUTPUT, load
from capture_checkpoint import save
from proof_chain import sha


def run(doc,baseline):
    params,frame = load()
    assert doc.Phase.ThetaDeg==baseline.Phase.ThetaDeg==0
    names = {'Block','AuxiliaryFrontShaft','AuxiliaryFrontBush','AuxiliaryRearBush'}
    originals = {d.Name:{o.Name:o.Visibility for o in d.Objects if hasattr(o,'Shape')}
                 for d in (doc,baseline)}
    images = []
    try:
        for target,label in ((baseline,'before'),(doc,'after')):
            for o in target.Objects:
                if hasattr(o,'Shape'):
                    o.Visibility = o.Name in names
            for view in ('Front','Isometric'):
                images.append(save(target,view,doc.Name+'-enclosure-'+label,0,
                    'Auxiliary housing comparison; unmeasured casting profile'))
        y = params['casting_visual_estimated']['value']['aux_y']
        tool = Part.makeBox(400,2,300,App.Vector(-100,y-1,-250))
        name = doc.Name+'_AuxiliarySection'
        path = OUTPUT/f'models/{name}.FCStd'
        assert not path.exists() and name not in App.listDocuments()
        section = App.newDocument(name)
        parts = []
        for source_name in sorted(names):
            source = doc.getObject(source_name)
            shape = source.Shape.common(tool)
            assert not shape.isNull() and shape.isValid()
            obj = section.addObject('Part::Feature',source_name)
            obj.Shape = shape
            obj.addProperty('App::PropertyString','SourcePartId','Provenance')
            obj.SourcePartId = source.PartId
            obj.ViewObject.ShapeColor = source.ViewObject.ShapeColor
            parts.append({'id':source.PartId,'volume_mm3':shape.Volume,'solids':len(shape.Solids)})
        section.recompute()
        images.append(save(section,'Front',name,0,'2-mm longitudinal slice through auxiliary axis'))
        section.saveAs(str(path)); App.closeDocument(name)
        reopened = App.openDocument(str(path))
        assert all(o.Shape.isValid() for o in reopened.Objects if hasattr(o,'Shape'))
        for o in doc.Objects:
            if hasattr(o,'Shape'):
                o.Visibility = True
        images.append(save(doc,'Isometric',doc.Name+'-enclosure-external',0,'Assembly with enclosed auxiliary shaft'))
    finally:
        for target in (doc,baseline):
            for name,visible in originals[target.Name].items():
                target.getObject(name).Visibility = visible
        App.setActiveDocument(doc.Name); Gui.setActiveDocument(doc.Name)
    return write_report(doc,baseline,images,path,parts,y)


def write_report(doc,baseline,images,path,parts,y):
    report = {'status':'CAPTURED_AWAITING_VISUAL_REVIEW','source_sha256':sha(OUTPUT/f'models/{doc.Name}.FCStd'),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),'baseline_sha256':sha(Path(baseline.FileName)),
              'images':images,'section_path':str(path.relative_to(OUTPUT)),'section_sha256':sha(path),
              'section_y_mm':y,'section_thickness_mm':2,'section_parts':parts,'theta_deg':0}
    (OUTPUT/f'reports/{doc.Name}_enclosure_captures.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
