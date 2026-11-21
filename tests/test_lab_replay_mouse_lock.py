"""Verify that GUI replay rejects mouse changes to physical controls."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


binary, rom, source_path, saved_path = sys.argv[1:5]
source = Path(source_path)
saved = Path(saved_path)
saved.unlink(missing_ok=True)
screenshot = saved.with_suffix(".png")
screenshot.unlink(missing_ok=True)
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
command = [binary, rom, "--live", "--window-frames", "240000",
           "--stop-ticks", "3000000", "--replay-controls", str(source),
           "--save-controls", str(saved), "--capture-tick", "500000",
           "--screenshot", str(screenshot)]

with tempfile.TemporaryFile(mode="w+") as log:
    process = subprocess.Popen(command, env=environment, stdout=log,
                               stderr=subprocess.STDOUT)
    try:
        window = ""
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and process.poll() is None:
            found = subprocess.run(["xdotool", "search", "--name",
                                    "FIAT TIPO"], text=True,
                                   capture_output=True)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[-1]
                break
            time.sleep(0.05)
        assert window, "Lab replay window did not appear"
        for x, y in ((65, 470), (170, 470), (275, 470),
                     (65, 516), (170, 516)):
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(x), str(y), "click", "1"], check=True,
                           capture_output=True)
            time.sleep(0.10)
        assert process.wait(timeout=20) == 0
        assert saved.read_bytes() == source.read_bytes(), saved.read_text()
        assert screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        print(f"[LAB-REPLAY-MOUSE] trace unchanged: {saved}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-3000:], file=sys.stderr)
        raise
