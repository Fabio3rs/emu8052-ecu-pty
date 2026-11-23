"""Openings, intended contacts and explicit missing interfaces of the preview."""
import FreeCAD as App
import Part
from config import layout
from valvetrain_layout import valves
from head_profiles import head_bounds, water_end_profile
from head_passages import port
from timing_sweeps import overlaps
from check_auxiliary import volume

V = App.Vector


def run(shapes,old_shapes,params,frame):
    h = params['head_lower_casting_estimated']['value']
    b = params['casting_visual_estimated']['value']
    body = shapes['HeadLower']
    water = [Part.makeBox(b['water_slot_length'],b['water_slot_width'],h['deck_coolant_recess_depth_mm'],
             V(x-b['water_slot_length']/2,side*55-b['water_slot_width']/2,0))
             for x in layout(params,frame)['centers'] for side in (-1,1)]
    water += [Part.makeCylinder(h['coolant_port_radius_mm'],h['manifold_flange_depth_mm']+1,
              V(x,h['manifold_face_y_mm']+1,h['coolant_port_z_mm']),V(0,-1,0))
              for x in layout(params,frame)['supports'][1::2]]
    end = water_end_profile(params,frame)
    depth = h['water_end_flange_depth_mm']+1
    end.translate(V(depth,0,0))
    water.append(end.extrude(V(-depth-h['water_end_depth_mm'],0,0)))
    gas_water = {}
    for row in valves(params,frame):
        passage = port(params,row)
        gas_water[row['id']] = [volume(passage.common(w)) if overlaps(passage,w) else 0.0 for w in water]
        assert max(gas_water[row['id']])<1e-5,(row['id'],gas_water[row['id']])
    contacts = {}
    for name,shape in old_shapes.items():
        if name.endswith(('_Seat','_Guide','_OuterSpringSeat')):
            contacts[name] = body.distToShape(shape)[0]
            assert contacts[name]<1e-6,name
    for a,c in [('HeadLower','HeadGasket'),('HeadLower','CarrierGasket'),
                ('HeadGasket','Block'),('CarrierGasket','CamCarrier')]:
        contacts[a+'/'+c] = shapes[a].distToShape(shapes.get(c,old_shapes.get(c)))[0]
        assert contacts[a+'/'+c]<1e-6,(a,c)
    gaps = {}
    for row in valves(params,frame):
        inner = old_shapes[row['id']+'_InnerSpringSeat']
        outer = old_shapes[row['id']+'_OuterSpringSeat']
        gaps[row['id']] = {'inner_seat_to_head_mm':inner.distToShape(body)[0],
                           'inner_seat_to_outer_seat_mm':inner.distToShape(outer)[0]}
    supported = all(g['inner_seat_to_outer_seat_mm']<1e-7 for g in gaps.values())
    limitations = ['Water recesses are intentionally blind; complete cooling/oil routing is absent',
                   'Chamber volume and casting angles remain unresolved geometrical approximations']
    if not supported:
        limitations.append('Eight inner spring seats retain the previous unsupported height offset')
    return {'status':('PASS_CONTACTS_AND_SEPARATE_VISUAL_PASSAGES_WITH_SUPPORTED_SEATS' if supported
                      else 'PASS_CONTACTS_AND_SEPARATE_VISUAL_PASSAGES_WITH_KNOWN_GAPS'),
            'contacts_mm':contacts,'gas_to_water_overlap_mm3':gas_water,
            'inherited_inner_spring_seat_support_gaps':gaps,
            'inner_seat_supported_via_outer_region':supported,'limitations':limitations}
