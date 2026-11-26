"""Shift the drain bore, boss and plug together on the reviewed deep sump floor."""
from pathlib import Path

import FreeCAD as App
import Part

from config import load
from oil_pan import build


def run(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    delta = App.Vector(0, params["drain_y_estimated"]["value"], 0)
    shapes = build(params, frame, offset_drain=True)
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        pan, plug = doc.OilPan, doc.OilDrainPlug
        prev = plug.Shape.copy()
        prev.translate(delta)
        assert abs(prev.common(shapes["OilDrainPlug"]).Volume-prev.Volume) < 1e-5
        old_volume = pan.Shape.Volume
        pan.Shape, plug.Shape = shapes["OilPan"], shapes["OilDrainPlug"]
        doc.recompute()
        assert abs(old_volume-pan.Shape.Volume) < 1e-3
        assert pan.Shape.distToShape(plug.Shape)[0] < 1e-6
        for obj in (pan, plug):
            obj.Shape.check()
            assert len(obj.Shape.Solids) == 1 and obj.Shape.Solids[0].isClosed()
            for other in doc.Objects:
                if other == obj or not hasattr(other, "Shape"):
                    continue
                if obj.Shape.BoundBox.intersect(other.Shape.BoundBox):
                    assert abs(obj.Shape.common(other.Shape).Volume) < 1e-5, other.Name
        # The saved sump has an open oilway when the plug is removed.
        b = plug.Shape.optimalBoundingBox(False)
        probe = Part.makeCylinder(9, 12, App.Vector(b.Center.x, b.Center.y, b.ZMax-7))
        assert abs(pan.Shape.common(probe).Volume) < 1e-6
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
