"""Four three-material plug previews aligned to the existing chamber bores."""
import math
import FreeCAD as App
import Part
from config import layout

V = App.Vector


def build(params,frame):
    h = params['head_lower_casting_estimated']['value']
    p = params['spark_plug_visual_estimated']['value']
    origin = V(0,h['spark_plug_y_mm'],h['spark_plug_z_mm'])
    target = V(0,-10,h['head_gasket_thickness_mm']+3)
    axis = target-origin
    reach = axis.Length-p['tip_setback_mm']
    axis.normalize()
    assert reach>20 and 0<p['electrode_radius_mm']<p['shell_inner_radius_mm']
    radius,inner = h['spark_plug_radius_mm'],p['shell_inner_radius_mm']
    shell = Part.makeCylinder(radius,reach-12)
    shell = shell.fuse(Part.makeCone(radius,inner+1,6,V(0,0,reach-12)))
    vertices = [V(p['hex_radius_mm']*math.cos(i*math.pi/3),
                  p['hex_radius_mm']*math.sin(i*math.pi/3),-p['hex_height_mm']) for i in range(6)]
    hexagon = Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(V(0,0,p['hex_height_mm']))
    shell = shell.fuse(hexagon).cut(Part.makeCylinder(inner,reach+10,V(0,0,-p['hex_height_mm']-1)))
    # Ground strap rises on the chamber-roof side of the inclined bore.
    strap = Part.makeBox(1.2,1.5,7,V(-0.6,-4.5,reach-7))
    bridge = Part.makeBox(1.2,4.5,0.8,V(-0.6,-4.5,reach-0.8))
    shell = shell.fuse(strap).fuse(bridge).removeSplitter()
    ceramic = Part.makeCylinder(inner,reach-3+p['ceramic_length_mm'],V(0,0,-p['ceramic_length_mm']))
    ceramic = ceramic.fuse(Part.makeCylinder(p['ceramic_outer_radius_mm'],22,V(0,0,-29)))
    ribs = [Part.makeCylinder(p['rib_radius_mm'],1.5,V(0,0,t)) for t in (-27,-23,-19,-15,-11)]
    ceramic = ceramic.multiFuse(ribs)
    ceramic = ceramic.cut(Part.makeCylinder(p['electrode_radius_mm'],reach+40,V(0,0,-35)))
    tip = reach-0.8-p['spark_gap_mm']
    electrode = Part.makeCylinder(p['electrode_radius_mm'],tip+33,V(0,0,-33))
    electrode = electrode.fuse(Part.makeCylinder(p['terminal_radius_mm'],p['terminal_length_mm'],V(0,0,-35)))
    prototypes = {'Shell':shell,'Ceramic':ceramic.removeSplitter(),'Electrode':electrode.removeSplitter()}
    result,interfaces = {},[]
    for i,x in enumerate(layout(params,frame)['centers'],1):
        placement = App.Placement(V(x,origin.y,origin.z),App.Rotation(V(0,0,1),axis))
        for suffix,prototype in prototypes.items():
            assert prototype.isValid() and len(prototype.Solids)==1,(suffix,len(prototype.Solids))
            shape = prototype.copy()
            shape.Placement = placement
            result[f'C{i}_Spark{suffix}'] = shape
        interfaces.extend([(f'C{i}_SparkShell','HeadLower'),
                           (f'C{i}_SparkCeramic',f'C{i}_SparkShell'),
                           (f'C{i}_SparkElectrode',f'C{i}_SparkCeramic')])
    return result,interfaces
