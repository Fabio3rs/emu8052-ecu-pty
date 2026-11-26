"""Test whether the photographed fastener stations fit all three mating lands."""
import json
from pathlib import Path

import FreeCAD as App
import Part

from config import load
from stationary import _sump


def inspect(doc, output):
    params, frame = load()
    block = params['block_visual_estimated']['value']
    sump = params['sump_outline_estimated']['value']
    closures = params['external_closures_estimated']['value']
    z = -block['height']
    rim = _sump.outline(params, frame, z)
    box = rim.BoundBox
    v = App.Vector
    centers = []
    # Pixel positions of fastening groups on gasket 980809. Outer bounds
    # register long-axis stations; intersect the CAD rim to allow for its
    # two unequal setbacks and the unknown projective distortion of the photo.
    for side, pixels in [(1,[133,255,392,523,655,788,920]),
                         (-1,[169,283,406,533,656,788,919])]:
        for u in pixels:
            x = box.XMin + (u-49)/947*box.XLength
            line = Part.makeLine(v(x,-150,z),v(x,150,z))
            ys = [p.Point.y for p in rim.section(line).Vertexes]
            y = max(ys) if side == 1 else min(ys)
            centers.append((x,y-side*sump['wall_inset']/2))
    for side, pixels in [(-1,[104,228,353,474]),(1,[147,323])]:
        for py in pixels:
            y = box.YMax-(py-25)/508*box.YLength
            line = Part.makeLine(v(box.XMin-2,y,z),v(box.XMax+2,y,z))
            xs = [p.Point.x for p in rim.section(line).Vertexes]
            x = min(xs) if side == -1 else max(xs)
            centers.append((x-side*closures['pan_inner_end_flange_mm']/2,y))
    gasket = closures['pan_gasket_mm']
    checks = []
    for x,y in centers:
        row = {'x_mm':x, 'y_mm':y, 'land_fraction':{}}
        for obj, start, depth in [(doc.Block,z,1), (doc.OilPanGasket,z-gasket,gasket),
                                   (doc.OilPan,z-gasket-closures['pan_flange_mm'],closures['pan_flange_mm'])]:
            # Provisional M6 clearance Ø6.6 plus 0.5 mm of surrounding land.
            probe = Part.makeCylinder(3.8,depth,v(x,y,start))
            row['land_fraction'][obj.Name] = probe.common(obj.Shape).Volume/probe.Volume
        checks.append(row)
    Path(output).write_text(json.dumps(checks,indent=2))
    return checks
