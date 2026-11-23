"""Two-journal auxiliary shaft and explicitly estimated internal casting clearance."""
import math
import FreeCAD as App
import Part
from timing_parts import cylinder, ring

V = App.Vector


def gear(p):
    wires = []
    for fraction in (0,.5,1):
        points = []
        for i in range(p['gear_teeth_visual_count']):
            for f,r in ((0,p['gear_root_radius_mm']),(.2,p['gear_root_radius_mm']),
                        (.35,p['gear_tip_radius_mm']),(.65,p['gear_tip_radius_mm']),
                        (.8,p['gear_root_radius_mm'])):
                a = 2*math.pi*(i+f)/p['gear_teeth_visual_count']
                a += math.radians(fraction*p['gear_twist_deg'])
                points.append(V(p['gear_x_mm']+fraction*p['gear_width_mm'],
                                r*math.cos(a),r*math.sin(a)))
        wires.append(Part.makePolygon(points+[points[0]]))
    # Ruled sections stay within the tooth-tip cylinder. A smooth interpolated
    # loft overshot this radius between sections despite valid end profiles.
    return Part.makeLoft(wires,True,True)


def build(params, front_local):
    p = params['auxiliary_internal_estimated']['value']
    n = params['auxiliary_nominal']['value']
    t = params['timing_visual_estimated']['value']
    x = t['aux_front_journal_x_mm']+t['aux_front_journal_width_mm']
    rear,width = p['rear_journal_x_mm'],p['rear_journal_width_mm']
    assert x<p['eccentric_x_mm']<p['gear_x_mm']<rear
    assert p['gear_x_mm']+p['gear_width_mm']<rear
    body = cylinder(p['body_radius_mm'],x,rear+width+p['tail_length_mm']-x)
    eccentric = cylinder(p['eccentric_radius_mm'],p['eccentric_x_mm'],p['eccentric_width_mm'])
    eccentric.translate(V(0,p['eccentric_offset_mm'],0))
    journal = cylinder(n['journal_diameters_mm'][1]/2,rear,width)
    shaft = front_local.multiFuse([body,eccentric,journal,gear(p)]).removeSplitter()
    bush = ring(n['block_seat_diameters_mm'][1]/2,n['bush_inner_diameters_mm'][1]/2,rear,width)
    envelope = front_local.multiFuse([body,journal,
        cylinder(p['eccentric_radius_mm']+abs(p['eccentric_offset_mm']),p['eccentric_x_mm'],p['eccentric_width_mm']),
        cylinder(p['gear_tip_radius_mm'],p['gear_x_mm'],p['gear_width_mm'])]).removeSplitter()
    for shape in (shaft,bush,envelope):
        assert shape.isValid() and len(shape.Solids)==1
    return shaft,bush,envelope


def casting_tools(params):
    p = params['auxiliary_internal_estimated']['value']
    n = params['auxiliary_nominal']['value']
    t = params['timing_visual_estimated']['value']
    c = params['casting_visual_estimated']['value']
    x = t['aux_front_journal_x_mm']+t['aux_front_journal_width_mm']
    rear,width = p['rear_journal_x_mm'],p['rear_journal_width_mm']
    gap,margin = p['running_clearance_mm'],p['rear_housing_margin_mm']
    end = rear+width+p['tail_length_mm']+gap
    tools = [cylinder(p['body_radius_mm']+gap,x,end-x),
             cylinder(n['journal_diameters_mm'][1]/2+gap,rear-gap,width+2*gap),
             cylinder(n['block_seat_diameters_mm'][1]/2,rear,width)]
    for prefix,radius in [('eccentric',p['eccentric_radius_mm']+abs(p['eccentric_offset_mm'])),
                          ('gear',p['gear_tip_radius_mm'])]:
        tools.append(cylinder(radius+gap,p[prefix+'_x_mm']-gap,p[prefix+'_width_mm']+2*gap))
    housing = cylinder(p['rear_housing_radius_mm'],rear-margin,width+2*margin)
    cutter = tools[0].multiFuse(tools[1:]).removeSplitter()
    for shape in (housing,cutter):
        shape.translate(V(0,c['aux_y'],c['aux_z']))
    return housing,cutter
