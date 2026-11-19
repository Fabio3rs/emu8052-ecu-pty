"""An induced stall lets exhaust flow stop and the lambda sensor cool."""

import json
import os
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
command = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
           "--stop-ticks", "50000000", "--adc7-mv", "1232",
           "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
           "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
           "--load-step-tick", "10000000", "--load-nm", "100",
           "--lambda-adc-gain", "5"]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run():
    return subprocess.run(command, env=environment, text=True,
                          capture_output=True, timeout=70, check=True).stdout


def physical_lines(text):
    # PTY allocation may change while other CTest jobs run.
    return [line for line in text.splitlines()
            if line.startswith('{"type":') or line.startswith("[PHYSICAL-")]


output = run()
assert physical_lines(output) == physical_lines(run())
summary = re.search(r"\[PHYSICAL-CRANK\] ticks=50000000 rpm=([\d.]+) "
                    r"angle_rad=[\d.]+ rising=\d+ falling=\d+ "
                    r"missing=\d+ ram47=(\d+)", output)
assert summary and float(summary.group(1)) == 0 and int(summary.group(2)) == 0
events = [json.loads(line) for line in output.splitlines()
          if line.startswith('{"type":')]
p54 = [event for event in events if event["type"] == "p54_raw"]
assert [(event["pc"], event["p54"]) for event in p54] == [
    (0x317A, 1), (0x3176, 0)]
assert p54[0]["ram47"] > 0 and p54[1]["ram47"] == 0
assert p54[0]["tick"] < 1000000 and p54[1]["tick"] > 30000000
by_type = {kind: {event["tick"]: event for event in events
                  if event["type"] == kind}
           for kind in ("combustion", "lambda", "diagnostic")}
before = by_type["lambda"][9900000]
stopped = by_type["lambda"][10890000]
# Old: the sample 9 s after the stall (19.8 M) already had the sensor below 300 C. The
# calibrated plant stalls slightly differently and the ROM keeps the heater relay on
# longer (438 C at 19.8 M), so the cooled state is read at 29.7 M instead.
cooled = by_type["lambda"][29700000]
late = by_type["lambda"][49500000]

assert by_type["combustion"][9900000]["rpm"] > 700
assert all(by_type["combustion"][tick]["rpm"] == 0
           for tick in (10890000, 19800000, 29700000, 49500000))
assert before["valid"] and before["temperature_c"] > 300
assert stopped["valid"] and stopped["temperature_c"] > 300
assert not cooled["valid"] and cooled["temperature_c"] < 300, (before, stopped, cooled)
assert not late["valid"] and late["temperature_c"] < 50
assert abs(cooled["voltage_v"] - 0.45) < 1e-6
assert abs(cooled["adc5_pin_v"] - 2.25) < 0.001
assert before["ram65"] != cooled["ram65"] == late["ram65"] == 115
# Keep fault banks raw: induced load and unverified bindings are not a DTC spec.
assert by_type["diagnostic"][49500000]["f84e"] == 0
print("stall -> exhaust cooldown -> ADC5/RAM65, deterministic")
