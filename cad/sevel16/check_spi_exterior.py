"""Verify the reopened SPI exterior against its v012 assembly and exchange solids."""
from collections import Counter
import json
from pathlib import Path

import FreeCAD as App
import Part

from assembly import apply_pose
from build_head_main_row import verify as verify_bolts
from build_head_intake_wall import separated
from build_spi_exterior import SOURCE, DEST
from config import OUTPUT, layout, load
from geometry_identity import difference
from polish_baseline import digest

CHANGED = ("Block", "HeadLower", "ValveCover", "OilPan", "PCVBreatherOutlet")


def bop_counts(shape):
    try:
        shape.check(True)
    except ValueError as error:
        return dict(Counter(line.strip() for line in str(error).splitlines() if "BOPAlgo" in line))
    return {}


def run(folder, source=SOURCE, candidate=DEST, *, changed=CHANGED, additions=()):
    folder = Path(folder)
    folder.mkdir(exist_ok=False, parents=True)
    params, frame = load()
    a = App.openDocument(str(source))
    b = App.openDocument(str(candidate))
    try:
        previous = {o.Name: o for o in a.Objects if hasattr(o, "Shape")}
        revised = {o.Name: o for o in b.Objects if hasattr(o, "Shape")}
        assert set(revised) == set(previous) | set(additions)
        assert set(additions).isdisjoint(previous)
        assert len({o.PartId for o in revised.values()}) == len(revised)
        report = {"source": digest(source), "candidate": digest(candidate),
                  "datum": digest(OUTPUT/"datums/reference_frame.json"), "parts": len(revised),
                  "changed": {}, "added_parts": {}, "poses": {}, "unchanged_breps": 0}
        for name, obj in revised.items():
            assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1 and obj.Shape.Solids[0].isClosed()
            if name in additions:
                assert obj.MotionType == "fixed"
                obj.Shape.check(True)
                path = folder/(name+"-after.step")
                obj.Shape.exportStep(str(path))
                restored = Part.read(str(path))
                restored.check(True)
                assert restored.isValid() and len(restored.Solids) == 1 and restored.Solids[0].isClosed()
                if abs(restored.Volume - obj.Shape.Volume) >= 1e-5:
                    from precise_volume import volumes
                    original, exchanged = volumes(obj.Shape, restored)
                    assert abs(original - exchanged) / original < 1e-6, name
                report["added_parts"][name] = {"part_id": obj.PartId, "volume_mm3": restored.Volume}
                continue
            old = previous[name]
            assert (old.PartId, old.MotionType, old.Placement) == (obj.PartId, obj.MotionType, obj.Placement)
            if name not in changed:
                assert difference(old.Shape, obj.Shape) < 1e-5, name
                report["unchanged_breps"] += 1
                continue
            versions = {}
            for label, item in (("before", old), ("after", obj)):
                shape = item.Shape
                path = folder/(name+"-"+label+".step")
                shape.exportStep(str(path))
                restored = Part.read(str(path))
                assert restored.isValid() and len(restored.Solids) == 1 and restored.Solids[0].isClosed()
                versions[label] = {"bop": bop_counts(shape), "step_bop": bop_counts(restored),
                                   "volume_mm3": shape.Volume, "faces": len(shape.Faces),
                                   "bounds_mm": str(shape.BoundBox)}
            report["changed"][name] = versions
            (folder/"components.json").write_text(json.dumps(report["changed"],indent=2)+"\n")
        verify_bolts(b, params, frame)
        face_y = params["head_lower_casting_estimated"]["value"]["manifold_face_y_mm"]
        # The intake valves are offset from the cylinder axes.
        from valvetrain_layout import valves
        for row in valves(params,frame):
            if row["kind"] == "intake":
                assert separated(b.HeadLower.Shape,row["axis_origin_mm"][0],face_y)
        for angle in (0,90,180,270,359,360,540,720):
            for doc in (a,b):
                apply_pose(doc,angle,params,frame,update_springs=False)
            assert all(previous[n].Placement.toMatrix().A == revised[n].Placement.toMatrix().A for n in previous)
            report["poses"][angle] = len(previous)
        report["bore_mm"] = frame["cylinder_bore_diameter_mm"]
        report["crank_radius_mm"] = layout(params,frame)["radius"]
        (folder/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
        return report
    finally:
        App.closeDocument(b.Name)
        App.closeDocument(a.Name)
