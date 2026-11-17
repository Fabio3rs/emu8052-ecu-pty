"""Exercise the live Lab button bar against the original ROM under Xvfb."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


binary, rom, trace_path = sys.argv[1:4]
trace = Path(trace_path)
trace.unlink(missing_ok=True)
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
command = [binary, rom, "--live", "--window-frames", "300",
           "--save-controls", trace_path]


def xdotool(*args):
    return subprocess.run(["xdotool", *args], check=True, text=True,
                          capture_output=True).stdout.strip()


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

        def click(x):
            xdotool("mousemove", "--window", window, str(x), "522")
            xdotool("click", "1")
            time.sleep(0.12)

        click(65)   # Key on
        xdotool("mousemove", "--window", window, "170", "522")
        xdotool("mousedown", "1")
        time.sleep(0.25)
        xdotool("mouseup", "1")
        time.sleep(0.12)
        click(380)  # Pedal up
        xdotool("mousemove", "--window", window, "1000", "458")
        xdotool("mousedown", "1")
        time.sleep(0.12)
        xdotool("mousemove", "--window", window, "1126", "458")
        time.sleep(0.15)
        xdotool("mouseup", "1")
        click(485)  # Load on
        click(590)  # Pause
        click(590)  # Resume
        click(800)  # Faster
        click(910)  # Mute
        assert process.wait(timeout=20) == 0
        lines = trace.read_text().splitlines()
        assert lines[0] == "sevel-ma17-controls-v2", lines[0]
        rows = [line.split() for line in lines[lines.index("controls") + 1:]]
        values = {(row[1], float(row[2])) for row in rows}
        for expected in {("key", 1.0), ("starter", 1.0),
                         ("starter", 0.0), ("pedal", 0.001),
                         ("load", 24.0)}:
            assert expected in values, (expected, rows)
        assert any(name == "pedal" and 0.012 < value < 0.014
                   for name, value in values), rows
        print(f"[LAB-MOUSE] controls={len(rows)} trace={trace}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-3000:], file=sys.stderr)
        raise
