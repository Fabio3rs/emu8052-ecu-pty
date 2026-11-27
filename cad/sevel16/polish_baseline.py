"""Snapshot the active Lab revision before an exterior review."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot(destination, registry=None):
    root = Path(__file__).resolve().parents[2]
    cad = root / "build/sevel-cad"
    registry = (registry or cad / "runtime-assets").resolve()
    revision = json.loads((registry / "current.json").read_text())["asset_revision"]
    manifest = registry / revision / "parts_manifest.json"
    data = json.loads(manifest.read_text())
    model = cad / "models" / data["source_fcstd"]
    working_hash = digest(model)
    if working_hash != data["source_sha256"]:
        model = model.with_suffix(".FCStd1")
    if digest(manifest) != revision or digest(model) != data["source_sha256"]:
        raise ValueError("Runtime revision and CAD checkpoint must match")
    for mesh in data["meshes"].values():
        if digest(manifest.parent / mesh["file"]) != mesh["sha256"]:
            raise ValueError(mesh["file"])
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for source in (manifest, model, cad / "parameters.json",
                   cad / "datums/reference_frame.json", cad / "datums/reference_gate.json"):
        name = data["source_fcstd"] if source == model else source.name
        shutil.copyfile(source, destination / name)
        hashes[str(source.relative_to(root))] = digest(source)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
    report = dict(commit=git("rev-parse", "HEAD"), branch=git("branch", "--show-current"),
                  status=git("status", "--short").splitlines(), revision=revision,
                  parts=len(data["parts"]), meshes=len(data["meshes"]), hashes=hashes,
                  working_fcstd_sha256=working_hash, acceptance="docs/SEVEL_LAB_3D_ACCEPTANCE.md")
    (destination / "baseline.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    snapshot(*(Path(arg) for arg in sys.argv[1:]))
