"""Piston, pin and split rings; all local origins are the piston pin center."""
import FreeCAD as App
import Part
from config import layout

V = App.Vector


def build(params, frame):
    p = params['piston_rod_visual_estimated']['value']
    n = params['piston_rod_nominal']['value']
    top = layout(params,frame)['compression_height']
    bottom, radius = -p['skirt_below_pin_mm'], n['piston_diameter_mm']/2
    outside = Part.makeCylinder(radius,top-bottom,V(0,0,bottom))
    cavity = Part.makeCylinder(radius-p['wall_mm'],top-bottom-p['crown_thickness_mm']+1,
                               V(0,0,bottom-1))
    body = outside.cut(cavity)
    for sign in [-1,1]:
        left = -radius if sign == -1 else p['boss_inner_x_mm']
        boss = Part.makeCylinder(p['boss_radius_mm'],radius-p['boss_inner_x_mm'],
                                V(left,0,0),V(1,0,0)).common(outside)
        body = body.fuse(boss)
    cuts = [Part.makeCylinder(n['piston_pin_bore_mm']/2,2*radius+2,V(-radius-1,0,0),V(1,0,0)),
            Part.makeCylinder(p['dish_radius_mm'],p['dish_depth_mm']+1,V(0,0,top-p['dish_depth_mm']))]
    for sign in [-1,1]:
        cuts.append(Part.makeCylinder(p['relief_radius_mm'],p['relief_depth_mm']+1,
                    V(sign*p['relief_offset_x_mm'],0,top-p['relief_depth_mm'])))
    rings = []
    for i, depth in enumerate(p['groove_depths_below_crown_mm']):
        width, ring_width = n['groove_widths_mm'][i], n['ring_widths_mm'][i]
        z = top-depth
        groove = Part.makeCylinder(radius+1,width,V(0,0,z-width/2)).cut(
                 Part.makeCylinder(radius-p['groove_radial_depth_mm'],width+2,V(0,0,z-width/2-1)))
        cuts.append(groove)
        outer = frame['cylinder_bore_diameter_mm']/2-p['ring_bore_radial_gap_mm']
        ring = Part.makeCylinder(outer,ring_width,V(0,0,z-ring_width/2)).cut(
               Part.makeCylinder(outer-p['ring_radial_width_mm'],ring_width+2,V(0,0,z-ring_width/2-1)))
        gap = Part.makeBox(outer+1,n['ring_end_gap_mm'],ring_width+2,
                          V(0,-n['ring_end_gap_mm']/2,z-ring_width/2-1))
        ring = ring.cut(gap)
        ring.rotate(V(),V(0,0,1),i*120)
        # Preserve the gap's local orientation beneath an identity root placement.
        # The assembly adapter owns the root placement and must not erase it.
        rings.append(Part.makeCompound([ring]))
    body = body.cut(Part.makeCompound(cuts)).removeSplitter()
    half = p['pin_length_mm']/2
    pin = Part.makeCylinder(n['pin_diameter_mm']/2,2*half,V(-half,0,0),V(1,0,0)).cut(
          Part.makeCylinder(p['pin_inner_radius_mm'],2*half+2,V(-half-1,0,0),V(1,0,0)))
    pieces = {'Piston':body,'Pin':pin,**{f'Ring{i+1}':s for i,s in enumerate(rings)}}
    for name, shape in pieces.items():
        if shape.isNull() or not shape.isValid() or len(shape.Solids)!=1:
            raise ValueError(f'{name} must be one valid solid')
    return pieces
