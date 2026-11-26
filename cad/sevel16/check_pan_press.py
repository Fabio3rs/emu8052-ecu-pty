"""Check a saved sump revision against its zero-phase FreeCAD baseline."""
import json
from pathlib import Path

import FreeCAD as App

from assembly import apply_pose
from config import load


def compare(source, candidate, report):
    params, frame = load()
    docs = []
    try:
        for path in (source, candidate):
            docs.append(App.openDocument(str(path)))
        old, new = docs
        def parts(doc):
            return {obj.PartId: obj for obj in doc.Objects if hasattr(obj, "Shape")}
        original, revised = map(parts, docs)
        assert revised.keys() == original.keys()
        pan = new.OilPan.Shape
        pan.check()
        assert pan.isValid() and pan.Solids[0].isClosed() and len(pan.Solids) == 1
        bop = {}
        for label, doc in zip(("baseline", "candidate"), docs):
            try:
                doc.OilPan.Shape.check(True)
                bop[label] = "pass"
            except ValueError as error:
                bop[label] = str(error)
        phase_rows = []
        for angle in sorted(set(range(0, 721, 15)) | {359}):
            for doc in docs:
                apply_pose(doc, angle, params, frame, update_springs=False)
            pairs = 0
            for key, obj in revised.items():
                previous = original[key]
                assert obj.MotionType == previous.MotionType
                assert obj.Placement.toMatrix().A == previous.Placement.toMatrix().A
                if obj.Name == "OilPan" or not pan.BoundBox.intersect(obj.Shape.BoundBox):
                    continue
                overlap = pan.common(obj.Shape).Volume
                assert abs(overlap) < 1e-5, (angle, key, overlap)
                pairs += 1
            phase_rows.append(dict(angle=angle, adjacent_pairs=pairs))
        result = dict(parts=len(revised), phases=phase_rows, bop=bop,
                      volume_mm3=pan.Volume, baseline_volume_mm3=old.OilPan.Shape.Volume,
                      area_mm2=pan.Area, bounds_mm=str(pan.BoundBox))
        Path(report).write_text(json.dumps(result, indent=2) + "\n")
    finally:
        for doc in reversed(docs):
            App.closeDocument(doc.Name)
