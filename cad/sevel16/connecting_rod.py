"""Split rod, cap, bearings and simplified bolts, with big-end local origin."""
import math
import FreeCAD as App
import Part

V = App.Vector


def ring_x(outer, inner, width, z=0):
    return Part.makeCylinder(outer,width,V(-width/2,0,z),V(1,0,0)).cut(
           Part.makeCylinder(inner,width+2,V(-width/2-1,0,z),V(1,0,0)))


def build(params, frame):
    p, n = params['piston_rod_visual_estimated']['value'], params['piston_rod_nominal']['value']
    length = params['moving_geometry_estimated']['value']['rod_length_mm']
    big, small = p['rod_big_radius_mm'], p['rod_small_radius_mm']
    bw, sw = p['rod_big_width_mm'], p['rod_small_width_mm']
    y, x = p['rod_beam_half_width_mm'], p['rod_beam_half_thickness_mm']
    corners = [V(-x,-y,big*0.7),V(-x,y,big*0.7),
               V(-x,y*0.65,length-small*0.7),V(-x,-y*0.65,length-small*0.7)]
    beam = Part.Face(Part.makePolygon(corners+[corners[0]])).extrude(V(2*x,0,0))
    # Two shallow pockets leave a central web and the two longitudinal flanges.
    for sign in [-1,1]:
        left = -x-1 if sign == -1 else p['rod_web_half_thickness_mm']
        beam = beam.cut(Part.makeBox(x-p['rod_web_half_thickness_mm']+1,2*(y-3),length-big-small,
                                    V(left,-y+3,big)))
    body = Part.makeCylinder(big,bw,V(-bw/2,0,0),V(1,0,0)).fuse(beam).fuse(
           Part.makeCylinder(small,sw,V(-sw/2,0,length),V(1,0,0)))
    bolt_y, half = p['rod_bolt_y_mm'], p['rod_bolt_half_length_mm']
    holes = [Part.makeCylinder(n['big_bearing_seat_mm']/2,bw+2,V(-bw/2-1,0,0),V(1,0,0)),
             Part.makeCylinder(n['small_bushing_seat_mm']/2,sw+2,V(-sw/2-1,0,length),V(1,0,0))]
    bolts = []
    for sign in [-1,1]:
        center_y = sign*bolt_y
        boss = Part.makeBox(bw,9,2*half,V(-bw/2,center_y-4.5,-half))
        body = body.fuse(boss)
        holes.append(Part.makeCylinder(p['rod_bolt_radius_mm']+0.1,2*half+2,V(0,center_y,-half-1)))
        # Flat under-head seat, so the hex does not penetrate the curved cap.
        holes.append(Part.makeCylinder(p['rod_bolt_head_radius_mm']+0.1,4,
                                       V(0,center_y,-half-4)))
        shank = Part.makeCylinder(p['rod_bolt_radius_mm'],2*half,V(0,center_y,-half))
        polygon = [V(p['rod_bolt_head_radius_mm']*math.cos(i*math.pi/3),
                     center_y+p['rod_bolt_head_radius_mm']*math.sin(i*math.pi/3),-half-4)
                   for i in range(6)]
        head = Part.Face(Part.makePolygon(polygon+[polygon[0]])).extrude(V(0,0,4))
        bolts.append(shank.fuse(head).removeSplitter())
    body = body.cut(Part.makeCompound(holes)).removeSplitter()
    lower = Part.makeBox(100,100,big+10,V(-50,-50,-big-10))
    cap, rod = body.common(lower).removeSplitter(), body.cut(lower).removeSplitter()
    bearing = ring_x(n['big_bearing_seat_mm']/2,
                    n['big_bearing_seat_mm']/2-n['rod_bearing_thickness_mm'],bw)
    pieces = {'Rod':rod,'RodCap':cap,'RodBearingUpper':bearing.cut(lower),
              'RodBearingLower':bearing.common(lower),
              'SmallBushing':ring_x(n['small_bushing_outer_mm']/2,n['small_bushing_inner_mm']/2,sw,length),
              'RodBolt1':bolts[0],'RodBolt2':bolts[1]}
    for name, shape in pieces.items():
        if shape.isNull() or not shape.isValid() or len(shape.Solids)!=1:
            raise ValueError(f'{name} must be one valid solid')
    return pieces
