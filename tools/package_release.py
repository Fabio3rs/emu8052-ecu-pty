#!/usr/bin/env python3
"""Create ROM-free release archives from an installed runtime or verified CAD registry.

The CAD archive contains sevel-cad/{current.json,LICENSE.txt,provenance.json}
and only the active revision. extract-cad creates DESTINATION/sevel-cad.
Application and assets archives share the application directory at their root.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

from sevel_cad_assets import switch


ROOT = Path(__file__).resolve().parents[1]
HASH = re.compile(r"[0-9a-f]{64}\Z")
BINARIES = {f"bin/{name}" for name in (
    "emu8051-tty", "sevel-ma17-lab", "sevel-cad-check", "sevel-dyno")}
LICENSES = {f"share/licenses/emu8052-ecu-pty/{name}" for name in (
    "LICENSE.txt", "emu8051_LICENSE.txt", "OpenEngineSim_LICENSE.txt",
    "SDL3_LICENSE.txt", "DejaVu_LICENSE.txt", "Silkscreen_LICENSE.txt")}
ASSETS = {f"bin/assets/{name}" for name in (
    "authored_meshes.obj.zlib.b64", "slkscr.ttf.zlib.b64",
    "DejaVuSansMono-Bold.ttf.zlib.b64", "Kottke Silkscreen License.txt",
    "DejaVu_LICENSE.txt", "SDL3_LICENSE.txt", "OpenEngineSim_LICENSE.txt",
    "lab-data/MA17_CALIBRATION_CATALOG.json", "lab-data/dyno_wot_e0.csv",
    "lab-data/dyno/rom/sweep_tdc117.csv", "lab-data/dyno/rom/sweep_tdc120.csv",
    "lab-data/dyno/rom/sweep_tdc123.csv")}
ASSETS |= {f"bin/assets/shaders/{name}.{stage}.{fmt}"
           for name in ("engine_sim", "sevel_cad")
           for stage in ("vertex", "fragment") for fmt in ("spv", "dxil", "msl")}
OPTIONAL = {"bin/libSDL3.so.0", "share/doc/emu8052-ecu-pty/README.md",
            "share/doc/emu8052-ecu-pty/RELEASING.md"}
CAD_METADATA = {"LICENSE.txt", "provenance.json"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError(f"JSON file too large: {path}")
    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return result


def regular_file(root, relative):
    path = root
    for part in PurePosixPath(relative).parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f"Symlink is not a release input: {path}")
    if not path.is_file():
        raise ValueError(f"Missing regular file: {path}")
    return path


def files_under(root):
    files = set()
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError(f"Non-regular release input: {path}")
        if path.is_file():
            files.add(path.relative_to(root).as_posix())
    return files


def cad_files(registry):
    """Check the active content-addressed payload; ignore unrelated revisions."""
    pointer = read_json(regular_file(registry, "current.json"))
    revision = pointer.get("asset_revision", "")
    if (type(pointer.get("schema_version")) is not int or pointer["schema_version"] != 1 or
            not isinstance(revision, str) or not HASH.fullmatch(revision)):
        raise ValueError("Invalid CAD revision pointer")
    manifest_name = f"{revision}/parts_manifest.json"
    manifest_path = regular_file(registry, manifest_name)
    if sha256(manifest_path) != revision:
        raise ValueError("CAD manifest SHA-256 mismatch")
    manifest = read_json(manifest_path)
    runtime = manifest.get("runtime", {})
    if (manifest.get("schema") != "sevel.parts.v1" or not isinstance(runtime, dict) or
            type(runtime.get("schema_version")) is not int or runtime["schema_version"] != 1 or
            not isinstance(runtime.get("rig"), dict) or not runtime["rig"] or
            not isinstance(manifest.get("parts"), list) or not manifest["parts"] or
            not isinstance(manifest.get("meshes"), dict) or not manifest["meshes"]):
        raise ValueError("Expected an animated SEVEL runtime manifest with a rig")
    files = {"current.json", manifest_name}
    for mesh in manifest["meshes"].values():
        if not isinstance(mesh, dict):
            raise ValueError("Invalid CAD mesh record")
        name, digest = mesh.get("file"), mesh.get("sha256")
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.obj", name) or
                not isinstance(digest, str) or not HASH.fullmatch(digest)):
            raise ValueError("Invalid CAD mesh name or SHA-256")
        relative = f"{revision}/{name}"
        if relative in files:
            raise ValueError(f"Duplicate CAD mesh path: {relative}")
        if sha256(regular_file(registry, relative)) != digest:
            raise ValueError(f"CAD mesh SHA-256 mismatch: {name}")
        files.add(relative)
    return revision, files


def write_archive(output, root, files, prefix):
    """Sort names and normalize metadata, preserving only executable permission."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        with temporary.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                for relative in sorted(files):
                    path = regular_file(root, relative)
                    entry = tarfile.TarInfo(f"{prefix}/{relative}")
                    entry.size = path.stat().st_size
                    entry.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                    entry.mtime = entry.uid = entry.gid = 0
                    with path.open("rb") as source:
                        archive.addfile(entry, source)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def package_cad(registry, checker, output):
    registry = registry.resolve(strict=True)
    cad_files(registry)
    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary) / "sevel-cad"
        switch(registry, staged, checker.resolve(strict=True))
        revision, files = cad_files(staged)
        shutil.copyfile(ROOT / "LICENSE", staged / "LICENSE.txt")
        (staged / "provenance.json").write_text(json.dumps({
            "schema_version": 1, "asset_revision": revision, "rom_included": False,
            "project": "Fabio3rs/emu8052-ecu-pty", "license_file": "LICENSE.txt",
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        write_archive(output, staged, files | CAD_METADATA, "sevel-cad")
    return {"archive": str(output), "sha256": sha256(output), "asset_revision": revision}


def extract_cad(archive_path, expected_sha256, destination):
    if not HASH.fullmatch(expected_sha256) or sha256(archive_path) != expected_sha256:
        raise ValueError("CAD archive SHA-256 mismatch")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "sevel-cad"
    if target.exists() or target.is_symlink():
        raise ValueError(f"CAD extraction target already exists: {target}")
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        stage = Path(temporary)
        names, total = set(), 0
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive:
                name = member.name
                path = PurePosixPath(name)
                if (not member.isfile() or path.is_absolute() or ".." in path.parts or
                        "\\" in name or name != path.as_posix() or not path.parts or
                        path.parts[0] != "sevel-cad" or name in names):
                    raise ValueError(f"Unsafe or duplicate CAD archive member: {name}")
                relative = path.relative_to("sevel-cad").as_posix()
                if relative not in {"current.json"} | CAD_METADATA:
                    pieces = PurePosixPath(relative).parts
                    if (len(pieces) != 2 or not HASH.fullmatch(pieces[0]) or
                            (pieces[1] != "parts_manifest.json" and
                             not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.obj", pieces[1]))):
                        raise ValueError(f"Unexpected CAD archive member: {name}")
                names.add(name)
                total += member.size
                if len(names) > 16384 or member.size < 0 or member.size > 1024 ** 3 or total > 4 * 1024 ** 3:
                    raise ValueError("CAD archive exceeds extraction limits")
                output = stage / name
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, output.open("xb") as dest:
                    shutil.copyfileobj(source, dest)
                output.chmod(0o644)
        registry = stage / "sevel-cad"
        revision, expected = cad_files(registry)
        if files_under(registry) != expected | CAD_METADATA:
            raise ValueError("CAD archive must contain exactly one active revision and its notices")
        provenance = read_json(registry / "provenance.json")
        if (provenance.get("schema_version") != 1 or provenance.get("asset_revision") != revision or
                provenance.get("rom_included") is not False or not (registry / "LICENSE.txt").stat().st_size):
            raise ValueError("Invalid CAD provenance or missing license notice")
        registry.rename(target)
    return {"directory": str(target), "asset_revision": revision}


def bundle(prefix, output_dir, version, commit, require_cad=False):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", version):
        raise ValueError("Version must be a filename-safe tag (maximum 80 characters)")
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise ValueError("Commit must be the full Git object ID")
    prefix = prefix.resolve(strict=True)
    output_dir = output_dir.resolve()
    if output_dir == prefix or prefix in output_dir.parents:
        raise ValueError("Output directory must be outside the installed prefix")
    files = files_under(prefix)
    files.discard("bin/assets/sevel-cad/.publish.lock")
    allowed = BINARIES | LICENSES | ASSETS | OPTIONAL
    revision = None
    registry = prefix / "bin/assets/sevel-cad"
    if registry.exists():
        revision, cad = cad_files(registry)
        allowed |= {f"bin/assets/sevel-cad/{name}" for name in cad | CAD_METADATA}
    if require_cad and revision is None:
        raise ValueError("This release requires an installed CAD runtime package")
    unexpected = files - allowed
    missing = (BINARIES | LICENSES | ASSETS) - files
    if unexpected or missing:
        raise ValueError(f"Invalid installed runtime; unexpected={sorted(unexpected)}, missing={sorted(missing)}")
    for name in BINARIES:
        if not (prefix / name).stat().st_mode & 0o111:
            raise ValueError(f"Installed program is not executable: {name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"emu8052-ecu-pty-{version}"
    app_name = f"{stem}-linux-x86_64"
    app = output_dir / f"{app_name}.tar.gz"
    assets = output_dir / f"{stem}-assets.tar.gz"
    write_archive(app, prefix, files, app_name)
    write_archive(assets, prefix, {p for p in files if p.startswith("bin/assets/") or p in LICENSES}, app_name)
    manifest = {
        "schema_version": 1, "version": version, "source_commit": commit,
        "platform": "linux-x86_64", "rom_included": False, "cad_asset_revision": revision,
        "files": {name: {"sha256": sha256(prefix / name), "size": (prefix / name).stat().st_size,
                         "mode": "0755" if (prefix / name).stat().st_mode & 0o111 else "0644"}
                  for name in sorted(files)},
        "artifacts": {p.name: {"sha256": sha256(p), "size": p.stat().st_size} for p in (app, assets)},
    }
    manifest_path = output_dir / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    artifacts = (app, assets, manifest_path)
    (output_dir / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in artifacts), encoding="utf-8")
    return {"directory": str(output_dir), "artifacts": [p.name for p in artifacts] + ["SHA256SUMS"],
            "cad_asset_revision": revision}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cad = commands.add_parser("cad", help="Archive only the checked active CAD revision")
    cad.add_argument("--registry", required=True, type=Path)
    cad.add_argument("--checker", required=True, type=Path)
    cad.add_argument("--output", required=True, type=Path)
    extract = commands.add_parser("extract-cad", help="Verify and unpack a CAD archive into a new directory")
    extract.add_argument("--archive", required=True, type=Path)
    extract.add_argument("--sha256", required=True)
    extract.add_argument("--destination", required=True, type=Path)
    release = commands.add_parser("bundle", help="Archive a cmake --install --component Runtime prefix")
    release.add_argument("--prefix", required=True, type=Path)
    release.add_argument("--output-dir", required=True, type=Path)
    release.add_argument("--version", required=True)
    release.add_argument("--commit", required=True)
    release.add_argument("--require-cad", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "cad":
            result = package_cad(args.registry, args.checker, args.output)
        elif args.command == "extract-cad":
            result = extract_cad(args.archive, args.sha256, args.destination)
        else:
            result = bundle(args.prefix, args.output_dir, args.version, args.commit, args.require_cad)
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"package_release: {error}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
