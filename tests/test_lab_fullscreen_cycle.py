"""Exercise fullscreen entry, rendering, return and restored hitboxes."""

import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib


binary, rom, output = sys.argv[1:4]
ui_scale = sys.argv[4] if len(sys.argv) > 4 else ""


def window_size(window):
    result = subprocess.run(
        ["xdotool", "getwindowgeometry", "--shell", window],
        text=True, capture_output=True)
    if result.returncode != 0:
        return None
    values = dict(re.findall(r"^(WIDTH|HEIGHT)=(\d+)$", result.stdout,
                             re.MULTILINE))
    return int(values["WIDTH"]), int(values["HEIGHT"])


def click(window, x, y):
    # Give XInput distinct press/release times. Xvfb can replay a zero-duration
    # XTEST click twice after the window manager changes fullscreen state.
    subprocess.run(["xdotool", "mousemove", "--window", window, x, y,
                    "mousedown", "1", "sleep", "0.07", "mouseup", "1"],
                   check=True, capture_output=True)


def wait_until(check, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.05)
    raise AssertionError("window or capture did not reach expected state")


def png_size(path):
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n") and complete_png(path)
    return struct.unpack(">II", data[16:24])


def complete_png(path):
    """A PNG is complete when every chunk CRC matches, the IDAT stream inflates
    fully and IEND is the last chunk. (A size threshold is not a completeness
    test: pixel-font captures are legitimately small.)"""
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    cursor = 8
    compressed = bytearray()
    while cursor + 12 <= len(data):
        size = struct.unpack(">I", data[cursor:cursor + 4])[0]
        end = cursor + 12 + size
        if end > len(data):
            return False
        kind = data[cursor + 4:cursor + 8]
        crc = struct.unpack(">I", data[end - 4:end])[0]
        if zlib.crc32(data[cursor + 4:end - 4]) != crc:
            return False
        if kind == b"IDAT":
            compressed.extend(data[cursor + 8:end - 4])
        if kind == b"IEND":
            try:
                zlib.decompress(bytes(compressed))
            except zlib.error:
                return False
            return end == len(data) and len(compressed) > 0
        cursor = end
    return False


with tempfile.TemporaryDirectory(prefix="sevel-fullscreen-") as directory:
    environment = os.environ.copy()
    environment["SDL_AUDIODRIVER"] = "dummy"
    manager = subprocess.Popen(["xfwm4"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    wait_until(lambda: "Xfwm4" in subprocess.run(
        ["wmctrl", "-m"], text=True, capture_output=True).stdout)
    command = [binary, rom, "--live", "--no-cad", "--bench-preset", "--no-audio",
               "--window-frames", "240000"]
    if ui_scale:
        command.extend(["--ui-scale", ui_scale])
    process = subprocess.Popen(
        command, cwd=directory, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        def find_window():
            found = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name",
                 "FIAT TIPO"],
                text=True, capture_output=True)
            return found.stdout.splitlines()[-1] if found.stdout.strip() else None

        def current_size():
            current = find_window()
            return window_size(current) if current else None

        window = wait_until(find_window)
        wait_until(lambda: current_size() == (1280, 720))
        time.sleep(0.4)
        window = wait_until(find_window)
        if ui_scale:
            subprocess.run(["xdotool", "key", "--window", window, "F11"],
                           check=True, capture_output=True)
        else:
            click(window, "790", "79")
        try:
            wait_until(lambda: current_size() == (1920, 1080))
        except AssertionError:
            actual_size = current_size()
            process.terminate()
            log, _ = process.communicate(timeout=5)
            raise AssertionError(f"fullscreen size={actual_size} "
                                 f"log={log[-1500:]}")
        window = wait_until(find_window)
        subprocess.run(["xdotool", "key", "--window", window, "F12"],
                       check=True, capture_output=True)
        captures = lambda: list(Path(directory).glob("sevel-ma17-lab-*.png"))
        full = wait_until(lambda: next(
            (path for path in captures() if complete_png(path)), None))
        assert png_size(full) == (1920, 1080)
        full_output = Path(output).with_name(Path(output).stem + "-full.png")
        shutil.copyfile(full, full_output)
        subprocess.run(["xdotool", "key", "--window", window, "F11"],
                       check=True, capture_output=True)
        wait_until(lambda: current_size() == (1280, 720))
        time.sleep(0.3)
        window = wait_until(find_window)
        subprocess.run(["xdotool", "key", "--window", window, "F12"],
                       check=True, capture_output=True)
        restored = wait_until(lambda: next(
            (path for path in captures() if path != full and
             complete_png(path)), None))
        shutil.copyfile(restored, output)
        assert png_size(restored) == (1280, 720), png_size(restored)
        click(window, "681", "156" if ui_scale else "79")
        wait_until(lambda: "| RADIAL |" in subprocess.check_output(
            ["xdotool", "getwindowname", window], text=True))
        subprocess.run(["xdotool", "key", "--window", window, "Escape"],
                       check=True, capture_output=True)
        log, _ = process.communicate(timeout=10)
        assert process.returncode == 0, log[-1500:]
    finally:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=5)
        manager.terminate()
        manager.wait(timeout=5)
