"""Refine the photographed SPI filler shoulder while retaining the cap and seal."""
from pathlib import Path

import FreeCAD as App

from config import load
from valve_cover import build


def run(source, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    updated = build(params, frame, photo_review=True,
                    neck_sections=params["spi_filler_neck_estimated"]["value"])
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        new = updated["ValveCover"]
        assert new.isValid() and len(new.Solids) == 1 and new.Solids[0].isClosed()
        assert new.Volume > doc.ValveCover.Shape.Volume
        for name in ("OilFillerCap", "ValveCoverGasket", "IgnitionCoilMount",
                     "IgnitionCoil", "ThermostatHousing", "CamCarrier"):
            neighbor = doc.getObject(name).Shape
            assert abs(new.common(neighbor).Volume) < 1e-5, name
            if name in ("OilFillerCap", "ValveCoverGasket"):
                assert new.distToShape(neighbor)[0] < 1e-6, name
        doc.ValveCover.Shape = new
        doc.Label = destination.stem
        doc.recompute()
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
