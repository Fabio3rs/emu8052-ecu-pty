"""Removable dark breather with a perforated pad, offset dome and insertion spigot."""
from pathlib import Path

import FreeCAD as App
import Part

from block_pcv_review import SEAT_TILT_DEG, circle, inclined
from config import layout, load

V = App.Vector


def fitting(params, frame):
    p = params["casting_visual_estimated"]["value"]
    dims = params["breather_profile_estimated"]["value"]
    xs = layout(params, frame)["centers"]
    x = xs[0] + (xs[-1] - xs[0]) * p["access_open_x_fraction"]
    seat = V(x, -96, p["access_open_z"] + 20)
    axis = inclined(SEAT_TILT_DEG)
    outward = V(0, -axis.z, axis.y)
    sections = [circle(seat + axis*z + outward*offset, axis, radius)
                for z, radius, offset in dims["dome"]]
    cap = Part.makeLoft(sections, True, False)
    bottom = seat - axis * dims["spigot_length"]
    spigot = Part.makeCylinder(dims["spigot_radius"], dims["spigot_length"]+2, bottom, axis)
    hose = inclined(dims["outlet_tilt"])
    root = seat + axis*12 + outward*10 + V(-6,0,0)
    tube = Part.makeCylinder(8.5, 34, root, hose)
    pad = seat + axis*16 + V(8,0,0) - outward*2
    boss = Part.makeCone(8.5, 5.8, 10, pad, axis)
    lip = Part.makeCylinder(9.1, 2.4, root + hose*31.6, hose)
    shell = cap.fuse([spigot, tube, lip, boss])
    tools = [Part.makeCylinder(dims["spigot_bore"], dims["spigot_length"]+15, bottom-axis, axis),
             Part.makeCylinder(6.1, 41, root-hose*6, hose),
             Part.makeCylinder(2.6, 20, pad-axis*7, axis)]
    result = shell.cut(tools).removeSplitter()
    assert result.isValid() and len(result.Solids) == 1 and result.Solids[0].isClosed()
    return result


def run(source, destination, make_fitting=fitting):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    shaped = make_fitting(*load())
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        for obj in doc.Objects:
            if obj.Name != "PCVBreatherOutlet" and hasattr(obj, "Shape"):
                if shaped.BoundBox.intersect(obj.Shape.BoundBox):
                    assert abs(shaped.common(obj.Shape).Volume) < 1e-5, obj.Name
        assert shaped.distToShape(doc.Block.Shape)[0] < 1e-5
        doc.PCVBreatherOutlet.Shape = shaped
        if App.GuiUp:
            doc.PCVBreatherOutlet.ViewObject.ShapeColor = (.18,.17,.16)
        doc.Label = destination.stem
        doc.recompute()
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
