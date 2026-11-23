"""Review the inclined cage interfaces and preserve full-assembly phase captures."""
import FreeCAD as App
import FreeCADGui as Gui
from capture_checkpoint import save
import capture_timing


def run(doc):
    assert doc.Phase.ThetaDeg==0
    visible = {o.Name:o.ViewObject.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    paths = capture_timing.run(doc)
    try:
        for name in visible:
            doc.getObject(name).ViewObject.Visibility=name=='CamCarrier'
        for view in ('Right','Isometric','Bottom'):
            paths.append(save(doc,view,doc.Name+'-carrier',0,
                              'Inclined casting interfaces and scallops; angles and radii provisional'))
        for name in visible:
            obj = doc.getObject(name)
            obj.ViewObject.Visibility = name in ('CamCarrier','Camshaft') or hasattr(obj,'ValveKind')
        paths.append(save(doc,'Isometric',doc.Name+'-valvetrain',0,
                          'Five cam supports and eight tappets; valve axes independent of casting slopes'))
    finally:
        for name,state in visible.items():
            doc.getObject(name).ViewObject.Visibility=state
        App.setActiveDocument(doc.Name)
        Gui.setActiveDocument(doc.Name)
    print('\n'.join(paths[-4:]))
    return paths
