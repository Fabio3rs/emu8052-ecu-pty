"""Rounded lateral casting around the existing auxiliary axis; additive only."""
import math
import FreeCAD as App
import Part
import auxiliary
from config import layout
from timing_parts import cylinder
from check_auxiliary import volume

V = App.Vector


def profile(x,r,y,z,inner):
    a,b,c,d = V(x,inner,z-r),V(x,y,z-r),V(x,y,z+r),V(x,inner,z+r)
    return Part.Wire([Part.makeLine(a,b),Part.Arc(b,V(x,y-r,z),c).toShape(),
                      Part.makeLine(c,d),Part.makeLine(d,a)])


def blended_profile(x,r,y,z,inner,above,below,taper_radius,full_radius):
    """Broaden the lobe into the wall with vertical tangents at both roots."""
    assert min(r,above,below,taper_radius,full_radius)>0 and inner>y
    # Small end stations disappear inside the existing wall instead of
    # ending in a broad exposed planar cap.
    depth_scale = min(1.0,(r/taper_radius)**2)
    height_scale = min(1.0,r/full_radius)
    outer = inner-(inner-y+r)*depth_scale
    top,bottom = z+r+above*height_scale,z-r-below*height_scale
    def curve(points):
        result = Part.BezierCurve()
        result.setPoles([V(x,yy,zz) for yy,zz in points])
        return result.toShape()
    upper = curve([(outer,z),(outer,z+(top-z)*0.55),
                   (inner,z+(top-z)*0.55),(inner,top)])
    lower = curve([(inner,bottom),(inner,z-(z-bottom)*0.55),
                   (outer,z-(z-bottom)*0.55),(outer,z)])
    return Part.Wire([upper,Part.makeLine(V(x,inner,top),V(x,inner,bottom)),lower])


def service_tools(params,frame):
    p = params['casting_visual_estimated']['value']
    extra = params['auxiliary_casting_enclosure_estimated']['value']['service_cut_extension_mm']
    xs = [b['x'] for b in frame['bore_circle_centers_mm']]
    span = xs[-1]-xs[0]
    angle = math.radians(params['side_access_inclination_estimated']['value'])
    normal = V(0,-math.cos(angle),math.sin(angle))
    mouth = V(xs[0]+span*p['access_open_x_fraction'],-82,p['access_open_z'])
    breather = Part.makeCylinder(p['access_open_radius'],35+extra,mouth-normal*27,normal)
    relief = params['auxiliary_casting_enclosure_estimated']['value'].get('breather_face_relief_mm',0)
    if relief:
        # Keep the original annular receiver face exposed. This cuts only
        # the added shell; the original cone and its mouth remain intact.
        breather = breather.fuse(Part.makeCylinder(p['access_open_radius']+relief,extra,mouth,normal))
    oil_filter = Part.makeCylinder(p['filter_radius'],47+extra,
        V(xs[0]+span*p['filter_x_fraction'],-100-extra,p['filter_z']),V(0,1,0))
    return {'breather':breather,'oil_filter':oil_filter}


def build(original,params,frame):
    p = params['auxiliary_casting_enclosure_estimated']['value']
    c = params['casting_visual_estimated']['value']
    t,n = params['timing_visual_estimated']['value'],params['auxiliary_nominal']['value']
    stations = p['stations_x_radius_mm']
    assert all(a[0]<b[0] for a,b in zip(stations,stations[1:]))
    assert c['aux_y']<p['inner_y_mm']<-frame['cylinder_bore_diameter_mm']/2
    if 'root_blend_above_mm' in p:
        wires = [blended_profile(x,r,c['aux_y'],c['aux_z'],p['inner_y_mm'],
                    p['root_blend_above_mm'],p['root_blend_below_mm'],
                    p['root_blend_taper_radius_mm'],p['root_blend_full_radius_mm']) for x,r in stations]
    else:
        wires = [profile(x,r,c['aux_y'],c['aux_z'],p['inner_y_mm']) for x,r in stations]
    outer = Part.makeLoft(wires,True,False)
    _,clearance = auxiliary.casting_tools(params)
    front = cylinder(n['block_seat_diameters_mm'][0]/2,t['aux_front_journal_x_mm'],
                     t['aux_front_journal_width_mm'])
    front.translate(V(0,c['aux_y'],c['aux_z']))
    gap = params['auxiliary_internal_estimated']['value']['running_clearance_mm']
    shoulder = cylinder(n['journal_diameters_mm'][0]/2+gap,t['aux_front_journal_x_mm']-gap,
                        t['aux_front_journal_width_mm']+2*gap)
    shoulder.translate(V(0,c['aux_y'],c['aux_z']))
    ports = service_tools(params,frame)
    tools = [clearance,front,shoulder,*ports.values()]
    if p.get('preserve_crank_bay_clearance',False):
        # Same conservative rod/bolt sweep used by stationary.clear_crank_bays.
        g = layout(params,frame)
        rod = params['piston_rod_visual_estimated']['value']
        moving = params['moving_geometry_estimated']['value']
        bound = math.hypot(rod['rod_bolt_y_mm']+rod['rod_bolt_head_radius_mm'],
                           rod['rod_bolt_half_length_mm']+4)
        radius = max(moving['counterweight_radius_mm'],g['radius']+bound,
                     g['radius']+params['moving_nominal']['crankpin_diameter_mm']['value']/2)
        radius += moving['crankcase_clearance_mm']
        half_web = params['block_visual_estimated']['value']['web_thickness']/2
        tools.extend(Part.makeCylinder(radius,b-a-2*half_web,V(a+half_web,0,-g['height']),V(1,0,0))
                     for a,b in zip(g['supports'],g['supports'][1:]))
    shell = outer.cut(Part.makeCompound(tools))
    result = original.fuse(shell)
    assert result.isValid() and len(result.Solids)==1
    added,removed = result.cut(original),original.cut(result)
    assert added.isValid() and volume(added)>0 and volume(removed)<1e-5
    box = added.optimalBoundingBox(False)
    assert box.YMax<-frame['cylinder_bore_diameter_mm']/2
    assert box.ZMin>-params['block_visual_estimated']['value']['height']
    for name,tool in ports.items():
        assert volume(added.common(tool))<1e-5,name
    return result,added,{'added_volume_mm3':volume(added),'removed_volume_mm3':volume(removed),
        'bore_plane_y_clearance_mm':-frame['cylinder_bore_diameter_mm']/2-box.YMax,
        'seal_plane_z_clearance_mm':box.ZMin+params['block_visual_estimated']['value']['height'],
        'service_openings_preserved':list(ports),'mode':'additive rounded loft; original material retained'}
