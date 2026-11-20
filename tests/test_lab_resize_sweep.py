"""Resize one live Lab window through desktop and compact layouts."""

import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time


binary, rom, output_dir = sys.argv[1:4]
output = Path(output_dir)
output.mkdir(parents=True, exist_ok=True)
sizes = [(1280, 720), (1440, 810), (1600, 900),
         (1920, 1080), (900, 620), (1280, 720)]


def xdotool(*args):
    return subprocess.run(["xdotool", *map(str, args)], check=True,
                          capture_output=True, text=True).stdout.strip()


def wait_until(check, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("live window did not reach expected state")


def window_size(window):
    geometry = xdotool("getwindowgeometry", "--shell", window)
    values = dict(re.findall(r"^(WIDTH|HEIGHT)=(\d+)$", geometry,
                             re.MULTILINE))
    return int(values["WIDTH"]), int(values["HEIGHT"])


def complete_png(path):
    data = path.read_bytes()
    return (len(data) > 20000 and data.startswith(b"\x89PNG\r\n\x1a\n")
            and data.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82"))


with tempfile.TemporaryDirectory(prefix="sevel-resize-sweep-") as directory:
    environment = os.environ.copy()
    environment["SDL_AUDIODRIVER"] = "dummy"
    command = [binary, rom, "--live", "--auto-start", "--bench-preset",
               "--no-audio", "--window-frames", "240000"]
    log_file = open(Path(directory) / "run.log", "w+")
    process = subprocess.Popen(command, cwd=directory, env=environment,
                               stdout=log_file, stderr=subprocess.STDOUT)
    index = 0
    previous = set()
    try:
        def find_window():
            found = subprocess.run(["xdotool", "search", "--onlyvisible",
                                    "--name", "FIAT TIPO"], capture_output=True,
                                   text=True)
            return found.stdout.splitlines()[-1] if found.stdout.strip() else None

        window = wait_until(find_window)
        for index, (width, height) in enumerate(sizes):
            if index:
                old_width, old_height = sizes[index - 1]
                for step in range(1, 7):
                    xdotool("windowsize", window,
                            round(old_width + (width - old_width) * step / 6),
                            round(old_height + (height - old_height) * step / 6))
            xdotool("windowsize", window, width, height)
            wait_until(lambda: window_size(window) == (width, height))
            time.sleep(0.25)
            if index == 3:
                xdotool("mousemove", "--window", window, 1010, 128)
                xdotool("click", 1)
                wait_until(lambda: "| RADIAL |" in
                           xdotool("getwindowname", window))
            if index == 5:
                xdotool("mousemove", "--window", window, 680, 85)
                xdotool("click", 1)
                wait_until(lambda: "| AXIAL 1/4 |" in
                           xdotool("getwindowname", window))
                xdotool("mousemove", "--window", window, 203, 649)
                xdotool("click", 1)
                wait_until(lambda: "| GEAR 1 |" in
                           xdotool("getwindowname", window))
            xdotool("key", "--window", window, "F12")

            def new_capture():
                for path in Path(directory).glob("sevel-ma17-lab-*.png"):
                    if path not in previous and complete_png(path):
                        return path
                return None

            image = wait_until(new_capture, 12.0)
            previous.add(image)
            assert struct.unpack(">II", image.read_bytes()[16:24]) == (width, height)
            shutil.copyfile(image, output / f"resize-sweep-{index}-{width}x{height}.png")
        xdotool("key", "--window", window, "Escape")
        process.wait(timeout=10)
        log_file.seek(0)
        log = log_file.read()
        assert process.returncode == 0, log[-1500:]
        (output / "resize-sweep.log").write_text(log)
        print(f"[LAB-RESIZE-SWEEP] captures={len(sizes)} view=AXIAL 1/4 gear=1")
    except Exception:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)
        log_file.seek(0)
        log = log_file.read()
        for path in Path(directory).glob("sevel-ma17-lab-*.png"):
            shutil.copyfile(path, output / f"failed-{index}-{path.name}")
        print(f"resize index={index} size={sizes[index]} "
              f"previous={[p.name for p in previous]} files="
              f"{[(p.name, p.stat().st_size, complete_png(p)) for p in Path(directory).glob('sevel-ma17-lab-*.png')]} "
              f"log={log[-1800:]}", file=sys.stderr)
        raise
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)
        log_file.close()
