"""Rebuild the SPI breather with the straight can and rib visible on part 4217279."""
import FreeCAD as App
import Part

from block_pcv_review import SEAT_TILT_DEG, inclined
from config import layout

V = App.Vector


def fitting(params, frame):
    block = params["casting_visual_estimated"]["value"]
    profile = params["breather_profile_estimated"]["value"]
    dims = params["breather_cast_shoulders_estimated"]["value"]
    centers = layout(params, frame)["centers"]
    x = centers[0] + (centers[-1] - centers[0]) * block["access_open_x_fraction"]
    seat = V(x, -96, block["access_open_z"] + 20)
    axis = inclined(SEAT_TILT_DEG)
    outward = V(0, -axis.z, axis.y)
    hose = inclined(profile["outlet_tilt"])

    can = Part.makeCylinder(profile["dome"][0][1], dims["can_height"], seat, axis)
    rim = max((edge for edge in can.Edges if edge.isClosed()),
              key=lambda edge: (edge.CenterOfMass - seat).dot(axis))
    can = can.makeFillet(dims["rim_radius"], [rim])
    bottom = seat - axis * dims["spigot_length"]
    spigot = Part.makeCylinder(profile["spigot_radius"], dims["spigot_length"] + 2, bottom, axis)

    # Offsets in the seat plane: the outlet and the drilled pad sit side by side.
    pad = seat + axis * 16 - outward * 1.6 + V(4.2, 0, 0)
    boss = Part.makeCone(dims["pad_base_radius"], dims["pad_top_radius"],
                         dims["pad_height"], pad, axis)
    root = seat + axis * 12 + outward * 13 - V(8, 0, 0)
    outlet = Part.makeCylinder(8.5, 34, root, hose)
    lip = Part.makeCylinder(9.1, 2.4, root + hose * 31.6, hose)
    points = [seat + outward * y + axis * z + V(4.2, 0, 0)
              for y, z in dims["web_profile_yz"]]
    web = Part.Face(Part.makePolygon(points + points[:1])).extrude(V(dims["web_width"], 0, 0))
    # Trim the narrow reinforcing web against the already united pad and can.
    # Including it in the multi-fuse changes the exchanged shoulder trim.
    shell = can.fuse([boss, spigot, outlet, lip]).fuse(web)

    bore = Part.makeCylinder(profile["spigot_bore"], dims["spigot_length"] + 19,
                             bottom - axis, axis)
    hose_bore = Part.makeCylinder(6.1, 42, root - hose * 6, hose)
    pad_bore = Part.makeCylinder(dims["pad_bore_radius"], 27, pad - axis * 3, axis)
    for passage in (hose_bore, pad_bore):
        assert bore.common(passage).Volume > 1, "Passage disconnected from lower bore"
    result = shell.cut([bore, hose_bore, pad_bore]).removeSplitter()
    assert result.isValid() and len(result.Solids) == 1 and result.Solids[0].isClosed()
    result.check(True)
    return result
