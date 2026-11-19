"""Open only the candidate idle-switch wire while the stop remains in contact."""

import json
import os
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "14000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5", "--tps-bench-profile"]
fault = ["--idle-contact-open-tick", "10000000",
         "--idle-contact-restore-tick", "12000000"]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(extra):
    result = subprocess.run(base + extra, env=environment, text=True,
                            capture_output=True, timeout=40, check=True)
    states = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":"idle_actuator"')]
    ports = [(int(match[2]), (int(match[1], 16) >> 6) & 1)
             for line in result.stderr.splitlines()
             if (match := re.search(
                 r"\[P4\.5\] Read: 0x([0-9A-F]+).*instru=(\d+)", line))]
    summary = re.search(r"\[PHYSICAL-DIAG\] ([^\n]+)", result.stdout)
    assert states and summary
    return states, ports, dict(part.split("=") for part in
                               summary.group(1).split())


invalid = base.copy()
invalid.remove("--idle-contact-p46")
assert subprocess.run(invalid + fault, env=environment, text=True,
                      capture_output=True, timeout=5).returncode == 2
assert subprocess.run(base + fault[:2] +
                      ["--idle-contact-restore-tick", "9000000"],
                      env=environment, text=True, capture_output=True,
                      timeout=5).returncode == 2

normal, _, normal_diag = run([])
opened, ports, opened_diag = run(fault)
assert [state for state in normal if state["tick"] < 10000000] == [
    state for state in opened if state["tick"] < 10000000]
normal_by_tick = {state["tick"]: state for state in normal}
opened_by_tick = {state["tick"]: state for state in opened}
for tick in (10890000, 11880000, 12870000):
    assert normal_by_tick[tick]["contact"]
    assert opened_by_tick[tick]["contact"]
assert opened_by_tick[11880000]["stem_m"] < \
       normal_by_tick[11880000]["stem_m"] - 0.001
assert opened_by_tick[12870000]["stem_m"] > \
       opened_by_tick[11880000]["stem_m"] + 0.001
assert [level for tick, level in ports
        if 10000000 <= tick < 12500000] == [1, 0]
assert all(diag["f84e"] == diag["f85e"] == "0"
           for diag in (normal_diag, opened_diag))
