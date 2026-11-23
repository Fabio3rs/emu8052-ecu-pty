"""Single solid SOHC shaft, eight contact-envelope lobes, five unequal journals."""
import FreeCAD as App
import Part
from config import layout
from cam_profile import profile_polygon
from valvetrain_layout import valves


def build(params, frame):
    p = params['valvetrain_layout_estimated']['value']
    n = params['valvetrain_nominal']['value']
    supports = layout(params,frame)['supports']
    width = p['cam_journal_width_mm']
    start,end = supports[0]-width/2,supports[-1]+width/2
    v = App.Vector
    shaft = Part.makeCylinder(p['cam_core_radius_mm'],end-start,v(start,0,0),v(1,0,0))
    additions, lobes = [], {}
    for i,x in enumerate(supports):
        j = p['cam_diagram_indices_in_positive_x'][i]
        radius = n['cam_journal_diameters_diagram_order_mm'][j]/2
        additions.append(Part.makeCylinder(radius,width,v(x-width/2,0,0),v(1,0,0)))
    polygon = profile_polygon(params)
    for row in valves(params,frame):
        x = row['axis_origin_mm'][0]
        width = p['cam_lobe_width_mm']
        points = [v(x-width/2,y,z) for y,z in polygon]
        lobe = Part.Face(Part.makePolygon(points+[points[0]])).extrude(v(width,0,0))
        lobe.rotate(v(),v(1,0,0),row['lobe_local_rx_deg'])
        additions.append(lobe)
        lobes[row['id']] = Part.makeCompound([lobe])
    shaft = shaft.multiFuse(additions).removeSplitter()
    assert shaft.isValid() and len(shaft.Solids)==1
    return shaft,lobes
