"""A Fiat ROM lambda limit crossing propagates to injector compare timing."""

import json
import os
import re
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "12000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5", "--lambda-stuck-tick", "2000000"]
env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
       "MA17_TRACE_PC": "1", "MA17_TRACE_LAMBDA_BOUNDS": "1",
       "MA17_TRACE_LAMBDA_PROPAGATION": "1",
       "MA17_TRACE_LAMBDA_DIRECTION": "1"}


def run(millivolts):
    result = subprocess.run(
        base + ["--lambda-stuck-mv", str(millivolts)], env=env,
        text=True, capture_output=True, timeout=60, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    classes = [event for event in events
               if event["type"] == "lambda_class_raw"]
    samples = [event for event in events if event["type"] == "lambda"]
    pulses = []
    start = None
    for edge in events:
        if edge["type"] != "cc3_pin":
            continue
        if not edge["high"]:
            start = edge
        elif start is not None:
            pulses.append((start["tick"], edge["tick"] - start["tick"],
                           start["ram14_15"], start["lambda_flags"]))
            start = None
    consumers = []
    for line in result.stderr.splitlines():
        if "[LAMBDA-PROPAGATION]" in line and "PC=1C8E" in line:
            match = re.search(r"tick=(\d+).*RAM5C5D=([0-9A-F]{4})", line)
            assert match, line
            consumers.append((int(match[1]), match[2]))
    return classes, samples, pulses, consumers, result.stderr


# ADC5 gain, ADC7, and idle hardware bindings remain scenario hypotheses.
low_class, low_samples, low_pulses, low_acc, low_trace = run(2940)
high_class, high_samples, high_pulses, high_acc, high_trace = run(2960)
assert all(sample["ram65"] == 151 for sample in low_samples[2:])
assert all(sample["ram65"] == 152 for sample in high_samples[2:])
assert len(low_pulses) == len(high_pulses) > 300
assert len(low_acc) == len(high_acc) > 400

bound_ticks = []
for address, old, new, source in (("F8EA", "0E", "0D", "16CC"),
                                  ("F8E8", "09", "08", "16EA")):
    pattern = (rf"\[LAMBDA-BOUND-XRAM\] tick=(\d+) addr={address} "
               rf"value={old}->{new} source_PC={source}")
    matches = [int(match[1]) for match in re.finditer(pattern, high_trace)]
    assert len(matches) == 1 and 7700000 < matches[0] < 8000000
    bound_ticks.append(matches[0])
assert 0 < bound_ticks[1] - bound_ticks[0] < 100

high_change = next(event for event in high_class
                   if event["tick"] > 2000000 and event["flags"] == 0)
low_change = next(event for event in low_class
                  if event["tick"] > 2000000 and event["flags"] == 0)
assert (high_change["pc"], high_change["ram65"],
        high_change["f8e8"], high_change["f8ea"]) == (0x167F, 152, 8, 13)
assert bound_ticks[1] < high_change["tick"] < bound_ticks[1] + 20000
assert low_change["tick"] > 10800000
assert all(value == "0000" for tick, value in high_acc
           if tick < high_change["tick"])
first_active = next(tick for tick, value in high_acc if value != "0000")
assert high_change["tick"] < first_active < high_change["tick"] + 1000
assert all(value == "0000" for tick, value in low_acc
           if tick < low_change["tick"])

paired = [(low, high) for low, high in zip(low_pulses, high_pulses)
          if low[0] > 2000000]
assert all(low == high for low, high in paired
           if low[0] < high_change["tick"])
first_pulse_change = next((low, high) for low, high in paired
                          if low[1:3] != high[1:3])
assert first_active < first_pulse_change[0][0] < high_change["tick"] + 100000
assert first_pulse_change[0][2] != first_pulse_change[1][2]
assert first_pulse_change[0][1] != first_pulse_change[1][1]

# With the sensor free, classification changes repeatedly between table steps.
natural_base = base[:base.index("--lambda-stuck-tick")]
natural_base[natural_base.index("--stop-ticks") + 1] = "20000000"
natural = subprocess.run(
    natural_base, env=env,
    text=True, capture_output=True, timeout=60, check=True)
natural_classes = [json.loads(line) for line in natural.stdout.splitlines()
                   if line.startswith('{"type":"lambda_class_raw"')]
natural_classes = [event for event in natural_classes
                   if event["tick"] > 3000000]
natural_steps = [line for line in natural.stderr.splitlines()
                 if "[LAMBDA-BOUND-XRAM]" in line and
                 "addr=F8EA" in line and "source_PC=16CC" in line]
assert len(natural_steps) == 5
assert len(natural_classes) > 4 * len(natural_steps)
directions = [(int(match[1]), (int(match[2], 16) >> 5) & 1)
              for match in re.finditer(
                  r"\[LAMBDA-DIRECTION\] tick=(\d+) PC=1958 .*"
                  r"PSW=([0-9A-F]{2})", natural.stderr)]
flips = [(tick, direction) for index, (tick, direction) in
         enumerate(directions) if index and direction != directions[index - 1][1]]
fast_writes = [int(match[1]) for match in re.finditer(
    r"\[LAMBDA-BOUND-XRAM\] tick=(\d+) addr=F8E9 ", natural.stderr)]
assert len(flips) >= 6 and len(fast_writes) > 100
for tick, _ in flips:
    prior_class = max(event["tick"] for event in natural_classes
                      if event["tick"] <= tick)
    assert 0 < tick - prior_class < 200
assert any(min(abs(tick - write) for write in fast_writes) > 20000
           for tick, _ in flips)
print("ROM limit crossing -> lambda flag -> active accumulator -> CC3 pulse")
