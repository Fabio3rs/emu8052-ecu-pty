"""Manifest helper shared by the dyno tools (GOAL_DYNO_ROM rule 6). LLM-written (Claude)."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state():
    def run(*args):
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                              text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"),
            "dirty_files": [l for l in run("status", "--porcelain").splitlines()
                            if not l.startswith("??")]}


def write_manifest(directory, **fields):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"code": git_state(), **fields}
    rom = fields.get("rom")
    if rom:
        manifest["rom_sha256"] = sha256(rom)
    with open(directory / "manifest.json", "w") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest
