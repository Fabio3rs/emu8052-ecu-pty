"""Persist bottom-end poses and derived cutaways; never overwrite evidence."""
import importlib.util
import json
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import OUTPUT, load
from assembly import apply_pose

_spec = importlib.util.spec_from_file_location('sevel_capture',OUTPUT/'generator/capture.py')
_capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_capture)
prepare_view = _capture.prepare


def save(doc, view, prefix, theta, note='bottom-end checkpoint; valve CAD pending'):
    App.setActiveDocument(doc.Name)
    assert App.ActiveDocument.Name==doc.Name
    path = _capture.save(view,OUTPUT/'evidence',prefix)
    from pathlib import Path
    meta_path = Path(path).with_suffix('.json')
    meta = json.loads(meta_path.read_text())
    assert meta['document']==doc.Name
    meta.update({'theta_deg':theta,'scope':note})
    meta_path.write_text(json.dumps(meta,indent=2)+'\n')
    return path


def run(doc):
    params,frame = load()
    prefix = doc.Name
    old_visibility = {o.Name:o.ViewObject.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    paths = []
    for angle in [0,90,180,270,360,450,540,630,720]:
        apply_pose(doc,angle,params,frame)
        paths.append(save(doc,'Isometric',f'{prefix}-pose{angle:03d}',angle))
    apply_pose(doc,0,params,frame)
    for o in doc.Objects:
        if hasattr(o,'Shape'):
            o.ViewObject.Visibility = o.Name.startswith('C1_')
    paths.append(save(doc,'Isometric',f'{prefix}-piston-rod',0))
    paths.append(save(doc,'Right',f'{prefix}-piston-rod',0))
    for o in doc.Objects:
        if hasattr(o,'Shape'):
            o.ViewObject.Visibility = True
    paths.append(save(doc,'Isometric',f'{prefix}-external',0))
    paths.append(save(doc,'Bottom',f'{prefix}-external',0))
    # Static cuts at a mid-stroke pose expose bosses, bushings and bearing seats.
    apply_pose(doc,90,params,frame)
    for label,box,view in [('Longitudinal',Part.makeBox(800,300,700,App.Vector(-200,0,-400)),'Front'),
                           ('TransverseC1',Part.makeBox(2,600,700,App.Vector(-1,-300,-400)),'Right')]:
        name = prefix+'_'+label
        path = OUTPUT/f'models/{name}.FCStd'
        if path.exists():
            raise FileExistsError(path)
        cut = App.newDocument(name)
        for original in doc.Objects:
            if not hasattr(original,'Shape'):
                continue
            shape = original.Shape.common(box)
            if shape.isNull() or shape.Volume<1e-7:
                continue
            assert shape.isValid()
            obj = cut.addObject('Part::Feature',original.Name)
            obj.Shape = shape
            obj.ViewObject.ShapeColor = original.ViewObject.ShapeColor
        cut.recompute()
        cut.saveAs(str(path))
        paths.append(save(cut,view,name,90,'Static section of bottom end at theta=90 degrees'))
    for o in doc.Objects:
        if hasattr(o,'Shape'):
            o.ViewObject.Visibility = old_visibility[o.Name]
    apply_pose(doc,0,params,frame)
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.activeDocument().activeView().fitAll()
    return paths
