"""Photo-estimated cast cheeks, fixing pads and manifold webs, in head datum mm."""
import math
import FreeCAD as App
import Part
from build_spark_review import pocket_tools
from config import layout
from valvetrain_layout import valves
from head_passages import port
from head_profiles import clipping_slab

V = App.Vector
UP = V(0, 0, 1)


def oval_loft(rows):
    wires = []
    for x, y, z, rx, ry in rows:
        center = V(x, y, z)
        edge = Part.Ellipse(V(x+rx, y, z), V(x, y+ry, z), center) if rx >= ry else (
            Part.Ellipse(V(x, y+ry, z), V(x-rx, y, z), center))
        # Keep the seam at +X throughout the loft even when the major axis changes.
        seam = 0 if rx >= ry else -math.pi/2
        wires.append(Part.Wire([edge.toShape(seam, seam+2*math.pi)]))
    return Part.makeLoft(wires, True, False)


def spark_face(doc, params, frame, *, upright_lower_bores=False, lower_pads=True):
    head = doc.HeadLower.Shape.copy()
    stations = layout(params, frame)
    block = params['casting_visual_estimated']['value']
    tools, feet = [], []
    # 723789, 726745, cabeçote_cima: broader feet, with unequal bay cheeks.
    for x, width in zip(stations['supports'], (16, 24, 21, 23, 15)):
        web = oval_loft([(x, -63, 4, width, 12), (x, -64, 12, width-.5, 12),
                         (x+1, -63, 24, width-3, 10), (x, -62, 43, 12, 9),
                         (x, -61, 58, 9, 8)])
        bore = Part.makeCylinder(block['deck_hole_radius'], 64, V(x, -block['deck_hole_y'], 0))
        feet.append(web.cut(bore))
    head = head.fuse(feet).removeSplitter()
    for i, (x, profile) in enumerate(zip(stations['centers'],
            ((1.04, 6, -3), (1.12, 8, 3), (1.07, 5, -2), (1.02, 7, 2))), 1):
        place = doc.getObject(f'C{i}_SparkShell').Placement
        tools.append(pocket_tools(x, place, profile))
    head = head.cut(tools).removeSplitter()
    if not lower_pads:
        return head
    # Small blind drilled bosses on the lower shelf beside the plug wells.
    pads, drills = [], []
    for x, offset in zip(stations['centers'], (-22, 22, -21, 22)):
        tip = V(x+offset, -69, 19)
        aim = UP if upright_lower_bores else V(0, -.87, .49).normalize()
        pad = Part.makeCone(10, 6.8, 20, tip-aim*20, aim)
        pads.append(pad.common(Part.makeBox(36,48,30,V(tip.x-18,-82,6))))
        drills.append(Part.makeCylinder(3.1, 10, tip-aim*9, aim))
    return head.fuse(pads).cut(drills).removeSplitter()


def manifold_face(head, params, frame):
    # 621331: webs sweep down into the port bosses behind the machined face.
    webs = []
    supports = layout(params, frame)['supports']
    for x, lean in zip(supports, (5, -6, 4, -6, -5)):
        webs.append(oval_loft([(x, 60, 38, 11, 9), (x, 59, 45, 10, 10),
                               (x+lean*.5, 51, 57, 7, 11), (x+lean, 39, 69, 5, 8),
                               (x+lean, 36, 73, 4, 3)]))
    block = params['casting_visual_estimated']['value']
    holes = [Part.makeCylinder(block['deck_hole_radius'], 90, V(x, block['deck_hole_y'], 0))
             for x in supports]
    holes.extend(port(params,row) for row in valves(params,frame))
    # Trim at the very same sloping joint plane used for the head blank.
    wall = params['head_lower_casting_estimated']['value']['carrier_gasket_vertical_thickness_mm']
    stock = Part.makeCompound(webs).common(clipping_slab(params,frame,1.2,wall)).cut(holes)
    return head.fuse(stock).removeSplitter()
