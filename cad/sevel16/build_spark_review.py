"""Rebuild the BCPR5ES review assembly from the saved A5 v002 checkpoint."""
import FreeCAD as App
import FreeCADGui as Gui
import Part

import bcpr5es as plug
from config import OUTPUT, layout, load
from head_passages import chambers

V = App.Vector


def pocket_tools(x, place, bay_profile=None):
    # Photos 723789 and 885508: the wall between bosses recedes continuously
    # above the seat, then sweeps out into the lower ledge. Sections are estimated.
    wires = []
    for z, y in [(-1,-80), (4.5,-65), (9,-53), (15,-41), (24,-35),
                 (38,-35), (52,-38), (68,-43), (88,-53)]:
        row = [(-47,-88), (-36,-88), (-29,y-1), (-15,y+1),
               (15,y+1), (29,y-1), (36,-88), (47,-88)]
        if bay_profile:
            width, setback, lean = bay_profile
            weight = max(0, 1-abs(z-34)/34)
            row = [(dx*width + lean*weight, depth + setback*weight) for dx, depth in row]
        points = [V(x+dx, depth, z) for dx, depth in row]
        curve = Part.BezierCurve()
        curve.setPoles(points)
        wires.append(Part.Wire([curve.toShape(), Part.makeLine(points[-1], points[0])]))
    bay = Part.makeLoft(wires, True, False)
    lip = plug.COUNTERBORE
    # Retain a small cast collar with a flat mouth for the recessed washer.
    collar = Part.makeCone(12.25, 18, lip+5, V(0, 0, -lip))
    mouth = Part.makeCylinder(12.25, 60-lip, V(0, 0, -60))
    well = Part.makeCylinder(plug.WELL_RADIUS, lip, V(0, 0, -lip))
    for tool in (collar, mouth, well):
        tool.Placement = place.multiply(tool.Placement)
    return bay.cut(collar).fuse(mouth).fuse(well)


def geometry(doc, params, frame):
    head = doc.HeadLower.Shape.copy()
    prototypes = plug.build()
    h = params['head_lower_casting_estimated']['value']
    block = params['casting_visual_estimated']['value']
    shapes, cuts, stations = {}, [], []
    for i, (x, chamber) in enumerate(zip(layout(params, frame)['centers'], chambers(params, frame)), 1):
        start = V(x, h['spark_plug_y_mm'], h['spark_plug_z_mm'])
        end = V(x, -10, h['head_gasket_thickness_mm']+3)
        axis = (end-start).normalize()
        ray = Part.makeLine(start, end + axis*20)
        entry = min((v.Point for v in chamber.section(ray).Vertexes), key=lambda p: (p-start).Length)
        seat = entry - axis*plug.SEAT_TO_CHAMBER
        placement = App.Placement(seat, App.Rotation(V(0, 0, 1), axis))
        cut = pocket_tools(x, placement)
        slot = Part.makeBox(block['water_slot_length'], block['water_slot_width'],
                            h['deck_coolant_recess_depth_mm'],
                            V(x-block['water_slot_length']/2, -55-block['water_slot_width']/2, 0))
        assert cut.distToShape(slot)[0] > 0 and cut.common(slot).Volume < 1e-7, ('coolant', i)
        cuts.append(cut)
        for key, prototype in prototypes.items():
            shape = prototype.copy()
            shape.Placement = placement
            shapes[f'C{i}_Spark{key}'] = shape
        stations.append((placement, chamber))
    shapes['HeadLower'] = head.cut(cuts).removeSplitter()
    for name, shape in shapes.items():
        assert shape.isValid() and len(shape.Solids) == 1, name
    for i, (place, chamber) in enumerate(stations, 1):
        shell = shapes[f'C{i}_SparkShell']
        ceramic = shapes[f'C{i}_SparkCeramic']
        electrode = shapes[f'C{i}_SparkElectrode']
        gap = shell.distToShape(electrode)[0]
        assert abs(gap-plug.GAP) < 1e-6, (i, gap)
        head = shapes['HeadLower']
        for piece in (shell, ceramic, electrode):
            assert head.common(piece).Volume < 1e-5, i
            for name in ('HeadGasket', f'C{i}_Piston', f'C{i}_intake_Valve', f'C{i}_exhaust_Valve'):
                assert piece.common(doc.getObject(name).Shape).Volume < 1e-5, (i, name)
        # Check the full annular washer footprint, and the actual spark location.
        pad = Part.makeCylinder(10, 0.05).cut(Part.makeCylinder(7.05, 0.05))
        pad.Placement = place
        assert pad.cut(head).Volume < 1e-5, ('seat', i)
        point = place.multVec(V(0, 0, plug.ELECTRODE_END))
        assert Part.makeSphere(0.15, point).cut(chamber).Volume < 1e-7, ('tip', i)
    return shapes


def show_head(doc):
    for obj in doc.Objects:
        if hasattr(obj, 'Shape'):
            obj.ViewObject.Visibility = obj.Name == 'HeadLower' or '_Spark' in obj.Name
            if obj.ViewObject.Visibility:
                obj.ViewObject.Deviation = 0.06
                obj.ViewObject.DisplayMode = 'Shaded'
    view = Gui.activeDocument().activeView()
    view.setCameraOrientation(App.Rotation(V(), V(0,0,1), V(-0.18,-1,0.68), 'ZYX').Q)
    view.fitAll()


def run():
    params, frame = load()
    folder = OUTPUT/'models'
    name = 'SEVEL_Accessories_A5_v003_SparkReview'
    path = folder/(name + '.FCStd')
    if path.exists() or name in App.listDocuments():
        raise FileExistsError(name)
    doc = App.newDocument(name)
    try:
        doc.mergeProject(str(folder/'SEVEL_Accessories_A5_v002.FCStd'))
        for name, shape in geometry(doc, params, frame).items():
            doc.getObject(name).Shape = shape
        doc.Label = path.stem
        doc.recompute()
        show_head(doc)
        doc.saveAs(str(path))
    finally:
        App.closeDocument(doc.Name)
    return App.openDocument(str(path))
