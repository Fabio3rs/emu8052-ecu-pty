"""Exercise the live Lab button bar against the original ROM under Xvfb."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import zlib


binary, rom, trace_path = sys.argv[1:4]
trace = Path(trace_path)
trace.unlink(missing_ok=True)
image = trace.with_suffix(".png")
image.unlink(missing_ok=True)
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
command = [binary, rom, "--live", "--window-frames", "300",
           "--capture-tick", "3000000",
           "--save-controls", trace_path, "--screenshot", str(image)]


def xdotool(*args):
    return subprocess.run(["xdotool", *args], check=True, text=True,
                          capture_output=True).stdout.strip()


def png_pixel(path, x, y):
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (1280, 720)
    compressed = bytearray()
    cursor = 8
    while cursor < len(data):
        size = struct.unpack(">I", data[cursor:cursor + 4])[0]
        if data[cursor + 4:cursor + 8] == b"IDAT":
            compressed.extend(data[cursor + 8:cursor + 8 + size])
        cursor += size + 12
    scanlines = zlib.decompress(compressed)
    stride = width * 4
    previous = bytearray(stride)
    for row in range(y + 1):
        offset = row * (stride + 1)
        filter_kind = scanlines[offset]
        pixels = bytearray(scanlines[offset + 1:offset + 1 + stride])
        for index in range(stride):
            left = pixels[index - 4] if index >= 4 else 0
            above = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if filter_kind == 1:
                predictor = left
            elif filter_kind == 2:
                predictor = above
            elif filter_kind == 3:
                predictor = (left + above) // 2
            elif filter_kind == 4:
                estimate = left + above - upper_left
                predictor = min((left, above, upper_left),
                                key=lambda value: abs(estimate - value))
            else:
                assert filter_kind == 0, filter_kind
                predictor = 0
            pixels[index] = (pixels[index] + predictor) & 255
        previous = pixels
    return tuple(previous[x * 4:x * 4 + 4])


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

        def click(x, y):
            xdotool("mousemove", "--window", window, str(x), str(y))
            xdotool("click", "1")
            time.sleep(0.12)

        xdotool("mousemove", "--window", window, "85", "606")
        xdotool("click", "1")  # Set volume to about 25%.
        time.sleep(0.12)
        click(60, 470)   # Key on
        xdotool("mousemove", "--window", window, "154", "470")
        xdotool("mousedown", "1")
        time.sleep(0.25)
        xdotool("mouseup", "1")
        time.sleep(0.12)
        click(60, 516)  # Pedal up
        xdotool("mousemove", "--window", window, "20", "76")
        xdotool("mousedown", "1")
        time.sleep(0.12)
        xdotool("mousemove", "--window", window, "153", "76")
        time.sleep(0.15)
        xdotool("mouseup", "1")
        xdotool("mousemove", "--window", window, "118", "516")
        xdotool("mousedown", "1")
        time.sleep(0.12)
        xdotool("mousemove", "--window", window, "183", "516")
        time.sleep(0.15)
        xdotool("mouseup", "1")  # Set about 50 Nm on the load control.
        click(247, 516)  # Pause
        before = int(re.search(r"tick (\d+)", xdotool("getwindowname", window))[1])
        xdotool("key", "--window", window, "period")
        deadline = time.monotonic() + 2.0
        stepped = before
        while time.monotonic() < deadline:
            stepped = int(re.search(r"tick (\d+)",
                                    xdotool("getwindowname", window))[1])
            if stepped >= before + 9900:
                break
            time.sleep(0.02)
        assert stepped == before + 9900, (before, stepped)
        xdotool("key", "--window", window, "comma")
        edge_tick = stepped
        last_change = time.monotonic()
        deadline = last_change + 3.0
        while time.monotonic() < deadline:
            current = int(re.search(r"tick (\d+)",
                                    xdotool("getwindowname", window))[1])
            if current != edge_tick:
                edge_tick = current
                last_change = time.monotonic()
            if edge_tick > stepped and time.monotonic() - last_change > 0.12:
                break
            time.sleep(0.02)
        assert stepped < edge_tick <= stepped + 990000, (stepped, edge_tick)
        click(247, 516)  # Resume
        click(154, 562)  # Faster
        click(247, 562)  # Mute
        assert process.wait(timeout=20) == 0
        log.seek(0)
        output = log.read()
        if edge_tick < stepped + 990000:
            assert f'"type":"ignition_pin","tick":{edge_tick},' in output, (
                stepped, edge_tick)
        else:
            assert edge_tick == stepped + 990000, (stepped, edge_tick)
        lines = trace.read_text().splitlines()
        assert lines[0] == "sevel-ma17-controls-v2", lines[0]
        rows = [line.split() for line in lines[lines.index("controls") + 1:]]
        values = {(row[1], float(row[2])) for row in rows}
        for expected in {("key", 1.0), ("starter", 1.0),
                         ("starter", 0.0)}:
            assert expected in values, (expected, rows)
        pedal_values = [float(row[2]) for row in rows if row[1] == "pedal"]
        assert any(0.0 < value <= 0.002 for value in pedal_values), rows
        assert all(abs(b - a) <= 0.000501 for a, b in
                   zip(pedal_values, pedal_values[1:])), rows
        assert any(name == "pedal" and 0.012 < value < 0.014
                   for name, value in values), rows
        assert any(name == "load" and 5.0 < value < 15.0
                   for name, value in values), rows
        assert any(name == "load" and 45.0 < value < 55.0
                   for name, value in values), rows
        for expected in {("pause", 0.0), ("step_ticks", 9900.0),
                         ("step_ignition", 990000.0), ("resume", 0.0)}:
            assert expected in values, (expected, rows)
        assert png_pixel(image, 65, 617)[:3] == (99, 211, 220)
        assert png_pixel(image, 150, 617)[:3] == (29, 43, 55)
        assert png_pixel(image, 150, 532)[:3] == (99, 211, 220)
        state = re.search(r"\[LAB-STATE\] tick=(\d+).*state=([0-9a-f]+) "
                          r"events=\d+ event_hash=([0-9a-f]+)", output)
        assert state, "live final state missing"
        replay_trace = trace.with_name(trace.stem + "-replay.txt")
        replay = subprocess.run(
            [binary, rom, "--headless", "--capture-tick", state[1],
             "--replay-controls", str(trace), "--save-controls",
             str(replay_trace), "--capture-svg", str(trace.with_suffix(".svg"))],
            capture_output=True, text=True, timeout=20)
        assert replay.returncode == 0, replay.stderr[-2000:]
        replay_state = re.search(r"\[LAB-STATE\] tick=(\d+).*state=([0-9a-f]+) "
                                 r"events=\d+ event_hash=([0-9a-f]+)",
                                 replay.stdout)
        assert replay_state and replay_state.groups() == state.groups(), (
            state.groups(), replay_state.groups() if replay_state else None)
        assert replay_trace.read_bytes() == trace.read_bytes()
        print(f"[LAB-MOUSE] controls={len(rows)} trace={trace}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-3000:], file=sys.stderr)
        raise
