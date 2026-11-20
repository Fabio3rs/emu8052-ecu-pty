#!/usr/bin/env python3
"""LabControls.RunWot (Y1): key 8 runs the ROM crank dyno from inside the Lab.

A two-point sweep (3000 and 3500 rpm, 10 cycles) runs in child processes; both
points must reach ACCEPTED with a plausible shaft torque and the sweep must
report done. Needs the emu8051-tty binary next to the Lab.

Usage: test_lab_run_wot.py <sevel-ma17-lab> <rom.bin> <screenshot.png>
"""
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    binary, rom, screenshot = sys.argv[1:4]
    screenshot = Path(screenshot)
    screenshot.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as work:
        env = dict(os.environ)
        env.update(XDG_DATA_HOME=work, SDL_AUDIODRIVER="dummy",
                   SEVEL_DYNO_RPMS="3000:3500:500", SEVEL_DYNO_CYCLES="10")
        log = Path(work) / "out.log"
        with open(log, "w") as out:
            process = subprocess.Popen(
                [binary, rom, "--live", "--bench-preset", "--no-audio", "--auto-start"],
                env=env, stdout=out, stderr=subprocess.STDOUT, text=True)
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
            time.sleep(1.0)
            subprocess.run(["xdotool", "key", "--window", window, "8"],
                           check=True, capture_output=True)
            deadline = time.monotonic() + 240.0
            while time.monotonic() < deadline and process.poll() is None:
                if "[LAB-DYNO-SWEEP] done" in log.read_text(errors="replace"):
                    break
                time.sleep(0.5)
            text = log.read_text(errors="replace")
            assert "[LAB-DYNO-SWEEP] done" in text, text[-2000:]
            # Freeze (key 0): the finished curve is kept for comparison.
            subprocess.run(["xdotool", "key", "--window", window, "0"],
                           check=True, capture_output=True)
            time.sleep(0.5)
            assert "[LAB-DYNO] froze RUN WOT curve" in log.read_text(
                errors="replace"), "key 0 did not freeze the curve"
            subprocess.run(["xdotool", "key", "--window", window, "F12"],
                           check=True, capture_output=True)
            time.sleep(1.0)
            # F12 writes into the Lab's working directory (this process's).
            fresh = [p for p in Path.cwd().glob("sevel-ma17-lab-*.png")
                     if time.time() - p.stat().st_mtime < 30]
            if fresh:
                newest = max(fresh, key=lambda p: p.stat().st_mtime)
                screenshot.write_bytes(newest.read_bytes())
                for p in fresh:
                    p.unlink()
            subprocess.run(["xdotool", "key", "--window", window, "Escape"],
                           check=True, capture_output=True)
            process.wait(timeout=20)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        points = re.findall(r"\[LAB-DYNO-SWEEP\] point=(\d+) state=(\w+) reason=(\S+) "
                            r"torque=([\d.]+)", text)
        assert len(points) == 2, points
        for rpm, state, reason, torque in points:
            assert state == "ACCEPTED", (rpm, state, reason)
            assert 100.0 < float(torque) < 135.0, (rpm, torque)
        done = re.search(r"done accepted=(\d+) points=(\d+)", text)
        assert done and done[1] == "2" and done[2] == "2", done
        print("run wot ok:", points)
    return 0


if __name__ == "__main__":
    sys.exit(main())
