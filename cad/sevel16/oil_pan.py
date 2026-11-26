"""Stepped hollow sump sharing the block's curved sealing outline."""
import copy
import math
import FreeCAD as App
import Part
from stationary import _sump
from config import layout

V = App.Vector


def _press_radius(body, deep, shallow, radius):
    # Trace the outside of the stepped floor. Transverse seams between its
    # tangent sections are internal to the floor and do not meet a side wall.
    perimeter = []
    for edge in body.Edges:
        box = edge.BoundBox
        if box.ZMin < deep-0.001 or box.ZMax > shallow+0.001:
            continue
        faces = body.ancestorsOfType(edge, Part.Face)
        if len(faces) != 2:
            continue
        floor = [face.BoundBox.ZMax <= shallow+0.001 for face in faces]
        if sum(floor) == 1:
            perimeter.append(edge)
    if len(perimeter) < 6:
        raise ValueError("Missing stamped floor perimeter")
    return body.makeFillet(radius, perimeter)


def _round_ends(body, deep, shallow, radius):
    """Roll each transverse end into its floor with an analytic cylindrical cut."""
    bounds = body.BoundBox
    reach = bounds.XLength + 20
    for direction, floor in ((1, deep), (-1, shallow)):
        def end_at(z):
            line = Part.makeLine(V(bounds.XMin-2, 0, z), V(bounds.XMax+2, 0, z))
            xs = [v.Point.x for v in body.section(line).Vertexes]
            return min(xs) if direction == 1 else max(xs)
        x1, x2 = end_at(floor+1), end_at(floor+2)
        x0 = 2*x1-x2
        slope = direction*(x2-x1)
        length = math.hypot(slope, 1)
        a, b = slope/length, 1/length
        center = radius*(slope+length)
        def point(x,z):
            return V(x0+direction*x, bounds.YMin-2, floor+z)
        start = point(center, 0)
        finish = point(center-radius*b, radius*(1+a))
        norm = math.hypot(b, 1-a)
        mid = point(center-radius*b/norm, radius-radius*(1-a)/norm)
        corners = [finish, point(-reach, radius*(1+a)), point(-reach,-2),
                   point(center,-2), start]
        wire = Part.Wire([Part.Arc(start,mid,finish).toShape()] +
                         [Part.makeLine(i,j) for i,j in zip(corners,corners[1:])])
        body = body.cut(Part.Face(wire).extrude(V(0,bounds.YLength+4,0)))
    return body


def build(params,frame, *, polish=False, offset_drain=False):
    p = params['external_closures_estimated']['value']
    block = params['block_visual_estimated']['value']
    contour = params['sump_outline_estimated']['value']
    xs = [c['x'] for c in frame['bore_circle_centers_mm']]
    lo,hi = xs[0]-block['end_margin'],xs[-1]+block['end_margin']
    seal = -block['height']
    top = seal-p['pan_gasket_mm']
    wall = p['pan_wall_mm']
    deep,shallow = top-p['pan_deep_depth_mm'],top-p['pan_shallow_depth_mm']
    assert deep<shallow<top-p['pan_shoulder_depth_mm']<top-p['pan_flange_mm']
    def outline(z,inset=0,end=None):
        local = copy.deepcopy(params)
        local['block_visual_estimated']['value']['end_margin'] -= inset if end is None else end
        return _sump.outline(local,frame,z,inset)
    def bottom_cut(offset):
        x0,x1 = [lo+(hi-lo)*f for f in p['pan_step_fractions']]
        assert lo<x0<x1<hi
        y = -2*block['half_width']
        d = (x1-x0)/3
        points = [(lo-1,deep-2*wall-1),(hi+1,deep-2*wall-1),
                  (hi+1,shallow+offset),(x1,shallow+offset)]
        vertices = [V(x,y,z) for x,z in points]
        edges = [Part.makeLine(a,b) for a,b in zip(vertices,vertices[1:])]
        curve = Part.BezierCurve()
        curve.setPoles([V(x1,y,shallow+offset),V(x1-d,y,shallow+offset),
                        V(x0+d,y,deep+offset),V(x0,y,deep+offset)])
        edges += [curve.toShape(),Part.makeLine(V(x0,y,deep+offset),V(lo-1,y,deep+offset)),
                  Part.makeLine(V(lo-1,y,deep+offset),vertices[0])]
        return Part.Face(Part.Wire(edges)).extrude(V(0,4*block['half_width'],0))
    flange = Part.Face(outline(top)).extrude(V(0,0,-p['pan_flange_mm']))
    zs = [top-p['pan_flange_mm'],top-p['pan_shoulder_depth_mm'],deep]
    insets = p['pan_body_insets_mm']
    assert len(insets)==len(zs)==3 and min(insets)>=0
    # Ruled walls avoid spline overshoot between the short shoulder and the
    # deep reservoir. Each transverse outline retains its curved perimeter.
    outer = Part.makeLoft([outline(z,i) for z,i in zip(zs,insets)],True,True)
    outer = outer.cut(bottom_cut(0)).fuse(flange)
    inner = Part.makeLoft([
        outline(top+1,contour['wall_inset'],p['pan_inner_end_flange_mm']),
        outline(zs[1],insets[1]+wall),outline(deep+wall,insets[2]+wall)],True,True)
    inner = inner.cut(bottom_cut(wall))
    if polish:
        radius = params['pan_press_radius_estimated']['value']
        if radius <= wall:
            raise ValueError("Exterior press radius must exceed sheet thickness")
        round_floor = _round_ends if polish == 'ends' else _press_radius
        outer = round_floor(outer, deep, shallow, radius)
        inner = round_floor(inner, deep+wall, shallow+wall, radius-wall)
    pan = outer.cut(inner)
    gasket = Part.Face(outline(top)).extrude(V(0,0,p['pan_gasket_mm']))
    gasket = gasket.cut(Part.Face(outline(top-1,contour['wall_inset'],p['pan_inner_end_flange_mm']))
                        .extrude(V(0,0,p['pan_gasket_mm']+2)))
    if p['preserve_crank_bay_clearance']:
        # Continue the block's existing conservative rod/bolt clearance into
        # the gasket and pan; nominal wall inset alone is too narrow at C3/C4.
        g = layout(params,frame)
        moving = params['moving_geometry_estimated']['value']
        rod = params['piston_rod_visual_estimated']['value']
        bound = math.hypot(rod['rod_bolt_y_mm']+rod['rod_bolt_head_radius_mm'],
                           rod['rod_bolt_half_length_mm']+4)
        radius = max(moving['counterweight_radius_mm'],g['radius']+bound,
                     g['radius']+params['moving_nominal']['crankpin_diameter_mm']['value']/2)
        radius += moving['crankcase_clearance_mm']
        half_web = block['web_thickness']/2
        cutters = [Part.makeCylinder(radius,b-a-2*half_web,V(a+half_web,0,-g['height']),V(1,0,0))
                   for a,b in zip(g['supports'],g['supports'][1:])]
        pan = pan.cut(Part.makeCompound(cutters))
        gasket = gasket.cut(Part.makeCompound(cutters))
    x = lo+(hi-lo)*p['drain_x_fraction']
    y = params['drain_y_estimated']['value'] if offset_drain else 0
    assert p['drain_x_fraction']<p['pan_step_fractions'][0]
    boss = p['drain_boss_height_mm']
    pan = pan.fuse(Part.makeCylinder(p['drain_boss_radius_mm'],boss+wall,V(x,y,deep-boss)))
    pan = pan.cut(Part.makeCylinder(p['drain_bore_radius_mm'],boss+wall+2,V(x,y,deep-boss-1)))
    z = deep-boss-p['drain_head_height_mm']
    vertices = [V(x+p['drain_head_radius_mm']*math.cos(i*math.pi/3),
                  y+p['drain_head_radius_mm']*math.sin(i*math.pi/3),z) for i in range(6)]
    plug = Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(V(0,0,p['drain_head_height_mm']))
    plug = plug.fuse(Part.makeCylinder(p['drain_bore_radius_mm'],boss+wall-1,V(x,y,deep-boss)))
    result = {'OilPan':pan.removeSplitter(),'OilPanGasket':gasket.removeSplitter(),
              'OilDrainPlug':plug.removeSplitter()}
    for name,shape in result.items():
        assert shape.isValid() and len(shape.Solids)==1 and shape.Volume>0,name
    return result
