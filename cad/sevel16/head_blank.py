"""Rounded lower casting and scalloped carrier interface; dimensions provisional."""
import FreeCAD as App
import Part
from config import layout
from cam_carrier import rounded_prism
from head_profiles import rounded_outline, head_bounds, clipping_slab, capsule, water_end_profile
from valvetrain_layout import valves

V = App.Vector


def carrier_footprint(params,frame,bottom,height):
    p = params['valvetrain_layout_estimated']['value']
    s = params['carrier_section_estimated']['value']
    c = params['cam_carrier_outline_estimated']['value']
    xs = layout(params,frame)['supports']
    lo,hi = xs[0]-p['cam_journal_width_mm']/2,xs[-1]+p['cam_journal_width_mm']/2
    w = s['base_half_width_mm']
    shape = rounded_prism(lo,-w,bottom,hi-lo,2*w,height,c['outer_corner_radius_mm'])
    holes = [Part.makeCylinder(s['scallop_radius_mm'],height+2,V(x,-w,bottom-1)) for x in xs[1:-1]]
    return shape.cut(Part.makeCompound(holes))


def oil_tray(params,frame,bottom,height):
    h = params['head_lower_casting_estimated']['value']
    s = params['carrier_section_estimated']['value']
    lo,hi = head_bounds(params,frame)
    inset,w = h['oil_tray_end_inset_mm'],h['oil_tray_half_width_mm']
    shape = rounded_prism(lo+inset,-w,bottom,hi-lo-2*inset,2*w,height,h['oil_tray_corner_radius_mm'])
    # The inner contour follows each outer scallop, retaining a continuous rim.
    wall = s['base_half_width_mm']-w
    bosses = [Part.makeCylinder(s['scallop_radius_mm']+wall,height+2,
                               V(x,-s['base_half_width_mm'],bottom-1))
              for x in layout(params,frame)['supports'][1:-1]]
    return shape.cut(Part.makeCompound(bosses))


def build(params,frame):
    h = params['head_lower_casting_estimated']['value']
    p = params['valvetrain_layout_estimated']['value']
    block = params['casting_visual_estimated']['value']
    lo,hi = head_bounds(params,frame)
    floor = p['outer_spring_seat_z_mm']-p['spring_seat_thickness_mm']
    sections = [(h['head_gasket_thickness_mm'],h['deck_half_width_mm']),
                (h['mid_height_mm'],h['mid_half_width_mm']),
                (floor,h['upper_half_width_mm'])]
    wires = [rounded_outline(lo,hi,w,z,h['corner_radius_mm']) for z,w in sections]
    body = Part.makeLoft(wires,True,False)
    rim = carrier_footprint(params,frame,floor-1,50).common(
        clipping_slab(params,frame,floor-1,h['carrier_gasket_vertical_thickness_mm']))
    additions = [rim]
    for x in layout(params,frame)['supports']:
        for y in (-block['deck_hole_y'],block['deck_hole_y']):
            additions.append(Part.makeCone(h['head_bolt_boss_radius_mm']+4,
                h['head_bolt_boss_radius_mm'],h['head_bolt_boss_top_z_mm']-h['head_gasket_thickness_mm'],
                V(x,y,h['head_gasket_thickness_mm'])))
    rows = valves(params,frame)
    for a,b in zip(rows,rows[1:]):
        ra,rb = [h[r['kind']+'_port_radius_mm']+h['port_boss_wall_mm'] for r in (a,b)]
        aa,bb = [(r['axis_origin_mm'][0],h[r['kind']+'_port_z_mm']) for r in (a,b)]
        flange = Part.Face(capsule(aa,bb,ra,rb)).extrude(V(0,0,h['manifold_flange_depth_mm']))
        flange.rotate(V(),V(1,0,0),90)
        flange.translate(V(0,h['manifold_face_y_mm'],0))
        additions.append(flange)
    depth = h['water_end_flange_depth_mm']
    additions.append(water_end_profile(params,frame,h['water_end_flange_wall_mm']).extrude(V(depth,0,0)))
    for y in (-h['water_end_bolt_half_pitch_mm'],h['water_end_bolt_half_pitch_mm']):
        additions.append(Part.makeCylinder(h['water_end_boss_radius_mm'],depth,
                          V(hi,y,h['water_end_z_mm']),V(1,0,0)))
    body = body.multiFuse(additions).removeSplitter()
    body = body.common(clipping_slab(params,frame,h['head_gasket_thickness_mm'],
                                    h['carrier_gasket_vertical_thickness_mm']))
    # All eight ports and the coolant mouths share one machined mounting plane.
    body = body.common(Part.makeBox(hi-lo+100,250+h['manifold_face_y_mm'],150,V(lo-50,-250,0)))
    assert body.isValid() and len(body.Solids)==1
    return body
