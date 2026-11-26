"""Revise the four lower fixing bosses using the deck normal as their axis."""
import hashlib
import math
from pathlib import Path

import FreeCAD as App
import Part
from config import OUTPUT, layout, load
import head_flanks
import head_water_end


def run():
    models = OUTPUT/'models'
    v7 = models/'SEVEL_Accessories_A5_v007_DrainReview.FCStd'
    v8 = models/'SEVEL_Accessories_A5_v008_HeadExterior.FCStd'
    dest = models/'SEVEL_Accessories_A5_v009_HeadBores.FCStd'
    if dest.exists():
        raise FileExistsError(dest)
    if hashlib.sha256(v8.read_bytes()).hexdigest()!='5fa4019e6f541398e24e7e2de00ba517a2d7c4d4eaa1c854186d6ef5b63e565a':
        raise ValueError('Unexpected v008 parent')
    src = App.newDocument('HeadBoresSource')
    doc = App.newDocument(dest.stem)
    params,frame = load()
    try:
        src.mergeProject(str(v7))
        doc.mergeProject(str(v8))
        head = head_flanks.spark_face(src,params,frame,upright_lower_bores=True)
        head = head_flanks.manifold_face(head,params,frame)
        head = head_water_end.revised(head,params,frame)
        assert head.isValid() and len(head.Solids)==1 and head.Solids[0].isClosed()
        verify(head,doc,params,frame)
        doc.HeadLower.Shape = head
        doc.Label = dest.stem
        doc.recompute()
        doc.saveAs(str(dest))
    finally:
        App.closeDocument(doc.Name)
        App.closeDocument(src.Name)
    return App.openDocument(str(dest))


def verify(head,doc,params,frame):
    v,up = App.Vector, App.Vector(0,0,1)
    result = {'lower_bosses_deg_from_deck_normal':[], 'spark_axes_deg_from_deck_normal':[]}
    for i,(x,offset) in enumerate(zip(layout(params,frame)['centers'],(-22,22,-21,22)),1):
        center = v(x+offset,-69,19)
        face, = [s for f in head.Faces if isinstance(s:=f.Surface,Part.Cylinder)
                 and abs(s.Radius-3.1)<1e-6 and (s.Center-center).cross(up).Length<1e-5]
        angle = math.degrees(math.acos(min(1,abs(face.Axis.dot(up)))))
        assert angle<1e-5
        probe = Part.makeCylinder(3.09,8.9,center-up*8.8)
        assert abs(head.common(probe).Volume)<1e-6
        pad = Part.makeCylinder(5.5,.05,center-up*.05).cut(Part.makeCylinder(3.11,.05,center-up*.05))
        assert abs(pad.cut(head).Volume)<1e-6
        result['lower_bosses_deg_from_deck_normal'].append(angle)
        plug=doc.getObject(f'C{i}_SparkShell')
        axis=plug.Placement.Rotation.multVec(up)
        result['spark_axes_deg_from_deck_normal'].append(math.degrees(math.acos(abs(axis.dot(up)))))
        assert abs(head.common(plug.Shape).Volume)<1e-5
    return result
