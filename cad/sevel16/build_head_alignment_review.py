"""A5 v010: register the four secondary fixings across the deck interfaces."""
import hashlib

import FreeCAD as App
import Part
from config import OUTPUT, layout, load
from head_fixing_alignment import lower_centers
import head_flanks
import head_water_end

V = App.Vector
UP = V(0,0,1)


def revise(doc,source,params,frame):
    xs = layout(params,frame)['centers']
    centers = lower_centers(xs)
    head = head_flanks.spark_face(source,params,frame,lower_pads=False)
    head = head_water_end.revised(head_flanks.manifold_face(head,params,frame),params,frame)
    parts = {'Block':doc.Block.Shape,'HeadGasket':doc.HeadGasket.Shape,'HeadLower':head}
    h = params['head_lower_casting_estimated']['value']['head_gasket_thickness_mm']
    # Only the corner of an inherited rectangular water opening touching the
    # new land is filled. Retain its remaining section on all three surfaces.
    stages = [('Block',-7,0,3.4),('HeadGasket',0,h,4.9),('HeadLower',h,10,4.3)]
    for name,bottom,top,radius in stages:
        stock,tools = [],[]
        for cx,cy in centers:
            base = V(cx,cy,bottom)
            if name=='HeadLower':
                stock.append(Part.makeCone(11,7.8,top-bottom,base))
                tools.append(Part.makeCylinder(7.6,4,V(cx,cy,top)))
            else:
                stock.append(Part.makeCylinder(7.6,top-bottom,base))
            start = -5 if name=='Block' else bottom-1
            tools.append(Part.makeCylinder(radius,top+1-start,V(cx,cy,start)))
        original, = parts[name].Solids
        joined = original.fuse(stock)
        assert not joined.isNull(),(name,'empty union')
        shape = joined.cut(tools).removeSplitter()
        assert shape.isValid() and len(shape.Solids)==1 and shape.Solids[0].isClosed(),name
        doc.getObject(name).Shape = shape
    doc.recompute()


def verify(doc,params,frame):
    h = params['head_lower_casting_estimated']['value']['head_gasket_thickness_mm']
    xs = layout(params,frame)['centers']
    for i,(cx,cy) in enumerate(lower_centers(xs),1):
        for name,z,top,r in [('Block',-5,0,3.4),('HeadGasket',0,h,4.9),('HeadLower',h,10,4.3)]:
            shape = doc.getObject(name).Shape
            axis = Part.makeCylinder(r-.01,top-z,V(cx,cy,z))
            assert abs(axis.common(shape).Volume)<1e-6,(i,name,'axis')
            land = Part.makeCylinder(7.5,top-z,V(cx,cy,z)).cut(
                Part.makeCylinder(r+.01,top-z,V(cx,cy,z)))
            assert abs(land.cut(shape).Volume)<1e-5,(i,name,'land',land.cut(shape).Volume)
        assert abs(doc.HeadLower.Shape.common(doc.getObject(f'C{i}_SparkShell').Shape).Volume)<1e-5


def run():
    folder = OUTPUT/'models'
    previous = folder/'SEVEL_Accessories_A5_v009_HeadBores.FCStd'
    dest = folder/'SEVEL_Accessories_A5_v010_HeadAlignment.FCStd'
    if dest.exists():
        raise FileExistsError(dest)
    if hashlib.sha256(previous.read_bytes()).hexdigest()!='aff7f343178a2b98e317c169d46cf2e4615b2624f2af12ff49df7cfb27bc435b':
        raise ValueError('Unexpected v009 parent')
    params,frame = load()
    source = App.newDocument('HeadAlignmentSource')
    doc = App.newDocument(dest.stem)
    try:
        source.mergeProject(str(folder/'SEVEL_Accessories_A5_v007_DrainReview.FCStd'))
        doc.mergeProject(str(previous))
        revise(doc,source,params,frame)
        verify(doc,params,frame)
        doc.Label = dest.stem
        doc.saveAs(str(dest))
    finally:
        App.closeDocument(source.Name)
        App.closeDocument(doc.Name)
    return App.openDocument(str(dest))
