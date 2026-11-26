"""Build a zero-phase sump review from a manifest-matched polish snapshot."""
import json
from pathlib import Path

import FreeCAD as App

from config import load
from oil_pan import build
from polish_baseline import digest


def run(snapshot, output):
    snapshot, output = Path(snapshot), Path(output)
    manifest = json.loads((snapshot / "parts_manifest.json").read_text())
    source = snapshot / manifest["source_fcstd"]
    if digest(source) != manifest["source_sha256"]:
        raise ValueError("Baseline checkpoint hash mismatch")
    if output.exists():
        raise FileExistsError(output)
    params, frame = load()
    candidate = App.newDocument(output.stem)
    try:
        candidate.mergeProject(str(source))
        shape = build(params, frame, polish=True)["OilPan"]
        shape.check()
        assert len(shape.Solids) == 1 and shape.Solids[0].isClosed()
        assert candidate.OilPan.PartId == "sevel.oilpan" and candidate.Phase.ThetaDeg == 0
        candidate.OilPan.Shape = shape
        candidate.recompute()
        candidate.saveAs(str(output))
    finally:
        App.closeDocument(candidate.Name)
