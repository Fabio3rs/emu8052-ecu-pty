"""Generate the manifold review from the assembled block/PCV checkpoint."""
import FreeCAD as App
import FreeCADGui as Gui
import Part
from assembly import add_part
from config import OUTPUT, layout, load
from manifold_castings import V, UP, SIDE, exhaust
from manifold_intake_casting import intake
from valvetrain_layout import valves

SOURCE = 'SEVEL_Accessories_A5_v004_BlockReview'
NAME = 'SEVEL_Accessories_A5_v005_ManifoldReview'


def verify(doc, params, frame):
    inlet, outlet = doc.IntakeManifold.Shape, doc.ExhaustManifold.Shape
    inlet.check(True)
    outlet.check(True)
    parts = [o for o in doc.Objects if hasattr(o, 'Shape')]
    assert len(parts) == len({o.PartId for o in parts}) == 224
    assert all(o.Shape.isValid() and len(o.Shape.Solids) == 1 for o in parts)
    changed = [doc.IntakeManifold, doc.ExhaustManifold] + stud_objects(doc)
    for obj in changed:
        for other in parts:
            if obj != other and obj.Shape.BoundBox.intersect(other.Shape.BoundBox):
                volume = obj.Shape.common(other.Shape).Volume
                assert abs(volume) < 1e-4, (obj.Name, other.Name, volume)
    h = params['head_lower_casting_estimated']['value']
    p = params['manifold_visual_estimated']['value']
    photo = params['manifold_photo_review_estimated']['value']
    y = h['manifold_face_y_mm'] + p['gasket_mm']
    caps = {'intake': [], 'exhaust': []}
    for row in valves(params, frame):
        kind = row['kind']
        body = inlet if kind == 'intake' else outlet
        point = V(row['axis_origin_mm'][0], y, h[kind+'_port_z_mm'])
        r = h[kind+'_port_radius_mm']
        opening = Part.makeCylinder(r-.1, 3, point, SIDE)
        rim = Part.makeCylinder(r+1.5, 1, point, SIDE).cut(Part.makeCylinder(r+.5, 1, point, SIDE))
        assert body.common(opening).Volume < 1e-5
        assert abs(rim.Volume - body.common(rim).Volume) < 1e-5
        caps[kind].append(Part.makeCylinder(r+1, 2, point-SIDE, SIDE))
    cx = sum(layout(params, frame)['centers'])/4
    exit_z, exit_r = photo['exhaust_exit_z'], photo['exhaust_exit_radius']
    for yy in photo['exhaust_exit_centers_y']:
        assert outlet.common(Part.makeCylinder(exit_r-.5, 7, V(cx, yy, exit_z))).Volume < 1e-5
        caps['exhaust'].append(Part.makeCylinder(exit_r+1, 2, V(cx, yy, exit_z-1)))
    web = Part.makeCylinder(2, 6, V(cx, sum(photo['exhaust_exit_centers_y'])/2, exit_z+1))
    assert abs(outlet.common(web).Volume-web.Volume) < 1e-5
    for x in layout(params, frame)['supports'][1::2]:
        probe = Part.makeCylinder(h['coolant_port_radius_mm']-.1, 3, V(x, y, h['coolant_port_z_mm']), SIDE)
        assert inlet.common(probe).Volume < 1e-5
        caps['intake'].append(Part.makeCylinder(6.3, 2, V(x, y-1, h['coolant_port_z_mm']), SIDE))
    throat_y = photo['intake_throttle_y']
    assert inlet.common(Part.makeCylinder(21.8, 7, V(cx, throat_y, 100))).Volume < 1e-5
    caps['intake'].append(Part.makeCylinder(23, 2, V(cx, throat_y, 106)))
    # Two closed voids: paired exhaust circuits or intake air and coolant.
    for body, lids in [(inlet, caps['intake']), (outlet, caps['exhaust'])]:
        sealed = body.copy().multiFuse(lids)
        assert sealed.isValid() and len(sealed.Solids) == 1 and len(sealed.Shells) == 3
    for obj in stud_objects(doc):
        assert obj.Shape.distToShape(outlet)[0] < 1e-6


def stud_objects(doc):
    return [doc.getObject('ExhaustOutletStud'+str(i)) for i in range(1, 5)]


def camera(center, back, height, up=UP):
    view = Gui.activeDocument().activeView()
    node = view.getCameraNode()
    back = V(*back).normalize()
    node.orientation.setValue(App.Rotation(V(), up, back, 'ZYX').Q)
    node.position.setValue(*(V(*center) + back*1100))
    node.focalDistance.setValue(1100)
    node.nearDistance.setValue(100)
    node.farDistance.setValue(2500)
    node.height.setValue(height)
    Gui.updateGui()


def assemble(doc, inlet, outlet, studs):
    doc.IntakeManifold.Shape, doc.ExhaustManifold.Shape = inlet, outlet
    for obj, color in [(doc.IntakeManifold, (.73,.74,.73)), (doc.ExhaustManifold, (.39,.33,.30))]:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Deviation = .08
        obj.ViewObject.DisplayMode = 'Shaded'
    for i, stud in enumerate(studs, 1):
        add_part(doc, 'ExhaustOutletStud'+str(i), stud, color=(.46,.43,.40))
    doc.Label = NAME
    doc.recompute()


def run():
    destination = OUTPUT/'models'/(NAME+'.FCStd')
    if NAME in App.listDocuments() or destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    inlet, _, _ = intake(params, frame)
    outlet, _, studs = exhaust(params, frame)
    doc = App.newDocument(NAME)
    doc.mergeProject(str(OUTPUT/'models'/(SOURCE+'.FCStd')))
    assemble(doc, inlet, outlet, studs)
    verify(doc, params, frame)
    camera((140, 30, -53), (.45, 1, .56), 590)
    doc.saveAs(str(destination))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(destination))
    verify(doc, params, frame)
    return doc
