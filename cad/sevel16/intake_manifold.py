"""Four inlet runners, common plenum and separate water-heating passage."""
import FreeCAD as App
import Part
from config import layout
from valvetrain_layout import valves
from manifold_profiles import sweep, flange
from cam_carrier import rounded_prism

V = App.Vector


def build(params,frame):
    h,p = params['head_lower_casting_estimated']['value'],params['manifold_visual_estimated']['value']
    rows = [r for r in valves(params,frame) if r['kind']=='intake']
    xs = [r['axis_origin_mm'][0] for r in rows]
    y = h['manifold_face_y_mm']+p['gasket_mm']
    z,r,w = h['intake_port_z_mm'],h['intake_port_radius_mm'],p['wall_mm']
    py,pz,pr = p['intake_plenum_y_mm'],p['intake_plenum_z_mm'],p['intake_plenum_radius_mm']
    def reservoir(radius):
        shape = Part.makeCylinder(radius,xs[-1]-xs[0],V(xs[0],py,pz),V(1,0,0))
        return shape.fuse(Part.makeSphere(radius,V(xs[0],py,pz))).fuse(
            Part.makeSphere(radius,V(xs[-1],py,pz)))
    outer,air = [reservoir(pr+w)],[reservoir(pr)]
    for row in rows:
        x = row['axis_origin_mm'][0]
        path = [(x,y,z),(x,y+35,z),(x,p['intake_runner_y_mm'],pz),(x,py,pz)]
        outer.append(sweep(path,r+w))
        air.append(sweep(path,r))
        # The sweep reaches the flange plane. An overlapping straight cutter
        # creates sliver faces where the curved passage starts to depart.
    for group in (rows[:2],rows[2:]):
        outer.append(flange(group,params,y,p['flange_mm'],w+2))
    center = (xs[0]+xs[-1])/2
    top = p['intake_top_z_mm']
    inlet = p['intake_inlet_radius_mm']
    outer += [Part.makeCylinder(inlet+w,top-pz,V(center,py,pz)),
              rounded_prism(center-45,py-35,top,90,70,p['flange_mm'],10)]
    air.append(Part.makeCylinder(inlet,top-pz+p['flange_mm']+1,V(center,py,pz)))
    fasteners = []
    for dx in (-33,33):
        for dy in (-25,25):
            fasteners.append(Part.makeCylinder(3.5,p['flange_mm']+2,V(center+dx,py+dy,top-1)))
    water = []
    water_xs = layout(params,frame)['supports'][1::2]
    cy,cz,cr = 110,82,p['coolant_tunnel_radius_mm']
    for x in water_xs:
        path = [(x,y,h['coolant_port_z_mm']),(x,y+16,h['coolant_port_z_mm']),
                (x,cy,cz-30),(x,cy,cz)]
        outer.append(sweep(path,cr+w))
        outer.append(Part.makeCylinder(cr+w,p['flange_mm'],V(x,y,h['coolant_port_z_mm']),V(0,1,0)))
        water.append(sweep(path,cr))
    for radius,collection in ((cr+w,outer),(cr,water)):
        collection.append(Part.makeCylinder(radius,water_xs[-1]-water_xs[0],V(water_xs[0],cy,cz),V(1,0,0)))
        collection.extend(Part.makeSphere(radius,V(x,cy,cz)) for x in water_xs)
    air_shape = air[0].multiFuse(air[1:]).removeSplitter()
    water_shape = water[0].multiFuse(water[1:]).removeSplitter()
    separation = air_shape.distToShape(water_shape)[0]
    assert separation>0.1,('air/water separation',separation)
    shape = outer[0].multiFuse(outer[1:]).cut(air_shape).cut(water_shape)
    shape = shape.cut(Part.makeCompound(fasteners)).removeSplitter()
    assert shape.isValid() and len(shape.Solids)==1
    assert len(air_shape.Solids)==len(water_shape.Solids)==1
    return shape,{'air':air_shape,'water':water_shape,'air_water_separation_mm':separation}
