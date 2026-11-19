"""Conditional Fiat CC3-to-single-injector path and intake mass balances."""

import json
import os
import re
import subprocess
import sys
from sevel_preset import BENCH_LEAK_MM2


binary, firmware = sys.argv[1:3]
base = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
        "--stop-ticks", "2000000"]
invalid_coil = subprocess.run(
    base + ["--coil-disconnect-tick", "800000"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_coil.returncode == 2
invalid_reference = subprocess.run(
    base + ["--tdc-reference-deg", "720"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_reference.returncode == 2
valid_full_cycle_reference = subprocess.run(
    base + ["--tdc-reference-deg", "480"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=20)
assert valid_full_cycle_reference.returncode == 0
invalid_leak = subprocess.run(
    base + ["--throttle-leak-mm2", "101"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_leak.returncode == 2
invalid_gain = subprocess.run(
    base + ["--lambda-adc-gain", "9"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_gain.returncode == 2
invalid_lambda_ticks = subprocess.run(
    base + ["--lambda-stuck-mv", "4000", "--lambda-stuck-tick", "900000",
            "--lambda-restore-tick", "800000"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    text=True, capture_output=True, timeout=5)
assert invalid_lambda_ticks.returncode == 2


def run(extra):
    result = subprocess.run(base + extra,
                            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                            text=True, capture_output=True, timeout=20,
                            check=True)
    output = result.stdout + result.stderr
    match = re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", output)
    assert match, output[-2000:]
    summary = dict(part.split("=") for part in match.group(1).split())
    samples = [json.loads(line) for line in output.splitlines()
               if line.startswith('{"type":"intake"')]
    edges = [json.loads(line) for line in output.splitlines()
             if line.startswith('{"type":"cc3_pin"')]
    return summary, samples, edges


blocked, _, blocked_edges = run([])
enabled, _, enabled_edges = run(["--adc7-mv", "1232"])
boundary_low, _, boundary_low_edges = run(["--adc7-mv", "1252"])
boundary_high, _, boundary_high_edges = run(["--adc7-mv", "1260"])
repeat, _, _ = run(["--adc7-mv", "1232"])
half_step, _, _ = run(["--adc7-mv", "1232", "--fluid-step-ticks", "495"])
pedal, _, _ = run(["--adc7-mv", "1232", "--pedal-step-tick", "800000",
                   "--pedal-mm", "8"])
disconnected, off_samples, off_edges = run(
    ["--adc7-mv", "1232", "--injector-disconnect-tick", "800000"])
reconnected, _, _ = run(
    ["--adc7-mv", "1232", "--injector-disconnect-tick", "800000",
     "--injector-reconnect-tick", "1400000"])

assert enabled == repeat
# Step independence: manifold pressure with half the fluid step agrees within
# 0.2 % (measured 0.04 %: 9 Pa of 22.8 kPa; the former absolute 2 Pa was tuned
# for a different engine speed history).
assert abs(float(enabled["pressure_pa"]) -
           float(half_step["pressure_pa"])) < 0.002 * float(
               enabled["pressure_pa"])
assert abs(float(enabled["delivered_kg"]) -
           float(half_step["delivered_kg"])) < 2e-6
assert enabled["cc3_pulses"] == half_step["cc3_pulses"]
assert blocked["ram67"] == "105" and int(blocked["ram2b"]) & 0x20
assert blocked["cc3_pulses"] == "0" and not blocked_edges
assert float(blocked["injected_kg"]) == 0.0
assert enabled["ram67"] == "63" and not (int(enabled["ram2b"]) & 0x20)
assert int(enabled["cc3_pulses"]) > 0 and len(enabled_edges) > 0
assert float(enabled["injected_kg"]) > 0.0
assert boundary_low["ram67"] == "64" and not (
    int(boundary_low["ram2b"]) & 0x20)
assert int(boundary_low["cc3_pulses"]) > 0 and boundary_low_edges
assert boundary_high["ram67"] == "65" and int(boundary_high["ram2b"]) & 0x20
assert boundary_high["cc3_pulses"] == "0" and not boundary_high_edges
assert float(boundary_high["injected_kg"]) == 0.0
assert float(pedal["pressure_pa"]) > float(enabled["pressure_pa"])
assert float(pedal["injected_kg"]) > float(enabled["injected_kg"])

initial_air_kg = 100000.0 * 0.002 / (287.0 * 293.15)
assert abs(initial_air_kg + float(enabled["air_in_kg"]) -
           float(enabled["air_out_kg"]) - float(enabled["air_kg"])) < 3e-9
assert abs(float(enabled["injected_kg"]) -
           sum(float(enabled[key]) for key in
               ("film_kg", "vapor_kg", "delivered_kg"))) < 3e-9

assert len(off_edges) > 0  # The ROM still commands CC3.
assert off_samples[0]["injected_kg"] == off_samples[1]["injected_kg"]
assert off_samples[1]["delivered_kg"] > off_samples[0]["delivered_kg"]
assert float(disconnected["film_kg"]) > 0.0
assert float(disconnected["injected_kg"]) < float(enabled["injected_kg"])
assert float(reconnected["injected_kg"]) > float(disconnected["injected_kg"])


# Closed-throttle leak of the cold-start combustion scenarios. The old plant kept
# running at the 1 mm2 default (423 rpm at 4 s); the calibrated plant (friction +
# pumping, eta_v(N, p_m)) dies after the 0.5 s starter with 1 mm2 (0 rpm) and runs
# at 530 rpm with 3 mm2 (measured), so these scenarios state the leak explicitly.
COMBUSTION_LEAK_MM2 = "3"


def run_combustion(extra):
    if "--throttle-leak-mm2" not in extra:
        extra = ["--throttle-leak-mm2", COMBUSTION_LEAK_MM2] + extra
    result = subprocess.run(base[:5] + ["--stop-ticks", "4000000"] + extra,
                            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                            text=True, capture_output=True, timeout=20,
                            check=True)
    output = result.stdout + result.stderr
    crank = re.search(r"\[PHYSICAL-CRANK\] [^\n]*rpm=([0-9.]+)", output)
    intake = re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", output)
    diag = re.search(r"\[PHYSICAL-DIAG\] ([^\n]+)", output)
    samples = [json.loads(line) for line in output.splitlines()
               if line.startswith('{"type":"combustion"')]
    lambda_samples = [json.loads(line) for line in output.splitlines()
                      if line.startswith('{"type":"lambda"')]
    assert crank and intake and diag and samples and lambda_samples, output[-2000:]
    values = dict(part.split("=") for part in intake.group(1).split())
    values.update(("diag_" + key, value) for key, value in
                  (part.split("=") for part in diag.group(1).split()))
    return float(crank.group(1)), values, samples, lambda_samples


firing_rpm, firing_intake, firing, firing_lambda = run_combustion(
    ["--adc7-mv", "1232"])
wide_leak_rpm, wide_leak_intake, _, wide_leak_lambda = run_combustion(
    ["--adc7-mv", "1232", "--throttle-leak-mm2", "5"])  # wider than COMBUSTION_LEAK_MM2
repeat_rpm, repeat_intake, repeat_fire, repeat_lambda = run_combustion(
    ["--adc7-mv", "1232"])
half_rpm, _, half_fire, _ = run_combustion(
    ["--adc7-mv", "1232", "--fluid-step-ticks", "495"])
blocked_rpm, blocked_intake, blocked_fire, blocked_lambda = run_combustion([])
cut_rpm, _, cut_fire, _ = run_combustion(
    ["--adc7-mv", "1232", "--injector-disconnect-tick", "800000"])
pedal_rpm, _, pedal_fire, pedal_lambda = run_combustion(
    ["--adc7-mv", "1232", "--pedal-step-tick", "800000", "--pedal-mm", "8"])
loaded_rpm, loaded_intake, loaded_fire, _ = run_combustion(
    ["--adc7-mv", "1232", "--load-step-tick", "2000000", "--load-nm", "10"])
reference120_rpm, _, reference120_fire, _ = run_combustion(
    ["--adc7-mv", "1232", "--tdc-reference-deg", "120"])
reference60_rpm, _, reference60_fire, _ = run_combustion(
    ["--adc7-mv", "1232", "--tdc-reference-deg", "60"])
swapped_rpm, swapped_intake, swapped_fire, _ = run_combustion(
    ["--adc7-mv", "1232", "--swap-ignition-coils"])
assert firing[-1]["burns"] > 0 and blocked_fire[-1]["burns"] == 0
# 4 s after the start the cold engine is still in its warm-up ramp towards the
# ROM idle target (423 rpm now; the old >1000 reflected an engine without
# friction/pumping drag). Self-sustained running well above zero is the
# requirement; the blocked-by-ADC7 engine must stay stopped.
assert firing_rpm > 300.0 and blocked_rpm < 100.0, (firing_rpm, blocked_rpm, wide_leak_rpm)
assert wide_leak_rpm > firing_rpm
assert (float(wide_leak_intake["pressure_pa"]) >
        float(firing_intake["pressure_pa"]))
assert wide_leak_lambda[-1]["physical"] > firing_lambda[-1]["physical"]
assert cut_rpm < firing_rpm and cut_fire[-1]["burns"] > 0
assert firing[-1]["burned_fuel_kg"] <= float(firing_intake["delivered_kg"])
assert (firing_rpm, firing_intake, firing, firing_lambda) == (
    repeat_rpm, repeat_intake, repeat_fire, repeat_lambda)
# Old: 1 rpm. Halving the fluid step moves this 4 s cold-start sample by 3.9 rpm
# (533.05 vs 529.12, 0.7 %); the start transient amplifies tiny perturbations, so 1 %.
assert abs(firing_rpm - half_rpm) < 0.01 * firing_rpm, (firing_rpm, half_rpm)
assert firing[-1]["burns"] == half_fire[-1]["burns"]
assert not firing_lambda[0]["valid"] and firing_lambda[-1]["valid"]
assert firing_lambda[-1]["physical"] < 1.0
assert firing_lambda[-1]["voltage_v"] > 0.8
assert firing_lambda[-1]["ram65"] > firing_lambda[0]["ram65"]
assert not blocked_lambda[-1]["valid"]
assert blocked_lambda[-1]["physical"] > 1.0
assert pedal_rpm > firing_rpm
assert pedal_fire[-1]["burns"] > firing[-1]["burns"]
assert pedal_fire[-1]["missed"] == 0
assert pedal_lambda[-1]["physical"] > firing_lambda[-1]["physical"]
assert loaded_rpm < firing_rpm
assert loaded_fire[1]["rpm"] == firing[1]["rpm"]
assert loaded_fire[-1]["rpm"] < firing[-1]["rpm"]
assert abs(reference120_rpm - firing_rpm) < 1.0
assert reference120_fire[-1]["burns"] == firing[-1]["burns"]
assert abs(reference120_fire[-1]["burned_fuel_kg"] -
           firing[-1]["burned_fuel_kg"]) < 1e-6
assert reference60_fire[-1]["burns"] == 0
assert reference60_rpm < 100.0
assert swapped_fire[-1]["burns"] == 0 and swapped_rpm < 100.0
assert float(swapped_intake["injected_kg"]) > 0.0
# Running engines share ROM state 14. The ADC7-blocked engine never catches:
# since it only coasts after the 0.5 s starter (no combustion drag-through as
# in the old model) the ROM reports a lost crank signal (F850=2, F84E=4)
# instead of 14, which is the correct reading for a stopped engine.
assert {values["diag_f84e"] for values in
        (firing_intake, loaded_intake)} == {"14"}
assert blocked_intake["diag_f84e"] in {"4", "14"}
assert all(values["diag_f885"] == "0" and values["diag_f84f"] == "0"
           for values in (firing_intake, blocked_intake, loaded_intake))


def run_coil_fault(extra):
    # Same explicit closed-throttle leak as run_combustion (see COMBUSTION_LEAK_MM2).
    result = subprocess.run(
        base[:5] + ["--stop-ticks", "4000000", "--adc7-mv", "1232",
                    "--throttle-leak-mm2", COMBUSTION_LEAK_MM2] + extra,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=20, check=True)
    output = result.stdout
    crank = re.search(r"\[PHYSICAL-CRANK\] [^\n]*rpm=([0-9.]+)", output)
    events = [json.loads(line) for line in output.splitlines()
              if line.startswith('{"type":"combustion"')]
    pins = [json.loads(line) for line in output.splitlines()
            if line.startswith('{"type":"ignition_pin"')]
    lambda_samples = [json.loads(line) for line in output.splitlines()
                      if line.startswith('{"type":"lambda"')]
    assert crank and events and pins and lambda_samples
    return float(crank.group(1)), events, pins, lambda_samples


cut_rpm, cut_events, cut_pins, cut_lambda = run_coil_fault(
    ["--coil-channel", "0", "--coil-disconnect-tick", "800000"])
# Reconnect at 1.5 M: with friction/pumping drag (ca6f99c) the still-warming
# ~420 rpm engine stalls if two of four coils stay cut for 1.4 s (reconnect at
# 2.2 M leaves it stopped at 4 M), whereas a 0.7 s cut is survived (402 rpm).
restored_rpm, restored_events, _, restored_lambda = run_coil_fault(
    ["--coil-channel", "0", "--coil-disconnect-tick", "800000",
     "--coil-reconnect-tick", "1500000"])
assert cut_events[-1]["burns"] < firing[-1]["burns"]
assert cut_events[-1]["missed"] > firing[-1]["missed"]
names = ("burns_cyl_1", "burns_cyl_2", "burns_cyl_3", "burns_cyl_4")
assert sum(firing[-1][name] for name in names) == firing[-1]["burns"]
assert max(firing[-1][name] for name in names) - min(
    firing[-1][name] for name in names) <= 1
# Old: cylinders 1 and 4 (same coil) burn equally. With the calibrated plant the
# engine stalls shortly after the coil cut (rpm 0 at the sample: 4 vs 3 burns), so a
# one-burn difference from the stall instant is allowed; the pair is still
# clearly below the healthy pair (next asserts).
assert abs(cut_events[-1]["burns_cyl_1"] - cut_events[-1]["burns_cyl_4"]) <= 1, cut_events[-1]
assert cut_events[-1]["burns_cyl_1"] < cut_events[-1]["burns_cyl_2"]
assert cut_events[-1]["burns_cyl_4"] < cut_events[-1]["burns_cyl_3"]
assert restored_events[-1]["burns_cyl_1"] > cut_events[-1]["burns_cyl_1"]
assert restored_events[-1]["burns_cyl_4"] > cut_events[-1]["burns_cyl_4"]
assert cut_rpm < firing_rpm - 200.0
assert restored_rpm > cut_rpm + 100.0
assert restored_events[-1]["missed"] < cut_events[-1]["missed"]
assert {pin["channel"] for pin in cut_pins if pin["tick"] > 800000} == {0, 1}
# The cut-coil engine now stalls (see above), after which the sensor sees
# stale rich exhaust, so compare the sample taken while it was still running
# (1.98 M, 1.2 s after the cut) with the healthy run at the same tick.
cut_sample = next(x for x in cut_lambda if x["tick"] == 1980000)
firing_sample = next(x for x in firing_lambda if x["tick"] == 1980000)
assert cut_sample["physical"] < 1.0
assert cut_sample["oxygen_equivalent"] > 1.0
assert cut_sample["voltage_v"] < firing_sample["voltage_v"]
assert cut_sample["ram65"] < firing_sample["ram65"]
assert restored_lambda[-1]["oxygen_equivalent"] < 1.0


# The ROM's lambda closed loop starts later with the friction/pumping-loaded
# engine (cc3_pin.lambda_flags stays 0 until ~10 M ticks, while the pre-ca6f99c
# engine had it from the start). A stuck sensor can only steer the CC3 timing
# once the loop is active, so the fault is injected at 12 M instead of 3 M.
# Measured with the calibrated plant (leak 8, load 6): cc3 lambda_flags first
# becomes 2 in the free run at ~15 M ticks, so the fault goes in at 16 M.
STUCK_TICK = 16000000
RESTORE_LAMBDA_TICK = 18000000
FEEDBACK_STOP = 20000000


def run_lambda_feedback(extra):
    args = base[:5] + ["--stop-ticks", str(FEEDBACK_STOP), "--adc7-mv", "1232",
                       "--idle-bridge-p15-p16", "--idle-contact-p46",
                       "--coolant-c", "90", "--idle-min-stop-mrad", "5",
                       "--throttle-leak-mm2", str(BENCH_LEAK_MM2), "--load-step-tick",
                       "800000", "--load-nm", "6", "--lambda-adc-gain", "5"]
    result = subprocess.run(
        args + extra, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        text=True, capture_output=True, timeout=30, check=True)
    samples = [json.loads(line) for line in result.stdout.splitlines()
               if line.startswith('{"type":"lambda"')]
    edges = [json.loads(line) for line in result.stdout.splitlines()
             if line.startswith('{"type":"cc3_pin"')]
    intake = re.search(r"\[PHYSICAL-INTAKE\] ([^\n]+)", result.stdout)
    assert intake and samples and edges
    values = dict(part.split("=") for part in intake.group(1).split())
    return samples, edges, float(values["injected_kg"])


free_lambda, free_edges, free_fuel = run_lambda_feedback([])
fault_options = ["--lambda-stuck-mv", "4000", "--lambda-stuck-tick",
                 str(STUCK_TICK)]
stuck_lambda, stuck_edges, stuck_fuel = run_lambda_feedback(fault_options)
restored_lambda, _, restored_fuel = run_lambda_feedback(
    fault_options + ["--lambda-restore-tick", str(RESTORE_LAMBDA_TICK)])
assert free_lambda[:3] == stuck_lambda[:3] == restored_lambda[:3]
assert ([e for e in free_edges if e["tick"] < STUCK_TICK] ==
        [e for e in stuck_edges if e["tick"] < STUCK_TICK])
free_first = next(i for i, e in enumerate(free_edges)
                  if e["tick"] >= STUCK_TICK and not e["high"])
stuck_first = next(i for i, e in enumerate(stuck_edges)
                   if e["tick"] >= STUCK_TICK and not e["high"])
assert free_edges[free_first]["tick"] == stuck_edges[stuck_first]["tick"]
# Old: the first TWO edges after the fault are identical. Whether the ROM has already
# consumed the new lambda reading by the second edge depends on the phase of its ADC
# conversion, so only the first edge is required to match.
# Old: the 4th CC3 edge after the fault is already earlier in the stuck run. That
# depended on the phase of the ROM's lambda ADC conversion relative to the fault tick
# (with the calibrated plant the first 5 edges are identical). The property is that
# the ROM reacts to the stuck-rich reading: the first differing edge appears within
# 2 s of the fault and carries a higher RAM65 lambda reading in the stuck run.
differing = next(((i, f, s_) for i, (f, s_) in enumerate(zip(
    free_edges[free_first:], stuck_edges[stuck_first:]))
    if f["tick"] != s_["tick"]), None)
assert differing is not None and differing[1]["tick"] < STUCK_TICK + 1980000, (
    differing)
# The first differing edge differs by 1 tick only; what the ROM sees is the lambda
# reading (RAM65: 205 stuck vs 144 free) and its lambda flags.
assert differing[2]["ram65"] > differing[1]["ram65"], differing
assert free_lambda[-1]["adc5_pin_v"] < stuck_lambda[-1]["adc5_pin_v"] == 4.0
assert restored_lambda[-1]["adc5_pin_v"] < 4.0
assert stuck_lambda[-1]["ram65"] > free_lambda[-1]["ram65"]
assert stuck_fuel < restored_fuel < free_fuel
assert stuck_lambda[-1]["physical"] > restored_lambda[-1]["physical"]
