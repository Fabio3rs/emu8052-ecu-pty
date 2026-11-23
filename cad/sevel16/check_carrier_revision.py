"""Prove a carrier-only change using the baseline cycle and continuous envelopes."""
import hashlib
import json
from pathlib import Path
import Part
from config import OUTPUT, load
from carrier_swept_envelopes import build, bottom_max_z


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(doc, baseline):
    params,frame = load()
    previous = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:v for k,v in params.items() if k!='cam_carrier_outline_estimated'}==previous
    report_path = OUTPUT/f'reports/{baseline.Name}_valvetrain_cycle.json'
    cycle = json.loads(report_path.read_text())
    assert cycle['status']=='PASS_A3_COLLISIONS' and not cycle['collisions']
    assert cycle['source_sha256']==sha(baseline.FileName)
    assert cycle['completed_angles']==cycle['target_angles'] and len(cycle['target_angles'])==220
    assert doc.Phase.ThetaDeg==baseline.Phase.ThetaDeg==0
    unchanged = {}
    for obj in doc.Objects:
        if not hasattr(obj,'Shape') or obj.Name=='CamCarrier':
            continue
        old = baseline.getObject(obj.Name)
        assert old and obj.PartId==old.PartId and obj.MotionType==old.MotionType
        assert obj.CylinderId==old.CylinderId
        a,b = obj.Shape,old.Shape
        delta = abs(a.cut(b).Volume)+abs(b.cut(a).Volume)
        assert delta<1e-5,(obj.Name,delta)
        unchanged[obj.Name] = delta
    assert len(unchanged)==165 and len(doc.CamCarrier.Shape.Solids)==1
    old_parts = [o.Shape for o in baseline.Objects
                 if o.Name=='CamCarrier' or o.Name.startswith('CamCap')]
    assert len(old_parts)==6
    old_cage = Part.makeCompound(old_parts)
    new_cage = doc.CamCarrier.Shape
    added = new_cage.cut(old_cage).removeSplitter()
    removed = old_cage.cut(new_cage).removeSplitter()
    assert added.isValid() and added.Volume>0 and removed.Volume>0
    envelopes = build(doc,params,frame)
    intersections = {}
    for name,envelope in envelopes.items():
        volume = abs(added.common(envelope).Volume)
        assert volume<1e-5,(name,volume)
        intersections[name] = volume
    bottom_bounds = {}
    for obj in doc.Objects:
        if (not hasattr(obj,'Shape') or obj.Name in ('CamCarrier','Camshaft')
                or hasattr(obj,'ValveKind')):
            continue
        bound = bottom_max_z(obj,params,frame)
        assert bound<added.BoundBox.ZMin,(obj.Name,bound,added.BoundBox.ZMin)
        bottom_bounds[obj.Name] = bound
    assert len(bottom_bounds)==68
    report = {'status':'PASS_CARRIER_CHANGE_CONTINUOUS_ENVELOPES',
              'source_sha256':sha(doc.FileName),'baseline_sha256':sha(baseline.FileName),
              'baseline_cycle_report_sha256':sha(report_path),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'unchanged_parts_symmetric_difference_mm3':unchanged,
              'added_volume_mm3':added.Volume,'removed_volume_mm3':removed.Volume,
              'added_against_full_cycle_envelopes_mm3':intersections,
              'bottom_full_cycle_upper_z_mm':bottom_bounds,
              'added_min_z_mm':added.BoundBox.ZMin,
              'scope':'Only fixed carrier changed: baseline collisions retained; additions clear full-cycle bounds.',
              'limits':'Proves interference exclusion for this geometry, not casting fidelity or target dimensions.'}
    (OUTPUT/f'reports/{doc.Name}_carrier_change.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,dict)}))
    return report
