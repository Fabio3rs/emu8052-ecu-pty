#!/usr/bin/env python3
"""LabCapture.TextMask (L3): text renders the same on the GPU and on llvmpipe.

The same state is captured twice: SDL offscreen on the real GPU and Xvfb on the
software rasterizer (llvmpipe). Text is drawn from a pixel face with NEAREST
sampling; with glyph origins snapped to whole device pixels the two backends
must produce the same text mask. The mask is "bright pixel" over the header
strip and the left-column dial titles, where there is only text on dark panels.

Skips (exit 77) without xvfb-run or without a usable GPU render node.

Usage: test_lab_text_mask.py <sevel-ma17-lab> <rom.bin> [out_dir]
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

REGIONS = {                      # name: (x0, y0, x1, y1) at 1280x720
    "header": (16, 16, 828, 68),
    "left_dial_titles": (10, 92, 300, 112),
    "gauge_titles": (846, 14, 1272, 40),
}
MAX_DIFFERING_FRACTION = 0.01     # of the mask pixels, per region


def run_capture(binary, rom, png, gpu):
    with tempfile.TemporaryDirectory() as prefs:
        env = dict(os.environ)
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "SDL_RENDER_DRIVER", "SEVEL_FONT"):
            env.pop(name, None)
        env["XDG_DATA_HOME"] = prefs
        command = [binary, rom, "--live", "--bench-preset", "--no-audio",
                   "--auto-start", "--window-frames", "240000",
                   "--capture-tick", "800000", "--stop-ticks", "800000",
                   "--screenshot", str(png)]
        if gpu:
            env["SDL_VIDEODRIVER"] = "offscreen"
        else:
            command = ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24", *command]
        done = subprocess.run(command, env=env, capture_output=True, text=True,
                              timeout=180)
        output = done.stdout + done.stderr
        assert done.returncode == 0, output[-1500:]
        return output


def mask(image, box):
    x0, y0, x1, y1 = box
    crop = np.asarray(image.convert("L"), dtype=np.uint8)[y0:y1, x0:x1]
    return crop > 140


def main() -> int:
    binary, rom = sys.argv[1:3]
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    if not shutil.which("xvfb-run"):
        print("SKIP: no xvfb-run")
        return 77
    nodes = sorted(Path("/dev/dri").glob("renderD*")) if Path("/dev/dri").is_dir() else []
    if not any(os.access(n, os.R_OK | os.W_OK) for n in nodes):
        print("SKIP: no accessible /dev/dri/renderD* node")
        return 77
    with tempfile.TemporaryDirectory() as work:
        gpu_png, cpu_png = Path(work) / "gpu.png", Path(work) / "cpu.png"
        gpu_log = run_capture(binary, rom, gpu_png, gpu=True)
        cpu_log = run_capture(binary, rom, cpu_png, gpu=False)
        video = lambda log: re.search(r"\[LAB-VIDEO\] renderer=(\S+) video=(\S+) device=(.*)", log)
        assert video(gpu_log) and "llvmpipe" not in video(gpu_log)[3], video(gpu_log)
        assert video(cpu_log) and "llvmpipe" in video(cpu_log)[3].lower(), video(cpu_log)
        gpu, cpu = Image.open(gpu_png), Image.open(cpu_png)
        assert gpu.size == cpu.size == (1280, 720), (gpu.size, cpu.size)
        if out:
            out.mkdir(parents=True, exist_ok=True)
            shutil.copy(gpu_png, out / "text-mask-gpu.png")
            shutil.copy(cpu_png, out / "text-mask-llvmpipe.png")
        for name, box in REGIONS.items():
            a, b = mask(gpu, box), mask(cpu, box)
            ink = max(int(a.sum()), int(b.sum()))
            assert ink > 100, (name, "no text found", ink)
            differing = int((a ^ b).sum())
            fraction = differing / ink
            print(f"{name}: ink={ink} differing={differing} ({fraction:.4f})")
            assert fraction <= MAX_DIFFERING_FRACTION, (name, differing, ink)
            # Sensitivity control: a one-pixel shift of the same mask must be
            # caught, so a pass above means the text really is identical.
            shifted = np.roll(a, 1, axis=1)
            assert (int((shifted ^ a).sum()) / ink) > MAX_DIFFERING_FRACTION * 5, name
    return 0


if __name__ == "__main__":
    sys.exit(main())
