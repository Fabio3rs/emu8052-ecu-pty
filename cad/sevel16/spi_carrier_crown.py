"""Open-window reliefs on the carrier, registered in the cover gasket plane."""
import math

import FreeCAD as App
import Part

from cam_carrier import rounded_prism
from config import layout

V = App.Vector


def window(lo,hi,half,z,radius):
    solid = rounded_prism(lo,-half,z,hi-lo,2*half,1,radius)
    face, = [f for f in solid.Faces if f.BoundBox.ZLength<1e-6 and abs(f.BoundBox.ZMin-z)<1e-6]
    return face.OuterWire


def crown_tools(params,frame):
    spec = params["spi_carrier_crown_estimated"]["value"]
    v = params["valvetrain_layout_estimated"]["value"]
    c = params["cam_carrier_outline_estimated"]["value"]
    angle = params["carrier_section_estimated"]["value"]["top_slope_y_deg"]
    place = App.Placement(V(0,0,v["carrier_cap_top_z_mm"]),App.Rotation(V(1,0,0),angle))
    stations = layout(params,frame)["supports"]
    half = (v["carrier_half_width_mm"]-c["side_rail_width_mm"])/math.cos(math.radians(angle))
    w = v["cam_journal_width_mm"]
    tools = []
    for x in stations[1:-1]:
        for y in (-spec["cup_offset_y"],spec["cup_offset_y"]):
            tools.append(Part.makeCone(spec["cup_floor_radius"],spec["cup_radius"],spec["cup_depth"],
                         V(x,y,-spec["cup_depth"])).fuse(Part.makeCylinder(spec["cup_radius"],1,V(x,y,0))))
    # Widen the middle bridge openings only at their tops. The right end of
    # the last window flares above the end journal. The rail width is retained.
    for i in (1,2,3):
        a,b = stations[i]+w/2,stations[i+1]-w/2
        target_a = stations[i]+spec["central_bridge_width"]/2 if i==2 else a
        target_b = stations[i+1]-spec["central_bridge_width"]/2 if i==1 else b
        if i==3:
            target_b = spec["window_top_end_x"]
        # Start inside the existing opening. Coincident side walls would cut
        # the support of the long gasket rails on the inclined casting.
        sections = [window(a+.5,b-.5,half-2,-spec["flare_depth"],c["window_corner_radius_mm"]),
                    window(target_a,target_b,half-.6,0,spec["end_corner_radius"] if i==3 else 6),
                    window(target_a,target_b,half-.6,1,spec["end_corner_radius"] if i==3 else 6)]
        # The original window sides are vertical in engine coordinates, while
        # the gasket plane is inclined. Follow those sides through the depth
        # to avoid adding a longitudinal step along the far rail.
        for wire in sections:
            wire.translate(V(0,wire.BoundBox.Center.z*math.tan(math.radians(angle)),0))
        tools.append(Part.makeLoft(sections,True,True))
    for tool in tools:
        tool.Placement = place.multiply(tool.Placement)
    n = params["valvetrain_nominal"]["value"]
    journal_guards = []
    for i,x in enumerate(stations):
        j = v["cam_diagram_indices_in_positive_x"][i]
        radius = n["cam_housing_diameters_diagram_order_mm"][j]/2+spec["journal_wall_allowance"]
        journal_guards.append(Part.makeCylinder(radius,w+.2,V(x-w/2-.1,0,v["cam_axis_z_mm"]),V(1,0,0)))
    return Part.makeCompound(tools).cut(journal_guards)


def revise(carrier,params,frame):
    revised = carrier.Solids[0].cut(crown_tools(params,frame)).removeSplitter()
    assert revised.isValid() and len(revised.Solids)==1 and revised.Solids[0].isClosed()
    assert .98*carrier.Volume<revised.Volume<carrier.Volume
    return revised
