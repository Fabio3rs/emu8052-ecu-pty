"""Rebuild the SPI cover and plug-side lower rim from the v019 assembly."""
from pathlib import Path

import FreeCAD as App
import Part

from build_head_main_row import verify
from build_spi_pan_floor import DEST as SOURCE
from check_spi_deck_faces import accept, run as check_deck
from config import OUTPUT, load
from geometry_identity import difference
from spi_cover_ribs import profile
from spi_head_front_rim import trim
from valve_cover import build as make_cover

DEST = OUTPUT/"models/SEVEL_Accessories_A5_v020_SPIUpperCastings.FCStd"


def verify_seats(doc):
    head = doc.HeadLower.Shape
    for cylinder in range(1,5):
        shell = doc.getObject(f"C{cylinder}_SparkShell")
        pad = Part.makeCylinder(10,.05).cut(Part.makeCylinder(7.05,.05))
        pad.Placement = shell.Placement
        if abs(pad.cut(head).Volume)>1e-5:
            raise ValueError(f"Washer seat lost at cylinder {cylinder}")
        for suffix in ("Shell","Electrode","Ceramic"):
            plug = doc.getObject(f"C{cylinder}_Spark{suffix}")
            if abs(head.common(plug.Shape).Volume)>1e-5:
                raise ValueError(f"Spark plug overlap at {plug.Name}")


def run(source=SOURCE,destination=DEST):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if not App.GuiUp:
        raise RuntimeError("Build the coloured assembly in the FreeCAD GUI")
    params,frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        neck = params["spi_filler_neck_estimated"]["value"]
        parts = make_cover(params,frame,photo_review=True,neck_sections=neck,cover_profile=profile(params))
        for name in ("OilFillerCap","ValveCoverGasket"):
            assert difference(parts[name],doc.getObject(name).Shape)<1e-5,name
        for name,shape in (("ValveCover",parts["ValveCover"]),("HeadLower",trim(doc.HeadLower.Shape,params,frame))):
            obj = doc.getObject(name)
            placement,color = obj.Placement,obj.ViewObject.ShapeColor
            obj.Shape = shape
            assert obj.Placement==placement and obj.ViewObject.ShapeColor==color,name
        doc.recompute()
        verify_seats(doc)
        verify(doc,params,frame)
        accept(check_deck(doc,params,frame))
        doc.Label = destination.stem
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return destination
