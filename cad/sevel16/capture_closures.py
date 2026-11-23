"""Capture closures and a reversible exploded view of the external assembly."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT
from proof_chain import sha
from check_auxiliary import difference
from capture_checkpoint import save


def run(doc):
    assert doc.Phase.ThetaDeg==0
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    visible = {o.Name:o.Visibility for o in objects}
    images = []
    try:
        for group,names,views in (
            ('cover',{'ValveCover','OilFillerCap'},('Isometric','Bottom')),
            ('pan',{'OilPan','OilDrainPlug'},('Isometric','Top','Bottom')),
            ('closures',set(visible),('Isometric',))):
            for obj in objects:
                obj.Visibility = obj.Name in names
            for view in views:
                images.append(save(doc,view,doc.Name+'-'+group,0,
                    'Provisional external closures; catalogue identity and uncalibrated photo contours'))
        name = doc.Name+'_Exploded'
        path = OUTPUT/f'models/{name}.FCStd'
        assert not path.exists() and name not in App.listDocuments()
        exploded = App.newDocument(name)
        shifts = {'Block':0,'HeadGasket':45,'HeadLower':80,'CarrierGasket':160,
                  'CamCarrier':195,'ValveCoverGasket':240,'ValveCover':265,
                  'OilFillerCap':300,'OilPanGasket':-45,'OilPan':-85,'OilDrainPlug':-110}
        for label,z in shifts.items():
            source = doc.getObject(label)
            obj = exploded.addObject('Part::Feature',label)
            shape = source.Shape.copy()
            shape.translate(App.Vector(0,0,z))
            obj.Shape = shape
            obj.ViewObject.ShapeColor = source.ViewObject.ShapeColor
            obj.addProperty('App::PropertyString','SourcePartId','Provenance')
            obj.SourcePartId = source.PartId
            obj.addProperty('App::PropertyVector','PresentationTranslation','Provenance')
            obj.PresentationTranslation = App.Vector(0,0,z)
        exploded.recompute()
        exploded.saveAs(str(path))
        App.closeDocument(name)
        exploded = App.openDocument(str(path))
        rows = []
        for obj in exploded.Objects:
            source = doc.getObject(obj.Name)
            assert obj.SourcePartId==source.PartId and obj.Shape.isValid()
            assert len(obj.Shape.Solids)==1
            restored = obj.Shape.copy()
            restored.translate(-obj.PresentationTranslation)
            error = difference(restored,source.Shape)
            assert error<1e-5
            rows.append({'source_object':obj.Name,'source_part_id':obj.SourcePartId,
                         'translation_mm':list(obj.PresentationTranslation),
                         'restored_symmetric_difference_mm3':error})
        assert len(rows)==len(shifts)==11
        images.append(save(exploded,'Isometric',name,0,
            'External assembly only; presentation translations are reversible, not assembly instructions'))
        report = {'status':'CAPTURED_AWAITING_VISUAL_REVIEW','document':doc.Name,
            'source_sha256':sha(Path(doc.FileName)),
            'parameter_sha256':sha(OUTPUT/'parameters.json'),
            'exploded_model':str(path.relative_to(OUTPUT)),'exploded_sha256':sha(path),
            'exploded_parts':rows,'restored_theta_deg':doc.Phase.ThetaDeg,
            'images':[{'path':str(Path(p).relative_to(OUTPUT)),'sha256':sha(Path(p)),
                       'metadata_sha256':sha(Path(p).with_suffix('.json'))} for p in images]}
        (OUTPUT/f'reports/{doc.Name}_closure_captures.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'images':images,'exploded_parts':len(rows)}))
        return report
    finally:
        for obj in objects:
            obj.Visibility = visible[obj.Name]
        App.setActiveDocument(doc.Name)
        Gui.setActiveDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.activeDocument().activeView().fitAll()
