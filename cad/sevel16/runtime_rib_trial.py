"""Reversible visual-only rib variation for the Lab replacement acceptance test."""
import FreeCAD as App
import Part
from config import OUTPUT, load


def run():
    source = OUTPUT/'models/SEVEL_Accessories_A5_v005_ManifoldReview.FCStd'
    name = 'SEVEL_Accessories_A5_v005_RuntimeRibTrial'
    output = OUTPUT/'trials'/(name+'.FCStd')
    if output.exists():
        raise FileExistsError(output)
    params,frame = load()
    p = params['casting_visual_estimated']['value']
    centers = frame['bore_circle_centers_mm']
    x = (centers[1]['x'] + centers[2]['x'])/2
    v = App.Vector
    # Extend the lower end of the middle plug-side rib, below the plug seat.
    points = [(x-9,-108),(x+7,-108),(x+14,p['rib_base_z']+14),(x-14,p['rib_base_z']+14)]
    outline = [v(xx,60,zz) for xx,zz in points]
    extension = Part.Face(Part.makePolygon(outline+outline[:1])).extrude(v(0,18,0))
    extension = extension.makeFillet(p['edge_blend_radius'],extension.Edges)
    doc = App.newDocument(name)
    try:
        doc.mergeProject(str(source))
        before = doc.Block.Shape
        revised = before.Solids[0].fuse(extension.Solids[0]).removeSplitter()
        assert revised.isValid() and len(revised.Solids)==1 and revised.Volume > before.Volume
        for obj in doc.Objects:
            if hasattr(obj,'Shape') and obj != doc.Block and extension.BoundBox.intersect(obj.Shape.BoundBox):
                assert extension.common(obj.Shape).Volume < 1e-5, obj.Name
        doc.Block.Shape = revised
        doc.recompute()
        doc.saveAs(str(output))
    finally:
        App.closeDocument(doc.Name)
    return output
