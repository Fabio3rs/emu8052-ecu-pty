"""Warm coil interruption reaches exhaust oxygen, ADC5, and recovery."""

import json
import os
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "16000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--load-step-tick", "800000", "--load-nm", "24",
        "--lambda-adc-gain", "5"]


def run(extra):
    result = subprocess.run(
        base + extra, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=45, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    return (events,
            {event["tick"]: event for event in events
             if event["type"] == "lambda"},
            {event["tick"]: event for event in events
             if event["type"] == "combustion"})


# These electrical bindings and gain are conditional Fiat model assumptions.
_, normal_lambda, normal_fire = run([])
events, fault_lambda, fault_fire = run(
    ["--coil-channel", "0", "--coil-disconnect-tick", "10000000",
     "--coil-reconnect-tick", "11000000"])
assert [(event["type"], event["tick"], event["channel"])
        for event in events if event["type"] in
        ("coil_disconnect", "coil_reconnect")] == [
            ("coil_disconnect", 10000000, 0),
            ("coil_reconnect", 11000000, 0)]
assert normal_lambda[9900000] == fault_lambda[9900000]
assert normal_fire[9900000] == fault_fire[9900000]
assert fault_fire[10890000]["missed"] > 0
assert fault_fire[10890000]["rpm"] < normal_fire[10890000]["rpm"] - 300
exhaust = fault_lambda[10890000]
assert exhaust["valid"] and exhaust["physical"] < 1.0
assert exhaust["oxygen_equivalent"] > 1.5
assert (exhaust["oxygen_equivalent"] >
        normal_lambda[10890000]["oxygen_equivalent"] + 0.5)
assert exhaust["voltage_v"] < 0.2 and exhaust["adc5_pin_v"] < 1.0
assert exhaust["ram65"] < normal_lambda[10890000]["ram65"]
assert fault_fire[11880000]["rpm"] > fault_fire[10890000]["rpm"] + 300
assert fault_fire[11880000]["missed"] == fault_fire[15840000]["missed"]
assert fault_lambda[11880000]["oxygen_equivalent"] < 1.0
assert fault_lambda[11880000]["voltage_v"] > 0.7
assert all(event["f84e"] == event["f84f"] == 0 for event in events
           if event["type"] == "diagnostic" and event["tick"] >= 11880000)
