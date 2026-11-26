"""External cam housing and transverse bridge reliefs from 621331/649747/833777."""
import math
import FreeCAD as App
import Part
from cam_carrier import rounded_prism
from config import layout
from head_flanks import oval_loft
from inclined_carrier import section_prism

V = App.Vector
AXIS = V(1, 0, 0)
# Locations in the end view, relative to the cam centre, in estimated mm.
MOUNT_HOLES = ((7, 30), (-25, -23), (28, -16))


def end_plate(x, z, outline, thickness):
    curve = Part.BSplineCurve()
    curve.interpolate([V(x,y,z+h) for y,h in outline], PeriodicFlag=True)
    return Part.Face(Part.Wire([curve.toShape()])).extrude(AXIS*thickness)


def revised(doc, params, frame):
    p = params['valvetrain_layout_estimated']['value']
    section = params['carrier_section_estimated']['value']
    top, z = p['carrier_cap_top_z_mm'], p['cam_axis_z_mm']
    stations = layout(params,frame)['supports']
    lo,hi = stations[0]-p['cam_journal_width_mm']/2, stations[-1]+p['cam_journal_width_mm']/2
    cage = doc.CamCarrier.Shape.copy()
    additions, cuts = [], []
    # Curved vertical webs pull back towards the top rail, with unequal widths.
    for x,lean,width in zip(stations,(7,-9,5,-7,-6),(7,9,7,9,7)):
        web = oval_loft([(x,33,70,width+2,5),(x+lean*.3,36,81,width+5,9),
                         (x+lean,35,105,width+1,10),(x+lean*.6,32,131,width*.8,9),
                         (x,30,151,width*.65,6),(x,29,161,4,3)])
        # Existing stock below this boundary already encloses the bearing.
        additions.append(web.common(Part.makeBox(60,40,98,V(x-30,27,68))))
    for x,offset in zip(stations[1:-1],(-3,2,4)):
        # 726745: short raised pairs of webs along the plug-side rail.
        for shoulder in (-5,5):
            xx = x+offset+shoulder
            ridge = oval_loft([(xx,-35,91,3,3),(xx,-35,97,3,5),
                               (xx+1,-34,107,2.6,5),(xx+2,-32,119,2.3,4),
                               (xx+2,-31,126,2,2)])
            additions.append(ridge)
    # Through-housing stays coaxial with the existing working journal.
    end = end_plate(hi-.5,z,[(0,34),(9,36),(22,23),(35,-9),(33,-19),
                    (10,-32),(-16,-35),(-30,-29),(-32,-10),(-27,13)],4.5)
    end = end.fuse(Part.makeCylinder(27,3,V(hi+4,0,z),AXIS))
    end = end.cut(Part.makeCylinder(24.8,10,V(hi-1,0,z),AXIS))
    additions.append(end)
    cuts.extend(Part.makeCylinder(3.35,12,V(hi+5,y,z+h),-AXIS) for y,h in MOUNT_HOLES)
    slot = rounded_prism(-7,-2.4,0,14,4.8,9,2)
    slot.rotate(V(), V(1,1,1),120)
    slot.translate(V(hi-4,-8,z-29))
    cuts.append(slot)
    # Opposite end: smaller drive journal and stepped ring behind the sprocket.
    timing = end_plate(lo+.4,z,[(-21,-21),(-28,1),(-21,21),(-9,27),
                           (13,24),(23,8),(25,-15),(16,-23),(-3,-27)],-3.4)
    timing = timing.fuse(Part.makeCylinder(23,3,V(lo-3,0,z),-AXIS))
    additions.append(timing.cut(Part.makeCylinder(16,9,V(lo+1,0,z),-AXIS)))
    # Shallow pockets and blind circular openings in each bridge. The lowest
    # tool face stays above the original bearing crown.
    tilt = section['top_slope_y_deg']
    normal = V(0,-math.sin(math.radians(tilt)),math.cos(math.radians(tilt)))
    for x in stations[1:-1]:
        for y in (-18,18):
            pocket = rounded_prism(-4.8,-5.8,-4.5,9.6,11.6,6,2)
            pocket.rotate(V(),AXIS,tilt)
            pocket.translate(V(x,y,top+y*math.tan(math.radians(tilt))))
            cuts.append(pocket)
        cuts.append(Part.makeCylinder(2.8,5,V(x,0,top)+normal,-normal))
    slope = math.tan(math.radians(tilt))
    base_slope = math.tan(math.radians(section['base_slope_y_deg']))
    bottom = p['carrier_base_z_mm']
    envelope = section_prism(lo-15,hi+15,[(-65,bottom-65*base_slope),
                 (65,bottom+65*base_slope),(65,top+65*slope),(-65,top-65*slope)])
    stock = Part.makeCompound(additions).common(envelope)
    rim = params['cam_carrier_outline_estimated']['value']
    bores = []
    for fraction in rim['cover_boss_fractions']:
        for y in (-p['carrier_half_width_mm'],p['carrier_half_width_mm']):
            center = V(lo+fraction*(hi-lo),y,top+y*slope)
            depth = section['cover_ear_depth_mm']+3
            bores.append(Part.makeCylinder(rim['cover_hole_radius_mm'],depth+1,
                                           center-normal*depth,normal))
    stock = stock.cut(bores)
    return cage.fuse(stock).cut(cuts).removeSplitter()
