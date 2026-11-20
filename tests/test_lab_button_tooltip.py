"""C5: resting the pointer on a button shows its shortcut tooltip (cyan frame
above the button); with the pointer elsewhere nothing is drawn there. Xvfb."""

import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

binary, rom, out_dir = sys.argv[1:4]
out = Path(out_dir)
out.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, SDL_AUDIODRIVER="dummy")
FRAME = (90, 200, 215)


def capture(shot, point):
    process = subprocess.Popen(
        [binary, rom, "--live", "--window-frames", "200", "--capture-tick",
         "3000000", "--screenshot", str(shot)], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    window = ""
    for _ in range(80):
        found = subprocess.run(["xdotool", "search", "--name", "SEVEL MA1.7"],
                               text=True, capture_output=True)
        if found.stdout.strip():
            window = found.stdout.split()[-1]
            break
        time.sleep(0.05)
    assert window, "Lab window did not appear"
    time.sleep(1.0)
    subprocess.run(["xdotool", "mousemove", "--window", window, *map(str, point)],
                   check=True)
    assert process.wait(timeout=30) == 0


def frame_pixels(shot):
    image = Image.open(shot).convert("RGB")
    return sum(1 for x in range(100, 300) for y in range(470, 500)
               if image.getpixel((x, y)) == FRAME)


capture(out / "tooltip-off.png", (700, 300))     # over the scene: no tooltip
capture(out / "tooltip-on.png", (150, 520))      # over LOAD
off, on = frame_pixels(out / "tooltip-off.png"), frame_pixels(out / "tooltip-on.png")
assert off == 0, off
assert on > 150, on  # a ~160x20 frame outline
print(f"[LAB-TOOLTIP] frame pixels off={off} on={on}")
