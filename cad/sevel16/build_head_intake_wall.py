"""A5 v012. Close the four intake roofs and machine the common gasket face."""
import FreeCAD as App
import Part
from config import OUTPUT, layout, load
from head_passages import port
from manifold_gasket_trace import profile
from valvetrain_layout import valves

V = App.Vector
SIDE = V(0,1,0)
NAME = 'SEVEL_Accessories_A5_v012_IntakeWall'


def wall(core,x):
    # Both joins lie in intact casting. Offset the actual flow surface so the
    # skin follows the bend without changing the throat or the manifold lip.
    zone = Part.makeBox(64,46,94,V(x-32,24,-3))
    section, = core.common(zone).Solids
    outer = section.makeOffsetShape(3,.001)
    assert outer.isValid() and len(outer.Solids)==1
    return outer.common(zone).cut(section)


def separated(shape,x,face_y):
    # A transverse slab cuts off the legitimate ends of the air passage.
    # An exterior breach places these two points in the same connected void.
    slab = Part.makeBox(48,face_y-24,75,V(x-24,24,8))
    air,exterior = V(x,50,45),V(x,50,80)
    voids = slab.cut(shape).Solids
    passage, = [s for s in voids if s.isInside(air,1e-6,False)]
    assert any(s.isInside(exterior,1e-6,False) for s in voids)
    return not passage.isInside(exterior,1e-6,False)


def revise(doc,params,frame):
    h = params['head_lower_casting_estimated']['value']
    y = h['manifold_face_y_mm']
    depth = params['manifold_visual_estimated']['value']['gasket_mm']
    face,fixings = profile(params,frame)
    face.translate(V(0,y-4,0))
    flange = face.extrude(SIDE*4)
    gasket = face.extrude(SIDE*depth)
    gasket.translate(SIDE*4)
    rows = valves(params,frame)
    cores = [port(params,row) for row in rows]
    old, = doc.HeadLower.Shape.Solids
    intake = [(r['axis_origin_mm'][0],c) for r,c in zip(rows,cores) if r['kind']=='intake']
    skins = [wall(core,x) for x,core in intake]
    stock = old.fuse(skins)
    bbox = stock.BoundBox
    trim = Part.makeBox(bbox.XLength+2,8,bbox.ZLength+2,V(bbox.XMin-1,y-4,bbox.ZMin-1))
    stock = stock.cut(trim).fuse(flange)
    drills,apertures = [],[]
    for row in rows:
        x = row['axis_origin_mm'][0]
        kind = row['kind']
        apertures.append(Part.makeCylinder(h[kind+'_port_radius_mm'],depth+2,
                         V(x,y-1,h[kind+'_port_z_mm']),SIDE))
    for x in layout(params,frame)['supports'][1::2]:
        drills.append(Part.makeCylinder(h['coolant_port_radius_mm'],h['manifold_flange_depth_mm']+depth,
                      V(x,y-h['manifold_flange_depth_mm'],h['coolant_port_z_mm']),SIDE))
    for p in fixings:
        drills.append(Part.makeCylinder(h['manifold_stud_radius_mm'],6+depth,V(p.x,y-6,p.z),SIDE))
    head = stock.cut(cores+drills).removeSplitter()
    gasket = gasket.cut(apertures+drills).removeSplitter()
    # The runtime has two gasket part IDs. Partition a single traced face at
    # their existing split plane; the two solids share the complete seam.
    mid = layout(params,frame)['supports'][2]
    half = Part.makeBox(mid-bbox.XMin+5,depth+2,bbox.ZLength+5,V(bbox.XMin-5,y-1,bbox.ZMin-2))
    for obj,s in [(doc.HeadLower,head),(doc.ManifoldGasket1,gasket.common(half)),
                  (doc.ManifoldGasket2,gasket.cut(half))]:
        s = s.removeSplitter()
        assert s.isValid() and len(s.Solids)==1 and s.Solids[0].isClosed(),obj.Name
        obj.Shape = s
    doc.recompute()
    for x,core in intake:
        assert not separated(old,x,y) and separated(head,x,y),(x,'roof')
        assert abs(core.common(head).Volume)<1e-5,(x,'obstructed intake')


def run():
    folder = OUTPUT/'models'
    dest = folder/(NAME+'.FCStd')
    if dest.exists():
        raise FileExistsError(dest)
    doc = App.newDocument(NAME)
    try:
        doc.mergeProject(str(folder/'SEVEL_Accessories_A5_v011_HeadMainRow.FCStd'))
        revise(doc,*load())
        doc.Label = NAME
        doc.saveAs(str(dest))
    finally:
        App.closeDocument(doc.Name)
    return App.openDocument(str(dest))
