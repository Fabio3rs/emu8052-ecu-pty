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
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
command = [binary, rom, "--live", "--window-frames", "240",
           "--replay-controls", str(source), "--save-controls", str(saved)]

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
        assert window, "Lab replay window did not appear"
        for x in (65, 170, 275, 380, 485):
            subprocess.run(["xdotool", "mousemove", "--window", window,
                            str(x), "522", "click", "1"], check=True,
                           capture_output=True)
            time.sleep(0.10)
        assert process.wait(timeout=20) == 0
        assert saved.read_bytes() == source.read_bytes(), saved.read_text()
        print(f"[LAB-REPLAY-MOUSE] trace unchanged: {saved}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-3000:], file=sys.stderr)
        raise
