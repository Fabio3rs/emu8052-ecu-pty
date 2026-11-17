"""Require live ROM/SEVEL motion in the GUI's mechanical viewport."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile


binary, rom = sys.argv[1:3]
ticks = (1_500_000, 1_550_000)
crop = (120, 120, 850, 455)


def mechanical_pixels(path: Path) -> list[bytes]:
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


with tempfile.TemporaryDirectory() as directory:
    environment = os.environ.copy()
    environment["SDL_AUDIODRIVER"] = "dummy"
    captures = []
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
        captures.append(mechanical_pixels(image))
    assert counts[1][0] > counts[0][0], counts
    assert counts[1][1] > counts[0][1], counts
    changed = sum(first != second for first, second in zip(*captures))
    fraction = changed / len(captures[0])
    assert fraction > 0.05, (changed, fraction)
    print(f"[LAB-MOTION] ticks={ticks} cc3/burns={counts} "
          f"mechanical_changed={changed}/{len(captures[0])} ({fraction:.1%})")
