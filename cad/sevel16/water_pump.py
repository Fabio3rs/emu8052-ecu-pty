"""External accessory-driven pump preview on the existing block water pad."""
import math
import FreeCAD as App
import Part
from trigger_layout import axial_layout

V = App.Vector


def build(params,frame):
    p = params['water_pump_visual_estimated']['value']
    lo = frame['bore_circle_centers_mm'][0]['x']-params['block_visual_estimated']['value']['end_margin']
    x = lo+12
    y = 83
    def pad(at_y):
        points = [V(x,at_y,-20),V(x+47,at_y,-20),V(x+43,at_y,-108),V(x,at_y,-108)]
        return Part.Wire(Part.makePolygon(points+[points[0]]).Edges)
    def mouth(at_y):
        points = [V(x+9,at_y,-32),V(x+36,at_y,-32),V(x+36,at_y,-96),V(x+9,at_y,-96)]
        return Part.Wire(Part.makePolygon(points+[points[0]]).Edges)
    front,back = p['body_front_x_mm'],p['body_back_x_mm']
    cy,cz = p['axis_y_mm'],p['axis_z_mm']
    seat = y+p['gasket_mm']
    body = Part.makeCylinder(p['body_radius_mm'],back-front,V(front,cy,cz),V(1,0,0))
    # A closed cover around the rectangular port joins the axial pump chamber.
    # Keep the mounting face planar instead of lofting it onto a circular edge.
    connector = Part.Face(pad(seat)).extrude(V(0,p['cover_depth_mm'],0))
    body = body.fuse(connector)
    body = body.common(Part.makeBox(160,160,160,V(front-50,seat,cz-80)))
    assert body.isValid() and len(body.Solids)==1
    cavity = Part.makeCylinder(p['body_radius_mm']-8,back-front-4,V(front+2,cy,cz),V(1,0,0))
    inlet = Part.Face(mouth(seat-1)).extrude(V(0,p['inlet_depth_mm']+1,0))
    cavity = cavity.fuse(inlet)
    assert cavity.isValid() and len(cavity.Solids)==1
    body = body.cut(cavity).removeSplitter()
    assert body.isValid() and len(body.Solids)==1 and body.Volume>0
    ax = axial_layout(params)
    center_x = ax['pulley_front']+params['accessory_visual_estimated']['value']['pulley_width_mm']/2
    pulley_front = center_x-p['pulley_width_mm']/2
    neck_front = pulley_front+p['pulley_width_mm']+3
    neck = Part.makeCone(14,20,front-neck_front,V(neck_front,cy,cz),V(1,0,0))
    neck = neck.cut(Part.makeCylinder(p['shaft_radius_mm'],front-neck_front+1,V(neck_front-1,cy,cz),V(1,0,0)))
    body = body.fuse(neck)
    gasket = Part.Face(pad(y)).extrude(V(0,p['gasket_mm'],0))
    gasket = gasket.cut(Part.Face(mouth(y-1)).extrude(V(0,p['gasket_mm']+2,0)))
    bolts = [Part.makeCylinder(3,p['gasket_mm']+p['flange_mm']+2,V(xx,y-1,zz),V(0,1,0))
             for xx in (x+5,x+40) for zz in (-26,-101)]
    body = body.cut(Part.makeCompound(bolts)).removeSplitter()
    gasket = gasket.cut(Part.makeCompound(bolts)).removeSplitter()
    shaft = Part.makeCylinder(p['shaft_radius_mm'],front-pulley_front,V(pulley_front,cy,cz),V(1,0,0))
    radius,width = p['pulley_radius_mm'],p['pulley_width_mm']
    pulley = Part.makeCylinder(radius,width,V(pulley_front,0,0),V(1,0,0))
    half = p['pulley_groove_width_mm']/2
    points = [V(center_x-half,radius,0),V(center_x,radius-p['pulley_groove_depth_mm'],0),
              V(center_x+half,radius,0),V(center_x+half,radius+2,0),V(center_x-half,radius+2,0)]
    groove = Part.Face(Part.makePolygon(points+[points[0]])).revolve(V(),V(1,0,0),360)
    holes = [Part.makeCylinder(p['shaft_radius_mm'],width+2,V(pulley_front-1,0,0),V(1,0,0))]
    for i in range(4):
        a = i*math.pi/2
        holes.append(Part.makeCylinder(7,width+2,V(pulley_front-1,25*math.cos(a),25*math.sin(a)),V(1,0,0)))
    pulley = pulley.cut(groove).cut(Part.makeCompound(holes)).removeSplitter()
    pulley.translate(V(0,cy,cz))
    result = {'WaterPumpBody':body,'WaterPumpGasket':gasket,'WaterPumpShaft':shaft,'WaterPumpPulley':pulley}
    for name,shape in result.items():
        assert shape.isValid() and len(shape.Solids)==1 and shape.Volume>0,name
    assert body.distToShape(gasket)[0]<1e-6
    contacts = [('WaterPumpBody','WaterPumpGasket'),('WaterPumpGasket','Block'),
                ('WaterPumpBody','WaterPumpShaft'),('WaterPumpPulley','WaterPumpShaft')]
    return result,contacts
