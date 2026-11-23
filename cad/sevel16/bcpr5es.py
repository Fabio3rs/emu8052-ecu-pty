"""NGK 6130 visual reconstruction. Local +Z runs from flat gasket seat to chamber."""
import math

import FreeCAD as App
import Part

V = App.Vector
# Nominals supplied for the BCPR5ES; the 0.8 mm gap is the Tipo application value.
DIAMETER, PITCH, REACH, HEX_AF, GAP = 14.0, 1.25, 19.0, 16.0, 0.8
NOSE = REACH + 3.0
ELECTRODE_END = NOSE + 0.8
# User photo estimates (mm); external silhouette from PhotosMotor/BCPR5ES61UgZsbZz6L.jpg.
SEAT_TO_CHAMBER, COUNTERBORE, TERMINAL_HEIGHT = 19.5, 5.0, 53.0
WELL_RADIUS = 11.5


def turned(profile):
    points = [V(r, 0, z) for r, z in profile]
    return Part.Face(Part.makePolygon(points + points[:1])).revolve(V(), V(0, 0, 1), 360)


def shell():
    radius = DIAMETER / 2
    body = turned([(3.5, -15), (6.5, -15), (7.5, -14), (7.5, -6.5),
                   (9.6, -5.5), (9.6, -2.5), (8.7, -2.5), (8.7, -1.7),
                   (10, -1.7), (10, 0), (radius, 0), (radius, REACH - 0.5),
                   (radius - 0.5, REACH), (4.9, REACH), (3.5, REACH - 4)])
    corner = HEX_AF / math.sqrt(3)
    hex_points = [V(corner*math.cos(i*math.pi/3), corner*math.sin(i*math.pi/3), -13.8)
                  for i in range(6)]
    hexagon = Part.Face(Part.makePolygon(hex_points + hex_points[:1])).extrude(V(0, 0, 7))
    body = body.fuse(hexagon.cut(Part.makeCylinder(3.5, 8, V(0, 0, -14))))
    guide = Part.makeHelix(PITCH, REACH - 2, radius)
    groove = [V(radius + 0.15, 0, -0.55), V(radius - 0.60, 0, -0.10),
              V(radius - 0.60, 0, 0.10), V(radius + 0.15, 0, 0.55)]
    tool = guide.makePipeShell([Part.makePolygon(groove + groove[:1])], True, True)
    tool.translate(V(0, 0, 1))
    body = body.cut(tool)
    # Bent ground electrode with a flat face across the center electrode.
    z = ELECTRODE_END + GAP
    pts = [(-6.35, REACH-0.6), (-5.05, REACH-0.6), (-5.05, z-1),
           (-4.05, z), (0.9, z), (0.9, z+1.2), (-4.6, z+1.2), (-6.35, z-0.55)]
    outline = [V(x, -1.2, height) for x, height in pts]
    strap = Part.Face(Part.makePolygon(outline + outline[:1])).extrude(V(0, 2.4, 0))
    return body.fuse(strap).removeSplitter()


def build():
    ceramic = turned([(1.15, -43.5), (3.8, -43.5), (4.7, -42.5), (4.7, -30),
                      (5.25, -29), (5.25, -15), (3.5, -15), (3.5, REACH-4),
                      (1.65, NOSE), (1.15, NOSE)])
    for z in (-41, -38.5, -36, -33.5, -31):
        ceramic = ceramic.fuse(Part.makeTorus(4.65, 1.0, V(0, 0, z)))
    terminal = turned([(0, -TERMINAL_HEIGHT), (2.5, -TERMINAL_HEIGHT),
                       (3.25, -52.1), (3.25, -50), (2.55, -48.6), (2.55, -46.4),
                       (3.1, -45.6), (3.1, -43.5), (1.15, -43.5),
                       (1.15, ELECTRODE_END), (0, ELECTRODE_END)])
    return dict(Shell=shell(), Ceramic=ceramic.removeSplitter(), Electrode=terminal)
