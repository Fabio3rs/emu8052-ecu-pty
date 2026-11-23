"""Valve stack in local X=Y=0 with rest Z positions relative to the master deck."""
import FreeCAD as App
import Part

V = App.Vector


def ring(outer, inner, bottom, height):
    return Part.makeCylinder(outer,height,V(0,0,bottom)).cut(
           Part.makeCylinder(inner,height+2,V(0,0,bottom-1)))


def build(params, row):
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    radius,stem = n[row['kind']+'_head_mm']/2,n['stem_mm']/2
    base = p['valve_face_closed_z_mm']
    margin,face,neck = p['valve_margin_mm'],p['valve_face_height_mm'],p['valve_neck_height_mm']
    cone_z = base+margin
    valve = Part.makeCylinder(radius,margin,V(0,0,base)).fuse(
            Part.makeCone(radius,radius-face,face,V(0,0,cone_z)))
    valve = valve.fuse(Part.makeCone(radius-face,stem,neck,V(0,0,cone_z+face)))
    shaft_z = cone_z+face+neck
    valve = valve.fuse(Part.makeCylinder(stem,row['stem_top_closed_z_mm']-shaft_z,V(0,0,shaft_z)))
    gz,gh,depth = p['keeper_groove_z_mm'],p['keeper_groove_height_mm'],p['keeper_groove_depth_mm']
    valve = valve.cut(ring(stem+1,stem-depth,gz,gh)).removeSplitter()
    seat = Part.makeCylinder(radius+p['seat_radial_wall_mm'],p['seat_height_mm'],V(0,0,cone_z))
    seat = seat.cut(Part.makeCone(radius,radius-p['seat_height_mm'],p['seat_height_mm'],V(0,0,cone_z)))
    guide = ring(n['guide_outer_mm']/2,n['guide_inner_mm']/2,p['guide_base_z_mm'],p['guide_length_mm'])
    bottom,top = row['tappet_bottom_closed_z_mm'],row['tappet_top_closed_z_mm']
    tappet = Part.makeCylinder(n['tappet_mm']/2,top-bottom,V(0,0,bottom)).cut(
             Part.makeCylinder(n['tappet_mm']/2-p['tappet_wall_mm'],top-bottom-p['tappet_wall_mm']+1,V(0,0,bottom-1)))
    shim = Part.makeCylinder(p['shim_diameter_mm']/2,n['shim_mm'],V(0,0,top))
    kb,kh = p['keeper_base_z_mm'],p['keeper_height_mm']
    r0,r1 = p['keeper_radii_mm']
    cone = Part.makeCone(r0,r1,kh,V(0,0,kb))
    keepers = cone.cut(Part.makeCylinder(stem,kh+2,V(0,0,kb-1)))
    keepers = keepers.fuse(ring(stem,stem-depth,gz,gh)).removeSplitter()
    gap = p['keeper_split_gap_mm']
    halves = [keepers.common(Part.makeBox(r1+1,2*r1+2,kh+2,V(gap/2,-r1-1,kb-1))),
              keepers.common(Part.makeBox(r1+1,2*r1+2,kh+2,V(-r1-1-gap/2,-r1-1,kb-1)))]
    retainer = Part.makeCylinder(p['retainer_radius_mm'],p['retainer_thickness_mm'],
                                V(0,0,p['retainer_bottom_z_mm'])).cut(cone)
    pieces = {'Valve':(valve,'valve'),'Seat':(seat,'fixed'),'Guide':(guide,'fixed'),
              'Tappet':(tappet,'valve'),'Shim':(shim,'valve'),'Retainer':(retainer,'valve'),
              'Keeper1':(halves[0],'valve'),'Keeper2':(halves[1],'valve')}
    for kind in ('inner','outer'):
        top = p[kind+'_spring_seat_z_mm']
        bottom = top-p['spring_seat_thickness_mm']
        support = params.get('spring_seat_support_estimated',{}).get('value',{})
        if support:
            if support.get('mode')!='stepped_lower_seat_partition':
                raise ValueError('Unknown lower spring-seat construction mode')
            if kind=='inner':
                bottom = p['outer_spring_seat_z_mm']
        assert top>bottom
        shape = ring(p[kind+'_spring_seat_radius_mm'],n['guide_outer_mm']/2,
                     bottom,top-bottom)
        pieces[kind.title()+'SpringSeat'] = (shape,'fixed')
    for name,(shape,_) in pieces.items():
        assert shape.isValid() and len(shape.Solids)==1,name
    return pieces
