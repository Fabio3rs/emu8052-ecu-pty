"""A5 v011. Register the five plug-side head bolts to both gasket photographs."""
from pathlib import Path

import FreeCAD as App
import Part
from config import OUTPUT, layout, load
from head_fixing_alignment import LANDMARKS, register
from build_head_alignment_review import verify as verify_small

V = App.Vector
STEM = 'SEVEL_Accessories_A5_v011_HeadMainRow'


def centers(xs):
    rows = [register(points,xs)['plug_side'] for points in LANDMARKS.values()]
    return [(round(sum(x for x,y in pair)/len(pair)),round(sum(y for x,y in pair)/len(pair)))
            for pair in zip(*rows)]


def cylinder(x,y,r,bottom,top):
    return Part.makeCylinder(r,top-bottom,V(x,y,bottom))


def trim_old_shoulder(x, y):
    # Retreat the old column into the casting above the low continuous ledge.
    # Limit the operation to the old column and its tapered reinforcement.
    points = [(y-35,10),(y-17,10),(y+17,60),(y+17,63),(y-35,63)]
    wire = Part.makePolygon([V(x-24,py,z) for py,z in [*points,points[0]]])
    return Part.Face(wire).extrude(V(48,0,0))


def revise(doc,params,frame):
    g = layout(params,frame)
    block = params['casting_visual_estimated']['value']
    head = params['head_lower_casting_estimated']['value']
    old_y, radius = -block['deck_hole_y'],block['deck_hole_radius']
    plane,seat = head['head_gasket_thickness_mm'],head['head_bolt_boss_top_z_mm']
    targets = centers(g['centers'])
    for name,bottom,top in [('Block',-24,0),('HeadGasket',0,plane),('HeadLower',plane,seat)]:
        obj = doc.getObject(name)
        original, = obj.Shape.Solids
        plugs = [cylinder(x,old_y,radius,bottom,top) for x in g['supports']]
        solid = original.fuse(plugs).removeSplitter()
        if name=='HeadLower':
            solid = solid.cut([trim_old_shoulder(x,old_y) for x in g['supports']])
            boss_r = head['head_bolt_boss_radius_mm']
            bosses = [Part.makeCone(boss_r+4,boss_r,seat-plane,V(x,y,plane)) for x,y in targets]
            solid = solid.fuse(bosses)
            # Clear the flat seat and the space occupied by a bolt head above it.
            solid = solid.cut([cylinder(x,y,boss_r+.1,seat,seat+14) for x,y in targets])
        drills = [cylinder(x,y,radius,bottom,top+1) for x,y in targets]
        solid = solid.cut(drills).removeSplitter()
        assert solid.isValid() and len(solid.Solids)==1 and solid.Solids[0].isClosed(),name
        obj.Shape = solid
    doc.recompute()


def verify(doc,params,frame):
    g = layout(params,frame)
    targets = centers(g['centers'])
    radius = params['casting_visual_estimated']['value']['deck_hole_radius']
    head = params['head_lower_casting_estimated']['value']
    plane,seat = head['head_gasket_thickness_mm'],head['head_bolt_boss_top_z_mm']
    for name,lo,hi in [('Block',-24,0),('HeadGasket',0,plane),('HeadLower',plane,seat)]:
        shape = doc.getObject(name).Shape
        assert shape.isValid() and len(shape.Solids)==1,name
        for x,y in targets:
            bore = cylinder(x,y,radius-.01,lo,hi)
            assert abs(shape.common(bore).Volume)<1e-5,(name,x,'obstruction')
            land = cylinder(x,y,radius+1,lo,hi).cut(cylinder(x,y,radius+.01,lo,hi))
            assert abs(land.cut(shape).Volume)<1e-5,(name,x,'broken wall')
            if name=='HeadLower':
                ring = cylinder(x,y,9.5,seat-.5,seat).cut(cylinder(x,y,radius+.01,seat-.5,seat))
                assert abs(ring.cut(shape).Volume)<1e-5,(x,'seat')
                assert abs(cylinder(x,y,9.5,seat,seat+10).common(shape).Volume)<1e-5,(x,'head space')
    verify_small(doc,params,frame)
    return targets


def run():
    folder = OUTPUT/'models'
    path = folder/(STEM+'.FCStd')
    if path.exists():
        raise FileExistsError(path)
    params,frame = load()
    doc = App.newDocument(STEM)
    try:
        doc.mergeProject(str(folder/'SEVEL_Accessories_A5_v010_HeadAlignment.FCStd'))
        revise(doc,params,frame)
        verify(doc,params,frame)
        doc.Label = STEM
        doc.saveAs(str(path))
    finally:
        App.closeDocument(doc.Name)
    return App.openDocument(str(path))
