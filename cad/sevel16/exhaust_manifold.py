"""Four exhaust runners with a common downward outlet, on the inlet side."""
import FreeCAD as App
import Part
from valvetrain_layout import valves
from manifold_profiles import flange

V = App.Vector


def rounded_path(points,radius):
    # Analytic cylinders with spherical elbows survive STEP round-tripping.
    # The former spatial Bezier pipe passed BOPCheck but changed its trimmed
    # surface domain on STEP import. Keep the same interfaces and endpoints.
    points = [V(*point) for point in points]
    segments = [Part.makeCylinder(radius,(b-a).Length,a,b-a)
                for a,b in zip(points,points[1:])]
    segments.extend(Part.makeSphere(radius,point) for point in points[1:-1])
    return segments[0].multiFuse(segments[1:]).removeSplitter()


def build(params,frame):
    h,p = params['head_lower_casting_estimated']['value'],params['manifold_visual_estimated']['value']
    rows = [r for r in valves(params,frame) if r['kind']=='exhaust']
    y = h['manifold_face_y_mm']+p['gasket_mm']
    z,r,w = h['exhaust_port_z_mm'],h['exhaust_port_radius_mm'],p['wall_mm']
    cx = (rows[0]['axis_origin_mm'][0]+rows[-1]['axis_origin_mm'][0])/2
    cy,cz = p['exhaust_outlet_y_mm'],p['exhaust_outlet_z_mm']
    outer,holes,paths = [],[],[]
    # Spread the four entries along a short collector. Coincident tangent
    # pipe ends at one point make the Boolean junction numerically singular.
    outlets = [cx+p['exhaust_runner_spacing_mm']*factor for factor in (-1.5,-0.5,0.5,1.5)]
    for row,end_x in zip(rows,outlets):
        x = row['axis_origin_mm'][0]
        path = [(x,y,z),(x,p['exhaust_merge_y_mm'],z),
                (end_x,cy,p['exhaust_merge_z_mm']),(end_x,cy,cz+50)]
        paths.append(path)
        outer.append(rounded_path(path,r+w))
        holes.append(rounded_path(path,r))
        # The curved bore already opens at the flange. A straight overlapping
        # cutter leaves thin internal seams that cannot be meshed closed.
    for group in (rows[:1],rows[1:3],rows[3:]):
        outer.append(flange(group,params,y,p['flange_mm'],w))
    radius = p['exhaust_outlet_radius_mm']
    collector_start = len(outer)
    for rr,collection in ((radius+w,outer),(radius,holes)):
        collection.append(Part.makeCylinder(rr,outlets[-1]-outlets[0],V(outlets[0],cy,cz+50),V(1,0,0)))
        collection.extend(Part.makeSphere(rr,V(xx,cy,cz+50)) for xx in (outlets[0],outlets[-1]))
    outer += [Part.makeCylinder(radius+w,50,V(cx,cy,cz)),
              Part.makeCylinder(p['exhaust_flange_radius_mm'],p['flange_mm'],V(cx,cy,cz))]
    holes.append(Part.makeCylinder(radius,52,V(cx,cy,cz-1)))
    # Start with the common collector, then add complete runners. Combining
    # intersecting runner ends first lost a branch in an OCC Boolean result.
    holes = holes[len(rows):]+holes[:len(rows)]
    gas = holes[0]
    for hole in holes[1:]:
        gas = gas.fuse(hole)
    gas = gas.removeSplitter()
    # Inset the independent passage probes to avoid coincident trim faces.
    # This checks the entire route, not just its opening at the head.
    passage_missing = [rounded_path(path,r-0.1).cut(gas).Volume for path in paths]
    assert max(passage_missing)<1e-5,passage_missing
    fasteners = []
    for dx,dy in ((-30,0),(15,-26),(15,26)):
        fasteners.append(Part.makeCylinder(4,p['flange_mm']+2,V(cx+dx,cy+dy,cz-1)))
    outer = outer[collector_start:]+outer[:collector_start]
    shape = outer[0]
    for addition in outer[1:]:
        shape = shape.fuse(addition)
    shape = shape.cut(gas).cut(Part.makeCompound(fasteners)).removeSplitter()
    assert shape.isValid() and len(shape.Solids)==1
    assert gas.isValid() and len(gas.Solids)==1
    return shape,{'gas':gas,'runner_probe_margin_mm':0.1,
                  'runner_probe_missing_mm3':passage_missing}
