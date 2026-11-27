"""Build the open-carrier crown and preserve the support of the inclined cover gasket."""
from pathlib import Path

import FreeCAD as App
import Part

from build_spi_ignition_side import DEST as SOURCE
from config import OUTPUT, layout, load
from spi_carrier_crown import revise

DEST = OUTPUT/"models/SEVEL_Accessories_A5_v022_SPIBridgeWindows.FCStd"
V = App.Vector


def verify(doc,before,after,params,frame):
    angle = params["carrier_section_estimated"]["value"]["top_slope_y_deg"]
    normal = App.Rotation(V(1,0,0),angle).multVec(V(0,0,1))
    seal = doc.ValveCoverGasket.Shape.copy()
    seal.translate(-normal*.25)
    backing = [s.common(seal).Volume for s in (before,after)]
    assert min(backing)>0 and abs(backing[0]-backing[1])<1e-5
    v = params["valvetrain_layout_estimated"]["value"]
    n = params["valvetrain_nominal"]["value"]
    w = v["cam_journal_width_mm"]
    allowance = params["spi_carrier_crown_estimated"]["value"]["journal_wall_allowance"]
    for i,x in enumerate(layout(params,frame)["supports"]):
        j = v["cam_diagram_indices_in_positive_x"][i]
        radius = n["cam_housing_diameters_diagram_order_mm"][j]/2
        origin = V(x-w/2+.01,0,v["cam_axis_z_mm"])
        ring = Part.makeCylinder(radius+allowance-.01,w-.02,origin,V(1,0,0))
        ring = ring.cut(Part.makeCylinder(radius+.01,w,origin-V(.01,0,0),V(1,0,0)))
        assert abs(before.common(ring).Volume-after.common(ring).Volume)<1e-5,("Journal land",i)
    for name in ("Camshaft","ValveCover","IgnitionCoilMount","CarrierGasket"):
        other = doc.getObject(name).Shape
        assert abs(before.common(other).Volume-after.common(other).Volume)<1e-5,name
    return backing


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
        old = doc.CamCarrier.Shape
        new = revise(old,params,frame)
        verify(doc,old,new,params,frame)
        doc.CamCarrier.Shape = new
        doc.recompute()
        doc.Label = destination.stem
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return destination
