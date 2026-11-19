"""Fiat P3.4 relay candidate powers the lambda heater conditionally."""

import json
import os
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "20000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"]


def run(args):
    result = subprocess.run(args, env=environment, text=True,
                            capture_output=True, timeout=60, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    relay = [event for event in events
             if event["type"] == "pump_relay_candidate"]
    samples = [event for event in events if event["type"] == "lambda"]
    edges = [event for event in events if event["type"] == "cc3_pin"]
    crank = re.search(r"\[PHYSICAL-CRANK\] ticks=\d+ rpm=([\d.]+)",
                      result.stdout)
    diagnostic = re.search(r"\[PHYSICAL-DIAG\] ([^\n]+)", result.stdout)
    assert crank and diagnostic
    faults = dict(part.split("=") for part in diagnostic.group(1).split())
    return relay, samples, float(crank.group(1)), faults, edges


assert subprocess.run([binary, firmware, "--pump-relay-p34"],
                      env=environment, text=True, capture_output=True,
                      timeout=5).returncode == 2

no_start = [binary, firmware, "--physical-crank", "--starter-ticks", "1",
            "--stop-ticks", "5000000", "--adc7-mv", "1232"]
off_relay, off_lambda, off_rpm, _, _ = run(no_start)
on_relay, on_lambda, on_rpm, _, _ = run(no_start + ["--pump-relay-p34"])
assert not off_relay and off_rpm == on_rpm == 0.0
assert [(event["closed"], event["p34_high"]) for event in on_relay] == [
    (True, False), (False, True)]
assert on_relay[0]["tick"] < 1000
assert 1100000 < on_relay[1]["tick"] < 1300000
assert all(sample["temperature_c"] == 20.0 for sample in off_lambda)
assert on_lambda[0]["temperature_c"] > 70.0
assert on_lambda[-1]["temperature_c"] < on_lambda[1]["temperature_c"]
assert not any(sample["valid"] for sample in on_lambda)

_, cold_lambda, _, cold_faults, cold_edges = run(base)
hot_relay, hot_lambda, hot_rpm, hot_faults, hot_edges = run(
    base + ["--pump-relay-p34"])
assert len(hot_relay) == 1 and hot_relay[0]["closed"]
assert hot_lambda[0]["temperature_c"] > \
    cold_lambda[0]["temperature_c"] + 50.0
assert hot_lambda[1]["valid"] and hot_rpm > 700
assert hot_lambda[0]["adc5_pin_v"] == cold_lambda[0]["adc5_pin_v"]
assert hot_lambda[0]["ram65"] == cold_lambda[0]["ram65"]
assert hot_lambda[1]["adc5_pin_v"] > cold_lambda[1]["adc5_pin_v"]
assert hot_lambda[1]["ram65"] > cold_lambda[1]["ram65"]
assert all(hot_faults[key] == cold_faults[key] == "0"
           for key in ("ram27", "f84e", "f84f", "f850",
                       "f85e", "f85f", "f860"))
first_ram65 = next(index for index, (cold, hot) in
                   enumerate(zip(cold_edges, hot_edges))
                   if cold["ram65"] != hot["ram65"])
first_flags = next(index for index, (cold, hot) in
                   enumerate(zip(cold_edges, hot_edges))
                   if cold["lambda_flags"] != hot["lambda_flags"])
first_command = next(index for index, (cold, hot) in
                     enumerate(zip(cold_edges, hot_edges))
                     if cold["ram14_15"] != hot["ram14_15"])
assert cold_edges[:first_ram65] == hot_edges[:first_ram65]
assert first_ram65 < first_flags < first_command
assert 1000000 < hot_edges[first_command]["tick"] < 2000000

finer = base.copy()
finer[finer.index("--stop-ticks") + 1] = "10000000"
_, finer_lambda, _, _, _ = run(finer + ["--pump-relay-p34",
                                      "--fluid-step-ticks", "495"])
for reference, reduced in zip(hot_lambda[:3], finer_lambda[:3]):
    assert abs(reference["temperature_c"] - reduced["temperature_c"]) < 0.5
    assert abs(reference["adc5_pin_v"] - reduced["adc5_pin_v"]) < 0.01

stall = base.copy()
stall[stall.index("--stop-ticks") + 1] = "15000000"
stall[stall.index("--load-step-tick") + 1] = "10000000"
stall[stall.index("--load-nm") + 1] = "100"
stall_relay, stall_lambda, stall_rpm, _, _ = run(stall +
                                                ["--pump-relay-p34"])
assert stall_rpm == 0.0
assert len(stall_relay) == 2 and stall_relay[0]["closed"]
assert not stall_relay[1]["closed"]
assert 11000000 < stall_relay[1]["tick"] < 12000000
assert stall_lambda[-1]["temperature_c"] < stall_lambda[-2]["temperature_c"]
