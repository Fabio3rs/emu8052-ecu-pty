"""Visible head openings; water jacket and flow geometry are not reconstructed."""
import FreeCAD as App
import Part
from config import layout
from valvetrain_layout import valves
from head_profiles import capsule, head_bounds, water_end_profile
from head_blank import oil_tray

V = App.Vector


def circle(center,normal,radius):
    return Part.Wire([Part.makeCircle(radius,V(*center),V(*normal))])


def chambers(params,frame):
    h = params['head_lower_casting_estimated']['value']
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    rows = valves(params,frame)
    result = []
    for i in range(4):
        a,b = rows[2*i:2*i+2]
        ra,rb = [n[r['kind']+'_head_mm']/2+h['chamber_radial_clearance_mm'] for r in (a,b)]
        aa,bb = [r['axis_origin_mm'][:2] for r in (a,b)]
        expansion = h['chamber_deck_expansion_mm']
        lower = capsule(aa,bb,ra+expansion,rb+expansion,h['head_gasket_thickness_mm'])
        upper = capsule(aa,bb,ra,rb,p['valve_face_closed_z_mm']+p['valve_margin_mm'])
        chamber = Part.makeLoft([lower,upper],True,True)
        assert chamber.isValid() and len(chamber.Solids)==1
        result.append(chamber)
    return result


def port(params,row):
    h = params['head_lower_casting_estimated']['value']
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    x,y,_ = row['axis_origin_mm']
    start = p['valve_face_closed_z_mm']+p['valve_margin_mm']+p['seat_height_mm']
    throat = n[row['kind']+'_head_mm']/2-p['seat_height_mm']
    radius,z = h[row['kind']+'_port_radius_mm'],h[row['kind']+'_port_z_mm']
    sections = [circle((x,y,start),(0,0,1),throat),
                circle((x,5,start+h['port_throat_rise_mm']),(0,0.7,0.7),throat),
                circle((x,h['port_bend_y_mm'],z),(0,1,0),radius),
                circle((x,h['manifold_face_y_mm']+1,z),(0,1,0),radius)]
    shape = Part.makeLoft(sections,True,False)
    assert shape.isValid() and len(shape.Solids)==1,row['id']
    return shape


def build(params,frame):
    h = params['head_lower_casting_estimated']['value']
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    block = params['casting_visual_estimated']['value']
    floor = p['outer_spring_seat_z_mm']-p['spring_seat_thickness_mm']
    chamber_shapes = chambers(params,frame)
    holes = [oil_tray(params,frame,floor,70),*chamber_shapes]
    for row in valves(params,frame):
        x,y,_ = row['axis_origin_mm']
        radius = n[row['kind']+'_head_mm']/2+p['seat_radial_wall_mm']
        seat_z = p['valve_face_closed_z_mm']+p['valve_margin_mm']
        holes.extend([Part.makeCylinder(radius,p['seat_height_mm'],V(x,y,seat_z)),
                      Part.makeCylinder(n['guide_outer_mm']/2,p['guide_length_mm'],V(x,y,p['guide_base_z_mm'])),
                      Part.makeCylinder(h['stem_relief_radius_mm'],p['guide_base_z_mm']-seat_z,V(x,y,seat_z)),
                      port(params,row)])
    for x in layout(params,frame)['supports']:
        for y in (-block['deck_hole_y'],block['deck_hole_y']):
            holes.append(Part.makeCylinder(block['deck_hole_radius'],100,V(x,y,0)))
    for x in layout(params,frame)['centers']:
        origin = V(x,h['spark_plug_y_mm'],h['spark_plug_z_mm'])
        end = V(x,-10,h['head_gasket_thickness_mm']+3)
        delta = end-origin
        holes.append(Part.makeCylinder(h['spark_plug_radius_mm'],delta.Length,origin,delta))
        for side in (-1,1):
            holes.append(Part.makeBox(block['water_slot_length'],block['water_slot_width'],
                h['deck_coolant_recess_depth_mm'],
                V(x-block['water_slot_length']/2,side*55-block['water_slot_width']/2,0)))
    for x in layout(params,frame)['supports'][1::2]:
        holes.append(Part.makeCylinder(h['coolant_port_radius_mm'],h['manifold_flange_depth_mm']+1,
            V(x,h['manifold_face_y_mm']+1,h['coolant_port_z_mm']),V(0,-1,0)))
    _,hi = head_bounds(params,frame)
    depth = h['water_end_flange_depth_mm']+1
    mouth = water_end_profile(params,frame)
    mouth.translate(V(depth,0,0))
    holes.append(mouth.extrude(V(-depth-h['water_end_depth_mm'],0,0)))
    for y in (-h['water_end_bolt_half_pitch_mm'],h['water_end_bolt_half_pitch_mm']):
        holes.append(Part.makeCylinder(h['water_end_bolt_radius_mm'],depth+h['water_end_depth_mm'],
            V(hi+depth,y,h['water_end_z_mm']),V(-1,0,0)))
    return holes,chamber_shapes


def finish(blank,params,frame):
    holes,chamber_shapes = build(params,frame)
    shape = blank.cut(Part.makeCompound(holes)).removeSplitter()
    assert shape.isValid() and len(shape.Solids)==1
    return shape,{'chamber_tool_volumes_cm3':[s.Volume/1000 for s in chamber_shapes],
                  'documented_chamber_volume_cm3':params['head_chamber_documented_volume']['value'],
                  'limits':['Chamber tools exclude valve-seat and spark-plug recess volumes',
                            'Water openings are blind visual recesses; no connected water jacket',
                            'Port paths are provisional lofts, not measured flow passages']}
