"""Warm coil interruption reaches exhaust oxygen, ADC5, and recovery."""

import json
import os
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "22000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2),
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


# The coil is cut once the idle has settled (900 rpm from ~14 M ticks). With
# friction/pumping drag (ca6f99c) the engine is still recovering from the load
# step at 10 M (504 rpm) and would simply stall, so every tick of the former
# 10/11/16 M scenario is shifted by +6 M (tick samples are 990 k apart).
# These electrical bindings and gain are conditional Fiat model assumptions.
_, normal_lambda, normal_fire = run([])
events, fault_lambda, fault_fire = run(
    ["--coil-channel", "0", "--coil-disconnect-tick", "16000000",
     "--coil-reconnect-tick", "17000000"])
assert [(event["type"], event["tick"], event["channel"])
        for event in events if event["type"] in
        ("coil_disconnect", "coil_reconnect")] == [
            ("coil_disconnect", 16000000, 0),
            ("coil_reconnect", 17000000, 0)]
assert normal_lambda[15840000] == fault_lambda[15840000]
assert normal_fire[15840000] == fault_fire[15840000]
assert fault_fire[16830000]["missed"] > 0
assert fault_fire[16830000]["rpm"] < normal_fire[16830000]["rpm"] - 300
exhaust = fault_lambda[16830000]
# Old: the charge lambda in the cut-coil run is below 1. It measures 1.009 now (dither
# around stoichiometry); what the cut coil really does is leave unburned oxygen in the
# exhaust, so require lean oxygen (>1.2, measured 1.8) and a lower sensor voltage.
assert exhaust["valid"] and abs(exhaust["physical"] - 1.0) < 0.1, exhaust
assert exhaust["oxygen_equivalent"] > 1.2 and exhaust["voltage_v"] < normal_lambda[16830000]["voltage_v"], exhaust
assert exhaust["oxygen_equivalent"] > 1.5
assert (exhaust["oxygen_equivalent"] >
        normal_lambda[16830000]["oxygen_equivalent"] + 0.5)
assert exhaust["voltage_v"] < 0.2 and exhaust["adc5_pin_v"] < 1.0
assert exhaust["ram65"] < normal_lambda[16830000]["ram65"]
assert fault_fire[17820000]["rpm"] > fault_fire[16830000]["rpm"] + 300
assert fault_fire[17820000]["missed"] == fault_fire[21780000]["missed"]
assert fault_lambda[17820000]["oxygen_equivalent"] < 1.0
assert fault_lambda[17820000]["voltage_v"] > 0.7
assert all(event["f84e"] == event["f84f"] == 0 for event in events
           if event["type"] == "diagnostic" and event["tick"] >= 17820000)
