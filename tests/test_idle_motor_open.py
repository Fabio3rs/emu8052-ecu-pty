"""Open the candidate idle motor circuit without changing ECU commands."""

import json
import os
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "20000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
        "--pedal-release-tick", "12000000", "--pedal-mm", "8"]
fault = ["--idle-motor-disconnect-tick", "10000000",
         "--idle-motor-reconnect-tick", "12000000"]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(extra):
    result = subprocess.run(base + extra, env=environment, text=True,
                            capture_output=True, timeout=55, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    by_type = {kind: [event for event in events if event["type"] == kind]
               for kind in ("idle_actuator", "bridge_candidate",
                            "idle_fault_raw", "idle_motor_disconnect",
                            "idle_motor_reconnect")}
    diagnostic = next(line for line in result.stdout.splitlines()
                      if line.startswith("[PHYSICAL-DIAG]"))
    return by_type, dict(part.split("=") for part in diagnostic.split()[1:])


assert subprocess.run(base + [fault[2], fault[3]], env=environment,
                      text=True, capture_output=True, timeout=5).returncode == 2
assert subprocess.run(base + fault + ["--idle-motor-reconnect-tick", "9000000"],
                      env=environment, text=True, capture_output=True,
                      timeout=5).returncode == 2
without_bridge = base.copy()
without_bridge.remove("--idle-bridge-p15-p16")
without_bridge.remove("--idle-contact-p46")
stop_setting = without_bridge.index("--idle-min-stop-mrad")
del without_bridge[stop_setting:stop_setting + 2]
assert subprocess.run(without_bridge + fault, env=environment, text=True,
                      capture_output=True, timeout=5).returncode == 2

normal, normal_diag = run([])
open_motor, open_diag = run(fault)
assert [(event["type"], event["tick"]) for kind in
        ("idle_motor_disconnect", "idle_motor_reconnect")
        for event in open_motor[kind]] == [
            ("idle_motor_disconnect", 10000000),
            ("idle_motor_reconnect", 12000000)]
assert [event for event in normal["idle_actuator"]
        if event["tick"] < 10000000] == [
            event for event in open_motor["idle_actuator"]
            if event["tick"] < 10000000]

normal_at = {event["tick"]: event for event in normal["idle_actuator"]}
open_at = {event["tick"]: event for event in open_motor["idle_actuator"]}
for tick in (10890000, 11880000):
    assert normal_at[tick]["stem_m"] > open_at[tick]["stem_m"] + 0.003
    assert normal_at[tick]["angle_rad"] == open_at[tick]["angle_rad"] == 0.28
    assert not normal_at[tick]["contact"] and not open_at[tick]["contact"]
    assert normal_at[tick]["ram66"] == open_at[tick]["ram66"] == 157
assert open_at[12870000]["stem_m"] > open_at[11880000]["stem_m"]

def during_pedal(events):
    return [event for event in events
            if 10000000 <= event["tick"] < 12000000]


assert during_pedal(normal["bridge_candidate"]) == during_pedal(
    open_motor["bridge_candidate"])
assert during_pedal(normal["idle_fault_raw"]) == during_pedal(
    open_motor["idle_fault_raw"])
assert any(event["pc"] == 0x41E5 and event["f84e"] == 10
           for event in during_pedal(open_motor["idle_fault_raw"]))
assert normal_diag["f84e"] == open_diag["f84e"] == "0"
assert normal_diag["f85e"] == open_diag["f85e"] == "10"
