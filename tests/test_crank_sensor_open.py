"""A physical wheel keeps turning during an electrical crank-sensor open."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "16000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"]
open_wire = ["--crank-sensor-open-tick", "10000000"]
restore = ["--crank-sensor-restore-tick", "10150000"]


def run(args):
    result = subprocess.run(args, env=environment, text=True,
                            capture_output=True, timeout=80, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    summary = re.search(r"\[PHYSICAL-CRANK\] ([^\n]+)", result.stdout)
    diagnostic = re.search(r"\[PHYSICAL-DIAG\] ([^\n]+)", result.stdout)
    assert summary and diagnostic
    return (events,
            dict(part.split("=") for part in summary.group(1).split()),
            dict(part.split("=") for part in diagnostic.group(1).split()))


for invalid in (restore, ["--crank-sensor-open-tick", "16000000"],
                open_wire + ["--crank-sensor-restore-tick", "9999999"]):
    assert subprocess.run(base + invalid, env=environment, text=True,
                          capture_output=True, timeout=5).returncode == 2
assert subprocess.run([binary, firmware] + open_wire, env=environment,
                      text=True, capture_output=True, timeout=5).returncode == 2

normal, normal_crank, _ = run(base)
fault, fault_crank, fault_diag = run(base + open_wire)
recovered, recovered_crank, recovered_diag = run(base + open_wire + restore)
assert [event for event in normal if event["tick"] < 10000000] == [
    event for event in fault if event["tick"] < 10000000] == [
        event for event in recovered if event["tick"] < 10000000]

def event_ticks(events, kind):
    return [event["tick"] for event in events if event["type"] == kind]


assert event_ticks(fault, "crank_sensor_open") == [10000000]
assert event_ticks(recovered, "crank_sensor_open") == [10000000]
assert event_ticks(recovered, "crank_sensor_restore") == [10150000]
assert any(event["type"] == "crank_gap" and
           10000000 < event["tick"] < 11000000 and event["rpm"] > 0
           for event in fault)
assert not any(event["type"] == "cc3_pin" and not event["high"] and
               event["tick"] >= 10000000 for event in fault)
assert float(fault_crank["rpm"]) == 0.0 and fault_crank["ram47"] == "0"
assert fault_diag["f850"] == "2"  # Raw value after the engine has stopped.
assert any(event["type"] == "cc3_pin" and not event["high"] and
           event["tick"] > 10150000 for event in recovered)
assert float(normal_crank["rpm"]) > 700
assert float(recovered_crank["rpm"]) > 700
assert int(recovered_crank["ram47"]) > 0
assert all(recovered_diag[key] == "0" for key in
           ("ram27", "f84e", "f84f", "f850", "f85e", "f85f", "f860"))

finer, finer_crank, finer_diag = run(
    base + open_wire + restore + ["--fluid-step-ticks", "495"])
assert abs(float(finer_crank["rpm"]) -
           float(recovered_crank["rpm"])) < 5.0
assert sum(event["type"] == "cc3_pin" and not event["high"]
           for event in finer) == sum(event["type"] == "cc3_pin" and
                                   not event["high"] for event in recovered)
assert all(finer_diag[key] == "0" for key in
           ("ram27", "f84e", "f84f", "f850", "f85e", "f85f", "f860"))
