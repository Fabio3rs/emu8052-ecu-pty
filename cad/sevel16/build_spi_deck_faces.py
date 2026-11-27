"""Build and verify the three photographed surfaces of the SPI deck joint."""
import json
from pathlib import Path

import FreeCAD as App

from build_head_main_row import verify as verify_fixings
from build_spi_end_accessories import DEST as SOURCE
from check_spi_deck_faces import accept, run as inspect
from config import OUTPUT, load
from spi_deck_surfaces import casting, gasket, registration

DEST = OUTPUT/"models/SEVEL_Accessories_A5_v017_SPIRegisteredDeck.FCStd"
CHANGED = ("HeadGasket","Block","HeadLower")


def run(source=SOURCE, destination=DEST, report_path=None, geometry_checkpoint=None):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if destination==DEST and not App.GuiUp:
        raise RuntimeError("Build the visual checkpoint in the FreeCAD GUI to preserve assembly colours")
    params,frame = load()
    data = registration(params,frame)
    doc = App.newDocument(destination.stem)
    geometry = None
    try:
        doc.mergeProject(str(source))
        colors = ({o.Name:tuple(o.ViewObject.ShapeColor) for o in doc.Objects if hasattr(o,"Shape")}
                  if App.GuiUp else {})
        if geometry_checkpoint is not None:
            geometry = App.openDocument(str(geometry_checkpoint))
        for name in CHANGED:
            obj = doc.getObject(name)
            pos = obj.Placement
            if geometry is not None:
                obj.Shape = geometry.getObject(name).Shape.copy()
            else:
                obj.Shape = gasket(params,frame,data) if name=="HeadGasket" else casting(obj.Shape,name,params,data)
            obj.Placement = pos
        doc.recompute()
        report = inspect(doc,params,frame)
        if report_path is not None:
            with Path(report_path).open("x") as handle:
                json.dump(report,handle,indent=2)
                handle.write("\n")
        accept(report)
        verify_fixings(doc,params,frame)
        assert len({o.PartId for o in doc.Objects if hasattr(o,"Shape")})==240
        for name,color in colors.items():
            assert tuple(doc.getObject(name).ViewObject.ShapeColor)==color,name
        doc.Label = destination.stem
        doc.saveAs(str(destination))
    finally:
        if geometry is not None:
            App.closeDocument(geometry.Name)
        App.closeDocument(doc.Name)
    return destination
