"""Cast fields around the three plugs and the descending skirt, traced in XZ."""
import FreeCAD as App
import Part

from inclined_carrier import section_prism

V = App.Vector


def rounded_stock(outline, y, depth, radius):
    corners = [V(x, y, z) for x, z in outline]
    prism = Part.Face(Part.makePolygon(corners + corners[:1])).extrude(V(0, depth, 0))
    uprights = [e for e in prism.Edges if e.BoundBox.YLength > depth - 1e-5]
    return prism.makeFillet(radius, uprights)


def cast_skin(profile):
    wall = rounded_stock(profile["outline_xz"], 55, 31, 3)
    depth = section_prism(-2, 340, profile["outer_yz"])
    # Ease the draft changes along the casting. The inner deck clearance step
    # stays sharp so the seats and blind holes retain their existing envelope.
    flanks = [e for e in depth.Edges if e.BoundBox.XLength > 341.9
              and e.CenterOfMass.y >= 66 and -154 < e.CenterOfMass.z < -39]
    depth = depth.makeFillet(24, flanks)
    wall = wall.common(depth)
    for contour, floor in zip(profile["pockets_xz"], profile["pocket_floor_y"], strict=True):
        tool = rounded_stock(contour, floor, 20, profile["pocket_corner_radius"])
        edges = [e for e in tool.Edges if abs(e.BoundBox.YMax - floor) < 1e-5]
        tool = tool.makeFillet(profile["floor_blend_radius"], edges)
        wall = wall.cut(tool)
    # The oblique foot grows out of the skirt. Its long upper flank returns
    # into the wall, and the lower return casts the shadow seen on 710159.
    start = V(*profile["foot_start_mm"])
    sweep = V(*profile["foot_sweep_mm"])
    upper = start + V(0, -12, 27)
    lower = start + V(0, -12, -9)
    ridge = start + V(0, 1, 2)
    crown = Part.Arc(upper, start + V(0, -3, 13), ridge).toShape()
    lip = Part.Arc(ridge, start + V(0, 0, -5), lower).toShape()
    foot = Part.Face(Part.Wire([crown, lip, Part.makeLine(lower, upper)])).extrude(sweep)
    end = [e for e in foot.Edges if abs(e.BoundBox.XMin - (start.x + sweep.x)) < 1e-5]
    foot = foot.makeFillet(2.5, end)
    return wall.fuse(foot).removeSplitter()
