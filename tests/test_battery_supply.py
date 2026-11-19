"""One physical supply feeds Fiat ADC1, injector dead time and lambda heater."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(starter_ticks, stop_ticks, millivolts, relay=False):
    command = [binary, firmware, "--physical-crank", "--starter-ticks",
               str(starter_ticks), "--stop-ticks", str(stop_ticks),
               "--adc7-mv", "1232", "--battery-mv", str(millivolts)]
    if relay:
        command.append("--pump-relay-p34")
    result = subprocess.run(command, env=environment, text=True,
                            capture_output=True, timeout=30, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    thermal = next(event for event in events
                   if event["type"] == "thermal")
    lambdas = [event for event in events if event["type"] == "lambda"]
    intake = re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", result.stdout)
    assert intake and lambdas
    summary = dict(part.split("=") for part in intake.group(1).split())
    return thermal, lambdas, summary


for invalid in (5999, 16001):
    command = [binary, firmware, "--physical-crank", "--starter-ticks",
               "1", "--stop-ticks", "2000000", "--battery-mv",
               str(invalid)]
    assert subprocess.run(command, env=environment, text=True,
                          capture_output=True, timeout=5).returncode == 2

low_idle, low_lambda, _ = run(1, 2000000, 10000, relay=True)
high_idle, high_lambda, _ = run(1, 2000000, 14500, relay=True)
assert low_idle["ram61"] == 133 and high_idle["ram61"] == 193
assert low_lambda[0]["temperature_c"] < high_lambda[0]["temperature_c"]
assert high_lambda[0]["temperature_c"] - low_lambda[0]["temperature_c"] > 40
assert all(not event["valid"] for event in low_lambda + high_lambda)

low_running, _, low_intake = run(495000, 4000000, 10000)
high_running, _, high_intake = run(495000, 4000000, 14500)
assert low_running["ram61"] == 133 and high_running["ram61"] == 193
# The pulse count is set by the ROM, not by the supply: it must match across
# voltages. The absolute count (150 before ca6f99c, 55 now) follows engine
# speed over the window, so only require that injection really happened.
assert low_intake["cc3_pulses"] == high_intake["cc3_pulses"], (low_intake["cc3_pulses"], high_intake["cc3_pulses"], low_running, high_running)
assert int(low_intake["cc3_pulses"]) > 20
assert float(low_intake["injected_kg"]) < float(high_intake["injected_kg"])
print("physical supply -> Fiat ADC1, injector mass and lambda heater")
