"""Visible accessory-side casting and removable crankcase vent on the A5 assembly."""
import math

import FreeCAD as App
import Part

from auxiliary_enclosure import service_tools
from config import layout

V = App.Vector
# ASSUMPTION, angles from the block vertical, toward -Y. Photos 699233/946397.
SEAT_TILT_DEG, OUTLET_TILT_DEG = 18, 15


def inclined(angle):
    rad = math.radians(angle)
    return V(0, -math.sin(rad), math.cos(rad))


def circle(point, normal, radius):
    return Part.Wire([Part.makeCircle(radius, point, normal)])


def panel():
    # Estimated X/Y/Z stations (mm) from 600896, 946397 and bare casting 702072.
    # Curved shoulders return into the old wall at the front and behind the PCV.
    profiles = []
    for z, left, right, face in [(-208,-39,129,-79), (-198,-46,143,-90),
                                  (-176,-46,146,-94), (-149,-46,161,-108),
                                  (-128,-46,166,-111), (-97,-46,151,-108),
                                  (-73,-44,149,-100), (-56,-41,143,-90),
                                  (-46,-32,126,-73)]:
        inner = -67
        a, b = V(left,inner,z), V(right,inner,z)
        c, d = V(left+16,face,z), V(right-12,face,z)
        def shoulder(points):
            curve = Part.BezierCurve()
            curve.setPoles(points)
            return curve.toShape()
        profiles.append(Part.Wire([shoulder([a,V(left,face,z),c]),
            Part.makeLine(c,d), shoulder([d,V(right,face,z),b]), Part.makeLine(b,a)]))
    return Part.makeLoft(profiles, True, False)


def casting(original, params, frame):
    p = params['casting_visual_estimated']['value']
    g = layout(params,frame)
    start, end = g['centers'][0], g['centers'][-1]
    old = V(start+(end-start)*p['access_open_x_fraction'], -82, p['access_open_z'])
    legacy_axis = inclined(90-params['side_access_inclination_estimated']['value'])
    seat, normal = old+V(0,-14,20), inclined(SEAT_TILT_DEG)
    seat_r = p['access_open_radius']
    def transition(r1, r2):
        return Part.makeLoft([circle(old-legacy_axis*9,legacy_axis,r1),
                              circle(seat,normal,r2)], True, True)
    filter_x = start+(end-start)*p['filter_x_fraction']
    filter_face = V(filter_x,-106,p['filter_z'])
    outward = V(0,-1,0)
    filter_land = Part.makeCone(p['filter_radius']+10,p['filter_radius']+7,
                                21,filter_face-outward*21,outward)
    stock = panel().multiFuse([transition(seat_r+9,seat_r+6),filter_land])
    # Cast, blind fixing bosses visible around the filter on 946397 and 702072.
    spot_drills = []
    for x,z,face_y in [(-23,-149,-113),(-27,-186,-99),(127,-193,-101)]:
        face = V(x,face_y,z)
        stock = stock.fuse(Part.makeCone(12,8,22,face-outward*22,outward))
        spot_drills.append(Part.makeCylinder(4,9,face+outward,-outward))
    # Preserve the internal running envelopes while adding the outer casting.
    aux = Part.makeCylinder(p['aux_housing_radius']-12,235,V(-65,p['aux_y'],p['aux_z']),V(1,0,0))
    moving = params['moving_geometry_estimated']['value']
    rod = params['piston_rod_visual_estimated']['value']
    radius = max(moving['counterweight_radius_mm'],g['radius']+math.hypot(
        rod['rod_bolt_y_mm']+rod['rod_bolt_head_radius_mm'],rod['rod_bolt_half_length_mm']+4))
    crank = Part.makeCylinder(radius+moving['crankcase_clearance_mm'],235,
                              V(-65,0,-g['height']),V(1,0,0))
    filter_port = service_tools(params,frame)['oil_filter']
    pad = Part.makeCylinder(p['filter_radius']+7,70,filter_face,outward)
    # Overlap the inherited passage at the transition to avoid coincident faces.
    old_bore = Part.makeCylinder(seat_r+0.2,28,old-legacy_axis*36,legacy_axis)
    passage = transition(seat_r+0.1,seat_r)
    seat_cut = Part.makeCylinder(seat_r+7,100,seat,normal)
    for tool in (aux,crank,filter_port,old_bore):
        stock = stock.cut(tool)
    block = original.fuse(stock)
    for tool in (passage,seat_cut,pad,*spot_drills):
        block = block.cut(tool)
    block = block.removeSplitter()
    assert block.isValid() and len(block.Solids)==1
    return block, seat, normal


def fitting(seat, normal):
    # Pressed cap, offset hose outlet and fastening pad, sized visually in mm.
    cap = Part.makeCylinder(29,17,seat,normal)
    top = max((e for e in cap.Edges if e.isClosed()),
              key=lambda e:(e.CenterOfMass-seat).dot(normal))
    cap = cap.makeFillet(5,[top])
    root = seat + normal*13 + V(-5,0,0) + V(0,-normal.z,normal.y)*9
    outlet = inclined(OUTLET_TILT_DEG)
    tube = Part.makeCylinder(8,33,root,outlet)
    boss = Part.makeCone(7.5,5.4,6,seat+normal*16+V(8,0,0),normal)
    cavity = Part.makeCylinder(25,14,seat-normal,normal)
    bore = Part.makeCylinder(6.2,40,root-outlet*5,outlet)
    return cap.fuse(tube).fuse(boss).cut([cavity,bore]).removeSplitter()


def filter_spigot(block, params, frame):
    # Smooth visual nipple seen with the cartridge removed; thread size unknown.
    p = params['casting_visual_estimated']['value']
    xs = layout(params,frame)['centers']
    front = V(xs[0]+(xs[-1]-xs[0])*p['filter_x_fraction'],-122,p['filter_z'])
    axis = V(0,1,0)
    tube = Part.makeCylinder(10,56,front,axis).cut(Part.makeCylinder(6.7,56,front,axis))
    floor = block.common(Part.makeBox(34,60,34,front+V(-17,-1,-17)))
    return min(tube.cut(floor).Solids,key=lambda solid: solid.CenterOfMass.y)
