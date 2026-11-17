"""Capture the live SDL window after shrinking to the button-bar minimum."""

import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time


binary, rom, image_path = sys.argv[1:4]
image = Path(image_path)
image.unlink(missing_ok=True)
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
command = [binary, rom, "--live", "--window-frames", "240",
           "--capture-tick", "250000", "--screenshot", str(image)]

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
        subprocess.run(["xdotool", "windowsize", window, "900", "620"],
                       check=True, capture_output=True)
        assert process.wait(timeout=20) == 0
        header = image.read_bytes()[:24]
        assert header.startswith(b"\x89PNG\r\n\x1a\n"), header
        size = struct.unpack(">II", header[16:24])
        assert size == (900, 620), size
        print(f"[LAB-RESIZE] png={image} size={size}")
    except Exception:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read()[-3000:], file=sys.stderr)
        raise
