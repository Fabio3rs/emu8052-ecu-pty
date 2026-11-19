"""ADC7 startup state stays latched through a later physical pedal step."""

import json
import os
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "4000000"]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def run(extra):
    result = subprocess.run(base + extra, env=environment,
                            text=True, capture_output=True, timeout=20,
                            check=True)

    def summary(name):
        match = re.search(rf"\[PHYSICAL-{name}\] ([^\n]+)", result.stdout)
        assert match, result.stdout[-2000:]
        return dict(part.split("=") for part in match.group(1).split())

    return summary("CRANK"), summary("INTAKE"), summary("ADC7")


invalid = subprocess.run(base + ["--adc7-step-mv", "1260",
                                 "--adc7-step-tick", "3000000"],
                         env=environment, text=True, capture_output=True,
                         timeout=5)
assert invalid.returncode == 2

low_crank, low_intake, low_gate = run(["--adc7-mv", "1232"])
ground_crank, ground_intake, ground_gate = run(["--adc7-mv", "0"])
late_crank, late_intake, late_gate = run([
    "--adc7-mv", "1232", "--adc7-step-mv", "1260",
    "--adc7-step-tick", "3000000"])
_, early_intake, early_gate = run([
    "--adc7-mv", "1232", "--adc7-step-mv", "1260",
    "--adc7-step-tick", "800000"])
_, restored_intake, restored_gate = run([
    "--adc7-mv", "1260", "--adc7-step-mv", "1232",
    "--adc7-step-tick", "3000000"])
_, grounded_intake, grounded_gate = run([
    "--adc7-mv", "1260", "--adc7-step-mv", "0",
    "--adc7-step-tick", "3000000"])

# Injection really ran. The count follows engine speed over the 4 M window
# (>100 before ca6f99c, 55 with friction/pumping drag), so only the order of
# magnitude is checked; the gate behaviour below is what the test is about.
assert int(low_intake["cc3_pulses"]) > 20
assert ground_crank == low_crank
assert ground_intake == low_intake | {"ram67": "0"}
assert ground_gate == {"ram67": "0", "f8dd": "170", "gate2b5": "0"}
assert low_gate == {"ram67": "63", "f8dd": "170", "gate2b5": "0"}
assert late_gate == {"ram67": "65", "f8dd": "170", "gate2b5": "0"}
assert late_intake == low_intake | {"ram67": "65"}
assert late_crank == low_crank
assert 0 < int(early_intake["cc3_pulses"]) < int(low_intake["cc3_pulses"])
assert early_gate == {"ram67": "65", "f8dd": "85", "gate2b5": "1"}
assert restored_intake["cc3_pulses"] == "0"
assert restored_gate == {"ram67": "63", "f8dd": "85", "gate2b5": "1"}
assert grounded_intake == restored_intake | {"ram67": "0"}
assert grounded_gate == {"ram67": "0", "f8dd": "85", "gate2b5": "1"}


# The same electrical step after successful startup must not explain the
# candidate idle fault caused by a later cable pull.
pedal_base = base.copy()
pedal_base[pedal_base.index("--stop-ticks") + 1] = "20000000"
pedal_base += ["--adc7-mv", "1232", "--idle-bridge-p15-p16",
               "--idle-contact-p46", "--coolant-c", "90",
               "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
               "--load-step-tick", "800000", "--load-nm", "24",
               "--lambda-adc-gain", "5", "--pedal-step-tick", "10000000",
               "--pedal-release-tick", "12000000", "--pedal-mm", "8"]


def pedal_run(extra):
    result = subprocess.run(pedal_base + extra, env=environment,
                            text=True, capture_output=True, timeout=50,
                            check=True)
    faults = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":"idle_fault_raw"')]
    faults = [event for event in faults
              if 10000000 <= event["tick"] < 12000000]
    match = re.search(r"\[PHYSICAL-ADC7\] ([^\n]+)", result.stdout)
    assert match
    gate = dict(part.split("=") for part in match.group(1).split())
    return faults, gate


pedal_faults, pedal_gate = pedal_run([])
stepped_faults, stepped_gate = pedal_run([
    "--adc7-step-mv", "1260", "--adc7-step-tick", "9000000"])
assert [(event["pc"], event["tick"], event["ram27"], event["f84e"])
        for event in pedal_faults] == [
            (event["pc"], event["tick"], event["ram27"], event["f84e"])
            for event in stepped_faults]
assert any(event["f84e"] == 10 for event in pedal_faults)
assert pedal_gate == {"ram67": "63", "f8dd": "170", "gate2b5": "0"}
assert stepped_gate == {"ram67": "65", "f8dd": "170", "gate2b5": "0"}
