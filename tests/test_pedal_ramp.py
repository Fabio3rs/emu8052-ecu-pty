"""A finite cable motion avoids a diagnosis triggered by an instant step."""

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
        "--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
        "--pedal-release-tick", "12000000", "--pedal-mm", "8"]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(extra):
    result = subprocess.run(base + extra, env=environment, text=True,
                            capture_output=True, timeout=50, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    diag = [event for event in events if event["type"] == "diagnostic"]
    pedal = [event for event in events if event["type"] in
             ("pedal_command", "pedal", "pedal_release")]
    intake = re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", result.stdout)
    assert intake
    fields = dict(part.split("=") for part in intake.group(1).split())
    return diag, pedal, fields


for invalid_ticks in ("0", "2000000"):
    bad = subprocess.run(base + ["--pedal-rise-ticks", invalid_ticks],
                         env=environment, text=True, capture_output=True,
                         timeout=5)
    assert bad.returncode == 2

step_diag, step_events, step_intake = run([])
ramp_diag, ramp_events, ramp_intake = run(["--pedal-rise-ticks", "200000"])
assert [(event["tick"], event["type"]) for event in ramp_events] == [
    (10000000, "pedal_command"), (10200000, "pedal"),
    (12000000, "pedal_release")]
assert ramp_events[1]["pull_m"] == step_events[0]["pull_m"] == 0.008
assert ramp_events[1]["angle_rad"] == step_events[0]["angle_rad"]
assert not ramp_events[1]["contact"]
assert ramp_events[2]["contact"]
assert any(event["f84e"] == 10 for event in step_diag)
assert step_diag[-1]["f85e"] == 10
assert all(event["f84e"] == event["f85e"] == 0 for event in ramp_diag)
# The lambda closed loop is active when the CC3 output keeps toggling. Its
# limit-cycle rate follows intake dynamics (pumping work, manifold pressure,
# transport delay): measured 593 pulses before pumping torque was modelled
# (ca6f99c^), 462 at ca6f99c/HEAD, 457 with the series-motor starter. The old
# ">500" encoded the pre-pumping rate; require a clearly active loop instead.
MIN_CC3_PULSES = 300
assert int(step_intake["cc3_pulses"]) > MIN_CC3_PULSES, step_intake["cc3_pulses"]
assert int(ramp_intake["cc3_pulses"]) > MIN_CC3_PULSES, ramp_intake["cc3_pulses"]

# A stronger physical cable pull still reaches the ROM's guarded lambda path.
strong = base.copy()
strong[strong.index("--pedal-mm") + 1] = "40"
strong_env = dict(environment, MA17_TRACE_PC="1",
                  MA17_TRACE_LAMBDA_ROUTE="1")
result = subprocess.run(strong + ["--pedal-rise-ticks", "200000"],
                        env=strong_env, text=True, capture_output=True,
                        timeout=55, check=True)
events = [json.loads(line) for line in result.stdout.splitlines()
          if line.startswith('{"type":')]
strong_diag = [event for event in events if event["type"] == "diagnostic"]
strong_lambda = [event for event in events if event["type"] == "lambda"]
route = []
for line in result.stderr.splitlines():
    if not line.startswith("[LAMBDA-ROUTE]"):
        continue
    fields = dict(part.split("=", 1) for part in line.split() if "=" in part)
    route.append((int(fields["tick"]), fields["PC"]))
blocked = [entry for index, entry in enumerate(route[:-1])
           if entry[0] >= 12000000 and entry[1] == "1810" and
           (route[index + 1][1] != "186D" or
            route[index + 1][0] - entry[0] > 10)]
# The guarded path (PC 0x1810 not followed by 0x186D) is what this test is
# about: it must be reached right after the pedal release. How often it recurs
# afterwards follows the lambda limit cycle, which depends on intake/pumping
# dynamics: 108 hits through 19.7 Ms before pumping torque (ca6f99c^), 2 hits
# (first 12.73 Ms, last 15.55 Ms) with pumping torque + series-motor starter.
# Counting recurrences encoded the old dynamics, so only the entry is required.
assert len(blocked) >= 1
assert 12000000 < blocked[0][0] < 13000000
assert all(event["f84e"] == event["f85e"] == 0 for event in strong_diag)
assert any(event["tick"] > 12000000 and event["physical"] < 0.8
           for event in strong_lambda)
print("Finite pedal rise reaches the target without transient ROM fault")
