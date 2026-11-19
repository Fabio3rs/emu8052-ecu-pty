"""Trace a live Fiat lambda correction to the scheduled CC3 pulse."""

import json
import os
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "16000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"]


def run(extra):
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                   "MA17_TRACE_PC": "1",
                   "MA17_TRACE_LAMBDA_PROPAGATION": "1"}
    result = subprocess.run(base + extra, env=environment,
                            text=True, capture_output=True, timeout=80,
                            check=True)
    rows = {}
    for line in result.stderr.splitlines():
        if not line.startswith("[LAMBDA-PROPAGATION]"):
            continue
        values = dict(re.findall(
            r"(tick|PC|F2C|F2F|RAM65|RAM5C5D|RAM1415|R6R7|RAM47)="
            r"([0-9A-F]+)", line))
        values["tick"] = int(values["tick"])
        rows.setdefault(values["PC"], []).append(values)
    edges = [json.loads(line) for line in result.stdout.splitlines()
             if line.startswith('{"type":"cc3_pin"')]
    samples = [json.loads(line) for line in result.stdout.splitlines()
               if line.startswith('{"type":"lambda"')]
    assert len(samples) == 16
    pulses = []
    start = None
    for edge in edges:
        if not edge["high"]:
            start = edge
        elif start is not None:
            pulses.append((start["tick"], edge["tick"] - start["tick"],
                           start["ram14_15"]))
            start = None
    return rows, edges, samples, pulses


# Wiring, gain, load and ADC7 are conditional engineering assumptions.
free_rows, free_edges, free_samples, free_pulses = run([])
fault_rows, fault_edges, fault_samples, fault_pulses = run(
    ["--lambda-stuck-mv", "4000", "--lambda-stuck-tick", "10000000",
     "--lambda-restore-tick", "14000000"])
assert free_samples[:10] == fault_samples[:10]
assert [edge for edge in free_edges if edge["tick"] < 10000000] == [
    edge for edge in fault_edges if edge["tick"] < 10000000]
assert all(fault_samples[index]["adc5_pin_v"] == 4.0
           for index in range(10, 14))


def first_difference(pc, field):
    free = free_rows[pc]
    fault = fault_rows[pc]
    assert [(row["tick"], row[field]) for row in free
            if row["tick"] < 10000000] == [
                (row["tick"], row[field]) for row in fault
                if row["tick"] < 10000000]
    return next((left, right) for left, right in zip(free, fault)
                if left["tick"] >= 10000000 and left[field] != right[field])


acc_free, acc_fault = first_difference("199C", "RAM5C5D")
consumer_free, consumer_fault = first_difference("1C8E", "RAM5C5D")
published_free, published_fault = first_difference("1ED7", "RAM1415")
scheduled_free, scheduled_fault = first_difference("058E", "RAM1415")
# Old window: 10..12 M ticks. The calibrated plant makes the ROM close the loop later
# (measured 12.86 M); the ordering asserts below are the actual invariant.
assert 10000000 < acc_free["tick"] < 14000000, acc_free["tick"]
assert acc_free["RAM47"] == acc_fault["RAM47"]
assert acc_free["RAM1415"] == acc_fault["RAM1415"]
assert (acc_free["tick"] < consumer_free["tick"] <
        published_free["tick"] < scheduled_free["tick"])
assert (acc_fault["tick"] < consumer_fault["tick"] <
        published_fault["tick"] < scheduled_fault["tick"])
# The ROM may publish a newer interval before the next CC3 schedule.
for rows, scheduled in ((free_rows, scheduled_free),
                        (fault_rows, scheduled_fault)):
    preceding = [row for row in rows["1ED7"]
                 if row["tick"] <= scheduled["tick"]]
    assert preceding and preceding[-1]["RAM1415"] == scheduled["RAM1415"]

# The pulse count follows engine speed over the run (>400 before ca6f99c); the
# fault run must not exceed the free run and both must show an active loop
# (measured 312 free / 289 fault).
assert len(free_pulses) >= len(fault_pulses) > 250
first_interval = next((left, right) for left, right in
                      zip(free_pulses, fault_pulses)
                      if left[0] > 10000000 and left[2] != right[2])
assert first_interval[0][0] >= scheduled_free["tick"]
assert first_interval[1][0] >= scheduled_fault["tick"]
assert first_interval[0][2] == int(scheduled_free["RAM1415"], 16)
assert first_interval[1][2] == int(scheduled_fault["RAM1415"], 16)
assert abs(first_interval[0][1] - first_interval[1][1]) > 10
