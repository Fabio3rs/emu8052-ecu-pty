"""Water flange traced on the end view, in the existing +X end plane."""
import math

import FreeCAD as App
import Part
from head_profiles import head_bounds, water_end_profile

V = App.Vector
AXIS = V(1, 0, 0)
# Original 649747 pixels. Keep the provisional 62 mm CAD pitch independently
# of the apparent 6.31 degree slope and the unconfirmed loose-housing estimate.
LEFT, RIGHT = (210, 891), (644, 939)
MOUTH = [(282,872),(300,840),(367,795),(429,771),(484,777),(545,807),
         (582,852),(588,909),(584,970),(562,1019),(523,1041),(479,1032),
         (454,1009),(441,975),(431,968),(420,982),(399,988),(356,969),
         (301,947),(281,928)]
OUTLINE = [(158,881),(188,850),(282,792),(377,733),(443,714),(498,723),
           (570,770),(619,815),(653,872),(685,929),(683,955),(654,981),
           (606,1043),(551,1084),(499,1099),(427,1078),(331,1033),
           (239,988),(180,955),(157,921)]


def datum(params,frame):
    h = params['head_lower_casting_estimated']['value']
    _, end = head_bounds(params,frame)
    scale = 2*h['water_end_bolt_half_pitch_mm']/math.dist(LEFT,RIGHT)
    def project(pixel):
        return V(end, (pixel[0]-427)*scale, h['water_end_z_mm']-(pixel[1]-915)*scale)
    return h, project


def profile(points, project):
    curve = Part.BSplineCurve()
    curve.interpolate([project(p) for p in points], PeriodicFlag=True)
    return Part.Face(Part.Wire([curve.toShape()]))


def revised(head,params,frame):
    h,project = datum(params,frame)
    end = project(LEFT).x
    depth, recess = h['water_end_flange_depth_mm'], h['water_end_depth_mm']
    # Rebuild only the old raised pad and its blind cuts, from the original
    # head end face. The other service openings remain in their own planes.
    body = head.cut(Part.makeBox(depth+2,82,67,V(end,-41,1)))
    fill = water_end_profile(params,frame,.15).extrude(-AXIS*(recess+.3))
    stock = [fill]
    radius = h['water_end_bolt_radius_mm']
    for y in (-h['water_end_bolt_half_pitch_mm'], h['water_end_bolt_half_pitch_mm']):
        stock.append(Part.makeCylinder(radius+.15,recess+.3,V(end,y,h['water_end_z_mm']),-AXIS))
    pad = profile(OUTLINE,project).extrude(AXIS*depth)
    stock.append(pad)
    body = body.fuse(stock)
    mouth = profile(MOUTH,project)
    mouth.translate(AXIS*(depth+1))
    tools = [mouth.extrude(-AXIS*(recess+depth+1))]
    for center in (LEFT,RIGHT):
        tools.append(Part.makeCylinder(radius,recess+depth+1,project(center)+AXIS*(depth+1),-AXIS))
    return body.cut(tools).removeSplitter()
