"""Draw the deep-end shelf and the shallow longitudinal channel in the sheet."""
import FreeCAD as App
import Part

V = App.Vector


def shelf_die(spec, floor, wall, reach, offset):
    x,y = spec["shelf_corner_xy"]
    radius = spec["shelf_corner_radius"]
    width = spec["shelf_runout"]
    lift = spec["shelf_lift"]
    center = V(x,y,0)
    def section(axis):
        def point(r,z):
            return center + axis*r + V(0,0,z)
        low = floor-2*wall+offset
        near = point(radius,floor+lift+offset)
        far = point(radius+width,floor+offset)
        # Two tangent circular arcs give the die flat entry and exit tangents.
        # Revolving these sections makes toroidal blends at the shelf corner.
        blend = (width**2+lift**2)/(4*lift)
        if offset >= blend:
            raise ValueError("Sheet gauge exceeds the concave press radius")
        first = point(radius,floor+lift-blend)
        second = point(radius+width,floor+blend)
        tangent_normal = (second-first).normalize()
        mid = first+tangent_normal*(blend+offset)
        mean_normal = (V(0,0,1)+tangent_normal).normalize()
        shoulder = first+mean_normal*(blend+offset)
        foot = second-mean_normal*(blend-offset)
        transition = [Part.Arc(near,shoulder,mid).toShape(),Part.Arc(mid,foot,far).toShape()]
        loop = [far,point(radius+width,low),point(0,low),point(0,floor+lift+offset),near]
        return Part.Face(Part.Wire(transition+[Part.makeLine(a,b) for a,b in zip(loop,loop[1:])]))
    sx = section(V(1,0,0))
    corner = sx.revolve(center,V(0,0,-1),90)
    front = sx.extrude(V(0,reach,0))
    end = section(V(0,-1,0)).extrude(V(-reach,0,0))
    middle = Part.makeBox(reach,reach,lift+2*wall,V(x-reach,y,floor-2*wall+offset))
    return corner.fuse([front,end,middle]).removeSplitter()


def dies(params, deep, shallow, offset=0):
    spec = params["spi_pan_floor_estimated"]["value"]
    wall = params["external_closures_estimated"]["value"]["pan_wall_mm"]
    shelf = shelf_die(spec,deep,wall,400,offset)
    x0,x1 = spec["shallow_channel_ends_x"]
    radius = spec["shallow_channel_radius"]
    height = shallow+spec["shallow_channel_depth"]-radius
    radius += offset
    a,b = [V(x,spec["shallow_channel_y"],height) for x in (x0,x1)]
    barrel = Part.makeCylinder(radius,x1-x0,a,V(1,0,0))
    channel = barrel.fuse([Part.makeSphere(radius,a),Part.makeSphere(radius,b)]).removeSplitter()
    return Part.makeCompound([shelf,channel])
