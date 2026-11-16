"""Fiat ROM response to cable-driven TPS voltage and one electrical fault."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base_args = [binary, firmware, "--physical-crank", "--starter-ticks",
             "495000", "--stop-ticks", "2000000"]
for invalid in (["--tps2-restore-tick", "1200000"],
                ["--tps2-high-tick", "2000000"],
                ["--tps2-high-tick", "800000",
                 "--tps2-restore-tick", "700000"]):
    assert subprocess.run(base_args + invalid, text=True,
                          capture_output=True, timeout=5).returncode == 2


def run(extra):
    result = subprocess.run(base_args + extra,
                            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                            text=True, capture_output=True, timeout=20,
                            check=True)
    output = result.stdout + result.stderr
    summary = re.search(r"\[PHYSICAL-TPS\] ([^\n]+)", output)
    assert summary, output[-2000:]
    fields = dict(part.split("=") for part in summary.group(1).split())
    events = [json.loads(line) for line in output.splitlines()
              if line.startswith('{"type":')]
    return fields, events


closed, _ = run([])
pedal, pedal_events = run(["--pedal-step-tick", "800000", "--pedal-mm", "8"])
fault, fault_events = run(["--tps1-high-tick", "800000"])
restored, restore_events = run(["--tps1-high-tick", "800000",
                               "--tps1-restore-tick", "1200000"])
tps2_fault, tps2_events = run(["--tps2-high-tick", "800000"])
tps2_restored, tps2_restore_events = run(
    ["--tps2-high-tick", "800000", "--tps2-restore-tick", "1200000"])
tps2_with_pedal, _ = run(
    ["--tps2-high-tick", "800000", "--tps2-restore-tick", "1200000",
     "--pedal-step-tick", "1400000", "--pedal-mm", "20"])
tps2_rearmed, _ = run(
    ["--tps2-high-tick", "800000", "--tps2-restore-tick", "1200000",
     "--tps1-high-tick", "1400000", "--tps1-restore-tick", "1800000"])

assert (closed["ram60"], closed["ram66"], closed["contact"]) == ("40", "95", "1")
assert (pedal["ram60"], pedal["ram66"], pedal["contact"]) == ("82", "157", "0")
assert (closed["ram6f"], closed["ram70"]) != (pedal["ram6f"], pedal["ram70"])
assert all(closed[key] == "0" and pedal[key] == "0"
           for key in ("ram28", "fault85", "fault4f"))
assert any(event["type"] == "pedal" and event["tick"] == 800000
           for event in pedal_events)
changes = [event for event in pedal_events if event["type"] == "tps_ram"
           and event["tick"] > 800000]
assert changes[-1]["ram60"] == 82 and changes[-1]["ram66"] == 157
assert changes[-1]["tick"] < 810000

assert fault["ram60"] == closed["ram60"] and fault["ram66"] == "255"
assert fault["angle_rad"] == closed["angle_rad"]
assert any(event["type"] == "tps_fault" and event["tick"] == 800000
           for event in fault_events)
assert restored["ram66"] == closed["ram66"]
assert (restored["ram6f"], restored["ram70"]) == (closed["ram6f"], closed["ram70"])
assert any(event["type"] == "tps_restore" and event["tick"] == 1200000
           for event in restore_events)
assert any(event["type"] == "tps_ram" and event["ram66"] == 255
           for event in restore_events)
assert any(event["type"] == "tps_ram" and event["ram66"] == 95
           and event["tick"] > 1200000 for event in restore_events)

assert tps2_fault["ram60"] == "255" and tps2_fault["ram66"] == "95"
assert tps2_fault["angle_rad"] == closed["angle_rad"]
assert tps2_fault["ram28"] == tps2_fault["fault4f"] == "4"
assert any(event["type"] == "tps_fault" and event["channel"] == 0
           and event["tick"] == 800000 for event in tps2_events)
assert any(event["type"] == "tps_ram" and event["ram60"] == 255
           and event["adc0_v"] == 5.0 for event in tps2_events)
assert tps2_restored["ram60"] == closed["ram60"]
assert tps2_restored["adc0_v"] == closed["adc0_v"]
assert tps2_restored["ram28"] == tps2_restored["fault4f"] == "4"
assert any(event["type"] == "tps_restore" and event["channel"] == 0
           and event["tick"] == 1200000 for event in tps2_restore_events)
assert tps2_with_pedal["ram66"] == "197"
assert tps2_with_pedal["ram28"] == tps2_with_pedal["fault4f"] == "4"
assert tps2_rearmed["ram60"] == closed["ram60"]
assert tps2_rearmed["ram66"] == closed["ram66"]
assert tps2_rearmed["ram28"] == tps2_rearmed["fault4f"] == "0"
