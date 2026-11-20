#!/usr/bin/env python3
"""LabControls.RunSnapshots (K4): keys 1 and 2 save snapshots A and B.

Starts the Lab live, presses 1, changes the load, presses 2, and checks the
saved JSON (schema, ROM SHA-256 against an independent hash, tables) and the
comparison lines.

Usage: test_lab_snapshots.py <sevel-ma17-lab> <rom.bin>
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    binary, rom = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as work:
        env = dict(os.environ)
        env.update(XDG_DATA_HOME=work, SDL_AUDIODRIVER="dummy",
                   SEVEL_SNAPSHOT_DIR=str(Path(work) / "snaps"))
        process = subprocess.Popen(
            [binary, rom, "--live", "--bench-preset", "--no-audio", "--auto-start"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            window = ""
            deadline = time.monotonic() + 6.0
            while time.monotonic() < deadline and process.poll() is None:
                found = subprocess.run(["xdotool", "search", "--name", "FIAT TIPO"],
                                       text=True, capture_output=True)
                if found.returncode == 0 and found.stdout.strip():
                    window = found.stdout.splitlines()[-1]
                    break
                time.sleep(0.05)
            assert window, "Lab window did not appear"

            def key(name):
                subprocess.run(["xdotool", "key", "--window", window, name],
                               check=True, capture_output=True)
                time.sleep(0.4)

            time.sleep(1.5)       # let the engine run
            key("1")              # snapshot A
            key("l")              # change the scenario (load)
            time.sleep(0.8)
            key("2")              # snapshot B
            key("3")              # reopen the saved A (K4)
            key("4")              # reopen the saved B
            key("Escape")
            output, _ = process.communicate(timeout=15)
        finally:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=5)
        loaded = re.findall(r"\[LAB-SNAPSHOT\] loaded=(\S+) label=(\w) rom=(\w+)", output)
        assert [label for _, label, _ in loaded] == ["A", "B"], (
            loaded, [l for l in output.splitlines() if "SNAPSHOT" in l or "DBG" in l])
        saved = re.findall(r"\[LAB-SNAPSHOT\] saved=(\S+) label=(\w) rom=(\w+)", output)
        assert len(saved) == 2, output[-2000:]
        expected_sha = hashlib.sha256(Path(rom).read_bytes()).hexdigest()
        for path, label, sha in saved:
            assert sha == expected_sha, (label, sha, expected_sha)
            data = json.loads(Path(path).read_text())
            assert data["schema"] == "sevel-run-snapshot-v1"
            assert data["label"] == label
            assert data["rom_sha256"] == expected_sha
            assert len(data["tables"]) == 34, len(data["tables"])
            assert data["code_sha"], data
        deltas = re.findall(r"\[LAB-SNAPSHOT-DELTA\] (.+)", output)
        assert "SCENARIO DIFFERS" in deltas, deltas
        assert "ROM DIFFERS" not in deltas and "CODE DIFFERS" not in deltas, deltas
        print("snapshots ok:", deltas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
