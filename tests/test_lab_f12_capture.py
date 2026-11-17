"""Capture the live Lab window with F12 while the ROM worker is paused."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time


binary, rom = sys.argv[1:3]
with tempfile.TemporaryDirectory(prefix="sevel-f12-") as directory:
    environment = os.environ.copy()
    environment["SDL_AUDIODRIVER"] = "dummy"
    command = [binary, rom, "--live", "--bench-preset", "--no-audio",
               "--window-frames", "300"]
    process = subprocess.Popen(command, cwd=directory, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True)
    try:
        window = ""
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and process.poll() is None:
            found = subprocess.run(["xdotool", "search", "--name", "SEVEL MA1.7"],
                                   capture_output=True, text=True)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[-1]
                break
            time.sleep(0.05)
        assert window, "Lab window did not appear"
        subprocess.run(["xdotool", "key", "--window", window, "space"], check=True)
        time.sleep(0.15)
        title = subprocess.check_output(["xdotool", "getwindowname", window],
                                        text=True)
        paused_tick = int(re.search(r"tick (\d+)", title)[1])
        time.sleep(0.15)
        title = subprocess.check_output(["xdotool", "getwindowname", window],
                                        text=True)
        assert int(re.search(r"tick (\d+)", title)[1]) == paused_tick
        subprocess.run(["xdotool", "key", "--window", window, "F12"], check=True)
        image = None
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and process.poll() is None:
            images = list(Path(directory).glob("sevel-ma17-lab-*.png"))
            if images and images[0].stat().st_size >= 24:
                image = images[0]
                break
            time.sleep(0.05)
        assert image, "F12 did not save a PNG"
        data = image.read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        assert struct.unpack(">II", data[16:24]) == (1280, 720)
        assert image.name.startswith(f"sevel-ma17-lab-{paused_tick}-")
        subprocess.run(["xdotool", "key", "--window", window, "Escape"],
                       check=True)
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 0, output[-2000:]
        assert re.search(r"\[LAB-CAPTURE\] saved=.* tick=\d+", output), output[-2000:]
        print(f"[LAB-F12] image={image.name} bytes={len(data)}")
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=5)
