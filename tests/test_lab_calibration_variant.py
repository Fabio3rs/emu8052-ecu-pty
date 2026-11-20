#!/usr/bin/env python3
"""LabCapture.CalibrationVariant (K3): the heatmap can compare ROM variants.

Runs the Lab offscreen with the 7CAE table selected and S88 preselected; the
frame must differ from the same table without a variant (the diverging diff
replaces the byte heatmap) and the run must not fail.

Usage: test_lab_calibration_variant.py <sevel-ma17-lab> <rom.bin>
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def capture(binary, rom, variant):
    with tempfile.TemporaryDirectory() as work:
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_RENDER_DRIVER", "SEVEL_FONT",
                     "SEVEL_CALIBRATION_VARIANT"):
            env.pop(name, None)
        env.update(SDL_VIDEODRIVER="offscreen", XDG_DATA_HOME=work,
                   SEVEL_CALIBRATION_VIEW="20")
        if variant:
            env["SEVEL_CALIBRATION_VARIANT"] = variant
        png = Path(work) / "out.png"
        done = subprocess.run(
            [binary, rom, "--capture-tick", "1485000", "--window-frames", "2",
             "--screenshot", str(png)],
            env=env, capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, (done.stdout + done.stderr)[-1500:]
        return png.read_bytes()


def main() -> int:
    binary, rom = sys.argv[1:3]
    plain = capture(binary, rom, None)
    diff = capture(binary, rom, "S88")
    assert plain.startswith(b"\x89PNG") and diff.startswith(b"\x89PNG")
    assert plain != diff, "the variant diff did not change the heatmap"
    # A variant name the catalog does not know keeps the plain heatmap.
    assert capture(binary, rom, "NOPE") == plain
    print("variant diff ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
