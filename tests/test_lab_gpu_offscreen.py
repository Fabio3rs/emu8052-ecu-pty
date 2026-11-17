"""Exercise the donor GPU preview with SDL's offscreen video driver."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zlib


binary, rom = sys.argv[1:3]


def png_foreground_bounds(data):
    width, height = struct.unpack(">II", data[16:24])
    assert data[24:29] == b"\x08\x06\x00\x00\x00"  # RGBA8
    compressed = bytearray()
    cursor = 8
    while cursor < len(data):
        size = struct.unpack(">I", data[cursor:cursor + 4])[0]
        if data[cursor + 4:cursor + 8] == b"IDAT":
            compressed.extend(data[cursor + 8:cursor + 8 + size])
        cursor += size + 12
    rows = zlib.decompress(compressed)
    stride = width * 4
    previous = bytearray(stride)
    background = None
    bounds = [width, height, -1, -1]
    for row in range(height):
        offset = row * (stride + 1)
        kind = rows[offset]
        pixels = bytearray(rows[offset + 1:offset + 1 + stride])
        for index in range(stride):
            left = pixels[index - 4] if index >= 4 else 0
            above = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if kind == 1:
                predictor = left
            elif kind == 2:
                predictor = above
            elif kind == 3:
                predictor = (left + above) // 2
            elif kind == 4:
                estimate = left + above - upper_left
                predictor = min((left, above, upper_left),
                                key=lambda value: abs(estimate - value))
            else:
                assert kind == 0, kind
                predictor = 0
            pixels[index] = (pixels[index] + predictor) & 255
        if background is None:
            background = pixels[:4]
        for x in range(0, width, 2):
            if pixels[x * 4:x * 4 + 4] != background:
                bounds[0] = min(bounds[0], x)
                bounds[1] = min(bounds[1], row)
                bounds[2] = max(bounds[2], x)
                bounds[3] = max(bounds[3], row)
        previous = pixels
    return bounds


with tempfile.TemporaryDirectory(prefix="sevel-gpu-offscreen-") as directory:
    image = Path(directory) / "main.png"
    gpu_image = image.with_name("main-gpu.png")
    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "offscreen"
    environment["SDL_AUDIODRIVER"] = "dummy"
    command = [binary, rom, "--live", "--gpu-preview", "--no-audio",
               "--auto-start", "--bench-preset", "--window-frames", "180",
               "--capture-tick", "1500000", "--screenshot", str(image)]
    completed = subprocess.run(command, env=environment, text=True,
                               capture_output=True, timeout=30)
    output = completed.stdout + completed.stderr
    if "[LAB-GPU] preview_ready=1" not in output:
        if ("SDL GPU preview unavailable:" in output or
                "SDL renderer:" in output or "SDL window:" in output):
            print("[LAB-GPU-OFFSCREEN] backend unavailable; skip")
            sys.exit(77)
        raise AssertionError(output[-3000:])
    assert completed.returncode == 0, output[-3000:]
    assert "SDL GPU preview stopped:" not in output, output[-3000:]
    main_capture = re.search(r"\[LAB-CAPTURE\] saved=.* tick=(\d+)", output)
    gpu_capture = re.search(r"\[LAB-GPU\] scene_capture=.* tick=(\d+)", output)
    assert main_capture and gpu_capture, output[-3000:]
    assert main_capture.group(1) == gpu_capture.group(1)
    assert int(main_capture.group(1)) == 1500000
    state = re.search(r"\[LAB-STATE\] tick=(\d+).*cc3=(\d+) "
                      r"burns=(\d+).*overflow=(\d+)", output)
    assert state, output[-3000:]
    tick, cc3, burns, overflow = map(int, state.groups())
    assert tick > 1500000 and cc3 > 0 and burns > 0 and overflow == 0
    data = image.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert struct.unpack(">II", data[16:24]) == (1280, 720)
    gpu_data = gpu_image.read_bytes()
    assert gpu_data.startswith(b"\x89PNG\r\n\x1a\n")
    assert struct.unpack(">II", gpu_data[16:24]) == (960, 640)
    left, top, right, bottom = png_foreground_bounds(gpu_data)
    assert right - left > 500 and bottom - top > 250, (left, top, right, bottom)
    print(f"[LAB-GPU-OFFSCREEN] tick={tick} cc3={cc3} burns={burns} "
          f"capture_tick={main_capture.group(1)} "
          f"main_png_bytes={len(data)} gpu_png_bytes={len(gpu_data)}")
