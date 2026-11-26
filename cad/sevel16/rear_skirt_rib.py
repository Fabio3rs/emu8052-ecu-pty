"""Accessory-side skirt relief behind the filter wall (photographs 702072, 946397)."""
import FreeCAD as App
import Part


def build(original, params):
    sections = []
    for x, y, z, depth, height in params["rear_skirt_rib_estimated"]["value"]:
        # The photographed shelf merges upward into the wall. The lower lip
        # retains a shadow line, while the upper flank is broad and shallow.
        top = App.Vector(x, y+depth, z+3*height)
        bottom = App.Vector(x, y+depth, z-height)
        lip = App.Vector(x, y-depth, z)
        upper = Part.BezierCurve()
        upper.setPoles([top,App.Vector(x,y-.6*depth,z+2*height),
                        App.Vector(x,y-depth,z+height),lip])
        lower = Part.BezierCurve()
        lower.setPoles([lip,App.Vector(x,y-depth,z-height),bottom])
        sections.append(Part.Wire([upper.toShape(),lower.toShape(),Part.makeLine(bottom,top)]))
    rib = Part.makeLoft(sections, True, False)
    shape = original.Solids[0].fuse(rib).removeSplitter()
    assert len(shape.Solids) == 1 and shape.isValid() and shape.Volume > original.Volume
    return shape
