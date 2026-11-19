"""Exercise the live SDL audio worker with the original ROM under Xvfb."""

import os
from pathlib import Path
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


xvfb, binary, rom, image = sys.argv[1:5]
command = [xvfb, "-a", binary, rom, "--live", "--auto-start",
           "--window-frames", "180", "--capture-tick", "600000",
           "--screenshot", image, "--adc7-mv", "1232",
           "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c",
           "90", "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
           "--lambda-adc-gain", "5"]
environment = os.environ.copy()
environment["SDL_AUDIODRIVER"] = "dummy"
completed = subprocess.run(command, env=environment, text=True,
                           capture_output=True, timeout=30)
output = completed.stdout + completed.stderr
status = re.search(r"\[LAB-LIVE\] audio_dropped_samples=(\d+) "
                   r"audio_empty_queue=(\d+) audio_write_errors=(\d+) "
                   r"audio_mode_discarded_samples=(\d+) "
                   r"audio_device_need_samples=(\d+) "
                   r"audio_pcm_max_peak=(\d+)",
                   output)
fuel = re.findall(r"cc3_pulses=(\d+)", output)
if (completed.returncode != 0 or not Path(image).is_file() or
        not status or int(status.group(3)) != 0 or
        int(status.group(4)) != 0 or
        int(status.group(6)) == 0 or
        not fuel or int(fuel[-1]) <= 0):
    raise AssertionError(output[-3000:])
print(f"[LAB-LIVE-AUDIO] cc3={fuel[-1]} dropped={status.group(1)} "
      f"empty_queue={status.group(2)} mode={status.group(4)} "
      f"need={status.group(5)} pcm_peak={status.group(6)} png={image}")
