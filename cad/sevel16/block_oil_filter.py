"""Removable spin-on filter from F9Lhc and KpWw4 block photos; unscaled silhouette."""
import FreeCAD as App
import Part

V = App.Vector


def build(doc,params):
    spigot = doc.OilFilterSpigot.Shape.optimalBoundingBox(False)
    radius = params['casting_visual_estimated']['value']['filter_radius']
    # Revolved section (radius, projection from the machined land), in mm.
    # The visible can is roughly twice as long as wide in the two oblique views.
    outer = radius+7.0
    length = 3.7*outer
    def point(r,t):
        return V(r,0,t)
    contour = [(10.15,0),(radius+3.5,0),(radius+5.5,1.2),(radius+5.5,3.8),
               (outer,5),(outer,7.2),(outer-.9,8.3),(outer-.9,length-6)]
    pts = [point(*row) for row in contour]
    edges = [Part.makeLine(a,b) for a,b in zip(pts,pts[1:])]
    crown = point(outer-6,length-.5)
    edges.append(Part.Arc(pts[-1],point(outer-2.1,length-2.5),crown).toShape())
    inner = [crown,point(0,length),point(0,length-2),point(outer-5,length-3),
             point(outer-2.6,length-7),point(outer-2.6,6),point(11.7,6),
             point(11.7,17),point(10.15,17),pts[0]]
    edges.extend(Part.makeLine(a,b) for a,b in zip(inner,inner[1:]))
    shape = Part.Face(Part.Wire(edges)).revolve(V(),V(0,0,1),360)
    # Resolve the seal plane against the actual annular seat on the saved block.
    ray = Part.makeLine(V(spigot.Center.x,-160,spigot.Center.z+radius+2),
                        V(spigot.Center.x,-60,spigot.Center.z+radius+2))
    y = min(v.Point.y for v in doc.Block.Shape.section(ray).Vertexes)
    shape.Placement = App.Placement(V(spigot.Center.x,y,spigot.Center.z),
                                    App.Rotation(V(1,0,0),90))
    return shape
