"""A3 review views and 720-degree poses, preserved under a versioned prefix."""
import FreeCAD as App
import Part
from config import OUTPUT, load
from assembly import apply_pose, add_part
from capture_checkpoint import save


def run(doc):
    params,frame = load()
    visibility = {o.Name:o.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    paths = []
    note = 'A3 moving assembly; head casting and distribution absent; synthetic cam'
    try:
        for o in doc.Objects:
            if hasattr(o,'Shape'):
                o.Visibility = o.MotionType!='fixed' or hasattr(o,'ValveKind')
        for theta in [0,90,180,270,359,360,450,540,630,720]:
            apply_pose(doc,theta,params,frame)
            paths.append(save(doc,'Isometric',doc.Name+f'-cycle{theta:03d}',theta,note))
        apply_pose(doc,0,params,frame)
        for o in doc.Objects:
            if hasattr(o,'Shape'):
                o.Visibility = hasattr(o,'ValveKind') and o.CylinderId==1
        paths.append(save(doc,'Front',doc.Name+'-C1-springs',0,note))
        # A half-section exposes both coaxial springs, the cup and keeper groove.
        name = doc.Name+'_ValveSection'
        path = OUTPUT/f'models/{name}.FCStd'
        if path.exists():
            raise FileExistsError(path)
        section = App.newDocument(name)
        tool = Part.makeBox(100,60,200,App.Vector(-50,0,0))
        for o in doc.Objects:
            if hasattr(o,'ValveKind') and o.CylinderId==1:
                shape = o.Shape.common(tool)
                if not shape.isNull() and shape.Volume>1e-7:
                    assert shape.isValid()
                    add_part(section,o.Name,shape,color=o.ViewObject.ShapeColor)
        section.recompute()
        paths.append(save(section,'Isometric',name,0,'Static C1 valve half-section'))
        section.saveAs(str(path))
    finally:
        for o in doc.Objects:
            if hasattr(o,'Shape'):
                o.Visibility = visibility[o.Name]
        apply_pose(doc,0,params,frame)
    return paths
