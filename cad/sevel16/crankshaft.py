"""SEVEL crank in local coordinates: X axis through origin, C1 throw along +Z."""
import math
import FreeCAD as App
import Part
from config import layout

V = App.Vector
AXIS = V(1, 0, 0)


def cylinder(radius, left, width, z=0):
    return Part.makeCylinder(radius, width, V(left, 0, z), AXIS)


def cheek(left, width, main_r, pin_r, throw, counter_r, half_angle):
    # Convex hull of the two journal disks, with exact circular end arcs.
    t = (main_r-pin_r)/throw
    if not -1 < t < 1:
        raise ValueError('Journal radii do not permit this tangent web')
    s = math.sqrt(1-t*t)
    a, b = V(left, main_r*s, main_r*t), V(left, pin_r*s, throw+pin_r*t)
    c, d = V(left, -pin_r*s, throw+pin_r*t), V(left, -main_r*s, main_r*t)
    edges = [Part.makeLine(a, b), Part.Arc(b, V(left,0,throw+pin_r), c).toShape(),
             Part.makeLine(c, d), Part.Arc(d, V(left,0,-main_r), a).toShape()]
    shape = Part.Face(Part.Wire(edges)).extrude(V(width,0,0))
    if counter_r:
        angle = math.radians(half_angle)
        a = V(left, counter_r*math.sin(angle), -counter_r*math.cos(angle))
        b = V(left, -a.y, a.z)
        center = V(left,0,0)
        edges = [Part.makeLine(center,a), Part.Arc(a,V(left,0,-counter_r),b).toShape(),
                 Part.makeLine(b,center)]
        shape = shape.fuse(Part.Face(Part.Wire(edges)).extrude(V(width,0,0)))
    return shape


def build(params, frame):
    g, p = layout(params, frame), params['moving_geometry_estimated']['value']
    nominal = params['moving_nominal']
    mr, pr = nominal['main_journal_diameter_mm']['value']/2, nominal['crankpin_diameter_mm']['value']/2
    mw, pw = p['main_journal_width_mm'], p['crankpin_width_mm']
    xs, supports, r = g['centers'], g['supports'], g['radius']
    shapes = [cylinder(mr, x-mw/2, mw) for x in supports]
    interfaces = {'main_centers_local_mm': [[x,0,0] for x in supports],
                  'pin_centers_local_mm': [], 'web_axial_intervals_mm': []}
    for i, x in enumerate(xs):
        phase = 180 if i in (1,2) else 0
        pin = cylinder(pr, x-pw/2, pw, r)
        pin.rotate(V(), AXIS, phase)
        shapes.append(pin)
        interfaces['pin_centers_local_mm'].append([x,0,r if phase == 0 else -r])
        intervals = [(supports[i]+mw/2, x-pw/2), (x+pw/2, supports[i+1]-mw/2)]
        for side, (left, right) in enumerate(intervals):
            if right <= left:
                raise ValueError('No axial room for crank cheek')
            counter = p['counterweight_radius_mm'] if 2*i+side in p['counterweight_web_indices'] else 0
            web = cheek(left, right-left, mr, pr, r, counter, p['counterweight_half_angle_deg'])
            web.rotate(V(), AXIS, phase)
            shapes.append(web)
            interfaces['web_axial_intervals_mm'].append([left,right])
    front, rear = supports[0]-mw/2, supports[-1]+mw/2
    shapes += [cylinder(p['nose_radius_mm'], front-p['nose_length_mm'], p['nose_length_mm']),
               cylinder(p['rear_hub_radius_mm'], rear, p['rear_hub_length_mm']),
               cylinder(p['rear_flange_radius_mm'], rear+p['rear_hub_length_mm'], p['rear_flange_width_mm'])]
    result = shapes[0].multiFuse(shapes[1:]).removeSplitter()
    # Six through holes in the flange; pattern and dimensions are provisional.
    holes = []
    for i in range(6):
        a = math.radians(i*60)
        holes.append(Part.makeCylinder(p['rear_bolt_hole_radius_mm'],p['rear_flange_width_mm']+2,
                     V(rear+p['rear_hub_length_mm']-1,p['rear_bolt_circle_radius_mm']*math.sin(a),
                       p['rear_bolt_circle_radius_mm']*math.cos(a)),AXIS))
    result = result.cut(Part.makeCompound(holes)).removeSplitter()
    if result.isNull() or not result.isValid() or len(result.Solids) != 1:
        raise ValueError('Crank must be one continuous valid solid')
    return result, interfaces
