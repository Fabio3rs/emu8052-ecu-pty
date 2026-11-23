"""Conservative full-cycle envelopes for proving a fixed carrier revision safe."""
import math
import FreeCAD as App
import Part
from config import layout
from valvetrain_layout import valves


def build(doc, params, frame):
    p = params['valvetrain_layout_estimated']['value']
    n = params['valvetrain_nominal']['value']
    timing = params['valve_timing_nominal']['value']
    l = layout(params,frame)
    v = App.Vector
    envelopes = {}
    # Cylinders are invariant under a complete rotation of the cam about X.
    w = p['cam_journal_width_mm']
    xs = l['supports']
    start,end = xs[0]-w/2,xs[-1]+w/2
    z = p['cam_axis_z_mm']
    cam = [Part.makeCylinder(p['cam_core_radius_mm']+1e-5,end-start,
                            v(start,0,z),v(1,0,0))]
    for i,x in enumerate(xs):
        j = p['cam_diagram_indices_in_positive_x'][i]
        cam.append(Part.makeCylinder(n['cam_journal_diameters_diagram_order_mm'][j]/2+1e-5,
                                    w,v(x-w/2,0,z),v(1,0,0)))
    radius = params['cam_profile_estimated']['value']['base_radius_mm']+timing['cam_height_mm']
    for row in valves(params,frame):
        x = row['axis_origin_mm'][0]
        w = p['cam_lobe_width_mm']
        cam.append(Part.makeCylinder(radius+1e-5,w,v(x-w/2,0,z),v(1,0,0)))
    envelopes['Camshaft'] = cam[0].multiFuse(cam[1:]).removeSplitter()
    assert doc.Camshaft.Shape.cut(envelopes['Camshaft']).Volume<1e-5
    for row in valves(params,frame):
        objects = [o for o in doc.Objects if o.Name.startswith(row['id']+'_')]
        assert len(objects)==12
        low,high,radius = math.inf,-math.inf,0
        for obj in objects:
            shape = obj.Shape.copy()
            shape.Placement = App.Placement()
            b = shape.BoundBox
            radius = max(radius,math.hypot(max(abs(b.XMin),abs(b.XMax)),
                                          max(abs(b.YMin),abs(b.YMax))))
            lift = timing['cam_height_mm']-timing[row['kind']+'_lash_mm']
            low = min(low,b.ZMin-(lift if obj.MotionType=='valve' else 0))
            high = max(high,b.ZMax)
        # Spring helix height changes, but its circular wire radius does not.
        high = max(high,p['retainer_bottom_z_mm'])
        x,y,_ = row['axis_origin_mm']
        envelope = Part.makeCylinder(radius+1e-5,high-low+2e-5,v(x,y,low-1e-5))
        assert all(o.Shape.cut(envelope).Volume<1e-5 for o in objects)
        envelopes[row['id']] = envelope
    return envelopes


def bottom_max_z(obj, params, frame):
    """Global upper Z bound, using the entire possible rotation of local boxes."""
    l = layout(params,frame)
    shape = obj.Shape.copy()
    shape.Placement = App.Placement()
    b = shape.BoundBox
    radial = math.hypot(max(abs(b.YMin),abs(b.YMax)),max(abs(b.ZMin),abs(b.ZMax)))
    if obj.MotionType=='crank':
        return -l['height']+radial
    if obj.MotionType=='rod':
        return -l['height']+l['radius']+radial
    if obj.MotionType=='piston':
        length = params['moving_geometry_estimated']['value']['rod_length_mm']
        return -l['height']+l['radius']+length+b.ZMax
    assert obj.MotionType=='fixed'
    return obj.Shape.BoundBox.ZMax
