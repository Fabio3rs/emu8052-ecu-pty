"""Build the owner-photographed coil bracket, thermostat internals and hose clamps."""
from pathlib import Path

import FreeCAD as App

from assembly import add_part
from build_spi_cast_details import DEST as SOURCE, verify_mounts
from config import OUTPUT, load
from head_ignition import build as ignition
from thermostat_element import build as element
from thermostat_hose_clamps import build as hose_clamps

DEST = OUTPUT / "models/SEVEL_Accessories_A5_v016_SPIEndAccessories.FCStd"
CHANGED = ("IgnitionCoilMount", "ThermostatHousing", "ThermostatMainHose", "ThermostatBranchHose")
MOUNTS = {"ThermostatBridge": "ThermostatHousing", "ThermostatElement": "ThermostatSeat",
          "ThermostatSeat": "ThermostatHousing", "ThermostatReturnSpring": "ThermostatBridge",
          "ThermostatMainClamp": "ThermostatMainHose", "ThermostatBranchClamp": "ThermostatBranchHose"}


def verify(doc):
    verify_mounts(doc, MOUNTS, CHANGED)
    assert doc.ThermostatElement.Shape.distToShape(doc.ThermostatReturnSpring.Shape)[0] < 1e-6
    assert len({o.PartId for o in doc.Objects if hasattr(o,"Shape")}) == 240


def run(source=SOURCE, destination=DEST):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        coil = ignition(params,frame,mount_profile=params["coil_mount_shoulder_estimated"]["value"])
        housing, inside = element(doc.ThermostatHousing.Shape, params, frame)
        shapes, clamps = hose_clamps(doc, params, frame)
        shapes.update(IgnitionCoilMount=coil["IgnitionCoilMount"], ThermostatHousing=housing)
        for name, shape in shapes.items():
            obj = doc.getObject(name)
            placement = obj.Placement
            obj.Shape = shape
            obj.Placement = placement
        for name, shape, color in inside + clamps:
            if doc.getObject(name) is not None:
                raise ValueError("Accessory already present: " + name)
            add_part(doc, name, shape, color=color)
        doc.Label = destination.stem
        doc.recompute()
        verify(doc)
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return destination
