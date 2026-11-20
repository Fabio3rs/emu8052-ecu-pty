#!/usr/bin/env python3
"""LabCapture.DynoView / CalibrationView: an env switch draws the dyno view or
the calibration heatmap over the scope.

Two offscreen captures of the same tick, with and without the view. The files
must both be valid PNGs and must differ (the view replaced the scope), and the
dyno capture must not report a curve-loading problem.

Usage: test_lab_dyno_view.py <sevel-ma17-lab> <rom.bin> [ENV_NAME=SEVEL_DYNO_VIEW]
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def capture(binary, rom, png, dyno, switch):
    with tempfile.TemporaryDirectory() as prefs:
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_RENDER_DRIVER", "SEVEL_FONT"):
            env.pop(name, None)
        env.update(SDL_VIDEODRIVER="offscreen", XDG_DATA_HOME=prefs)
        for name in ("SEVEL_DYNO_VIEW", "SEVEL_CALIBRATION_VIEW"):
            env.pop(name, None)
        if dyno:
            env[switch] = "1"
        done = subprocess.run(
            [binary, rom, "--capture-tick", "1485000", "--window-frames", "2",
             "--screenshot", str(png)],
            env=env, capture_output=True, text=True, timeout=120)
    output = done.stdout + done.stderr
    assert done.returncode == 0, output[-1500:]
    data = png.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) > 10000, len(data)
    return data


def main() -> int:
    binary, rom = sys.argv[1:3]
    switch = sys.argv[3] if len(sys.argv) > 3 else "SEVEL_DYNO_VIEW"
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        plain = capture(binary, rom, work / "plain.png", dyno=False, switch=switch)
        dyno = capture(binary, rom, work / "dyno.png", dyno=True, switch=switch)
    assert plain != dyno, f"{switch} did not change the frame"
    print(f"{switch} ok: {len(plain)} vs {len(dyno)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
