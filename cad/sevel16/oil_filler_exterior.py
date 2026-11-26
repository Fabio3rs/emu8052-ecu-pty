"""Cover and offset filler in the cover's local plane. Dimensions are visual estimates."""
import math
import FreeCAD as App
import Part
from cam_carrier import rounded_prism

V = App.Vector
UP = V(0,0,1)


def ellipse(point, normal, a, b):
    side = V(0,1,0)
    long = side.cross(normal).normalize()
    curve = Part.Ellipse(point+long*a, point+side*b, point)
    return Part.Wire([curve.toShape()])


def grip_cap(mouth, axis):
    # Eight groups of grip grooves with smooth sectors between them.
    points = []
    for sector in range(8):
        for deg,r in ((0,34),(4,34),(5,33),(6.2,33),(7.2,34),(10,34),(11,33),
                      (12.2,33),(13.2,34),(16,34),(17,33),(18.2,33),(19.2,34),
                      (22,34),(23,33),(24.2,33),(25.2,34),(31,34),(38,34)):
            theta = math.radians(45*sector+deg)
            points.append(V(r*math.cos(theta),r*math.sin(theta),1))
    band = Part.Face(Part.makePolygon(points+[points[0]])).extrude(UP*8)
    shape = band.fuse([Part.makeCone(32,33,1),Part.makeCone(33,32,2,V(0,0,9))]).removeSplitter()
    shape.Placement = App.Placement(mouth,App.Rotation(UP,axis))
    return shape


def casting(body,lo,hi,half,roof,gasket,wall):
    # A full-width raised end with a sloping return to the lower central roof.
    def raised_end(start, sign, length):
        rows = [(1, .6), (6,3.4), (.42*length,5), (.8*length,4), (length,.5)]
        wires = []
        for distance, rise in rows:
            x = start + sign*distance
            width = half-(7 if distance<3 else 4)
            left,right = V(x,-width,roof-.6), V(x,width,roof-.6)
            arc = Part.BSplineCurve()
            arc.interpolate([right,V(x,width-2,roof+.4*rise),V(x,width-7,roof+rise),
                             V(x,0,roof+rise+1),V(x,-width+7,roof+rise),
                             V(x,-width+2,roof+.4*rise),left])
            wires.append(Part.Wire([Part.makeLine(left,right),arc.toShape()]))
        return Part.makeLoft(wires,True,False)
    stock = [raised_end(lo,1,46),raised_end(hi,-1,74)]
    # Rectangular cast loops along the side rails on 215616663404314.
    for fraction,side in ((.09,1),(.25,1),(.55,-1),(.69,1),(.83,-1)):
        x = lo+fraction*(hi-lo)
        y = half-4 if side>0 else -half-9
        lug = rounded_prism(x-10,y,gasket+5,20,13,6,2)
        hole = Part.makeBox(12,5.5,8,V(x-6,y+(5 if side>0 else 2.5),gasket+4))
        stock.append(lug.cut(hole))
    # Cast cylindrical eyelets adjacent to the peripheral fixing ears.
    for x,side in ((lo+11,-1),(lo+15,1),(hi-12,-1),(hi-22,1)):
        origin = V(x,side*(half-1),gasket+3)
        eye = Part.makeCylinder(6.5,10,origin)
        # Drill after joining to open the part of the eye which overlaps the wall.
        stock.append(eye)
    base = V(hi-28,-1,roof+1)
    axis = V(.50,0,.866).normalize()
    mid = base+V(9,0,14)
    mouth = base+V(24,0,39)
    outer = [ellipse(base-UP*2,UP,30,24),ellipse(mid,V(.26,0,.966).normalize(),26.5,24.6),
             ellipse(mouth-axis*4,axis,27.5,26.5),ellipse(mouth,axis,29,27.5)]
    stock.append(Part.makeLoft(outer,True,False))
    for y in (-18,18):
        # Triangular side webs descend from the lip to the flared base.
        pts = [base+V(-16,y,0),base+V(-24,y,0),mid+V(-14,y,3),
               mouth+V(-13,y,-2),mouth+V(-11,y,-3)]
        stock.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,2.5 if y>0 else -2.5,0)))
    bore = Part.makeLoft([ellipse(base-UP*(wall+6),UP,18,16),ellipse(mid,axis,19,18),
                          ellipse(mouth+axis*2,axis,21,20)],True,False)
    eye_holes = [Part.makeCylinder(3,10,V(x,side*(half-1),gasket+4))
                 for x,side in ((lo+11,-1),(lo+15,1),(hi-12,-1),(hi-22,1))]
    body = body.fuse(stock).cut([bore,*eye_holes]).removeSplitter()
    return body,grip_cap(mouth,axis)
