"""Analytic rounded contours for the provisional head casting and chambers."""
import math
import FreeCAD as App
import Part
from cam_carrier import rounded_prism
from config import layout

V = App.Vector


def capsule(a, b, ra, rb, z=0):
    """Convex tangent outline of unequal circles in XY, without polygon faceting."""
    delta = V(b[0]-a[0],b[1]-a[1],0)
    distance = delta.Length
    assert distance>abs(ra-rb)>-1 and min(ra,rb)>0
    u = delta/distance
    perpendicular = V(-u.y,u.x,0)
    cosine = (ra-rb)/distance
    sine = math.sqrt(1-cosine*cosine)
    ca,cb = V(*a,z),V(*b,z)
    up,down = u*cosine+perpendicular*sine,u*cosine-perpendicular*sine
    at,bt,bb,ab = ca+up*ra,cb+up*rb,cb+down*rb,ca+down*ra
    return Part.Wire([Part.makeLine(at,bt),Part.Arc(bt,cb+u*rb,bb).toShape(),
                      Part.makeLine(bb,ab),Part.Arc(ab,ca-u*ra,at).toShape()])


def rounded_outline(lo, hi, width, z, radius):
    prism = rounded_prism(lo,-width,z,hi-lo,2*width,1,radius)
    face = next(f for f in prism.Faces if f.BoundBox.ZLength<1e-7 and abs(f.BoundBox.ZMin-z)<1e-7)
    return face.OuterWire


def head_bounds(params,frame):
    g = layout(params,frame)
    margin = params['block_visual_estimated']['value']['end_margin']
    return g['centers'][0]-margin,g['centers'][-1]+margin


def clipping_slab(params,frame,base,offset=0):
    from inclined_carrier import section_prism
    p = params['valvetrain_layout_estimated']['value']
    s = params['carrier_section_estimated']['value']
    slope = math.tan(math.radians(s['base_slope_y_deg']))
    lo,hi = head_bounds(params,frame)
    return section_prism(lo-30,hi+30,[(-150,base),(150,base),
                         (150,p['carrier_base_z_mm']+150*slope-offset),
                         (-150,p['carrier_base_z_mm']-150*slope-offset)])


def water_end_profile(params,frame,extra=0):
    """Three-arc opening in the end plane, qualitatively traced from photo 901284."""
    h = params['head_lower_casting_estimated']['value']
    _,x = head_bounds(params,frame)
    r,z = h['water_end_radius_mm']+extra,h['water_end_z_mm']
    a,b,c = V(x,-r,z-.45*r),V(x,0,z+r),V(x,r,z-.45*r)
    edges = [Part.Arc(a,V(x,-.95*r,z+.4*r),b).toShape(),
             Part.Arc(b,V(x,.95*r,z+.4*r),c).toShape(),
             Part.Arc(c,V(x,0,z-.9*r),a).toShape()]
    return Part.Face(Part.Wire(edges))
