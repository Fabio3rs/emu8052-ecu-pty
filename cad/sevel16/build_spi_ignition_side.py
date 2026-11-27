"""Rebuild the cast spark pockets and identified cable ends of the installed SPI."""
import json
from pathlib import Path

import FreeCAD as App

from assembly import add_part
from build_head_main_row import verify
from build_spi_cast_details import verify_mounts
from build_spi_upper_castings import DEST as SOURCE, verify_seats
from check_spi_deck_faces import accept, run as check_deck
from config import OUTPUT, load
from head_blank import oil_tray
from head_passages import chambers, port
from spi_ignition_boots import build as make_boots
from spi_spark_bays import revise, third_foot, tool_for_bay
from valvetrain_layout import valves

DEST = OUTPUT/"models/SEVEL_Accessories_A5_v021_SPIIgnitionSide.FCStd"


def inspect_bay_clearances(doc,params,frame):
    layout = params["valvetrain_layout_estimated"]["value"]
    floor = layout["outer_spring_seat_z_mm"]-layout["spring_seat_thickness_mm"]
    tray = oil_tray(params,frame,floor,65)
    combustion = chambers(params,frame)
    rows = valves(params,frame)
    report = {}
    for i in range(4):
        tool = tool_for_bay(doc,params,frame,i)
        protected = {"oil_tray":tray,"chamber":combustion[i],"carrier_gasket":doc.CarrierGasket.Shape}
        protected.update({row["kind"]+"_port":port(params,row) for row in rows[2*i:2*i+2]})
        gaps = {name:tool.distToShape(shape)[0] for name,shape in protected.items()}
        if min(gaps.values())<=1:
            raise ValueError(f"Spark bay C{i+1} close to protected geometry: {gaps}")
        report[f"C{i+1}"] = gaps
    return report


def run(source=SOURCE,destination=DEST,report_path=None):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if not App.GuiUp:
        raise RuntimeError("Build the coloured assembly in the FreeCAD GUI")
    params,frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        report = {"distance_from_bay_tools_mm":inspect_bay_clearances(doc,params,frame)}
        previous = doc.HeadLower.Shape
        sculpted = revise(doc,previous,params,frame,range(4))
        final = third_foot(sculpted,params,frame)
        report["cast_removed_mm3"] = previous.Volume-final.Volume
        report["third_foot_removed_mm3"] = sculpted.Volume-final.Volume
        doc.HeadLower.Shape = final
        mounts = {}
        for name,shape,color in make_boots(doc,params):
            if doc.getObject(name):
                raise ValueError(f"Duplicated ignition piece: {name}")
            add_part(doc,name,shape,color=color)
            mounts[name] = "IgnitionCoil" if "Boot" in name else name.replace("Lead","Boot")
        doc.recompute()
        verify_seats(doc)
        verify(doc,params,frame)
        accept(check_deck(doc,params,frame))
        verify_mounts(doc,mounts)
        report["supports"] = mounts
        doc.Label = destination.stem
        doc.saveAs(str(destination))
        if report_path:
            Path(report_path).write_text(json.dumps(report,indent=2)+"\n")
    finally:
        App.closeDocument(doc.Name)
    return destination
