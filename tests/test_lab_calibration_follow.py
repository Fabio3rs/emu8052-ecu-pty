#!/usr/bin/env python3
"""LabCapture.CalibrationFollow (K2): the MOVC tracer marks catalog tables.

Runs the Lab offscreen at the warm-idle tick with the calibration view in
follow mode and checks the [LAB-CALIBRATION] line: the firmware did table reads
and at least one catalog table has an active cell.

Usage: test_lab_calibration_follow.py <sevel-ma17-lab> <rom.bin>
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    binary, rom = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as work:
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_RENDER_DRIVER", "SEVEL_FONT"):
            env.pop(name, None)
        env.update(SDL_VIDEODRIVER="offscreen", XDG_DATA_HOME=work,
                   SEVEL_CALIBRATION_VIEW="follow")
        png = Path(work) / "out.png"
        done = subprocess.run(
            [binary, rom, "--live", "--bench-preset", "--no-audio", "--auto-start",
             "--window-frames", "240000", "--capture-tick", "800000",
             "--stop-ticks", "800000", "--screenshot", str(png)],
            env=env, capture_output=True, text=True, timeout=180)
        output = done.stdout + done.stderr
        assert done.returncode == 0, output[-1500:]
    found = re.search(r"\[LAB-CALIBRATION\] table=(\S+) active_cells=(\d+) "
                      r"reads=(\d+) recent=(\d+) follow=1", output)
    assert found, output[-1500:]
    table, active, reads, recent = found[1], *map(int, found.groups()[1:])
    assert reads > 1000, ("firmware did no table reads", reads)
    assert recent > 0, recent
    assert active >= 1, ("no catalog table is active", table, active)
    print(f"K2 ok: {table} active_cells={active} reads={reads}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
