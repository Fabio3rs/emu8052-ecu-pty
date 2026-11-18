"""Require live ROM/SEVEL motion in the GUI's mechanical viewport."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile


binary, rom = sys.argv[1:3]
ticks = (1_500_000, 1_550_000, 1_650_000, 1_750_000,
         1_850_000, 1_950_000, 2_050_000, 2_150_000)
view_crops = {"longitudinal": (335, 110, 550, 360),
              "profile": (650, 110, 775, 360)}
viewport_crops = {"longitudinal": (307, 110, 576, 420),
                  "profile": (576, 110, 845, 420)}


def mechanical_pixels(path: Path, crop) -> list[bytes]:
    data = path.read_bytes()
    assert data[:2] == b"BM"
    offset = struct.unpack_from("<I", data, 10)[0]
    width, signed_height = struct.unpack_from("<ii", data, 18)
    bit_count = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    assert (width, abs(signed_height)) == (1280, 720)
    assert bit_count in (24, 32) and compression in (0, 3)
    pixel_size = bit_count // 8
    stride = ((width * pixel_size + 3) // 4) * 4
    x0, y0, x1, y1 = crop
    pixels = []
    for y in range(y0, y1):
        source_y = abs(signed_height) - 1 - y if signed_height > 0 else y
        start = offset + source_y * stride + x0 * pixel_size
        for x in range(x0, x1):
            index = start + (x - x0) * pixel_size
            pixels.append(data[index:index + 3])
    return pixels


def assert_geometry_clear_of_viewport_edges(path: Path, crop) -> None:
    pixels = mechanical_pixels(path, crop)
    width = crop[2] - crop[0]
    height = crop[3] - crop[1]
    bright = 0
    edge = 0
    for index, pixel in enumerate(pixels):
        if max(pixel) < 120:
            continue
        bright += 1
        x, y = index % width, index // width
        if x < 5 or x >= width - 5 or y < 5 or y >= height - 5:
            edge += 1
    assert bright > 500, (path, crop, bright)
    assert edge == 0, (path, crop, edge)


with tempfile.TemporaryDirectory() as directory:
    environment = os.environ.copy()
    environment["SDL_AUDIODRIVER"] = "dummy"
    captures = {view: [] for view in view_crops}
    counts = []
    for tick in ticks:
        image = Path(directory) / f"sevel-{tick}.bmp"
        command = [binary, rom, "--live", "--auto-start", "--bench-preset",
                   "--window-frames", "2400", "--capture-tick", str(tick),
                   "--stop-ticks", str(tick), "--screenshot", str(image)]
        result = subprocess.run(command, env=environment, text=True,
                                capture_output=True, timeout=60)
        assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
        state = re.search(r"\[LAB-STATE\] tick=(\d+).*cc3=(\d+) burns=(\d+)",
                          result.stdout)
        assert state and int(state[1]) == tick, result.stdout[-3000:]
        counts.append((int(state[2]), int(state[3])))
        for view, crop in view_crops.items():
            captures[view].append(mechanical_pixels(image, crop))
            assert_geometry_clear_of_viewport_edges(
                image, viewport_crops[view])
    assert counts[1][0] > counts[0][0], counts
    assert counts[1][1] > counts[0][1], counts
    motion = {}
    for view, frames in captures.items():
        changed = sum(first != second for first, second in
                      zip(frames[0], frames[1]))
        fraction = changed / len(frames[0])
        assert fraction > 0.05, (view, changed, fraction)
        motion[view] = f"{changed}/{len(frames[0])} ({fraction:.1%})"
    print(f"[LAB-MOTION] ticks={ticks} cc3/burns={counts} "
          f"mechanical_changed={motion}")
