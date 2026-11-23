"""Generate the assembled-engine review from the A5 spark-plug checkpoint."""
import FreeCAD as App
import FreeCADGui as Gui
import Part

import block_pcv_review as pcv
from assembly import add_part
from config import OUTPUT, layout, load

V = App.Vector
SOURCE = 'SEVEL_Accessories_A5_v003_SparkReview'
NAME = 'SEVEL_Accessories_A5_v004_BlockReview'


def verify(doc, params, frame):
    block = doc.Block.Shape
    fitting = doc.PCVBreatherOutlet.Shape
    shapes = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(shapes)==len({o.PartId for o in shapes})==220
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in shapes)
    for part in (doc.PCVBreatherOutlet,doc.OilFilterSpigot):
        assert block.distToShape(part.Shape)[0]<1e-6, part.Name
        for o in shapes:
            if o!=part and o.Shape.BoundBox.intersect(part.Shape.BoundBox):
                assert o.Shape.common(part.Shape).Volume<1e-5, (part.Name,o.Name)
    for name in ('AuxiliaryFrontBush','AuxiliaryRearBush','AuxiliaryFrontShaft'):
        assert block.common(doc.getObject(name).Shape).Volume<1e-5, name
    for bush in (doc.AuxiliaryFrontBush,doc.AuxiliaryRearBush):
        assert block.distToShape(bush.Shape)[0]<1e-6, bush.Name
    p = params['casting_visual_estimated']['value']
    xs = layout(params,frame)['centers']
    old = V(xs[0]+(xs[-1]-xs[0])*p['access_open_x_fraction'],-82,p['access_open_z'])
    old_axis = pcv.inclined(90-params['side_access_inclination_estimated']['value'])
    seat,normal = doc.PCVBreatherOutlet.SeatCenter,pcv.inclined(pcv.SEAT_TILT_DEG)
    bore_r = p['access_open_radius']-0.1
    probe = Part.makeLoft([pcv.circle(old-old_axis*9,old_axis,bore_r),
                           pcv.circle(seat,normal,bore_r)],True,True)
    assert block.common(probe).Volume<1e-5
    pad = Part.makeCylinder(28.8,0.1,seat-normal*0.1,normal).cut(
        Part.makeCylinder(25.2,0.1,seat-normal*0.1,normal))
    assert abs(pad.common(block).Volume-pad.Volume)<1e-5
    unit = pcv.inclined(pcv.OUTLET_TILT_DEG)
    root = seat+normal*13+V(-5,0,0)+V(0,-normal.z,normal.y)*9
    assert fitting.common(Part.makeCylinder(6,38,root-unit*5,unit)).Volume<1e-5


def present(doc):
    block = doc.Block
    block.ViewObject.ShapeColor = (0.26,0.27,0.28)
    block.ViewObject.Deviation = 0.09
    for obj in doc.Objects:
        if hasattr(obj,'Shape'):
            obj.ViewObject.Visibility = True
    back = V(0.42,-1,0.36).normalize()
    node = Gui.activeDocument().activeView().getCameraNode()
    node.orientation.setValue(App.Rotation(V(),V(0,0,1),back,'ZYX').Q)
    node.position.setValue(*(V(136,0,-62)+back*850))
    node.focalDistance.setValue(850)
    node.height.setValue(650)
    Gui.updateGui()


def save(doc, seat, params, frame):
    path = OUTPUT/'models'/(NAME+'.FCStd')
    if path.exists():
        raise FileExistsError(path)
    obj = doc.PCVBreatherOutlet
    for prop,kind,value in [('SeatCenter','Vector',seat),
                            ('SeatTiltFromVertical','Angle',pcv.SEAT_TILT_DEG),
                            ('OutletTiltFromVertical','Angle',pcv.OUTLET_TILT_DEG)]:
        obj.addProperty('App::Property'+kind,prop,'Photo estimate')
        setattr(obj,prop,value)
    doc.Label = NAME
    doc.recompute()
    verify(doc,params,frame)
    present(doc)
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(path))
    verify(reopened,params,frame)
    return reopened


def run():
    if NAME in App.listDocuments() or (OUTPUT/'models'/(NAME+'.FCStd')).exists():
        raise FileExistsError(NAME)
    params,frame = load()
    doc = App.newDocument(NAME)
    doc.mergeProject(str(OUTPUT/'models'/(SOURCE+'.FCStd')))
    block,seat,normal = pcv.casting(doc.Block.Shape,params,frame)
    doc.Block.Shape = block
    add_part(doc,'PCVBreatherOutlet',pcv.fitting(seat,normal),
             color=(0.75,0.76,0.77)).Label = 'Bocal da PCV'
    add_part(doc,'OilFilterSpigot',pcv.filter_spigot(block,params,frame),
             color=(0.57,0.54,0.48)).Label = 'Espigão do filtro de óleo'
    return save(doc,seat,params,frame)
