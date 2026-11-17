"""Compare one ROM replay across headless, GUI frame rates and audio modes."""

import os
from pathlib import Path
import re
import subprocess
import sys


binary, rom, trace, xvfb, output_dir = sys.argv[1:]
scenario = ["--idle-contact-p46", "--idle-bridge-p15-p16",
            "--adc7-mv", "1232"]
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"


def run(args):
    completed = subprocess.run(args, env=environment, text=True,
                               capture_output=True, timeout=25)
    assert completed.returncode == 0, (args, completed.stdout[-2000:],
                                       completed.stderr[-2000:])
    states = re.findall(r"^\[LAB-STATE\] .+$", completed.stdout, re.MULTILINE)
    assert len(states) == 1, completed.stdout[-2000:]
    return states[0]


baseline = run([binary, rom, "--headless", "--capture-tick", "1200000",
                "--replay-controls", trace, "--capture-svg",
                str(Path(output_dir) / "sevel-mode-compare.svg"), *scenario])
assert "tick=1200000 " in baseline and "overflow=0" in baseline
assert re.search(r"events=([1-9]\d*) ", baseline), baseline

for delay, audio in [(8, False), (32, False), (32, True)]:
    command = [xvfb, "-a", binary, rom, "--live", "--replay-controls", trace,
               "--stop-ticks", "1200000", "--window-frames", "300",
               "--frame-delay-ms", str(delay), *scenario]
    if not audio:
        command.append("--no-audio")
    actual = run(command)
    assert actual == baseline, (delay, audio, baseline, actual)

print("[LAB-MODE-DETERMINISM] headless/gui 8/32 ms audio off/on: "
      "state and events identical")
