"""ROM loop: integrated indicated energy per pulse (GOAL_DYNO_ROM 1.4). LLM-written (Claude).

The per-tick integral of combustion.torque_nm() must equal T * 2 rad summed over every
scheduled pulse (minus the unfinished tail of the last one) within 0.1 %.
"""
import os
import re
import subprocess
import sys

binary, rom = sys.argv[1:3]
out = subprocess.run(
    [binary, rom, "--physical-crank", "--starter-ticks", "495000", "--stop-ticks", "9000000",
     "--adc7-mv", "1232", "--idle-bridge-p15-p16", "--idle-contact-p46", "--tps-bench-profile",
     "--idle-motor-speed-mm-s", "50", "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
     "--lambda-adc-gain", "5", "--coolant-c", "90", "--accessory-load"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")}, text=True, capture_output=True,
    timeout=120, check=True).stdout
m = re.search(r"\[PHYSICAL-ENERGY\] scheduled_j=([\d.]+) tail_j=([\d.]+) "
              r"integrated_j=([\d.]+) burns=(\d+)", out)
assert m, out[-1500:]
scheduled, tail, integrated, burns = float(m[1]), float(m[2]), float(m[3]), int(m[4])
assert burns > 100, burns
rel = abs(integrated - (scheduled - tail)) / (scheduled - tail)
assert rel < 0.001, (scheduled, tail, integrated, rel)
print(f"rom pulse energy ok: {burns} pulses, relative error {rel:.2e}")
