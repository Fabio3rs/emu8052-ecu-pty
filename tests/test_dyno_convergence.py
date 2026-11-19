"""Dyno time-step convergence (GOAL_DYNO_ROM 1.4). LLM-written (Claude).

|P(100 us) - P(1 us)| / P(1 us) < 0.2 % at 3000 and 6000 rpm for MBT and 30 deg fixed,
and P(MBT) >= P(fixed) - 0.1 % at every point (MBT is the maximum by construction).
"""
import csv
import io
import subprocess
import sys

dyno = sys.argv[1]
COMMON = ["--ethanol", "22", "--throttle-leak-mm2", "9", "--cycles", "40",
          "--rpm-min", "3000", "--rpm-max", "6000", "--rpm-step", "3000"]


def power(dt, extra):
    out = subprocess.run([dyno, *COMMON, "--dt-us", str(dt), *extra], capture_output=True,
                         text=True, check=True).stdout
    return {int(float(r["rpm"])): float(r["power_kw"]) for r in csv.DictReader(io.StringIO(out))}


mbt = {dt: power(dt, []) for dt in (100, 1)}
fixed = {dt: power(dt, ["--fixed-spark", "--spark-btdc-deg", "30"]) for dt in (100, 1)}
for name, series in (("MBT", mbt), ("fixed30", fixed)):
    for rpm in (3000, 6000):
        rel = abs(series[100][rpm] - series[1][rpm]) / series[1][rpm]
        assert rel < 0.002, (name, rpm, series[100][rpm], series[1][rpm], rel)
for dt in (100, 1):
    for rpm in (3000, 6000):
        assert mbt[dt][rpm] >= fixed[dt][rpm] * (1 - 0.001), (dt, rpm, mbt[dt][rpm], fixed[dt][rpm])
print("dyno convergence ok", mbt, fixed)
