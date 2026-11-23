"""Check only new casting material, retaining the previous assembly collision proof."""
import math
import json
import FreeCAD as App
import Part
from config import OUTPUT
from check_auxiliary import volume, difference
from check_moving import snapshot, placed
from check_crank import overlap
from kinematics import pose
from timing_sweeps import bounds, build as timing_envelopes
from check_cam_contacts import angles
import auxiliary

V = App.Vector


def prepare(doc,front_baseline,added,params,frame):
    assert doc.Phase.ThetaDeg==front_baseline.Phase.ThetaDeg==0
    timing = timing_envelopes(front_baseline,params,frame)
    front = front_baseline.AuxiliaryFrontShaft.Shape.copy()
    front.Placement = App.Placement()
    shaft,bush,envelope = auxiliary.build(params,front)
    for s in (shaft,bush,envelope):
        s.translate(doc.AuxiliaryFrontShaft.Placement.Base)
    assert difference(shaft,doc.AuxiliaryFrontShaft.Shape)<1e-5
    assert volume(shaft.cut(envelope))<1e-5
    timing['AuxiliaryFrontShaft'] = envelope
    moving = [p for p in snapshot(doc) if p['kind'] in ('crank','rod','piston')]
    fixed,separations = {},{}
    top = bounds(added).ZMax
    for obj in doc.Objects:
        if not hasattr(obj,'Shape') or obj.Name=='Block' or obj.MotionType in ('crank','rod','piston'):
            continue
        kind = obj.MotionType
        if kind in ('cam','valve','spring'):
            b = bounds(obj.Shape)
            if kind=='cam':
                pivot = obj.Placement.Base
                radius = math.hypot(max(abs(b.YMin-pivot.y),abs(b.YMax-pivot.y)),
                                    max(abs(b.ZMin-pivot.z),abs(b.ZMax-pivot.z)))
                low = pivot.z-radius
            else:
                low = b.ZMin-params['valve_timing_nominal']['value']['cam_height_mm']
            assert low>top,obj.Name
            separations[obj.Name] = low-top
        elif kind in ('aux','tensioner'):
            fixed[obj.Name] = timing[obj.Name].copy()
        else:
            assert kind=='fixed',obj.Name
            fixed[obj.Name] = obj.Shape.copy()
    assert len(moving)+len(fixed)+len(separations)==191
    return moving,fixed,separations,envelope


def run(block,added,old_shapes,inputs,params,frame,progress_name):
    moving,fixed,separations,envelope = inputs
    counts = {p['name']:{'bbox_filtered':0,'brep_tested':0} for p in moving}
    counts.update({n:{'bbox_filtered':0,'brep_tested':0} for n in fixed})
    failures = []
    # Conservative B-rep boxes suffice for rejection; avoid recomputing the
    # spline loft's optimal box for every part at every phase.
    target_box = added.BoundBox
    def check(name,shape,theta=None):
        row = counts[name]
        if not overlap(target_box,shape.BoundBox):
            row['bbox_filtered'] += 1
            return
        intersection = volume(added.common(shape))
        row['brep_tested'] += 1
        if intersection>1e-5:
            failures.append({'part':name,'theta_deg':theta,'intersection_mm3':intersection})
    for name,shape in fixed.items():
        check(name,shape)
    samples = angles(params)
    progress = OUTPUT/f'reports/{progress_name}.progress.json'
    for i,theta in enumerate(samples):
        state = pose(theta,params,frame)
        for part in moving:
            check(part['name'],placed(part,state),theta)
        progress.write_text(json.dumps({'completed':i+1,'total':len(samples),'theta_deg':theta,
                                        'failures':len(failures),'recent_failures':failures[-4:]})+'\n')
    assert len(counts)+len(separations)==191
    gap = block.distToShape(envelope)[0]
    assert volume(block.common(envelope))<1e-5
    assert gap>=params['auxiliary_internal_estimated']['value']['running_clearance_mm']-1e-6,gap
    bush_contacts = {}
    for name in ('AuxiliaryFrontBush','AuxiliaryRearBush'):
        shape = old_shapes[name]
        assert volume(block.common(shape))<1e-5
        bush_contacts[name] = block.distToShape(shape)[0]
        assert bush_contacts[name]<1e-7
    c = params['casting_visual_estimated']['value']
    cover = {}
    for x in range(-40,158,5):
        ray = Part.makeLine(V(x,c['aux_y'],c['aux_z']),V(x,c['aux_y']-100,c['aux_z']))
        cover[x] = block.common(ray).Length
        assert cover[x]>2,(x,cover[x])
    return {'status':'FAIL_ENCLOSURE_COLLISION' if failures else 'PASS_AUXILIARY_ENCLOSURE',
            'angles_deg':samples,'pair_coverage':counts,'continuous_upper_separations_mm':separations,
            'failures':failures,'continuous_auxiliary_gap_mm':gap,'bush_contacts_mm':bush_contacts,
            'outward_wall_ray_lengths_mm':cover,
            'scope':'Added casting versus all 191 retained parts; 220 lower poses and continuous auxiliary/upper bounds',
            'limits':['Outer profile estimated; ray samples do not certify all wall thicknesses',
                      'Oil pump and its mating gear are not modelled']}
