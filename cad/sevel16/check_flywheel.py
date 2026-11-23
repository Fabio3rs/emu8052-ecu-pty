"""Validate the incremental flywheel assembly, retaining the A3 evidence chain."""
import hashlib
import itertools
import json
from pathlib import Path
import FreeCAD as App
from config import OUTPUT, load
from assembly import apply_pose
from flywheel import mount_x


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(doc, baseline):
    params,frame = load()
    p = params['flywheel_visual_estimated']['value']
    previous = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:params[k] for k in previous}==previous
    evidence = OUTPUT/f'reports/{baseline.Name}_carrier_change.json'
    proof = json.loads(evidence.read_text())
    assert proof['status']=='PASS_CARRIER_CHANGE_CONTINUOUS_ENVELOPES'
    assert proof['source_sha256']==sha(baseline.FileName)
    assert doc.Phase.ThetaDeg==baseline.Phase.ThetaDeg==0
    unchanged = {}
    for old in baseline.Objects:
        if not hasattr(old,'Shape'):
            continue
        obj = doc.getObject(old.Name)
        assert obj and obj.PartId==old.PartId and obj.MotionType==old.MotionType
        assert obj.CylinderId==old.CylinderId
        for prop in ('ValveKind','SpringKind','RestBase'):
            assert getattr(obj,prop,None)==getattr(old,prop,None)
        delta = abs(obj.Shape.cut(old.Shape).Volume)+abs(old.Shape.cut(obj.Shape).Volume)
        assert delta<1e-5,(old.Name,delta)
        unchanged[old.Name] = delta
    assert len(unchanged)==166
    added = [o for o in doc.Objects if hasattr(o,'Shape') and o.Name not in unchanged]
    assert len(added)==8 and all(o.MotionType=='crank' for o in added)
    x = mount_x(params,frame)
    # Display triangulation can under-bound a circle: use exact CAD geometry.
    box = doc.Flywheel.Shape.optimalBoundingBox(False)
    assert abs(box.XMin-x)<1e-7 and abs(box.XLength-p['thickness_mm'])<1e-7
    assert abs(box.YLength-2*p['body_radius_mm'])<1e-7
    assert abs(doc.StarterRing.Shape.optimalBoundingBox(False).XLength-p['ring_width_mm'])<1e-7
    pairs = {}
    for a,b in itertools.combinations([doc.Crankshaft,*added],2):
        overlap = abs(a.Shape.common(b.Shape).Volume)
        assert overlap<1e-5,(a.Name,b.Name,overlap)
        pairs[a.Name+'/'+b.Name] = overlap
    contacts = [('Crankshaft','Flywheel'),('Flywheel','StarterRing')]
    contacts += [('Flywheel',f'FlywheelBolt{i}') for i in range(1,7)]
    gaps = {a+'/'+b:doc.getObject(a).Shape.distToShape(doc.getObject(b).Shape)[0]
            for a,b in contacts}
    assert max(gaps.values())<1e-7
    # All existing rigid motions preserve X; spring deformation changes height,
    # with exact circular-wire radial bounds instead of a pose-only mesh bound.
    bounds = {}
    for old in baseline.Objects:
        if not hasattr(old,'Shape') or old.Name=='Crankshaft':
            continue
        bound = old.Shape.optimalBoundingBox(False).XMax
        if old.MotionType=='spring':
            s = params['valvetrain_layout_estimated']['value']
            bound = old.RestBase.x+s[old.SpringKind+'_spring_mean_radius_mm']+s[old.SpringKind+'_spring_wire_radius_mm']
        bounds[old.Name] = bound
    gap = min(o.Shape.optimalBoundingBox(False).XMin for o in added)-max(bounds.values())
    assert gap>0, gap
    original = {o.Name:o.Shape.Vertexes[0].Point for o in added}
    pivot = doc.Crankshaft.Placement.Base
    worst = 0
    try:
        for angle in range(0,721,5):
            apply_pose(doc,angle,params,frame,update_springs=False)
            rotation = App.Rotation(App.Vector(1,0,0),angle%360)
            for obj in added:
                expected = pivot+rotation.multVec(original[obj.Name]-pivot)
                error = (obj.Shape.Vertexes[0].Point-expected).Length
                worst = max(worst,error)
                assert error<1e-7
                assert (obj.Placement.Base-doc.Crankshaft.Placement.Base).Length<1e-9
                assert obj.Placement.Rotation.isSame(doc.Crankshaft.Placement.Rotation,1e-9)
    finally:
        apply_pose(doc,0,params,frame,update_springs=False)
    report = {'status':'PASS_FLYWHEEL_INCREMENT_CONTINUOUS_CLEARANCE',
              'source_sha256':sha(doc.FileName),'baseline_sha256':sha(baseline.FileName),
              'baseline_proof_sha256':sha(evidence),'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'unchanged_parts_symmetric_difference_mm3':unchanged,
              'rigid_group_pair_intersections_mm3':pairs,'expected_contact_gaps_mm':gaps,
              'minimum_full_cycle_axial_separation_mm':gap,
              'old_component_full_cycle_xmax_mm':bounds,'pose_samples':145,
              'max_pose_vertex_error_mm':worst,'mount_face_x_mm':x,
              'bounding_policy':'optimalBoundingBox(useTriangulation=False)',
              'scope':'New crank-fixed group: invariant B-rep pairs and full-cycle axial separation; unchanged A3 proof retained.',
              'limits':['Preview dimensions and tooth count are assumptions',
                        'No claim about absent distribution, trigger wheel or starter engagement',
                        'Samples update rigid placements; spring deformation covered by prior A3 validation and axial bounds']}
    (OUTPUT/f'reports/{doc.Name}_flywheel_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,dict)}))
    return report
