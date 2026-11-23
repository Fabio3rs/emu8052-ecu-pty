"""Continuous clearance and load-path proof for the stepped lower-seat regions."""
import math
from check_auxiliary import difference, volume
from check_head_increment import scan
from timing_sweeps import bounds
from valvetrain_layout import valves


def run(replacements,old_shapes,envelopes,params,frame):
    retained = {k:v for k,v in envelopes.items() if k not in replacements}
    assert len(replacements)==8 and len(retained)==184
    report = scan(replacements,retained)
    assert report['status']=='PASS_HEAD_INCREMENT_GEOMETRY',report['failures']
    assert report['pairs_checked']==1500
    report['status'] = 'PASS_STEPPED_SPRING_SEATS'
    report['scope'] = 'Eight modified fixed seat regions versus 184 retained parts and each other; continuous bounds'
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    added,contacts = {},{}
    for row in valves(params,frame):
        prefix = row['id']
        name = prefix+'_InnerSpringSeat'
        shape,old = replacements[name],old_shapes[name]
        assert shape.isValid() and len(shape.Solids)==1
        q,previous = bounds(shape),bounds(old)
        assert abs(q.ZMax-previous.ZMax)<1e-7
        assert abs(q.ZMin-p['outer_spring_seat_z_mm'])<1e-7
        removed = volume(old.cut(shape))
        assert removed<1e-5
        added[name] = volume(shape.cut(old))
        expected = math.pi*(p['inner_spring_seat_radius_mm']**2-(n['guide_outer_mm']/2)**2)*(previous.ZMin-q.ZMin)
        assert abs(added[name]-expected)<1e-5,(name,added[name],expected)
        outer = old_shapes[prefix+'_OuterSpringSeat']
        united = shape.fuse(outer).removeSplitter()
        assert united.isValid() and len(united.Solids)==1
        assert volume(shape.common(outer))<1e-5
        lower_contact = outer.distToShape(old_shapes['HeadLower'])[0]
        joint_contact = shape.distToShape(outer)[0]
        assert max(lower_contact,joint_contact)<1e-7
        contacts[prefix] = {'outer_region_to_head_mm':lower_contact,
                            'inner_region_to_outer_region_mm':joint_contact,
                            'united_seat_solids':len(united.Solids),
                            'outer_spring_radial_gap_mm':p['outer_spring_mean_radius_mm']-
                                p['outer_spring_wire_radius_mm']-p['inner_spring_seat_radius_mm']}
        assert contacts[prefix]['outer_spring_radial_gap_mm']>0
    report.update(added_volumes_mm3=added,load_path_contacts=contacts,
        limitations=['Two CAD solids partition one catalogued lower seat; not two OEM parts',
                     'Axial and radial seat dimensions remain provisional',
                     'Unground helical spring-end clearance remains documented separately'])
    return report
