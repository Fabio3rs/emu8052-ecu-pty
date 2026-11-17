"""Check that optional donor GPU preview preserves the main Lab window."""

import os
from pathlib import Path
import re
import struct
import subprocess
import sys


xvfb, binary, rom, image_path = sys.argv[1:5]
command = [xvfb, "-a", binary, rom, "--live", "--auto-start",
           "--gpu-preview", "--window-frames", "90", "--stop-ticks",
           "2000000", "--capture-tick", "600000", "--screenshot",
           image_path]
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
completed = subprocess.run(command, env=environment, text=True,
                           capture_output=True, timeout=30)
output = completed.stdout + completed.stderr
image = Path(image_path)
png = image.read_bytes() if image.is_file() else b""
size = struct.unpack(">II", png[16:24]) if len(png) >= 24 else None
gpu_result = ("[LAB-GPU] preview_ready=1" in output or
              "SDL GPU preview unavailable:" in output)
renderer = re.search(r"\[LAB-VIDEO\] renderer=([^\s]+)", output)
if (completed.returncode != 0 or not gpu_result or not renderer or
        size != (1280, 720)):
    raise AssertionError(output[-3000:])
print(f"[LAB-GPU-TEST] preview_ready={'[LAB-GPU]' in output} "
      f"renderer={renderer.group(1)} png={image} size={size}")
