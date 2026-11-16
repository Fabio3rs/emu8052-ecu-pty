"""Fiat ROM response to an independently sourced TPS electrical profile."""

import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "20000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"]


def run(extra, stop_ticks=20000000):
    args = base.copy()
    args[args.index("--stop-ticks") + 1] = str(stop_ticks)
    result = subprocess.run(
        args + extra, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=45, check=True)

    def summary(name):
        match = re.search(rf"\[PHYSICAL-{name}\] ([^\n]+)", result.stdout)
        assert match, result.stdout[-2000:]
        return dict(part.split("=") for part in match.group(1).split())

    return {name: summary(name) for name in
            ("CRANK", "TPS", "INTAKE", "DIAG", "IDLE")}


invalid = subprocess.run(
    [binary, firmware, "--tps-bench-profile"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid.returncode == 2

default = run([])
bench = run(["--tps-bench-profile"])
for result in (default, bench):
    assert 700 < float(result["CRANK"]["rpm"]) < 1200
    assert int(result["INTAKE"]["cc3_pulses"]) > 500
    assert result["TPS"]["contact"] == "1"
    assert result["TPS"]["fault85"] == result["TPS"]["fault4f"] == "0"
    assert result["DIAG"]["ram27"] == result["DIAG"]["f84e"] == "0"

assert bench["TPS"]["ram60"] == "0"
assert int(bench["TPS"]["ram66"]) < int(default["TPS"]["ram66"])
assert int(bench["TPS"]["ram6f"]) < int(default["TPS"]["ram6f"])
assert float(bench["IDLE"]["stem_m"]) > float(default["IDLE"]["stem_m"])

# 9–12 mm spans approximately 18–25 degrees through the two-track overlap.
# The earlier straight-line track 2 fit raised ROM TPS fault bits at 10/11 mm.
overlap = [run(["--tps-bench-profile", "--pedal-step-tick", "1000000",
                "--pedal-mm", str(mm)], 4000000) for mm in (9, 10, 11, 12)]
for result in overlap:
    assert result["TPS"]["contact"] == "0"
    assert result["TPS"]["ram28"] == "0"
    assert result["TPS"]["fault85"] == result["TPS"]["fault4f"] == "0"
assert all(int(a["TPS"]["ram60"]) < int(b["TPS"]["ram60"])
           for a, b in zip(overlap, overlap[1:]))
assert all(int(a["TPS"]["ram66"]) < int(b["TPS"]["ram66"])
           for a, b in zip(overlap, overlap[1:]))
assert 0.45 < float(overlap[2]["TPS"]["adc0_v"]) < 0.70
