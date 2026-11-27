"""Build the accessory-side skirt and separate the dark thermostat valve disc."""
from pathlib import Path

import FreeCAD as App

from assembly import add_part
from build_spi_cast_details import verify_mounts
from build_spi_deck_faces import DEST as SOURCE
from check_spi_deck_faces import accept, run as inspect_deck
from config import OUTPUT, load
from spi_filter_wall import build as filter_wall
from thermostat_element import separate_disc

DEST = OUTPUT/"models/SEVEL_Accessories_A5_v018_SPIFilterWall.FCStd"
CHANGED = ("Block","ThermostatElement")
DISC = "ThermostatValveDisc"


def run(source=SOURCE, destination=DEST):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if not App.GuiUp:
        raise RuntimeError("Build the visual checkpoint in the FreeCAD GUI to preserve assembly colours")
    params,frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        original = doc.Block.Shape
        doc.Block.Shape = filter_wall(original,params,frame)
        capsule,disc = separate_disc(doc.ThermostatElement.Shape,params,frame)
        doc.ThermostatElement.Shape = capsule
        add_part(doc,DISC,disc,color=(.27,.28,.27)).Label = "Disco da válvula termostática"
        doc.recompute()
        verify_mounts(doc,{DISC:"ThermostatSeat","ThermostatElement":DISC})
        assert doc.ThermostatReturnSpring.Shape.distToShape(disc)[0]<1e-6
        assert len({o.PartId for o in doc.Objects if hasattr(o,"Shape")})==241
        accept(inspect_deck(doc,params,frame))
        doc.Label = destination.stem
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return destination
