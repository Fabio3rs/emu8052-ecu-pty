#!/usr/bin/env python3
"""B.14: the same scene and tick through SdlGpuRenderer and the SDL_Renderer replay.

The app renders the scene at the GPU preview viewport into the donor GPU
pipeline and, for the same tick, replays the recorded triangles with the donor
blend through SDL_Renderer. The two images must agree on content, not on every
rasterization detail. Skips (exit 77) when SDL GPU is unavailable.
"""
import os, re, struct, subprocess, sys, tempfile, zlib
from pathlib import Path

binary, rom = sys.argv[1:3]
out_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None


def read_png(path):
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", data[16:24])
    assert data[24:29] == b"\x08\x06\x00\x00\x00", "expected RGBA8"
    idat, cursor = bytearray(), 8
    while cursor < len(data):
        size = struct.unpack(">I", data[cursor:cursor + 4])[0]
        if data[cursor + 4:cursor + 8] == b"IDAT":
            idat.extend(data[cursor + 8:cursor + 8 + size])
        cursor += size + 12
    raw = zlib.decompress(bytes(idat))
    stride = width * 4
    rows, prev = [], bytearray(stride)
    for y in range(height):
        o = y * (stride + 1)
        kind, line = raw[o], bytearray(raw[o + 1:o + 1 + stride])
        for i in range(stride):
            a = line[i - 4] if i >= 4 else 0
            b = prev[i]
            c = prev[i - 4] if i >= 4 else 0
            if kind == 1: p = a
            elif kind == 2: p = b
            elif kind == 3: p = (a + b) // 2
            elif kind == 4:
                e = a + b - c
                p = min((a, b, c), key=lambda v: abs(e - v))
            else: p = 0
            line[i] = (line[i] + p) & 255
        rows.append(line); prev = line
    return width, height, rows


with tempfile.TemporaryDirectory(prefix="sevel-equiv-") as tmp:
    directory = out_dir or Path(tmp)
    directory.mkdir(parents=True, exist_ok=True)
    image = directory / "main.png"
    env = dict(os.environ, SDL_VIDEODRIVER="offscreen", SDL_AUDIODRIVER="dummy")
    done = subprocess.run(
        [binary, rom, "--live", "--gpu-preview", "--no-audio", "--auto-start",
         "--bench-preset", "--window-frames", "180", "--capture-tick", "1500000",
         "--screenshot", str(image)], env=env, text=True, capture_output=True, timeout=60)
    output = done.stdout + done.stderr
    if "[LAB-GPU] preview_ready=1" not in output:
        print("[LAB-EQUIV] SDL GPU unavailable; skip"); sys.exit(77)
    assert done.returncode == 0, output[-2000:]
    gpu_png, sdl_png = directory / "main-gpu.png", directory / "main-sdlscene.png"
    assert gpu_png.exists() and sdl_png.exists(), output[-2000:]
    gw, gh, grows = read_png(gpu_png)
    sw, sh, srows = read_png(sdl_png)
    assert (gw, gh) == (sw, sh), ((gw, gh), (sw, sh))

    def stats(rows):
        bg = rows[0][:4]
        xs0, ys0, xs1, ys1 = gw, gh, -1, -1
        for y, row in enumerate(rows):
            for x in range(0, gw, 2):
                if row[x * 4:x * 4 + 4] != bg:
                    xs0, ys0, xs1, ys1 = min(xs0, x), min(ys0, y), max(xs1, x), max(ys1, y)
        return (xs0, ys0, xs1, ys1)

    box_g, box_s = stats(grows), stats(srows)
    # Region colors: mean RGB over a 8x8 grid of cells.
    def grid(rows, n=8):
        cw, ch = gw // n, gh // n
        cells = []
        for gy in range(n):
            for gx in range(n):
                acc = [0, 0, 0]; cnt = 0
                for y in range(gy * ch, (gy + 1) * ch, 3):
                    row = rows[y]
                    for x in range(gx * cw, (gx + 1) * cw, 3):
                        for k in range(3): acc[k] += row[x * 4 + k]
                        cnt += 1
                cells.append([v / cnt for v in acc])
        return cells
    cells_g, cells_s = grid(grows), grid(srows)
    worst = max(abs(a - b) for cg, cs in zip(cells_g, cells_s) for a, b in zip(cg, cs))
    mean_diff = sum(abs(a - b) for cg, cs in zip(cells_g, cells_s) for a, b in zip(cg, cs)) / (64 * 3)
    differing = total = 0
    for rg, rs in zip(grows, srows):
        for x in range(0, gw, 2):
            total += 1
            if max(abs(rg[x * 4 + k] - rs[x * 4 + k]) for k in range(3)) > 48:
                differing += 1
    fraction = differing / total
    print(f"[LAB-EQUIV] size={gw}x{gh} bbox_gpu={box_g} bbox_sdl={box_s} "
          f"worst_cell={worst:.1f} mean_cell={mean_diff:.2f} px>48={fraction:.4f}")
    assert all(abs(a - b) <= 4 for a, b in zip(box_g, box_s)), (box_g, box_s)
    assert worst < 24.0 and mean_diff < 4.0, (worst, mean_diff)
    assert fraction < 0.04, fraction
