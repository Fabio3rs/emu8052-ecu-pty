"""Release boundary tests. Set SEVEL_CAD_CHECK to use the compiled CAD validator."""
from contextlib import nullcontext
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import package_release as packaging
from cad_fixture import moving_cube


class ReleasePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.registry = self.root / "registry"
        incoming = self.registry / "incoming"
        moving_cube(incoming)
        self.revision = packaging.sha256(incoming / "parts_manifest.json")
        incoming.rename(self.registry / self.revision)
        (self.registry / "current.json").write_text(json.dumps({
            "schema_version": 1, "asset_revision": self.revision}))
        self.checker = Path(os.environ.get("SEVEL_CAD_CHECK", sys.executable))

    def make_cad_archive(self, name="cad.tar.gz"):
        # The C++ format/geometry checker has its own tests. Without a compiled
        # binary, mock only its subprocess boundary; the staging and hashes run.
        check = nullcontext() if "SEVEL_CAD_CHECK" in os.environ else mock.patch("sevel_cad_assets.subprocess.run")
        with check:
            output = self.root / name
            packaging.package_cad(self.registry, self.checker, output)
        return output

    def make_prefix(self):
        prefix = self.root / "installed"
        for name in packaging.BINARIES | packaging.LICENSES | packaging.ASSETS:
            path = prefix / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture payload\n")
            path.chmod(0o755 if name in packaging.BINARIES else 0o644)
        return prefix

    def custom_archive(self, members):
        output = self.root / "malformed.tar.gz"
        with tarfile.open(output, "w:gz") as archive:
            for name, payload, kind in members:
                info = tarfile.TarInfo(name)
                info.type = kind
                if kind == tarfile.REGTYPE:
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
                else:
                    info.linkname = payload.decode()
                    archive.addfile(info)
        return output

    def test_cad_roundtrip_only_active_revision_and_deterministic_bytes(self):
        (self.registry / "firmware.bin").write_bytes(b"must not ship")
        (self.registry / ("b" * 64)).mkdir()
        (self.registry / ("b" * 64) / "firmware.bin").write_bytes(b"must not ship")
        (self.registry / self.revision / "unlisted.obj").write_text("unused mesh")
        archive = self.make_cad_archive()
        second = self.make_cad_archive("second.tar.gz")
        self.assertEqual(archive.read_bytes(), second.read_bytes())
        with tarfile.open(archive) as tar:
            names = tar.getnames()
            self.assertNotIn("sevel-cad/.publish.lock", names)
            self.assertFalse(any("firmware" in name or "unlisted" in name for name in names))
            self.assertTrue(all(m.uid == m.gid == m.mtime == 0 for m in tar))
        result = packaging.extract_cad(archive, packaging.sha256(archive), self.root / "unpacked")
        restored = Path(result["directory"])
        self.assertEqual(packaging.cad_files(restored)[0], self.revision)
        self.assertEqual((restored / self.revision / "parts_manifest.json").read_bytes(),
                         (self.registry / self.revision / "parts_manifest.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "already exists"):
            packaging.extract_cad(archive, packaging.sha256(archive), self.root / "unpacked")

    def test_archive_digest_is_checked_before_extraction(self):
        archive = self.make_cad_archive()
        destination = self.root / "unpacked"
        with self.assertRaisesRegex(ValueError, "archive SHA-256"):
            packaging.extract_cad(archive, "0" * 64, destination)
        self.assertFalse(destination.exists())

    def test_tampered_mesh_and_manifest_are_rejected(self):
        mesh = next((self.registry / self.revision).glob("*.obj"))
        mesh.write_text("tampered")
        with self.assertRaisesRegex(ValueError, "mesh SHA-256"):
            self.make_cad_archive()
        manifest = self.registry / self.revision / "parts_manifest.json"
        manifest.write_text("{}")
        with self.assertRaisesRegex(ValueError, "manifest SHA-256"):
            self.make_cad_archive()

    def test_extraction_rechecks_payload_hash_after_archive_checksum(self):
        archive = self.make_cad_archive()
        members = []
        with tarfile.open(archive) as tar:
            for member in tar:
                data = tar.extractfile(member).read()
                members.append((member.name, b"corrupt mesh" if member.name.endswith(".obj") else data, tarfile.REGTYPE))
        corrupt = self.custom_archive(members)
        with self.assertRaisesRegex(ValueError, "mesh SHA-256"):
            packaging.extract_cad(corrupt, packaging.sha256(corrupt), self.root / "unpacked")
        self.assertFalse((self.root / "unpacked/sevel-cad").exists())

    def test_unsafe_archive_members_are_rejected(self):
        cases = [
            [("../escaped", b"bad", tarfile.REGTYPE)],
            [("/tmp/escaped", b"bad", tarfile.REGTYPE)],
            [("sevel-cad/../escaped", b"bad", tarfile.REGTYPE)],
            [("sevel-cad\\current.json", b"bad", tarfile.REGTYPE)],
            [("sevel-cad/current.json", b"{}", tarfile.REGTYPE)] * 2,
            [("sevel-cad/current.json", b"../../escaped", tarfile.SYMTYPE)],
            [("sevel-cad/current.json", b"../../escaped", tarfile.LNKTYPE)],
            [("sevel-cad/rom.bin", b"bad", tarfile.REGTYPE)],
        ]
        for index, members in enumerate(cases):
            with self.subTest(index=index):
                archive = self.custom_archive(members)
                destination = self.root / f"unpacked-{index}"
                with self.assertRaises(ValueError):
                    packaging.extract_cad(archive, packaging.sha256(archive), destination)
                self.assertFalse((destination / "sevel-cad").exists())
        self.assertFalse((self.root / "escaped").exists())

    def test_source_symlink_and_checker_failure_are_rejected(self):
        with mock.patch("sevel_cad_assets.subprocess.run", side_effect=subprocess.CalledProcessError(1, "checker")):
            with self.assertRaises(subprocess.CalledProcessError):
                packaging.package_cad(self.registry, self.checker, self.root / "rejected.tar.gz")
        self.assertFalse((self.root / "rejected.tar.gz").exists())
        mesh = next((self.registry / self.revision).glob("*.obj"))
        saved = self.root / "outside.obj"
        mesh.rename(saved)
        mesh.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.make_cad_archive()

    def test_legacy_cad_without_animation_rig_is_rejected(self):
        folder = self.registry / self.revision
        manifest = json.loads((folder / "parts_manifest.json").read_text())
        del manifest["runtime"]
        (folder / "parts_manifest.json").write_text(json.dumps(manifest))
        revision = packaging.sha256(folder / "parts_manifest.json")
        folder.rename(self.registry / revision)
        (self.registry / "current.json").write_text(json.dumps({"schema_version": 1, "asset_revision": revision}))
        with self.assertRaisesRegex(ValueError, "animated"):
            self.make_cad_archive()

    def test_bundle_preserves_executables_and_emits_checksums(self):
        prefix = self.make_prefix()
        output = self.root / "dist"
        packaging.bundle(prefix, output, "v1.2.3", "c" * 40)
        app = output / "emu8052-ecu-pty-v1.2.3-linux-x86_64.tar.gz"
        with tarfile.open(app) as archive:
            entry = archive.getmember("emu8052-ecu-pty-v1.2.3-linux-x86_64/bin/sevel-ma17-lab")
            self.assertEqual(entry.mode, 0o755)
        assets = output / "emu8052-ecu-pty-v1.2.3-assets.tar.gz"
        with tarfile.open(assets) as archive:
            self.assertTrue(all("/bin/assets/" in name or "/share/licenses/" in name for name in archive.getnames()))
        manifest = json.loads((output / "release-manifest.json").read_text())
        self.assertFalse(manifest["rom_included"])
        self.assertIsNone(manifest["cad_asset_revision"])
        self.assertEqual(manifest["files"]["bin/sevel-ma17-lab"]["mode"], "0755")
        for line in (output / "SHA256SUMS").read_text().splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(packaging.sha256(output / name), digest)

    def test_bundle_rejects_rom_extra_files_symlinks_and_missing_cad(self):
        prefix = self.make_prefix()
        for name in ("firmware.bin", "bin/rom.hex", "bin/assets/renamed-firmware.txt",
                     "share/licenses/emu8052-ecu-pty/extra.txt", "bin/assets/model.FCStd"):
            with self.subTest(name=name):
                path = prefix / name
                path.write_text("must not ship")
                with self.assertRaisesRegex(ValueError, "unexpected"):
                    packaging.bundle(prefix, self.root / "dist", "v1", "d" * 40)
                path.unlink()
        with self.assertRaisesRegex(ValueError, "requires an installed CAD"):
            packaging.bundle(prefix, self.root / "dist", "v1", "d" * 40, require_cad=True)
        (prefix / "link").symlink_to(self.registry, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Non-regular"):
            packaging.bundle(prefix, self.root / "dist", "v1", "d" * 40)

    def test_bundle_records_installed_cad_revision(self):
        prefix = self.make_prefix()
        archive = self.make_cad_archive()
        packaging.extract_cad(archive, packaging.sha256(archive), prefix / "bin/assets")
        (prefix / "bin/assets/sevel-cad/.publish.lock").touch()
        result = packaging.bundle(prefix, self.root / "dist", "v1", "e" * 40, require_cad=True)
        self.assertEqual(result["cad_asset_revision"], self.revision)
        manifest = json.loads((self.root / "dist/release-manifest.json").read_text())
        self.assertNotIn("bin/assets/sevel-cad/.publish.lock", manifest["files"])


if __name__ == "__main__":
    unittest.main()
