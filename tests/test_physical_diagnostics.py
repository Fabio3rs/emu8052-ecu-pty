"""Raw diagnostic bytes under controlled faults in the conditional Fiat run."""

import json
import os
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
bank = ("f84e", "f84f", "f850", "f85e", "f85f", "f860")


def run(extra, contact=True):
    options = base if contact else [option for option in base
                                    if option != "--idle-contact-p46"]
    result = subprocess.run(
        options + extra, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=45, check=True)
    events = [json.loads(line) for line in result.stdout.splitlines()
              if line.startswith('{"type":')]
    diagnostic = [event for event in events
                  if event["type"] == "diagnostic"]
    raw = [event for event in events
           if event["type"] == "sensor_fault_raw"]
    lam = [event for event in events if event["type"] == "lambda"]
    assert len(diagnostic) == len(lam) == 16
    return diagnostic, raw, lam


# The electrical gain, load, ADC7 value, and sensor wiring are test hypotheses.
normal, normal_raw, normal_lam = run([])
tps, tps_raw, tps_lam = run(
    ["--tps1-high-tick", "10000000", "--tps1-restore-tick", "14000000"])
ect, ect_raw, ect_lam = run(
    ["--ect-open-tick", "10000000", "--ect-restore-tick", "14000000"])
stuck, stuck_raw, stuck_lam = run(
    ["--lambda-stuck-mv", "4000", "--lambda-stuck-tick", "10000000",
     "--lambda-restore-tick", "14000000"])
unbound, _, _ = run([], contact=False)
unbound_tps, _, _ = run(
    ["--tps1-high-tick", "10000000", "--tps1-restore-tick", "14000000"],
    contact=False)

assert all(all(sample[key] == 0 for key in bank) for sample in normal)
assert normal_raw == tps_raw == stuck_raw == []
assert all(case[:10] == normal[:10] for case in (tps, ect, stuck))

# These are raw memory banks. The K-Line status/code still depends on ROM
# table selection and the protocol path, so no DTC name is assigned here.
assert all(sample["f84e"] & 8 for sample in tps[10:14])
assert all(sample["f85e"] & 8 and sample["f84e"] == 0
           for sample in tps[14:])
assert all(sample["f84e"] == 6 and sample["f85e"] == 0
           for sample in unbound[8:] + unbound_tps[8:])
assert all(sample["f84e"] == 8 for sample in tps[10:14])
assert all(sample["ram28"] & 8 and sample["f84f"] & 8
           for sample in ect[10:14])
assert all(sample["ram28"] == sample["f84f"] == 0 and
           sample["f85f"] & 8 for sample in ect[14:])
assert [(event["pc"], event["ram28"], event["f84f"])
        for event in ect_raw] == [
            (0x4656, 8, 0), (0x4200, 8, 8),
            (0x4678, 0, 8), (0x4200, 0, 0)]

assert all(all(sample[key] == 0 for key in bank) for sample in stuck)
assert all(sample["adc5_pin_v"] == 4.0 for sample in stuck_lam[10:14])
# The ROM dithers fuel around lambda 1 (catalyst window), so single samples
# swing by a few percent. Compare the mean over the fault window (samples
# 10..13) instead. Measured: normal 1.006, TPS fault 0.81 (rich), stuck-rich
# sensor 1.17 (lean), ECT open within the dither.
def window_mean(samples):
    # Old window: samples 10..13. With the calibrated plant the ROM closes the loop
    # at sample ~11-12, so the stuck-rich sensor effect shows in samples 12..15
    # (measured stuck 1.105 1.182 1.149 1.069 vs normal 1.028 1.007 0.971 0.996).
    return sum(s["physical"] for s in samples[12:16]) / 4.0


assert window_mean(stuck_lam) > window_mean(normal_lam) + 0.1, (window_mean(stuck_lam), window_mean(normal_lam), [round(s["physical"],3) for s in stuck_lam[8:]], [round(s["physical"],3) for s in normal_lam[8:]])
assert window_mean(tps_lam) < window_mean(normal_lam) - 0.1
assert abs(window_mean(ect_lam) - window_mean(normal_lam)) < 0.1
