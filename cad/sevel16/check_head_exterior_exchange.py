"""Check carrier motion envelopes and a STEP round-trip of each revised solid."""
import json
import tempfile
from pathlib import Path

import Part
from carrier_interface_envelopes import build as envelopes
from check_head_exterior_review import CHANGED
from config import load


def run(old,doc,folder):
    params, frame = load()
    cage = doc.CamCarrier.Shape
    swept = envelopes(doc,params,frame,cage.optimalBoundingBox(False).ZMin)
    overlaps = {key:abs(cage.common(shape).Volume) for key,shape in swept.items()
                if cage.BoundBox.intersect(shape.BoundBox)}
    result = {'carrier_envelope_tests':len(overlaps),
              'carrier_overlap_mm3':{k:v for k,v in overlaps.items() if v>1e-5},
              'step':{}}
    names = CHANGED | {o.Name for o in doc.Objects if hasattr(o,'Shape') and old.getObject(o.Name) is None}
    with tempfile.TemporaryDirectory() as scratch:
        for name in sorted(names):
            shape = doc.getObject(name).Shape
            path = str(Path(scratch)/(name+'.step'))
            shape.exportStep(path)
            imported = Part.read(path)
            result['step'][name] = {
                'solid_count':len(imported.Solids),'valid':imported.isValid(),
                'closed':all(s.isClosed() for s in imported.Solids),
                'volume_error_fraction':abs(imported.Volume-shape.Volume)/shape.Volume}
    (folder/'exchange-motion.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
