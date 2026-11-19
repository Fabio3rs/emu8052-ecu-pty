"""Hold the candidate idle-switch input closed during a physical cable step."""

import json
import os
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "20000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5", "--tps-bench-profile",
        "--pedal-step-tick", "10000000", "--pedal-release-tick", "12000000",
        "--pedal-mm", "8"]
fault = ["--idle-contact-closed-tick", "10000000",
         "--idle-contact-restore-tick", "12000000"]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(extra, trace=False):
    run_env = environment.copy()
    if trace:
        run_env.update(MA17_TRACE_PC="1", MA17_TRACE_IDLE_CONTACT_CHECK="1")
    result = subprocess.run(base + extra, env=run_env, text=True,
                            capture_output=True, timeout=55, check=True)
    states = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":"idle_actuator"')]
    faults = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":"idle_fault_raw"')]
    summary = next(line for line in result.stdout.splitlines()
                   if line.startswith("[PHYSICAL-DIAG]"))
    fields = dict(part.split("=") for part in summary.split()[1:])
    return states, faults, fields, result.stderr


invalid = base.copy()
invalid.remove("--idle-contact-p46")
assert subprocess.run(invalid + fault, env=environment, text=True,
                      capture_output=True, timeout=5).returncode == 2
assert subprocess.run(base + fault +
                      ["--idle-contact-open-tick", "10000000"],
                      env=environment, text=True, capture_output=True,
                      timeout=5).returncode == 2

normal, normal_faults, normal_diag, _ = run([])
closed, closed_faults, closed_diag, closed_trace = run(fault, trace=True)
assert [state for state in normal if state["tick"] < 10000000] == [
    state for state in closed if state["tick"] < 10000000]
normal_by_tick = {state["tick"]: state for state in normal}
closed_by_tick = {state["tick"]: state for state in closed}
for tick in (10890000, 11880000):
    assert not normal_by_tick[tick]["contact"]
    assert not closed_by_tick[tick]["contact"]
    assert normal_by_tick[tick]["angle_rad"] == closed_by_tick[tick]["angle_rad"]
assert normal_by_tick[11880000]["stem_m"] > 0.012
assert closed_by_tick[11880000]["stem_m"] == 0.0

def during_pedal(events, pc):
    return [event for event in events if 10000000 <= event["tick"] < 12000000
            and event["pc"] == pc]


assert during_pedal(normal_faults, 0x2B42)
assert during_pedal(normal_faults, 0x2B49)
assert not during_pedal(closed_faults, 0x2B42)
assert not during_pedal(closed_faults, 0x2B49)
assert during_pedal(closed_faults, 0x2C0C)
first_arm = during_pedal(closed_faults, 0x2C0C)[0]
first_clear = next(event for event in closed_faults
                   if event["tick"] > first_arm["tick"] and
                   event["pc"] == 0x2C19)
retained = next(event for event in during_pedal(closed_faults, 0x2C0C)
                if event["f83b"] == 0)
published = next(event for event in closed_faults
                 if event["pc"] == 0x41E5 and event["f84e"] == 8)
recovered = next(event for event in closed_faults
                 if event["tick"] > 12000000 and event["pc"] == 0x41E5
                 and event["f84e"] == 0)
assert first_arm["f83b"] == 50
assert first_clear["tick"] - first_arm["tick"] < 10
assert 10500000 < retained["tick"] < published["tick"] < 12000000
assert recovered["tick"] > 12000000
checks = [(int(match[1]), int(match[2], 16), int(match[3], 16))
          for line in closed_trace.splitlines()
          if (match := re.search(
              r"\[IDLE-CONTACT-CHECK\] tick=(\d+) PC=2BC2 .*"
              r"F83A=([0-9A-F]{2}) F83B=([0-9A-F]{2})", line))]
assert checks[0][1:] == (15, 50)
zero_a = next(tick for tick, a, b in checks if a == 0)
zero_b = next(tick for tick, a, b in checks if b == 0)
assert 10000000 < zero_a < zero_b < retained["tick"]
assert normal_diag["f84e"] == closed_diag["f84e"] == "0"
assert normal_diag["f85e"] == "10"
assert closed_diag["f85e"] == "8"
