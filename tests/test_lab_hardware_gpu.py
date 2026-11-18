#!/usr/bin/env python3
"""LabCapture.HardwareGpu: the Lab must rasterize on a real GPU when one is
reachable through a DRI render node.

Uses SDL's offscreen video driver (no X server, no DRI3 requirement) and checks
the device string the Lab logs in "[LAB-VIDEO]". Skips (exit 77) when no render
node is accessible, so machines without a GPU are not reported as failures.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOFTWARE = re.compile(r"llvmpipe|softpipe|swrast|software|lavapipe", re.I)


def main() -> int:
    binary, rom, outdir = sys.argv[1:4]
    nodes = sorted(Path("/dev/dri").glob("renderD*")) if Path("/dev/dri").is_dir() else []
    if not any(os.access(node, os.R_OK | os.W_OK) for node in nodes):
        print("SKIP: no accessible /dev/dri/renderD* node")
        return 77

    with tempfile.TemporaryDirectory() as prefs:
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_RENDER_DRIVER", "SEVEL_FONT"):
            env.pop(name, None)
        env.update(SDL_VIDEODRIVER="offscreen", XDG_DATA_HOME=prefs)
        png = Path(outdir) / "sevel-hardware-gpu.png"
        png.unlink(missing_ok=True)
        done = subprocess.run(
            [binary, rom, "--capture-tick", "1485000", "--window-frames", "2",
             "--screenshot", str(png)],
            env=env, capture_output=True, text=True, timeout=120)
    output = done.stdout + done.stderr
    assert done.returncode == 0, output[-1500:]

    video = re.search(r"\[LAB-VIDEO\] renderer=(\S+) video=(\S+) device=(.*)", output)
    assert video, output[-1500:]
    renderer, driver, device = video[1], video[2], video[3].strip()
    print(f"renderer={renderer} video={driver} device={device}")
    assert driver == "offscreen", driver
    assert renderer != "software", "SDL fell back to the software renderer"
    assert device != "n/a", "renderer does not report a device; cannot prove hardware"
    assert not SOFTWARE.search(device), f"software rasterizer in use: {device}"

    data = png.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) > 10000, len(data)
    assert b"SEVEL Font\x00" in data, "face identity missing from PNG metadata"
    return 0


if __name__ == "__main__":
    sys.exit(main())
