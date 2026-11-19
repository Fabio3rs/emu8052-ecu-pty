"""End-to-end starter torque to Fiat ROM RPM, with no wall-clock pacing."""

import os
import json
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


# The ROM only lets the engine catch with the ADC7 input at its normal level
# (the value every other physical test uses). The pre-ca6f99c starter
# (constant 50 N-m, no speed limit) cranked fast enough to catch without it;
# the series-motor starter cranks at 400-520 rpm and honours the gate.
ADC7_MV = "1232"


def run(starter_ticks, stop_ticks=1485000, leak="9"):
    result = subprocess.run(
        [binary, firmware, "--physical-crank", "--starter-ticks",
         str(starter_ticks), "--stop-ticks", str(stop_ticks),
         "--adc7-mv", ADC7_MV, "--throttle-leak-mm2", leak],  # compressible plant: 1 mm2 default
        # gives no air for a cold start (see tests/sevel_preset.py)
        env=env, text=True, capture_output=True, timeout=20,
        check=True,
    )
    output = result.stdout + result.stderr
    summary = re.search(
        r"\[PHYSICAL-CRANK\] ticks=(\d+) rpm=([\d.]+) "
        r"angle_rad=([\d.]+) rising=(\d+) falling=(\d+) "
        r"missing=(\d+) ram47=(\d+)",
        output,
    )
    assert summary, output[-2000:]
    return summary.groups(), output


first, log = run(495000)
repeat, _ = run(495000)
assert first == repeat, (first, repeat)
ticks, rpm, angle, rising, falling, missing, ram47 = first
assert int(ticks) == 1485000
assert float(rpm) > 300 and float(angle) > 6.28
# A tooth can be mid-pulse at the stop tick, so the edge counts may differ by
# one (947/946 measured); equality only held by coincidence of the stop tick.
assert int(rising) > 58 and abs(int(rising) - int(falling)) <= 1
assert int(ram47) > 0 and abs(int(ram47) * 25 - float(rpm)) < 50
gaps = [json.loads(line) for line in log.splitlines()
        if line.startswith('{"type":"crank_gap"')]
assert len(gaps) == int(missing)
# The stop tick can fall between the two missing positions of the last gap (58 seen,
# 59 not yet), so an odd list ending in 58 is valid; equality only held by coincidence.
positions = [event["position"] for event in gaps]
assert positions == ([58, 59] * (len(positions) // 2) + [58] * (len(positions) % 2)), positions
assert all(a["tick"] < b["tick"] for a, b in zip(gaps, gaps[1:]))
assert re.search(r"\[COSIM-RPM\] tick=\d+ physical_rpm=[\d.]+ "
                 r"ram47=[1-9]\d* pc=0EA5", log), log[-2000:]

no_starter, _ = run(1)
assert float(no_starter[1]) == 0.0 and int(no_starter[3]) == 0
assert int(no_starter[5]) == 0 and int(no_starter[6]) == 0

# Old starter time: 198000 ticks. The cold engine now has oil-viscosity friction
# (x1.56 at 20 C, F-43), so 0.2 s of starter no longer spins the wheel enough for the
# ROM to latch a speed (RAM47 never becomes non-zero, so there is nothing to clear).
# 300000 ticks (measured: RAM47 set, then cleared at tick 2.198 M) keeps the scenario.
coast, coast_log = run(300000, 3000000, "1")  # leak 1: the 9 mm2 start leak lets it idle
assert float(coast[1]) == 0.0 and int(coast[6]) == 0
assert int(coast[3]) > 58
# The ROM clears RAM47 when the last teeth stop arriving; the wheel may still
# be creeping then (0.029 rpm measured), so require "stopped", not exactly 0.
assert any(float(m.group(1)) < 5.0 for m in re.finditer(
    r"\[COSIM-RPM\] tick=\d+ physical_rpm=([\d.]+) ram47=0 pc=",
    coast_log)), coast_log[-2000:]
