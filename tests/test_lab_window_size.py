#!/usr/bin/env python3
"""LabCapture.WindowSizeEnv: SEVEL_WINDOW_SIZE sets the initial window size, so
an offscreen capture (which cannot be resized afterwards) can be 1920x1080.

Usage: test_lab_window_size.py <sevel-ma17-lab> <rom.bin>
"""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def capture(binary, rom, size):
    with tempfile.TemporaryDirectory() as work:
        png = Path(work) / "out.png"
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_RENDER_DRIVER", "SEVEL_FONT"):
            env.pop(name, None)
        env.update(SDL_VIDEODRIVER="offscreen", XDG_DATA_HOME=work)
        if size is None:
            env.pop("SEVEL_WINDOW_SIZE", None)
        else:
            env["SEVEL_WINDOW_SIZE"] = size
        done = subprocess.run(
            [binary, rom, "--capture-tick", "1485000", "--window-frames", "2",
             "--screenshot", str(png)],
            env=env, capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, (done.stdout + done.stderr)[-1500:]
        data = png.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), "not a PNG"
    return struct.unpack(">II", data[16:24])


def main() -> int:
    binary, rom = sys.argv[1:3]
    assert capture(binary, rom, None) == (1280, 720)
    assert capture(binary, rom, "1920x1080") == (1920, 1080)
    assert capture(binary, rom, "bogus") == (1280, 720)      # invalid: default
    assert capture(binary, rom, "100x100") == (1280, 720)    # below the minimum
    print("window size ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
