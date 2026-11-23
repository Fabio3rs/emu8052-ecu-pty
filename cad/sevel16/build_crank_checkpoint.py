"""Run inside FreeCAD GUI; creates a new version and never edits the source block."""
import hashlib
import json
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import load, layout, ROOT, OUTPUT
from crankshaft import build
from stationary import clear_crank_bays


def run():
    params, frame = load()
    shape, interfaces = build(params, frame)
    g = layout(params, frame)
    source = OUTPUT / 'models/SEVEL_Block_M2b_v008.FCStd'
    old = next((d for d in App.listDocuments().values() if d.FileName == str(source)), None)
    old = old or App.openDocument(str(source))
    index = 1
    while (OUTPUT / f'models/SEVEL_Crank_A1_v{index:03d}.FCStd').exists():
        index += 1
    name = f'SEVEL_Crank_A1_v{index:03d}'
    doc = App.newDocument(name)
    doc.addObject('App::DocumentObjectGroup','Stationary')
    cavity_report = None
    for original in old.Objects:
        if not hasattr(original,'Shape'):
            continue
        obj = doc.addObject('Part::Feature',original.Name)
        obj.Shape = original.Shape.copy()
        if obj.Name == 'Block':
            obj.Shape, cavity_report = clear_crank_bays(obj.Shape,params,frame)
        obj.addProperty('App::PropertyString','SourceFile','Provenance')
        obj.SourceFile = str(source)
        obj.ViewObject.Visibility = False
        doc.Stationary.addObject(obj)
    obj = doc.addObject('Part::Feature','Crankshaft')
    obj.Shape = shape
    obj.Placement = App.Placement(App.Vector(0,0,-g['height']),App.Rotation())
    obj.addProperty('App::PropertyString','PartId','Provenance')
    obj.PartId = 'sevel.crankshaft'
    obj.addProperty('App::PropertyString','EvidenceStatus','Provenance')
    obj.EvidenceStatus = frame['status']
    obj.addProperty('App::PropertyAngle','ThetaDeg','Kinematics')
    obj.ThetaDeg = 0
    obj.ViewObject.ShapeColor = (0.40,0.43,0.47)
    obj.ViewObject.LineColor = (0.12,0.13,0.15)
    # Stable semantic material selection from cylindrical geometry, not face indices.
    colors = []
    for face in shape.Faces:
        surface = face.Surface
        machined = isinstance(surface,Part.Cylinder) and abs(abs(surface.Axis.x)-1)<1e-8
        colors.append((0.72,0.75,0.79) if machined else (0.25,0.28,0.32))
    obj.ViewObject.DiffuseColor = colors
    doc.recompute()
    path = OUTPUT / f'models/{name}.FCStd'
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    reopened = doc.Crankshaft.Shape
    assert reopened.isValid() and len(reopened.Solids) == 1
    assert abs(reopened.Volume-shape.Volume)<1e-5
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    report = {'checkpoint':name,'status':'A1_GEOMETRY_ONLY_PENDING_COLLISIONS',
              'freecad_version':App.Version(),'addon_version_verified':'0.1.32',
              'rpc_protocol_verified':3,'source_block':str(source),
              'source_block_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'parameters_sha256':hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest(),
              'reference_status':frame['status'],'interfaces':interfaces,
              'crank_pivot_mm':[0,0,-g['height']], 'height_closure_mm':g,
              'valid':reopened.isValid(),'solids':len(reopened.Solids),
              'volume_mm3':shape.Volume,'saved_reopened':True,
              'derived_cavity':cavity_report,
              'missing':['bearings','rods','pistons','valvetrain','timing','720 CAD collision sweep']}
    (OUTPUT/f'reports/{name}.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUTPUT/f'reports/{name}.parameters.json').write_text(json.dumps(params,indent=2)+'\n')
    return doc


if __name__ == '__main__':
    run()
