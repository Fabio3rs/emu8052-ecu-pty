"""A5 photo revision. Cast profiles in mm, estimated from uncalibrated views."""
import math
import FreeCAD as App
import Part
from head_profiles import capsule
from manifold_profiles import flange
from valvetrain_layout import valves

V = App.Vector
UP = V(0, 0, 1)
SIDE = V(0, 1, 0)


def union(parts):
    return parts[0].multiFuse(parts[1:]).removeSplitter()


def duct(points, radius, final_bend=22):
    """Constant section on straight runs with tangent circular bends."""
    points = [V(*point) for point in points]
    solids, start = [], points[0]
    for i, (a, corner, b) in enumerate(zip(points, points[1:], points[2:])):
        bend_radius = final_bend if i == len(points)-3 else 22
        incoming, outgoing = a - corner, b - corner
        u, v = incoming.normalize(), outgoing.normalize()
        half_cos = (u + v).Length / 2
        half_sin = (1-half_cos**2)**.5
        trim = bend_radius * half_cos / half_sin
        assert trim < min((corner-start).Length, (b-corner).Length)
        first, last = corner + u*trim, corner + v*trim
        solids.append(Part.makeCylinder(radius, (first-start).Length, start, -u))
        center = corner + (u+v).normalize() * (bend_radius/half_sin)
        disk = Part.Face(Part.Wire([Part.makeCircle(radius, first, -u)]))
        solids.append(disk.revolve(center, (-u).cross(v), math.degrees((-u).getAngle(v))))
        start = last
    delta = points[-1] - start
    solids.append(Part.makeCylinder(radius, delta.Length, start, delta))
    return union(solids)


def exhaust(params, frame):
    """Photos 881888, 626156, 812541. Outer pair and inner pair exit separately."""
    h = params['head_lower_casting_estimated']['value']
    p = params['manifold_visual_estimated']['value']
    photo = params['manifold_photo_review_estimated']['value']
    rows = [r for r in valves(params, frame) if r['kind'] == 'exhaust']
    xs = [r['axis_origin_mm'][0] for r in rows]
    cx = (xs[0] + xs[-1]) / 2
    y = h['manifold_face_y_mm'] + p['gasket_mm']
    z, radius = h['exhaust_port_z_mm'], h['exhaust_port_radius_mm']
    bottom, wall = photo['exhaust_exit_z'], 4
    shell, cores, outlets = [], [], []
    outer_y, inner_y = photo['exhaust_exit_centers_y']
    for pair, ports, end_y in [('outer', [xs[0], xs[3]], outer_y),
                               ('inner', xs[1:3], inner_y)]:
        bottom_center = V(cx, end_y, bottom)
        outlets.append(bottom_center)
        core = [Part.makeCylinder(photo['exhaust_exit_radius'], 22, bottom_center - UP, UP)]
        shell.append(Part.makeCylinder(photo['exhaust_exit_radius']+wall, 26, bottom_center, UP))
        for x in ports:
            dx = x - cx
            sign = 1 if dx > 0 else -1
            points = [(x, y, z), (x, y+20, z)]
            if pair == 'outer':
                points += [(x-sign*20, y+38, z-10), (cx+sign*11, end_y-2, -11)]
            else:
                points += [(cx+dx*.80, end_y-32, z+4), (cx+sign*8, end_y-2, 1)]
            points.append((cx+sign*4, end_y, bottom+10))
            core.append(duct(points, radius))
            shell.append(duct(points, radius+wall))
        cores.append(union(core))
    for group in (rows[:1], rows[1:3], rows[3:]):
        shell.append(flange(group, params, y, p['flange_mm'], 6))
    # The paired center entries share a cast back, visible in 626156 and 670103.
    profiles = []
    for yy, half, zz in [(80,28.5,23), (131,26,25), (166,23,26),
                         (180,20,22), (194,15,11), (202,9,0)]:
        section = capsule((cx-half, zz), (cx+half, zz), 11, 11)
        section.rotate(V(), V(1,0,0), 90)
        section.translate(V(0,yy,0))
        profiles.append(section)
    shell.append(Part.makeLoft(profiles, True, True))
    # End-pad ears and center pad aperture are visible in photo 859499.
    seats = [(xs[0]-17, z-14), (cx, z-11), (xs[-1]+17, z-14)]
    for x, zz in seats:
        shell.append(Part.makeCylinder(8.5, p['flange_mm'], V(x,y,zz), SIDE))
    # Offset stagger of the four M8 studs is visible on the gasket face, 812541.
    contour = capsule((cx, outlets[0].y), (cx, outlets[1].y), 30, 30, bottom)
    plate = Part.Face(contour).extrude(UP * 8)
    studs = []
    holes = [Part.makeCylinder(4, p['flange_mm']+2, V(x,y-1,zz), SIDE) for x, zz in seats]
    for x, yy, zz in [(xs[0]+3, y+21, 33), (xs[-1]-3, y+21, 33),
                       (cx, 112, 34), (cx-6, 190, 20)]:
        shell.append(Part.makeCone(8, 6, 16, V(x,yy,zz-4)))
        holes.append(Part.makeCylinder(2.8, 4, V(x,yy,zz+9)))
    for side in (-1, 1):
        for outlet in outlets:
            root = V(cx+side*23, outlet.y+side*10, bottom)
            holes.append(Part.makeCylinder(4, 10, root-UP, UP))
            studs.append(Part.makeCylinder(4, 27, root-UP*19, UP))
    casting = union(shell+[plate]).cut(union(cores+holes)).removeSplitter()
    # Each stud touches its flange, with an unthreaded visual envelope.
    studs = [stud.cut(casting).removeSplitter() for stud in studs]
    assert all(g.isValid() and len(g.Solids) == 1 for g in [casting, *cores, *studs])
    assert cores[0].distToShape(cores[1])[0] > 1
    return casting, cores, studs
