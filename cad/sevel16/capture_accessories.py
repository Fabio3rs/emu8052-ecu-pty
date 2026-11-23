"""Inspect the added external components without changing their saved poses."""
import json
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
from config import OUTPUT
from proof_chain import sha
from capture_checkpoint import save


def run(doc):
    assert doc.Phase.ThetaDeg==0
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    visible = {o.Name:o.Visibility for o in objects}
    groups = [
        ('manifolds',{'IntakeManifold','ExhaustManifold','ManifoldGasket1','ManifoldGasket2'},('Isometric','Back')),
        ('intake',{'IntakeManifold'},('Bottom',)),
        ('exhaust',{'ExhaustManifold'},('Front',)),
        ('pump',{o.Name for o in objects if o.Name.startswith('WaterPump')},('Isometric','Right')),
        ('spark',{o.Name for o in objects if o.Name.startswith('C1_Spark')},('Isometric','Front')),
        ('external-accessories',set(visible),('Back','Left'))]
    paths = []
    try:
        for group,names,views in groups:
            for obj in objects:
                obj.Visibility = obj.Name in names
            for view in views:
                paths.append(save(doc,view,doc.Name+'-'+group,0,
                    'Provisional accessory geometry; static water pump pulley belongs to accessory drive'))
        report = {'status':'CAPTURED_AWAITING_VISUAL_REVIEW','document':doc.Name,
            'source_sha256':sha(Path(doc.FileName)),
            'parameter_sha256':sha(OUTPUT/'parameters.json'),'restored_theta_deg':doc.Phase.ThetaDeg,
            'images':[{'path':str(Path(p).relative_to(OUTPUT)),'sha256':sha(Path(p)),
                       'metadata_sha256':sha(Path(p).with_suffix('.json'))} for p in paths]}
        assert len(paths)==10
        (OUTPUT/f'reports/{doc.Name}_accessory_captures.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'images':paths}))
        return report
    finally:
        for obj in objects:
            obj.Visibility = visible[obj.Name]
        App.setActiveDocument(doc.Name)
        Gui.setActiveDocument(doc.Name)
        Gui.activeDocument().activeView().viewIsometric()
        Gui.activeDocument().activeView().fitAll()
