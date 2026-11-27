"""Shape the sloping columns between plug bays below the registered head-bolt seats."""
from pathlib import Path

import FreeCAD as App
import Part

from build_head_main_row import centers, cylinder, verify
from config import layout, load
from head_flanks import oval_loft

V = App.Vector


def shoulders(params, frame):
    head = params["head_lower_casting_estimated"]["value"]
    rows = params["head_plug_buttresses_estimated"]["value"]
    bolts = centers(layout(params, frame)["centers"])
    main_radius = params["casting_visual_estimated"]["value"]["deck_hole_radius"]
    seat = head["head_bolt_boss_top_z_mm"]
    solids = []
    for (x, y), (lean, width, outside) in zip(bolts, rows, strict=True):
        web = oval_loft([
            (x + lean, outside + 13, 5, width * .70, 9),
            (x + lean, outside + 10, 12, width, 10),
            (x + lean * .8, outside + 12, 24, width * .85, 11),
            (x + lean * .4, y - 15, 38, width * .72, 11),
            (x + lean * .1, y - 7, 51, width * .67, 10),
            (x, y, seat - 1, 10, 10),
        ])
        solids.append(web.cut(cylinder(x, y, main_radius, 0, seat)))
    return solids


def run(source, destination):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        additions = shoulders(params, frame)
        base, = doc.HeadLower.Shape.Solids
        head = base.fuse(additions)
        assert head.isValid() and len(head.Solids) == 1 and head.Solids[0].isClosed()
        assert head.Volume > doc.HeadLower.Shape.Volume
        for column in additions:
            for obj in doc.Objects:
                if obj.Name == "HeadLower" or not hasattr(obj, "Shape"):
                    continue
                if column.BoundBox.intersect(obj.Shape.BoundBox):
                    assert abs(column.common(obj.Shape).Volume) < 1e-5, obj.Name
        doc.HeadLower.Shape = head
        doc.Label = destination.stem
        doc.recompute()
        verify(doc, params, frame)
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
