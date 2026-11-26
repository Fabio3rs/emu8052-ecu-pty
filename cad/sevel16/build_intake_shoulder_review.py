"""Regenerate the reviewed inlet from the archived v005 reference package."""
import json
from pathlib import Path

import FreeCAD as App

from build_manifold_review import verify
from config import load
from manifold_intake_casting import intake
from polish_baseline import digest


def run(snapshot, destination):
    snapshot, destination = Path(snapshot), Path(destination)
    manifest = json.loads((snapshot / "parts_manifest.json").read_text())
    source = snapshot / manifest["source_fcstd"]
    if digest(source) != manifest["source_sha256"]:
        raise ValueError("Unexpected input checkpoint")
    if destination.exists():
        raise FileExistsError(destination)
    params, frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        doc.IntakeManifold.Shape = intake(params, frame, polish=True)[0]
        doc.recompute()
        verify(doc, params, frame)
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
