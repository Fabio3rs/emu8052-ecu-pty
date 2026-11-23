"""Rebuild bottom-end assembly in a new version; execute in FreeCAD GUI."""
import json
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import load, layout, OUTPUT
from assembly import add_part, apply_pose
import crankshaft
import piston
import connecting_rod
from stationary import clear_crank_bays
from capture_checkpoint import prepare_view


def run():
    params, frame = load()
    g = layout(params,frame)
    source = OUTPUT/'models/SEVEL_Block_M2b_v008.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName==str(source)),None)
    old = old or App.openDocument(str(source))
    index = 1
    while (OUTPUT/f'models/SEVEL_Moving_A2_v{index:03d}.FCStd').exists():
        index += 1
    name = f'SEVEL_Moving_A2_v{index:03d}'
    doc = App.newDocument(name)
    phase = doc.addObject('App::FeaturePython','Phase')
    phase.addProperty('App::PropertyFloat','ThetaDeg','Kinematics')
    phase.addProperty('App::PropertyString','EvidenceStatus','Provenance')
    phase.EvidenceStatus = frame['status']
    for original in old.Objects:
        shape = original.Shape.copy()
        if original.Name == 'Block':
            shape, cavity_report = clear_crank_bays(shape,params,frame,include_rods=True)
        add_part(doc,original.Name,shape).ViewObject.Visibility = False
    crank, interfaces = crankshaft.build(params,frame)
    add_part(doc,'Crankshaft',crank,'crank',color=(0.38,0.41,0.45))
    housing = params['main_bearing_housing_diameter']['value']/2
    thickness = params['piston_rod_nominal']['value']['main_bearing_thickness_mm']
    width = params['block_visual_estimated']['value']['web_thickness']
    shell = connecting_rod.ring_x(housing,housing-thickness,width)
    lower = Part.makeBox(100,100,50,App.Vector(-50,-50,-50))
    for i,x in enumerate(g['supports']):
        for side,shape in [('Upper',shell.cut(lower)),('Lower',shell.common(lower))]:
            obj = add_part(doc,f'MainBearing{i+1}{side}',shape,color=(0.72,0.62,0.38))
            obj.Placement.Base = App.Vector(x,0,-g['height'])
    prototypes = {'piston':piston.build(params,frame),'rod':connecting_rod.build(params,frame)}
    for i in range(1,5):
        for kind,pieces in prototypes.items():
            for label,shape in pieces.items():
                color = (0.75,0.77,0.8) if kind=='piston' else (0.40,0.43,0.46)
                if 'Bearing' in label or 'Bushing' in label:
                    color = (0.72,0.62,0.38)
                if 'Ring' in label:
                    color = (0.24,0.26,0.29)
                add_part(doc,f'C{i}_{label}',shape.copy(),kind,i,color)
    apply_pose(doc,0,params,frame)
    for obj in doc.Objects:
        if hasattr(obj,'Shape'):
            assert obj.Shape.isValid() and len(obj.Shape.Solids)==1, obj.Name
    path = OUTPUT/f'models/{name}.FCStd'
    App.setActiveDocument(doc.Name)
    prepare_view('Isometric')
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    assert all(o.Shape.isValid() for o in doc.Objects if hasattr(o,'Shape'))
    (OUTPUT/f'reports/{name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    (OUTPUT/f'reports/{name}.casting.json').write_text(json.dumps(cavity_report,indent=2)+'\n')
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    print(name, 'saved and reopened; collision validation pending')
    return doc


if __name__=='__main__':
    run()
