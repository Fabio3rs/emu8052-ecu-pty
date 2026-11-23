"""Native GLB capability probe with asymmetric geometry and nonzero pivots."""
import json
import FreeCAD as App
import FreeCADGui as Gui
import Part
import ImportGui
from config import OUTPUT


def run(legacy=None):
    index = 1
    while (OUTPUT/f'exports/glb_calibration_v{index:03d}').exists():
        index += 1
    folder = OUTPUT/f'exports/glb_calibration_v{index:03d}'
    folder.mkdir(exist_ok=False)
    modules = App.getExportType('glb')
    assert 'ImportGui' in modules,modules
    active = App.ActiveDocument
    doc = App.newDocument('SEVEL_GLB_Calibration')
    pivot,offset = App.Vector(7,11,13),App.Vector(17,-23,41)
    rotation = App.Rotation(App.Vector(0,0,1),37).multiply(App.Rotation(App.Vector(1,0,0),23))
    basis = App.Rotation(App.Vector(1,0,0),-90)
    expected,objects = {},[]
    for i,color in enumerate(((.2,.7,.3),(.8,.25,.15))):
        obj = doc.addObject('Part::Feature','Probe'+str(i))
        obj.Label = 'sevel.calibration.'+str(i)
        obj.Shape = Part.makeBox(86.4,33.7,67.4)
        shift = offset+App.Vector(160*i,0,0)
        obj.Placement = App.Placement(shift+pivot-rotation.multVec(pivot),rotation)
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Visibility = True
        expected[obj.Label] = {'world_vertices_m':[list(basis.multVec(v.Point)*.001) for v in obj.Shape.Vertexes],
                               'cad_rgb':list(obj.ViewObject.ShapeColor)[:3],
                               'cad_pivot_mm':list(pivot),'world_pivot_m':list(basis.multVec(pivot+shift)*.001)}
        objects.append(obj)
    doc.recompute()
    path = folder/'calibration.glb'
    options = {} if legacy is None else {'legacy':legacy,'exportHidden':True,'keepPlacement':True}
    evidence = {'export_modules':modules,'freecad_version':App.Version()[:3],
                'expected':expected,'conversion':'CAD mm (x,y,z) -> runtime m .001*(x,z,-y)',
                'pre_tessellated_mm':.08,'options':options}
    (folder/'expected.json').write_text(json.dumps(evidence,indent=2)+'\n')
    try:
        for obj in objects:
            obj.Shape.tessellate(.08)
        Gui.updateGui()
        ImportGui.export(objects,str(path),**options)
        assert path.is_file() and path.read_bytes()[:4]==b'glTF'
    except Exception as error:
        (folder/'capability.json').write_text(json.dumps({'status':'FAIL_NATIVE_GLB_EXPORT',
            'error':type(error).__name__+': '+str(error),'pre_tessellated_mm':.08,
            'options':options},indent=2)+'\n')
        raise
    finally:
        App.closeDocument(doc.Name)
        if active:
            App.setActiveDocument(active.Name); Gui.setActiveDocument(active.Name)
    print(path)
    return folder
