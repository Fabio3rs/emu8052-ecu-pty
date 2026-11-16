"""End-to-end starter torque to Fiat ROM RPM, with no wall-clock pacing."""

import os
import json
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(starter_ticks, stop_ticks=1485000):
    result = subprocess.run(
        [binary, firmware, "--physical-crank", "--starter-ticks",
         str(starter_ticks), "--stop-ticks", str(stop_ticks)],
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
assert int(rising) > 58 and rising == falling
assert int(ram47) > 0 and abs(int(ram47) * 25 - float(rpm)) < 50
gaps = [json.loads(line) for line in log.splitlines()
        if line.startswith('{"type":"crank_gap"')]
assert len(gaps) == int(missing)
assert [event["position"] for event in gaps] == [58, 59] * (len(gaps) // 2)
assert all(a["tick"] < b["tick"] for a, b in zip(gaps, gaps[1:]))
assert re.search(r"\[COSIM-RPM\] tick=\d+ physical_rpm=[\d.]+ "
                 r"ram47=[1-9]\d* pc=0EA5", log), log[-2000:]

no_starter, _ = run(1)
assert float(no_starter[1]) == 0.0 and int(no_starter[3]) == 0
assert int(no_starter[5]) == 0 and int(no_starter[6]) == 0

coast, coast_log = run(198000, 3000000)
assert float(coast[1]) == 0.0 and int(coast[6]) == 0
assert int(coast[3]) > 58
assert re.search(r"\[COSIM-RPM\] tick=\d+ physical_rpm=0\.000 "
                 r"ram47=0 pc=", coast_log)
