"""A physical wheel keeps turning during an electrical crank-sensor open."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
# The sensor is opened once the idle has recovered from the 24 N-m load step.
# With friction and pumping torque modelled (ca6f99c) the engine holds only
# ~500 rpm until ~10 Mticks (measured 504 rpm at 10 M, 900 rpm from 14 M) and a
# 0.15 s loss of ignition at that speed legitimately stalls it. The earlier
# open tick of 10 M was calibrated on an engine without that drag.
OPEN_TICK = 16000000
# Measured at settled idle (900 rpm): an open of 20-60 ktick (20-60 ms) is
# recovered by the ROM (f850=0), 80 ktick and longer latches fault f850=2 and
# the engine, whose speed falls ~1800 rpm/s without combustion, stalls. The
# earlier 150 ktick was recovered only because the old model lacked friction.
RESTORE_TICK = OPEN_TICK + 50000
STOP_TICK = 22000000
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", str(STOP_TICK), "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"]
open_wire = ["--crank-sensor-open-tick", str(OPEN_TICK)]
restore = ["--crank-sensor-restore-tick", str(RESTORE_TICK)]


def run(args):
    result = subprocess.run(args, env=environment, text=True,
                            capture_output=True, timeout=300, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    summary = re.search(r"\[PHYSICAL-CRANK\] ([^\n]+)", result.stdout)
    diagnostic = re.search(r"\[PHYSICAL-DIAG\] ([^\n]+)", result.stdout)
    assert summary and diagnostic
    return (events,
            dict(part.split("=") for part in summary.group(1).split()),
            dict(part.split("=") for part in diagnostic.group(1).split()))


for invalid in (restore, ["--crank-sensor-open-tick", str(STOP_TICK)],
                open_wire + ["--crank-sensor-restore-tick", str(OPEN_TICK - 1)]):
    assert subprocess.run(base + invalid, env=environment, text=True,
                          capture_output=True, timeout=5).returncode == 2
assert subprocess.run([binary, firmware] + open_wire, env=environment,
                      text=True, capture_output=True, timeout=5).returncode == 2

# After a recovered dropout every active-fault byte must be clear. F860 is
# excluded: this ROM byte latches 0x40 for a dropout of any length depending
# only on where in the ROM's cycle it lands (pre-pumping binary: 64 for open
# at 10 M, 0 at 16 M; current: the reverse). Its meaning is not decoded, so it
# is not used as a pass/fail signal.
RECOVERED_CLEAR = ("ram27", "f84e", "f84f", "f850", "f85e", "f85f")
normal, normal_crank, _ = run(base)
fault, fault_crank, fault_diag = run(base + open_wire)
recovered, recovered_crank, recovered_diag = run(base + open_wire + restore)
assert [event for event in normal if event["tick"] < OPEN_TICK] == [
    event for event in fault if event["tick"] < OPEN_TICK] == [
        event for event in recovered if event["tick"] < OPEN_TICK]

def event_ticks(events, kind):
    return [event["tick"] for event in events if event["type"] == kind]


assert event_ticks(fault, "crank_sensor_open") == [OPEN_TICK]
assert event_ticks(recovered, "crank_sensor_open") == [OPEN_TICK]
assert event_ticks(recovered, "crank_sensor_restore") == [RESTORE_TICK]
assert any(event["type"] == "crank_gap" and
           OPEN_TICK < event["tick"] < OPEN_TICK + 1000000 and event["rpm"] > 0
           for event in fault)
assert not any(event["type"] == "cc3_pin" and not event["high"] and
               event["tick"] >= OPEN_TICK for event in fault)
assert float(fault_crank["rpm"]) == 0.0 and fault_crank["ram47"] == "0"
assert fault_diag["f850"] == "2"  # Raw value after the engine has stopped.
assert any(event["type"] == "cc3_pin" and not event["high"] and
           event["tick"] > RESTORE_TICK for event in recovered)
assert float(normal_crank["rpm"]) > 700
assert float(recovered_crank["rpm"]) > 700
assert int(recovered_crank["ram47"]) > 0
assert all(recovered_diag[key] == "0" for key in
           RECOVERED_CLEAR)

finer, finer_crank, finer_diag = run(
    base + open_wire + restore + ["--fluid-step-ticks", "495"])
assert abs(float(finer_crank["rpm"]) -
           float(recovered_crank["rpm"])) < 5.0
assert sum(event["type"] == "cc3_pin" and not event["high"]
           for event in finer) == sum(event["type"] == "cc3_pin" and
                                   not event["high"] for event in recovered)
assert all(finer_diag[key] == "0" for key in
           RECOVERED_CLEAR)
