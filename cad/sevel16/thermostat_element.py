"""Static visible bridge, spring and wax element registered to the water flange."""
import math

import FreeCAD as App
import Part

from head_water_end import AXIS, datum

V = App.Vector
STEM_RADIUS = 3.8
DISC_THICKNESS = 1.5


def separate_disc(original, params, frame):
    h, project = datum(params,frame)
    dims = params["thermostat_element_estimated"]["value"]
    base = (project((427,915)) + AXIS*(h["water_end_flange_depth_mm"]+dims["seat_x"])
            + V(0,0,dims["center_z"]))
    disc = Part.makeCylinder(dims["disc_radius"],DISC_THICKNESS,base,AXIS).cut(
        Part.makeCylinder(STEM_RADIUS,DISC_THICKNESS,base,AXIS))
    capsule = original.cut(disc).removeSplitter()
    assert len(capsule.Solids)==len(disc.Solids)==1
    assert abs(capsule.Volume+disc.Volume-original.Volume)<1e-6
    assert abs(disc.cut(original).Volume)<1e-6 and abs(capsule.common(disc).Volume)<1e-6
    return capsule,disc


def build(housing, params, frame):
    h, project = datum(params, frame)
    dims = params["thermostat_element_estimated"]["value"]
    center = project((427,915)) + AXIS*h["water_end_flange_depth_mm"] + V(0,0,dims["center_z"])
    front = dims["bridge_x"]
    back = front + dims["bridge_thickness"]
    seat = dims["seat_x"]

    def cylinder(radius, x0, x1):
        return Part.makeCylinder(radius, x1-x0, center + AXIS*x0, AXIS)

    ring = cylinder(dims["ring_outer"], front, back).cut(cylinder(dims["ring_inner"], front-1, back+1))
    posts, tabs = [], []
    for sign in (-1, 1):
        y = sign*dims["post_y"]
        # The upper face of each post supports the underside of the stamped bridge.
        section = [(back,-2.1), (back,2.1), (1,2.1), (3,7.1), (7,7.1), (7,-2.1)]
        pts = [center+V(x,y+sign*offset,-3.8) for x,offset in section]
        posts.append(Part.Face(Part.makePolygon(pts+pts[:1])).extrude(V(0,0,7.6)))
        side0 = min(sign*8.5, y+sign*2.1)
        tabs.append(Part.makeBox(back-front, abs(y)+2.1-8.5, 5.6, center+V(front,side0,-2.8)))
    casing = housing.fuse(posts).removeSplitter()
    bridge = ring.fuse(tabs).removeSplitter()

    # The central capsule and the poppet move together in a real thermostat.
    # Here both are shown in the fixed bench-photo position.
    element = cylinder(5.9, front-.9, back+5).fuse([
        cylinder(STEM_RADIUS, back+4, seat+.4), cylinder(dims["disc_radius"], seat, seat+DISC_THICKNESS)
    ]).removeSplitter()
    collar = cylinder(dims["seat_outer_radius"], seat+1.5, seat+3.8)
    collar = collar.cut(cylinder(dims["seat_inner_radius"], seat+1, seat+4)).cut(casing)
    wire = dims["wire_radius"]
    mean = dims["spring_radius"]
    length = seat-back-2*wire
    for _ in range(4):
        axial = wire/math.sqrt(1+(length/(dims["turns"]*2*math.pi*mean))**2)
        length = seat-back-2*axial
    pitch = length/dims["turns"]
    guide = Part.makeHelix(pitch, length, mean).Edges[0]
    # Sweeping one full helix puts a C0 spline seam on the exchanged wire.
    # Short arcs follow the same guide and keep both native and STEP faces smooth.
    segments = math.ceil(4*dims["turns"])
    u0, u1 = guide.FirstParameter, guide.LastParameter
    knots = [u0+(u1-u0)*i/segments for i in range(segments+1)]
    helix = Part.Wire([guide.Curve.toShape(a,b) for a,b in zip(knots,knots[1:])])
    edge = helix.Edges[0]
    loop = Part.Wire([Part.makeCircle(wire,edge.valueAt(edge.FirstParameter),
                                      edge.tangentAt(edge.FirstParameter))])
    spring = helix.makePipeShell([loop], True, True)
    # End planes of a helical circular section reach slightly less than one
    # full wire radius along the axis. Bring the wire into contact at each end.
    axial = wire/math.sqrt(1+(pitch/(2*math.pi*mean))**2)
    spring.rotate(V(), V(0,1,0), 90)
    spring.translate(center + AXIS*(back+axial))
    return casing, [("ThermostatBridge", bridge, (.59,.59,.57)),
                    ("ThermostatElement", element, (.63,.38,.22)),
                    ("ThermostatSeat", collar, (.22,.22,.21)),
                    ("ThermostatReturnSpring", spring, (.34,.35,.34))]
