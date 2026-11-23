"""Classify known casting interfaces geometrically, independent of B-rep face IDs."""
import math


def classify(name, vertices, triangles, params, frame):
    """Unrecognized casting surfaces retain their casting material, never guessed machining."""
    if name not in ('Block','HeadLower','CamCarrier'):
        return ['body_surface']*len(triangles)
    tolerance = 1e-5  # Numerical surface membership, in CAD millimetres.
    block = params['block_visual_estimated']['value']
    planes = []
    if name=='Block':
        planes = [(0,0,1,0),(0,0,1,-block['height'])]
    else:
        carrier = params['valvetrain_layout_estimated']['value']
        section = params['carrier_section_estimated']['value']
        slope = math.tan(math.radians(section['base_slope_y_deg']))
        if name=='CamCarrier':
            top = math.tan(math.radians(section['top_slope_y_deg']))
            planes = [(0,-slope,1,carrier['carrier_base_z_mm']),
                      (0,-top,1,carrier['carrier_cap_top_z_mm'])]
        else:
            head = params['head_lower_casting_estimated']['value']
            planes = [(0,0,1,head['head_gasket_thickness_mm']),
                      (0,1,0,head['manifold_face_y_mm']),
                      (0,-slope,1,carrier['carrier_base_z_mm']-
                       head['carrier_gasket_vertical_thickness_mm'])]
    radius = params['dimensions']['cylinder_bore_diameter_mm']['value']/2
    centers = frame['bore_circle_centers_mm']
    def machined(points):
        if any(all(abs(a*p[0]+b*p[1]+c*p[2]-d)<=tolerance for p in points)
               for a,b,c,d in planes):
            return True
        return name=='Block' and max(p[2] for p in points)-min(p[2] for p in points)>tolerance and any(all(
            -block['bore_depth']-tolerance<=p[2]<=tolerance and
            abs(math.hypot(p[0]-center['x'],p[1])-radius)<=tolerance
            for p in points) for center in centers)
    return ['machined_surface' if machined([vertices[i] for i in tri]) else 'cast_surface'
            for tri in triangles]


def bind(row, batches, manifest):
    base = manifest['material_bindings'][row['id']]
    machined = 'visual_machined_casting_interface'
    manifest['materials'][machined] = {'rgb':[.80,.81,.83],'opacity':1,
        'physical_material_verified':False,'semantic':'machined_surface'}
    row['material_bindings'] = {batch:machined if batch.startswith('machined_surface_') else base
                                for batch in batches}
    row['material_region_policy'] = 'Known analytic interfaces; remaining casting surfaces unclassified as machining'
