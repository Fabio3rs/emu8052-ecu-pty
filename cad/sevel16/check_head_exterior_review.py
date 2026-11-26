"""Probe the reopened model at its saved phase and record the measured results."""
import itertools
import json
import math

import FreeCAD as App
import Part
from config import layout, load
from head_water_end import AXIS, LEFT, RIGHT, datum
from valvetrain_layout import valves

V = App.Vector
CHANGED = {'HeadLower','CamCarrier','ValveCover','OilFillerCap'}


def run(old, doc, folder):
    params, frame = load()
    h, project = datum(params,frame)
    head = doc.HeadLower.Shape
    original = {o.Name:o for o in old.Objects if hasattr(o,'Shape')}
    objects = {o.Name:o for o in doc.Objects if hasattr(o,'Shape')}
    new = set(objects)-set(original)
    assert len(new)==7 and set(original)<=set(objects)
    assert old.Phase.ThetaDeg==doc.Phase.ThetaDeg==0
    issues = []
    report = {'objects':len(objects),'phase_deg':doc.Phase.ThetaDeg,'new':sorted(new)}
    for name,obj in objects.items():
        s = obj.Shape
        if not s.isValid() or len(s.Solids)!=1 or not s.Solids[0].isClosed():
            issues.append(('solid',name))
        if name not in new:
            src = original[name]
            if (src.PartId,src.MotionType,src.CylinderId)!=(obj.PartId,obj.MotionType,obj.CylinderId):
                issues.append(('identity',name))
            if name not in CHANGED and (abs(src.Shape.Volume-s.Volume)>1e-5 or
                    src.Placement!=obj.Placement or len(src.Shape.Faces)!=len(s.Faces)):
                issues.append(('legacy shape',name))
    probes = {}
    for i in range(1,5):
        pad = Part.makeCylinder(10,.05).cut(Part.makeCylinder(7.05,.05))
        pad.Placement = objects[f'C{i}_SparkShell'].Placement
        probes[f'washer_{i}_missing'] = abs(pad.cut(head).Volume)
    carrier = params['valvetrain_layout_estimated']['value']
    rim = params['cam_carrier_outline_estimated']['value']
    angle = params['carrier_section_estimated']['value']['top_slope_y_deg']
    stations = layout(params,frame)['supports']
    lo = stations[0]-carrier['cam_journal_width_mm']/2
    hi = stations[-1]+carrier['cam_journal_width_mm']/2
    top = App.Placement(V(0,0,carrier['carrier_cap_top_z_mm']),App.Rotation(AXIS,angle))
    for f in rim['cover_boss_fractions']:
        for side in (-1,1):
            y = side*carrier['carrier_half_width_mm']/math.cos(math.radians(angle))
            bolt = Part.makeCylinder(rim['cover_hole_radius_mm']-.02,62,V(lo+f*(hi-lo),y,-10))
            bolt.Placement = top.multiply(bolt.Placement)
            probes[f'cover_fixing_{f}_{side}'] = abs(doc.ValveCover.Shape.common(bolt).Volume)
            # The carrier's shorter holes follow its own original casting.
            before = old.CamCarrier.Shape.common(bolt)
            after = doc.CamCarrier.Shape.common(bolt)
            probes[f'carrier_fixing_change_{f}_{side}'] = abs(after.cut(before).Volume)
    rows = [(r['axis_origin_mm'][0],h[r['kind']+'_port_z_mm'],h[r['kind']+'_port_radius_mm'])
            for r in valves(params,frame)]
    rows += [(x,h['coolant_port_z_mm'],h['coolant_port_radius_mm'])
             for x in layout(params,frame)['supports'][1::2]]
    for i,(x,z,r) in enumerate(rows):
        # Probe the center and compare the entire lip to its v007 counterpart.
        # The lofted gas passages curve as they approach the machining plane.
        start = V(x,h['manifold_face_y_mm']+1,z)
        probe = Part.makeCylinder(r*.6,2,start,V(0,-1,0))
        probes[f'manifold_{i+1}_center_obstruction'] = abs(head.common(probe).Volume)
        region = Part.makeCylinder(r+2,2,start,V(0,-1,0))
        before = original['HeadLower'].Shape.common(region)
        after = head.common(region)
        probes[f'manifold_{i+1}_lip_change'] = abs(after.cut(before).Volume)+abs(before.cut(after).Volume)
    centers = [project(px) for px in (LEFT,RIGHT)]
    for i,center in enumerate(centers,1):
        bolt = Part.makeCylinder(h['water_end_bolt_radius_mm']-.1,
                                 h['water_end_flange_depth_mm']+11,center-AXIS*2,AXIS)
        for name in ('HeadLower','ThermostatGasket','ThermostatHousing'):
            probes[f'water_axis_{i}_{name}'] = abs(objects[name].Shape.common(bolt).Volume)
    delta = centers[1]-centers[0]
    report.update(water_pitch_mm=delta.Length,water_projected_slope_deg=math.degrees(
                  math.atan2(-delta.z,delta.y)),probe_volumes_mm3=probes)
    issues.extend((k,v) for k,v in probes.items() if v>1e-5)
    gaps = {}
    for a,b in [('Block','OilFilterCartridge'),('OilFilterSpigot','OilFilterCartridge'),
                ('CamCarrier','IgnitionCoilMount'),('IgnitionCoilMount','IgnitionCoil'),
                ('HeadLower','ThermostatGasket'),('ThermostatGasket','ThermostatHousing'),
                ('ValveCover','OilFillerCap'),('OilFillerCap','IgnitionCoilMount'),
                ('OilFillerCap','IgnitionCoil')]:
        gaps[a+' / '+b] = objects[a].Shape.distToShape(objects[b].Shape)[0]
    report['gaps_mm'] = gaps
    touched = CHANGED | new
    shapes = {k:v.Shape for k,v in objects.items()}
    boxes = {k:v.optimalBoundingBox(False) for k,v in shapes.items()}
    pairs = 0
    for a,b in itertools.combinations(objects,2):
        if not ({a,b} & touched) or not boxes[a].intersect(boxes[b]):
            continue
        pairs += 1
        vol = abs(shapes[a].common(shapes[b]).Volume)
        if vol>1e-5:
            prior = (abs(original[a].Shape.common(original[b].Shape).Volume)
                     if a in original and b in original else 0)
            if vol>prior+1e-5:
                issues.append(('interference mm3',a,b,vol,prior))
    report.update(bbox_candidate_pairs=pairs,issues=issues)
    (folder/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
