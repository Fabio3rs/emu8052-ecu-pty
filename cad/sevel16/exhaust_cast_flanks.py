"""Flared outer feet and paired central lobes of exhaust casting 7691880."""
import FreeCAD as App
import Part

V = App.Vector


def flank_wire(x, y, z, rx, rz):
    center = V(x, y, z)
    ellipse = Part.Ellipse(center + V(rx, 0, 0), center + V(0, 0, rz), center)
    return Part.Wire([ellipse.toShape()])


def flanks(params, ports, face_y, port_z):
    section = params["exhaust_cast_flanks_estimated"]["value"]
    center = (ports[0] + ports[-1]) / 2
    result = []
    for sign, port in ((-1, ports[0]), (1, ports[-1])):
        rings = [flank_wire(port + sign * offset, face_y + depth, port_z + dz, rx, rz)
                 for depth, offset, dz, rx, rz in section["feet"]]
        # Short drafted bands keep the ends inside the port boss. A single
        # interpolating spline overshoots the outer bend at the flywheel end.
        result.append(Part.makeLoft(rings, True, True))
    for sign in (-1, 1):
        rings = [flank_wire(center + sign * half, y, z, rx, rz)
                 for y, half, z, rx, rz in section["lobes"]]
        result.append(Part.makeLoft(rings, True, False))
    return result
