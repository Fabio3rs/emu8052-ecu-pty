"""Capture the live original-ROM session at a requested window size."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import zlib


binary, rom, image_path = sys.argv[1:4]
width, height = map(int, sys.argv[4:6]) if len(sys.argv) >= 6 else (900, 620)
radial_mode = sys.argv[6] if len(sys.argv) >= 7 else ""
view_keys = {"radial": 1, "radial-help": 1,
             "axial-14": 2, "axial-23": 3}.get(radial_mode, 0)
radial_view = view_keys > 0 or radial_mode == "radial-click"
expected_view = ("RADIAL" if radial_mode.startswith("radial") else
                 "AXIAL 1/4" if radial_mode == "axial-14" else "AXIAL 2/3")
image = Path(image_path)
image.unlink(missing_ok=True)
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
command = [binary, rom, "--live", "--auto-start", "--bench-preset",
           "--window-frames", "240000",
           "--capture-tick", "1500000", "--stop-ticks", "1500000",
           "--screenshot", str(image)]

with tempfile.TemporaryFile(mode="w+") as log:
    process = subprocess.Popen(command, env=environment, stdout=log,
                               stderr=subprocess.STDOUT)
    try:
        window = ""
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline and process.poll() is None:
            found = subprocess.run(["xdotool", "search", "--name",
                                    "SEVEL MA1.7"], text=True,
                                   capture_output=True)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[-1]
                break
            time.sleep(0.05)
        assert window, "Lab window did not appear"
        subprocess.run(["xdotool", "windowsize", window, str(width),
                        str(height)],
                       check=True, capture_output=True)
        if radial_view:
            if radial_mode == "radial-click":
                if width < 1280 or height < 720:
                    click_x = int(width * 0.88)
                    click_y = int(height * 0.45 - 19)
                else:
                    click_x = int(width * 0.76 - 120)
                    click_y = 79 if height < 900 else 97
                subprocess.run(
                    ["xdotool", "mousemove", "--window", window,
                     str(click_x), str(click_y), "click", "1"],
                    check=True, capture_output=True)
            else:
                for _ in range(view_keys):
                    subprocess.run(["xdotool", "key", "--window", window, "v"],
                                   check=True, capture_output=True)
            deadline = time.monotonic() + 2.0
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                title = subprocess.run(["xdotool", "getwindowname", window],
                                       text=True, capture_output=True,
                                       check=True).stdout
                if f"| {expected_view} |" in title:
                    break
                time.sleep(0.05)
            assert f"| {expected_view} |" in title, title
        if radial_mode == "radial-help":
            subprocess.run(["xdotool", "key", "--window", window, "h"],
                           check=True, capture_output=True)
        assert process.wait(timeout=60) == 0
        log.seek(0)
        output = log.read()
        state = re.search(r"\[LAB-STATE\].*cc3=(\d+) burns=(\d+)", output)
        assert state, "final Lab state missing"
        assert int(state[1]) > 0 and int(state[2]) > 0, state[0]
        header = image.read_bytes()[:24]
        assert header.startswith(b"\x89PNG\r\n\x1a\n"), header
        size = struct.unpack(">II", header[16:24])
        assert size == (width, height), size
        data = image.read_bytes()
        assert data[24:26] == b"\x08\x06", data[24:26]
        cursor = 8
        compressed = bytearray()
        while cursor < len(data):
            length = struct.unpack(">I", data[cursor:cursor + 4])[0]
            kind = data[cursor + 4:cursor + 8]
            if kind == b"IDAT":
                compressed.extend(data[cursor + 8:cursor + 8 + length])
            cursor += length + 12
        scanlines = zlib.decompress(compressed)
        stride = width * 4 + 1
        assert len(scanlines) == stride * height
        # A resize must produce a cleared frame, not a transparent new area.
        previous_alpha = 0
        for row in range(height):
            filter_kind = scanlines[row * stride]
            encoded_alpha = scanlines[row * stride + 4]
            if filter_kind in (0, 1):
                alpha = encoded_alpha
            elif filter_kind in (2, 4):
                alpha = (encoded_alpha + previous_alpha) % 256
            elif filter_kind == 3:
                alpha = (encoded_alpha + previous_alpha // 2) % 256
            else:
                raise AssertionError(f"unsupported PNG filter {filter_kind}")
            assert alpha == 255, (row, alpha)
            previous_alpha = alpha
        print(f"[LAB-RESIZE] png={image} size={size} "
              f"cc3={state[1]} burns={state[2]}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-3000:], file=sys.stderr)
        raise
