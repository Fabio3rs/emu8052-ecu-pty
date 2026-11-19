"""Fiat ROM lambda threshold table changes classification at fixed ADC5."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
# The held-ADC5 runs only diverge in CC3 interval once the lambda loop is
# closed: first interval difference at 18.2 M ticks with friction/pumping drag
# (earlier: before 12 M). The run is therefore 22 M ticks long.
STOP_TICKS = 22000000
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", str(STOP_TICKS), "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5", "--lambda-stuck-tick", "2000000"]


def run(millivolts, trace):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    if trace:
        env.update(MA17_TRACE_PC="1", MA17_TRACE_LAMBDA_BOUNDS="1",
                   MA17_TRACE_LAMBDA_PROPAGATION="1",
                   MA17_TRACE_LAMBDA_DIRECTION="1")
    result = subprocess.run(
        base + ["--lambda-stuck-mv", str(millivolts)], env=env,
        text=True, capture_output=True, timeout=50, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":"lambda_class_raw"')]
    samples = [json.loads(line) for line in result.stdout.splitlines()
               if line.startswith('{"type":"lambda"')]
    edges = [json.loads(line) for line in result.stdout.splitlines()
             if line.startswith('{"type":"cc3_pin"')]
    assert len(samples) == STOP_TICKS // 990000
    pulses = []
    start = None
    for edge in edges:
        if not edge["high"]:
            start = edge
        elif start is not None:
            pulses.append((start["tick"], edge["tick"] - start["tick"],
                           start["ram14_15"], start["lambda_flags"]))
            start = None
    return events, samples, pulses, result.stderr


# ADC5 gain and wiring are scenario hypotheses; this checks the original
# firmware's digital response to a held electrical input.
near, near_samples, near_pulses, trace = run(2600, True)
low, low_samples, low_pulses, _ = run(2500, False)
_, high_samples, _, high_trace = run(4000, True)
assert all(sample["adc5_pin_v"] == 2.6 and sample["ram65"] == 133
           for sample in near_samples[2:])
assert all(sample["adc5_pin_v"] == 2.5 and sample["ram65"] == 128
           for sample in low_samples[2:])
assert all(sample["adc5_pin_v"] == 4.0 and sample["ram65"] == 205
           for sample in high_samples[2:])

bound = [(int(match.group(1)), int(match.group(2), 16),
          int(match.group(3), 16))
         for line in trace.splitlines()
         if (match := re.search(
             r"\[LAMBDA-BOUND-XRAM\] tick=(\d+) addr=F8E8 "
             r"value=([0-9A-F]+)->([0-9A-F]+) source_PC=16EA", line))]
# Table-bound steps inside the original 12 M window (the longer run keeps
# stepping the bound further).
bound = [entry for entry in bound if entry[0] < 12000000]
assert [(old, new) for _, old, new in bound] == [(10, 9), (9, 8), (8, 7)]
crossing_tick = bound[1][0]
transition = [event for event in near
              if event["pc"] == 0x1673 and event["tick"] > 2000000]
assert len(transition) == 1
assert 0 < transition[0]["tick"] - crossing_tick < 20000
assert (transition[0]["ram65"], transition[0]["f8e8"],
        transition[0]["flags"]) == (133, 8, 8)
assert not any(event["pc"] == 0x1673 and event["tick"] > 2000000
               for event in low)
assert any(event["pc"] == 0x1677 and event["flags"] == 2
           for event in low if event["tick"] > 2000000)

# The comparator transition does not immediately change the interval
# delivered to CC3; later feedback can still change that interval.
assert len(near_pulses) == len(low_pulses)
before = [(a, b) for a, b in zip(near_pulses, low_pulses)
          if 2000000 <= a[0] < transition[0]["tick"]]
assert before and all(a[:3] == b[:3] for a, b in before)
immediate = [(a, b) for a, b in zip(near_pulses, low_pulses)
             if transition[0]["tick"] < a[0] < 8500000]
# Pulses between the comparator transition (~7.73 M) and 8.5 M: 21+ before
# ca6f99c, 12 now (pulse period follows engine speed). Require several.
assert len(immediate) > 6
assert all(a[2] == b[2] for a, b in immediate)
assert all(a[3] == 8 and b[3] == 2 for a, b in immediate)
late = [(a, b) for a, b in zip(near_pulses, low_pulses)
        if a[0] > 10000000]
assert any(a[2] != b[2] for a, b in late)


def accumulator_at_consumer(output):
    return [(int(match.group(1)), match.group(2))
            for line in output.splitlines()
            if (match := re.search(
                r"\[LAMBDA-PROPAGATION\] tick=(\d+) PC=1C8E "
                r".*RAM5C5D=([0-9A-F]{4})", line))]


near_acc = accumulator_at_consumer(trace)
high_acc = accumulator_at_consumer(high_trace)
assert len(near_acc) > 400 and len(high_acc) > 400
assert all(value == "0000" for _, value in near_acc)
assert all(value != "0000" for _, value in high_acc)

# The fast table counter still ticks with a fixed rich electrical input,
# while the original ROM keeps its correction in one direction.
high_counter = re.findall(
    r"\[LAMBDA-BOUND-XRAM\] tick=\d+ addr=F8E9 "
    r"value=[0-9A-F]{2}->[0-9A-F]{2}", high_trace)
high_direction = [int(match.group(1), 16) & 0x20
                  for match in re.finditer(
                      r"\[LAMBDA-DIRECTION\] tick=\d+ PC=1958 .*"
                      r"PSW=([0-9A-F]{2})", high_trace)]
assert len(high_counter) > 20
assert len(high_direction) > 100 and set(high_direction) == {0}
