"""Incremental closure proof: all retained parts and all new pairings."""
import itertools
import json
import math
import FreeCAD as App
import Part
from config import OUTPUT
from check_moving import snapshot, placed
from check_crank import overlap
from check_auxiliary import volume
from carrier_interface_envelopes import build as upper_envelopes
from check_cam_contacts import angles
from kinematics import pose


def run(doc,shapes,params,frame,progress_name):
    assert doc.Phase.ThetaDeg==0
    parts = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(parts)==192 and not set(shapes)&{o.Name for o in parts}
    upper = upper_envelopes(doc,params,frame,-500)
    fixed = {}
    moving = [p for p in snapshot(doc) if p['kind'] in ('crank','rod','piston')]
    for obj in parts:
        kind = obj.MotionType
        if kind in ('crank','rod','piston'):
            continue
        if kind=='fixed':
            fixed[obj.Name] = obj.Shape.copy()
        elif kind=='spring':
            # The thin nominal cylinder can miss the spline sweep by its
            # approximation tolerance. Use a deliberately wider continuous
            # bound; closures are remote from this valve-train region.
            v = params['valvetrain_layout_estimated']['value']
            wire = v[obj.SpringKind+'_spring_wire_radius_mm']
            radius = v[obj.SpringKind+'_spring_mean_radius_mm']+2*wire
            low = v[obj.SpringKind+'_spring_seat_z_mm']-2*wire
            high = v['retainer_bottom_z_mm']+2*wire
            fixed[obj.Name] = Part.makeCylinder(radius,high-low,
                App.Vector(obj.RestBase.x,obj.RestBase.y,low))
        elif kind in ('cam','valve'):
            fixed[obj.Name] = upper[obj.Name]
        else:
            assert kind in ('aux','tensioner')
            b,pivot = obj.Shape.BoundBox,obj.Placement.Base
            radius = math.hypot(max(abs(b.YMin-pivot.y),abs(b.YMax-pivot.y)),
                                max(abs(b.ZMin-pivot.z),abs(b.ZMax-pivot.z)))
            fixed[obj.Name] = Part.makeCylinder(radius+1e-6,b.XLength+2e-6,
                App.Vector(b.XMin-1e-6,pivot.y,pivot.z),App.Vector(1,0,0))
        assert volume(obj.Shape.cut(fixed[obj.Name]))<1e-5,obj.Name
    counts,failures = {},[]
    def check(a,b,sa,sb,theta=None):
        key = a+' / '+b
        count = counts.setdefault(key,{'bbox_filtered':0,'brep_tested':0})
        if not overlap(sa.BoundBox,sb.BoundBox):
            count['bbox_filtered'] += 1
            return
        common = volume(sa.common(sb))
        count['brep_tested'] += 1
        if common>1e-5:
            failures.append({'pair':[a,b],'theta_deg':theta,'volume_mm3':common})
    for a,sa in shapes.items():
        for b,sb in fixed.items():
            check(a,b,sa,sb)
    for a,b in itertools.combinations(shapes,2):
        check(a,b,shapes[a],shapes[b])
    samples = angles(params)
    for index,theta in enumerate(samples):
        state = pose(theta,params,frame)
        for part in moving:
            sb = placed(part,state)
            for a,sa in shapes.items():
                check(a,part['name'],sa,sb,theta)
        (OUTPUT/f'reports/{progress_name}.progress.json').write_text(json.dumps({
            'completed':index+1,'total':len(samples),'failures':len(failures)})+'\n')
    assert len(counts)==len(shapes)*len(parts)+len(shapes)*(len(shapes)-1)//2
    contacts = [('ValveCoverGasket','CamCarrier'),('ValveCover','ValveCoverGasket'),
                ('OilFillerCap','ValveCover'),('OilPanGasket','Block'),
                ('OilPan','OilPanGasket'),('OilDrainPlug','OilPan')]
    all_shapes = {**{o.Name:o.Shape for o in parts},**shapes}
    interfaces = {}
    for a,b in contacts:
        gap = all_shapes[a].distToShape(all_shapes[b])[0]
        interfaces[a+' / '+b] = gap
        if gap>1e-6:
            failures.append({'pair':[a,b],'interface_gap_mm':gap})
    return {'status':'FAIL_CLOSURES_INCREMENT' if failures else 'PASS_CLOSURES_INCREMENT',
            'angles_deg':samples,'pair_coverage':counts,'failures':failures,
            'contacts_mm':interfaces,'added_parts':list(shapes),'baseline_parts':len(parts),
            'continuous_envelope_parts':list(fixed),
            'scope':'New closures versus all retained parts, 220 lower poses and conservative upper/auxiliary envelopes',
            'limits':['Provisional wall thickness and outer dimensions; no oil capacity claim',
                      'Prior component collisions remain covered by the frozen baseline proof']}
