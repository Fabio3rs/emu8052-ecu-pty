"""C3: clicking the 4X / 0.25X / 1X segments of the toolbar speed selector
changes the simulation speed; the active segment is highlighted. Xvfb, 1280x720."""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

binary, rom, out_dir = sys.argv[1:4]
out = Path(out_dir)
out.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env["SDL_AUDIODRIVER"] = "dummy"
ON, OFF = (18, 52, 60), (20, 20, 24)


def xdotool(*args):
    return subprocess.run(["xdotool", *args], check=True, text=True,
                          capture_output=True).stdout.strip()


def run_with_click(click_x, shot, capture_tick=6000000):
    command = [binary, rom, "--live", "--window-frames", "240",
               "--capture-tick", str(capture_tick), "--screenshot", str(shot)]
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(command, env=env, stdout=log,
                                   stderr=subprocess.STDOUT)
        window = ""
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline and process.poll() is None:
            found = subprocess.run(["xdotool", "search", "--name", "SEVEL MA1.7"],
                                   text=True, capture_output=True)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[-1]
                break
            time.sleep(0.05)
        assert window, "Lab window did not appear"
        time.sleep(0.5)
        if click_x is not None:
            xdotool("mousemove", "--window", window, str(click_x), "85")
            xdotool("click", "1")
            time.sleep(0.3)
        assert process.wait(timeout=30) == 0


def pixel(path, x, y):
    from PIL import Image
    return Image.open(path).convert("RGB").getpixel((x, y))


# Segment geometry at 1280x720 (ui scale 1): x 323..509 in three 62 px parts.
SEG_X = (326, 388, 450)
Y = 74
shot = out / "speed-default.png"
run_with_click(None, shot)
assert [pixel(shot, x, Y) for x in SEG_X] == [OFF, ON, OFF], "default is 1X"
shot = out / "speed-4x.png"
run_with_click(480, shot)
assert [pixel(shot, x, Y) for x in SEG_X] == [OFF, OFF, ON], "click selects 4X"
shot = out / "speed-025x.png"
# At 0.25X the tick advances 4x slower, so aim for a nearer capture tick.
run_with_click(340, shot, capture_tick=1500000)
assert [pixel(shot, x, Y) for x in SEG_X] == [ON, OFF, OFF], "click selects 0.25X"
print("[LAB-SPEED] selector ok")
