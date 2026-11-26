"""Curved inlet casting and its separate heating gallery, photo review A5."""
import Part
from cam_carrier import rounded_prism
from config import layout
from head_profiles import capsule
from manifold_castings import V, UP, SIDE, union, duct
from manifold_profiles import flange
from valvetrain_layout import valves


def bowl(cx, sections):
    axis = V(cx, 168, 0)
    points = [axis + V(r, 0, z) for z, r in sections]
    curve = Part.BSplineCurve()
    curve.interpolate(points)
    low, high = axis + UP*sections[0][0], axis + UP*sections[-1][0]
    boundary = [Part.makeLine(low, points[0]), curve.toShape(),
                Part.makeLine(points[-1], high), Part.makeLine(high, low)]
    return Part.Face(Part.Wire(boundary)).revolve(axis, UP, 360)


def intake(params, frame, *, polish=False):
    """Photo estimates in mm from 713001, 807385, 909298 and 927431."""
    h = params['head_lower_casting_estimated']['value']
    p = params['manifold_visual_estimated']['value']
    throttle_y = params['manifold_photo_review_estimated']['value']['intake_throttle_y']
    rows = [r for r in valves(params, frame) if r['kind'] == 'intake']
    xs = [r['axis_origin_mm'][0] for r in rows]
    cx = (xs[0]+xs[-1])/2
    y = h['manifold_face_y_mm'] + p['gasket_mm']
    z, r = h['intake_port_z_mm'], h['intake_port_radius_mm']
    shell = [bowl(cx, [(54, 31), (66, 48), (81, 48), (94, 39), (102, 36)])]
    air = [bowl(cx, [(59, 26), (70, 43), (81, 43), (91, 33), (99, 23)])]
    for i, x in enumerate(xs):
        sign = 1 if x > cx else -1
        far = i in (0, 3)
        end_y = 213 if far else 169
        # Both horns of each side branch turn inward into the central bowl.
        path = [(x, y+12, z), (x, y+51, 82),
                (x, end_y+9, 78), (cx+sign*19, end_y-3, 78)]
        bend = 52 if far else 29
        shell.append(duct([(x, y+2, z), *path], r+4.5, bend))
        air.append(duct([(x, y-1, z), *path], r, bend))
    # The front of the plenum joins the broad U below the throttle pad.
    profiles = []
    for dx, yy, ry, rz in [(-55,214,17,16), (-24,208,24,21),
                           (0,206,26,22), (24,208,24,21), (55,214,17,16)]:
        center = V(cx+dx, yy, 78)
        ellipse = Part.Ellipse(center+SIDE*ry, center+UP*rz, center)
        profiles.append(Part.Wire([ellipse.toShape()]))
    shell.append(Part.makeLoft(profiles, True, False))
    air.append(Part.makeCylinder(13, 68, V(cx-34,208,78), V(1,0,0)))
    # Broad shoulders sweep around each pair of runners in the top view 713001.
    shoulders = [(117,164,15,9), (98,177,32,15), (69,185,31,17),
                 (40,189,25,16), (19,190,17,12)]
    if polish:
        shoulders = params['intake_shoulder_sections_estimated']['value']
    for side in (-1, 1):
        profiles = []
        for dx, yy, ry, rz in shoulders:
            center = V(cx+side*dx, yy, 79 if polish else 76)
            ellipse = Part.Ellipse(center+SIDE*ry, center+UP*rz, center)
            profiles.append(Part.Wire([ellipse.toShape()]))
        shell.append(Part.makeLoft(profiles, True, False))
    for group in (rows[:2], rows[2:]):
        shell.append(flange(group, params, y, p['flange_mm'], 6))

    # Underside of the U carries the transverse water gallery (927431).
    water = []
    water_x = layout(params, frame)['supports'][1::2]
    wy, wz, wr = 218, 49, h['coolant_port_radius_mm']
    for x in water_x:
        start = (x, y, h['coolant_port_z_mm'])
        path = [(x, y+15, start[2]), (x, y+57, 51), (x, wy+1, wz)]
        shell.append(duct([(x, y+2, start[2]), *path], wr+4))
        shell.append(Part.makeCylinder(wr+4.5, p['flange_mm'], V(*start), SIDE))
        water.append(duct([(x, y-1, start[2]), *path], wr))
    for rad, parts in [(wr, water), (wr+5, shell)]:
        parts.append(Part.makeCylinder(rad, water_x[-1]-water_x[0],
                                       V(water_x[0], wy, wz), V(1, 0, 0)))
        parts.extend(Part.makeSphere(rad, V(x, wy, wz)) for x in water_x)
    bolts = []
    for x in water_x:
        # Low skirt joins the heating jacket to the runner pair.
        shell.append(rounded_prism(x-24, wy-22, wz+1, 48, 30, 19, 9))
        bolts.append(Part.makeCylinder(3.5, p['flange_mm']+2, V(x, y-1, z+9), SIDE))
    # Cast wall carries the transverse heating gallery and the connection bosses.
    jacket = capsule((wy, wz), (wy-9, 73), 10, 15)
    jacket = Part.Face(jacket).extrude(UP * (water_x[-1]-water_x[0]+6))
    jacket.rotate(V(), V(1,1,1), 120)
    jacket.translate(V(water_x[0]-3,0,0))
    shell.append(jacket)
    for x, radius in [(water_x[0], 10), (cx, 10.5), (water_x[1], 10)]:
        shell.append(Part.makeCylinder(radius, 19, V(x, wy-2, wz+3), SIDE))
        bolts.append(Part.makeCylinder(4.5, 8, V(x, wy+10, wz+3), SIDE))
    for dx in (-30, 0, 30):
        corners = [V(cx+dx-2, yy, zz) for yy, zz in
                   [(125,100), (146,100), (155,64), (138,75)]]
        shell.append(Part.Face(Part.makePolygon(corners+corners[:1])).extrude(V(4,0,0)))
    top = rounded_prism(cx-48, throttle_y-37, 99, 96, 75, 8, 11)
    for side in (-1, 1):
        top = top.cut(Part.makeCylinder(29, 12, V(cx+side*65, throttle_y, 97)))
        for yy in (throttle_y-28, throttle_y+29):
            bolts.append(Part.makeCylinder(3.5, 16, V(cx+side*38, yy, 94)))
    shell.append(top)
    air.append(Part.makeCylinder(p['intake_inlet_radius_mm'], 16, V(cx, throttle_y, 94)))
    dry, wet = union(air), union(water)
    assert dry.distToShape(wet)[0] > 1
    casting = union(shell).cut(dry).cut(wet).cut(Part.makeCompound(bolts)).removeSplitter()
    assert all(s.isValid() and len(s.Solids) == 1 for s in [casting, dry, wet])
    assert casting.Volume > dry.Volume / 3
    return casting, dry, wet
