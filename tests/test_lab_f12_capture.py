"""Capture the live Lab window with F12 while the ROM worker is paused."""

import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time


binary, rom = sys.argv[1:3]
width, height = map(int, sys.argv[4:6]) if len(sys.argv) >= 6 else (1280, 720)
replay_trace = sys.argv[6] if len(sys.argv) >= 7 else ""
with tempfile.TemporaryDirectory(prefix="sevel-f12-") as directory:
    environment = os.environ.copy()
    environment["SDL_AUDIODRIVER"] = "dummy"
    command = [binary, rom, "--live", "--auto-start", "--bench-preset",
               "--no-audio", "--window-frames", "1000"]
    if replay_trace:
        command.remove("--auto-start")
        command.extend(["--replay-controls", replay_trace])
    log_file = open(Path(directory) / "run.log", "w+")
    process = subprocess.Popen(command, cwd=directory, env=environment,
                               stdout=log_file, stderr=subprocess.STDOUT)
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
        subprocess.run(["xdotool", "windowsize", window, str(width),
                        str(height)], check=True, capture_output=True)
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline and process.poll() is None:
            title = subprocess.check_output(["xdotool", "getwindowname", window],
                                            text=True)
            match = re.search(r"tick (\d+)", title)
            if match and int(match[1]) >= 1500000:
                break
            time.sleep(0.05)
        assert match and int(match[1]) >= 1500000, title
        if not replay_trace:
            subprocess.run(["xdotool", "key", "--window", window, "space"],
                           check=True)
        time.sleep(0.15)
        title = subprocess.check_output(["xdotool", "getwindowname", window],
                                        text=True)
        paused_tick = int(re.search(r"tick (\d+)", title)[1])
        time.sleep(0.15)
        title = subprocess.check_output(["xdotool", "getwindowname", window],
                                        text=True)
        assert int(re.search(r"tick (\d+)", title)[1]) == paused_tick
        if replay_trace:
            assert paused_tick == 1500000, paused_tick
        subprocess.run(["xdotool", "key", "--window", window, "F12"], check=True)
        image = None
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and process.poll() is None:
            images = list(Path(directory).glob("sevel-ma17-lab-*.png"))
            if images and images[0].read_bytes().endswith(
                    b"\x00\x00\x00\x00IEND\xaeB`\x82"):
                image = images[0]
                break
            time.sleep(0.05)
        assert image, "F12 did not save a PNG"
        data = image.read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        assert struct.unpack(">II", data[16:24]) == (width, height)
        assert image.name.startswith(f"sevel-ma17-lab-{paused_tick}-")
        if len(sys.argv) >= 4:
            shutil.copyfile(image, sys.argv[3])
        subprocess.run(["xdotool", "key", "--window", window, "Escape"],
                       check=True)
        process.wait(timeout=10)
        log_file.seek(0)
        output = log_file.read()
        assert process.returncode == 0, output[-2000:]
        assert re.search(r"\[LAB-CAPTURE\] saved=.* tick=\d+", output), output[-2000:]
        if replay_trace:
            assert re.search(r"\[LAB-STATE\] tick=1500000 .*burns=\d+",
                             output), output[-2000:]
        if len(sys.argv) >= 6:
            Path(sys.argv[3]).with_suffix(".log").write_text(output)
        print(f"[LAB-F12] image={image.name} bytes={len(data)}")
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)
        log_file.close()
