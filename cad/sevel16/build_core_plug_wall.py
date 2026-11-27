"""Sculpt the positive-Y cylinder-block wall against the three original plug seats."""
from pathlib import Path

import FreeCAD as App
import Part

from config import load

V = App.Vector


def cubic_knots(count):
    knots = list(range(count - 2))
    return [4] + [1] * (count - 4) + [4], knots


def cast_skin(profile):
    stations = profile["stations_x_relief"]
    levels = profile["levels_z_y_relief_drift"]
    poles = []
    for i, (x, relief) in enumerate(stations):
        # Hold the ends within the old wall beside the water pad and flywheel.
        drift_weight = min(1, i / 3, (len(stations) - 1 - i) / 3)
        poles.append([V(x + drift_weight * drift, y + relief * gain, z)
                      for z, y, gain, drift in levels])
    um, uk = cubic_knots(len(stations))
    vm, vk = cubic_knots(len(levels))
    surface = Part.BSplineSurface()
    surface.buildFromPolesMultsKnots(poles, um, vm, uk, vk, False, False, 3, 3)
    skin = surface.toShape().extrude(V(0, -20, 0))
    # All new stock stays outside the original crankcase and cylinder walls.
    skin = skin.common(Part.makeBox(400, 40, 180, V(-55, 56, -175)))
    # The deck's blind slots and fixing bores reach beyond Y=56. At their
    # depth the old exterior wall is already beyond Y=67. Join only there.
    return skin.cut(Part.makeBox(400, 27, 29, V(-55, 40, -26)))


def run(source, destination, stock=None):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    p = params["casting_visual_estimated"]["value"]
    xs = [b["x"] for b in frame["bore_circle_centers_mm"]]
    if stock is None:
        stock = cast_skin(params["core_plug_wall_estimated"]["value"])
    seats = [Part.makeCylinder(p["plug_diameter"] / 2, 40,
                               V((a + b) / 2, 60, p["plug_z"]), V(0, 1, 0))
             for a, b in zip(xs, xs[1:])]
    stock = stock.cut(seats)
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        old = doc.Block.Shape
        updated = old.fuse(stock).removeSplitter()
        assert updated.isValid() and len(updated.Solids) == 1
        assert updated.Solids[0].isClosed() and updated.Volume > old.Volume
        # Compare the complete material in the deck passage envelope, which
        # includes the slots and both fixing rows, with the reopened baseline.
        deck = Part.makeBox(420, 134, 26, V(-65, -67, -26))
        from geometry_identity import difference
        assert difference(old.common(deck), updated.common(deck)) < 1e-5
        # Check the new material against every neighboring assembly component.
        for obj in doc.Objects:
            if obj.Name == "Block" or not hasattr(obj, "Shape"):
                continue
            if stock.BoundBox.intersect(obj.Shape.BoundBox):
                assert abs(stock.common(obj.Shape).Volume) < 1e-5, obj.Name
        doc.Block.Shape = updated
        doc.Label = destination.stem
        doc.recompute()
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
