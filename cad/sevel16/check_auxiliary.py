"""Incremental proof of the complete auxiliary shaft, rear bush and casting edits."""
import hashlib
import json
from pathlib import Path
import FreeCAD as App
import Part
from config import OUTPUT, load
from timing_sweeps import bounds, overlaps
import auxiliary


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def volume(shape):
    return 0.0 if shape.isNull() else abs(shape.Volume)


def difference(a,b):
    return volume(a.cut(b))+volume(b.cut(a))


def prepare(doc, baseline):
    params,frame = load()
    previous = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:params[k] for k in previous}==previous
    evidence = OUTPUT/f'reports/{baseline.Name}_trigger_validation.json'
    proof = json.loads(evidence.read_text())
    assert proof['status']=='PASS_TRIGGER_INCREMENT' and proof['source_sha256']==sha(baseline.FileName)
    assert doc.Phase.ThetaDeg==baseline.Phase.ThetaDeg==0
    unchanged = {}
    for old in baseline.Objects:
        if not hasattr(old,'Shape') or old.Name in ('Block','AuxiliaryFrontShaft'):
            continue
        obj = doc.getObject(old.Name)
        assert obj.PartId==old.PartId and obj.MotionType==old.MotionType
        for prop in ('CylinderId','ValveKind','SpringKind','RestBase'):
            assert getattr(obj,prop,None)==getattr(old,prop,None)
        delta = difference(obj.Shape,old.Shape)
        assert delta<1e-5,(old.Name,delta)
        unchanged[old.Name] = delta
    assert len(unchanged)==186
    front = baseline.AuxiliaryFrontShaft.Shape.copy()
    front.Placement = App.Placement()
    shaft,bush,envelope = auxiliary.build(params,front)
    pivot = doc.AuxiliaryFrontShaft.Placement.Base
    for s in (shaft,bush,envelope):
        s.translate(pivot)
    assert difference(shaft,doc.AuxiliaryFrontShaft.Shape)<1e-5
    assert difference(bush,doc.AuxiliaryRearBush.Shape)<1e-5
    assert volume(shaft.cut(envelope))<1e-5
    rotated = envelope.copy()
    rotated.rotate(pivot,App.Vector(1,0,0),37)
    assert difference(rotated,envelope)<1e-5
    housing,cutter = auxiliary.casting_tools(params)
    added,removed = doc.Block.Shape.cut(baseline.Block.Shape),baseline.Block.Shape.cut(doc.Block.Shape)
    assert volume(added.cut(housing))<1e-5
    assert volume(removed.cut(cutter))<1e-5
    assert difference(doc.Block.Shape,baseline.Block.Shape.fuse(housing).cut(cutter))<1e-5
    # Neither edit reaches the bore surfaces: this is a stronger spatial bound
    # than checking that four nominal cylinders still fit inside the cavities.
    bore_y = -params['dimensions']['cylinder_bore_diameter_mm']['value']/2
    assert max(bounds(added).YMax,bounds(removed).YMax)<bore_y
    gaps = {}
    for name in ('Block','AuxiliaryFrontBush','AuxiliaryRearBush'):
        shape = doc.getObject(name).Shape
        assert volume(envelope.common(shape))<1e-5,name
        gaps[name] = envelope.distToShape(shape)[0]
        assert gaps[name]>0,name
    n = params['auxiliary_nominal']['value']
    for i,name in enumerate(('AuxiliaryFrontBush','AuxiliaryRearBush')):
        expected = (n['bush_inner_diameters_mm'][i]-n['journal_diameters_mm'][i])/2
        assert abs(gaps[name]-expected)<1e-7
    assert bush.distToShape(doc.Block.Shape)[0]<1e-7
    assert volume(bush.common(doc.Block.Shape))<1e-5
    report = {'status':'AUXILIARY_STATIC_PASS_CYCLE_PENDING','source_sha256':sha(doc.FileName),
              'baseline_proof_sha256':sha(evidence),'parameter_sha256':sha(OUTPUT/'parameters.json'),
              'unchanged_parts_symmetric_difference_mm3':unchanged,
              'block_added_volume_mm3':volume(added),'block_removed_volume_mm3':volume(removed),
              'bore_edit_y_clearance_mm':bore_y-max(bounds(added).YMax,bounds(removed).YMax),
              'rear_bush_block_overlap_mm3':volume(bush.common(doc.Block.Shape)),
              'continuous_auxiliary_gaps_mm':gaps,
              'limits':['Axial dimensions, eccentric and gear are provisional',
                        'No mating oil pump or gear engagement validation',
                        'Prior assembly proof retained; this check covers the auxiliary increment']}
    (OUTPUT/f'reports/{doc.Name}_auxiliary_static.json').write_text(json.dumps(report,indent=2)+'\n')
    return report,{'AuxiliaryEnvelope':envelope,'AuxiliaryRearBush':bush,'BlockAdded':added}
