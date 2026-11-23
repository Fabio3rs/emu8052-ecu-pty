"""Review both supported journals and their new internal passage without changing CAD."""
import FreeCAD as App
import FreeCADGui as Gui
import Part
from config import OUTPUT, load
from capture_checkpoint import save
import capture_timing


def run(doc):
    params,_ = load()
    assert doc.Phase.ThetaDeg==0
    visible = {o.Name:o.ViewObject.Visibility for o in doc.Objects if hasattr(o,'Shape')}
    paths = capture_timing.run(doc)
    names = ('AuxiliaryFrontShaft','AuxiliaryFrontBush','AuxiliaryRearBush','AuxSprocket')
    try:
        for name in visible:
            doc.getObject(name).ViewObject.Visibility=name in names
        for view in ('Isometric','Front'):
            paths.append(save(doc,view,doc.Name+'-auxiliary',0,
                              'Two journals and eccentric; ruled visual teeth, axial dimensions estimated'))
        section_name = doc.Name+'_AuxiliarySection'
        assert section_name not in App.listDocuments()
        section = App.newDocument(section_name)
        y = params['casting_visual_estimated']['value']['aux_y']
        box = Part.makeBox(1000,1000,1000,App.Vector(-300,y,-500))
        for name in ('Block',)+names:
            source = doc.getObject(name)
            obj = section.addObject('Part::Feature',name)
            obj.Shape = source.Shape.common(box) if name=='Block' else source.Shape.copy()
            obj.ViewObject.ShapeColor = source.ViewObject.ShapeColor
        section.recompute()
        App.setActiveDocument(section.Name)
        Gui.setActiveDocument(section.Name)
        paths.append(save(section,'Front',section.Name,0,
                          'Longitudinal section at auxiliary axis; both journals and rear support'))
        section.saveAs(str(OUTPUT/f'models/{section.Name}.FCStd'))
    finally:
        App.setActiveDocument(doc.Name)
        Gui.setActiveDocument(doc.Name)
        for name,state in visible.items():
            doc.getObject(name).ViewObject.Visibility=state
    print('\n'.join(paths[-3:]))
    return paths
