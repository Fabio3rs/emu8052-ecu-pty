"""Circular-wire helix at a requested installed height; CAD checkpoints only.

Runtime animation must use the mesh centerline with unchanged wire radius;
do not scale the CAD spring axially or run a pipe sweep every display frame.
"""
import math


def dimensions(params, kind, lift=0):
    p = params['valvetrain_layout_estimated']['value']
    seat = p[kind+'_spring_seat_z_mm']
    height = p['retainer_bottom_z_mm']-seat-lift
    radius = p[kind+'_spring_mean_radius_mm']
    wire = p[kind+'_spring_wire_radius_mm']
    turns = p[kind+'_spring_turns']
    if height <= 2*wire*(turns+1):
        raise ValueError('Spring coils would close or overlap')
    return seat,height,radius,wire,turns


def build(params, kind, lift=0):
    import FreeCAD as App
    import Part
    seat,height,radius,wire,turns = dimensions(params,kind,lift)
    central_height = height-2*wire
    path = Part.makeHelix(central_height/turns,central_height,radius)
    edge = path.Edges[0]
    start = edge.valueAt(edge.FirstParameter)
    tangent = edge.tangentAt(edge.FirstParameter)
    section = Part.Wire([Part.makeCircle(wire,start,tangent)])
    spring = Part.Wire(path.Edges).makePipeShell([section],True,True)
    spring.translate(App.Vector(0,0,seat+wire))
    assert spring.isValid() and len(spring.Solids)==1
    # Keep the installed Z offset inside the geometry when the assembly assigns
    # its root placement to the valve's X/Y position.
    return Part.makeCompound([spring])


def mesh(params, kind, lift=0, segments_per_turn=48, sides=12):
    """Tube mesh with caps, constant circular section normal to the helix."""
    seat,height,radius,wire,turns = dimensions(params,kind,lift)
    count = math.ceil(turns*segments_per_turn)
    rise = (height-2*wire)/(2*math.pi*turns)
    norm = math.hypot(radius,rise)
    vertices,triangles = [],[]
    for i in range(count+1):
        a = 2*math.pi*turns*i/count
        c,s = math.cos(a),math.sin(a)
        center = (radius*c,radius*s,seat+wire+rise*a)
        radial = (c,s,0)
        cross = (-rise*s/norm,rise*c/norm,-radius/norm)
        for j in range(sides):
            b = 2*math.pi*j/sides
            vertices.append(tuple(center[k]+wire*(math.cos(b)*radial[k]+math.sin(b)*cross[k]) for k in range(3)))
    for i in range(count):
        for j in range(sides):
            a,b = i*sides+j,i*sides+(j+1)%sides
            triangles.extend([(a,b,b+sides),(a,b+sides,a+sides)])
    for i,reverse in [(0,True),(count,False)]:
        ids = [i*sides+j for j in range(sides)]
        center = tuple(sum(vertices[n][k] for n in ids)/sides for k in range(3))
        ci = len(vertices)
        vertices.append(center)
        for j in range(sides):
            a,b = ids[j],ids[(j+1)%sides]
            triangles.append((ci,b,a) if reverse else (ci,a,b))
    return vertices,triangles
