"""Separate deck and inclined carrier gaskets from analytic interface outlines."""
import FreeCAD as App
import Part
from config import layout
from head_profiles import clipping_slab
from head_blank import carrier_footprint, oil_tray

V = App.Vector


def build(blank,params,frame):
    h = params['head_lower_casting_estimated']['value']
    block = params['casting_visual_estimated']['value']
    height = h['head_gasket_thickness_mm']
    faces = [f for f in blank.Faces if f.BoundBox.ZLength<1e-7
             and abs(f.BoundBox.ZMin-height)<1e-7]
    face = max(faces,key=lambda f:f.Area)
    deck = Part.Face(face.OuterWire).extrude(V(0,0,-height))
    holes = [Part.makeCylinder(h['head_gasket_opening_radius_mm'],height+2,V(x,0,-1))
             for x in layout(params,frame)['centers']]
    holes += [Part.makeCylinder(block['deck_hole_radius'],height+2,V(x,y,-1))
              for x in layout(params,frame)['supports']
              for y in (-block['deck_hole_y'],block['deck_hole_y'])]
    holes += [Part.makeBox(block['water_slot_length'],block['water_slot_width'],height+2,
                          V(x-block['water_slot_length']/2,side*55-block['water_slot_width']/2,-1))
              for x in layout(params,frame)['centers'] for side in (-1,1)]
    deck = deck.cut(Part.makeCompound(holes)).removeSplitter()
    footprint = carrier_footprint(params,frame,0,110)
    upper = footprint.common(clipping_slab(params,frame,0))
    lower = clipping_slab(params,frame,0,h['carrier_gasket_vertical_thickness_mm'])
    carrier = upper.cut(lower).cut(oil_tray(params,frame,0,110)).removeSplitter()
    for name,shape in [('HeadGasket',deck),('CarrierGasket',carrier)]:
        assert shape.isValid() and len(shape.Solids)==1,name
    return {'HeadGasket':deck,'CarrierGasket':carrier}
