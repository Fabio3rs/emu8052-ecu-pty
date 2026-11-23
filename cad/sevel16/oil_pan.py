"""Stepped hollow sump sharing the block's curved sealing outline."""
import copy
import math
import FreeCAD as App
import Part
from stationary import _sump
from config import layout

V = App.Vector


def build(params,frame):
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
    assert p['drain_x_fraction']<p['pan_step_fractions'][0]
    boss = p['drain_boss_height_mm']
    pan = pan.fuse(Part.makeCylinder(p['drain_boss_radius_mm'],boss+wall,V(x,0,deep-boss)))
    pan = pan.cut(Part.makeCylinder(p['drain_bore_radius_mm'],boss+wall+2,V(x,0,deep-boss-1)))
    z = deep-boss-p['drain_head_height_mm']
    vertices = [V(x+p['drain_head_radius_mm']*math.cos(i*math.pi/3),
                  p['drain_head_radius_mm']*math.sin(i*math.pi/3),z) for i in range(6)]
    plug = Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(V(0,0,p['drain_head_height_mm']))
    plug = plug.fuse(Part.makeCylinder(p['drain_bore_radius_mm'],boss+wall-1,V(x,0,deep-boss)))
    result = {'OilPan':pan.removeSplitter(),'OilPanGasket':gasket.removeSplitter(),
              'OilDrainPlug':plug.removeSplitter()}
    for name,shape in result.items():
        assert shape.isValid() and len(shape.Solids)==1 and shape.Volume>0,name
    return result
