"""Fuel composition changes the physical lambda input and Fiat CC3 response."""

import json
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


def run(percent):
    result = subprocess.run(
        base + ["--ethanol-percent", str(percent)],
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=45, check=True)
    lambda_samples = {
        sample["tick"]: sample
        for line in result.stdout.splitlines()
        if line.startswith('{"type":"lambda"')
        for sample in [json.loads(line)]
    }
    match = re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", result.stdout)
    assert match
    intake = dict(part.split("=") for part in match.group(1).split())
    return lambda_samples, intake


# ADC7, CC3, idle wiring and lambda ADC gain remain conditional bindings.
gasoline, gasoline_intake = run(0)
e25, e25_intake = run(25)
assert e25[4950000]["physical"] > gasoline[4950000]["physical"] + 0.05
assert e25[4950000]["voltage_v"] < gasoline[4950000]["voltage_v"]
assert float(e25_intake["injected_kg"]) > (
    1.05 * float(gasoline_intake["injected_kg"]))
gasoline_width = (int(gasoline_intake["on_ticks"]) /
                  int(gasoline_intake["cc3_pulses"]))
e25_width = (int(e25_intake["on_ticks"]) /
             int(e25_intake["cc3_pulses"]))
assert e25_width > gasoline_width * 1.02
assert 30000 < float(e25_intake["pressure_pa"]) < 60000
print("E25 physical lambda -> ROM CC3 response (conditional bindings)")
