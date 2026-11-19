"""Fit original Fiat P5 edges against ROM ignition byte in physical runs."""

import json
import math
import os
import re
import statistics
import subprocess
import sys


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "4000000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
        "--lambda-adc-gain", "5"]
env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
       "MA17_TRACE_PC": "1"}


def fit(rows):
    mean_byte = statistics.mean(byte for byte, _ in rows)
    mean_phase = statistics.mean(phase for _, phase in rows)
    slope = sum((byte - mean_byte) * (phase - mean_phase)
                for byte, phase in rows) / sum(
                    (byte - mean_byte) ** 2 for byte, _ in rows)
    intercept = mean_phase - slope * mean_byte
    rms = math.sqrt(statistics.mean(
        (phase - intercept - slope * byte) ** 2 for byte, phase in rows))
    return slope, intercept, rms


all_rows = []
for extra in ([], ["--load-step-tick", "800000", "--load-nm", "24"],
              ["--pedal-step-tick", "800000", "--pedal-mm", "8"]):
    result = subprocess.run(base + extra, env=env, capture_output=True,
                            text=True, timeout=50, check=True)
    pins = [json.loads(line) for line in result.stdout.splitlines()
            if line.startswith('{"type":"ignition_pin"')]
    latch = {int(match[1]): int(match[2], 16)
             for line in result.stderr.splitlines()
             if (match := re.search(
                 r"\[P5-LATCH\] instr=(\d+).*RAM69=([0-9A-F]{2})", line))}
    rising = [pin for pin in pins if pin["tick"] >= 800000 and pin["high"]
              and pin["tick"] in latch]
    assert {pin["channel"] for pin in rising} == {0, 1}
    rows = [(latch[pin["tick"]], math.degrees(pin["angle_rad"]) % 180.0)
            for pin in rising]
    assert len(rows) > 40
    bytes_seen = {byte for byte, _ in rows}
    # These 4 M-tick windows cover cranking and load/pedal transients, where
    # the ROM latency to the P5 edge varies with engine acceleration. Since the
    # engine has friction and pumping drag (ca6f99c) the windows hold fewer
    # samples and, for the load step, only 3 distinct RAM69 values (measured
    # slope 0.372, 0.371, 0.344; rms 0.33, 0.12, 1.31), so the slope is only
    # constrained when RAM69 actually varies. The tight check is the steady
    # idle fit below.
    if max(bytes_seen) - min(bytes_seen) >= 10:
        slope, intercept, rms = fit(rows)
        assert 0.33 < slope < 0.38
        assert 53.0 < intercept < 59.0
    else:
        _, _, rms = fit(rows) if len(bytes_seen) > 1 else (0, 0, 0.0)
    assert rms < 1.5
    all_rows.extend(rows)

assert len(all_rows) > 250
slope, intercept, rms = fit(all_rows)
assert 0.34 < slope < 0.37 and 54.0 < intercept < 59.0 and rms < 1.0

late_args = base.copy()
late_args[late_args.index("--stop-ticks") + 1] = "20000000"
late_result = subprocess.run(
    late_args + ["--load-step-tick", "800000", "--load-nm", "24",
                 "--throttle-leak-mm2", "9"],
    env=env, capture_output=True, text=True, timeout=80, check=True)
late_pins = [json.loads(line) for line in late_result.stdout.splitlines()
             if line.startswith('{"type":"ignition_pin"')]
late_latch = {int(match[1]): int(match[2], 16)
              for line in late_result.stderr.splitlines()
              if (match := re.search(
                  r"\[P5-LATCH\] instr=(\d+).*RAM69=([0-9A-F]{2})", line))}
late_rows = [(late_latch[pin["tick"]],
              math.degrees(pin["angle_rad"]) % 180.0)
             for pin in late_pins if pin["high"] and pin["tick"] >= 8000000
             and pin["tick"] in late_latch]
assert len(late_rows) > 300
late_slope, late_intercept, late_rms = fit(late_rows)
assert 0.34 < late_slope < 0.37
assert 54.0 < late_intercept < 59.0 and late_rms < 0.5
print(f"P5 phase = {intercept:.3f}° + {slope:.4f}° × RAM69; "
      f"RMS {rms:.3f}°, n={len(all_rows)}")

# In the physical Fiat scenario the cable step selects cells of the
# original 7B46h matrix. Other matrix bases exist but are not selected here.
matrix_base = base.copy()
matrix_base[matrix_base.index("--stop-ticks") + 1] = "15000000"
matrix_base += ["--load-step-tick", "800000", "--load-nm", "24"]
matrix_env = {**env, "MA17_TRACE_MOVC": "1"}


def matrix_reads(extra):
    result = subprocess.run(matrix_base + extra, env=matrix_env,
                            capture_output=True, text=True, timeout=80,
                            check=True)
    counts = {}
    for base_address in (0x7B46, 0x7BBE, 0x7C36,
                         0x7CAE, 0x7D26, 0x7D9E):
        counts[base_address] = sum(
            int(match[1]) for match in re.finditer(
                rf"\[MOVC-SUMMARY\] [^\n]*dptr={base_address:04X} "
                rf"[^\n]*count=(\d+)", result.stderr))
    return counts


steady_reads = matrix_reads([])
pedal_reads = matrix_reads(["--pedal-step-tick", "10000000",
                            "--pedal-release-tick", "12000000",
                            "--pedal-mm", "12"])
assert steady_reads[0x7B46] > 100
assert pedal_reads[0x7B46] > steady_reads[0x7B46] + 500
assert all(steady_reads[address] == pedal_reads[address] == 0
           for address in steady_reads if address != 0x7B46)
