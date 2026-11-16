"""Conditional Fiat CC3-to-single-injector path and intake mass balances."""

import json
import os
import re
import subprocess
import sys


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
assert abs(float(enabled["pressure_pa"]) -
           float(half_step["pressure_pa"])) < 2.0
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


def run_combustion(extra):
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
    ["--adc7-mv", "1232", "--throttle-leak-mm2", "3"])
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
assert firing_rpm > 1000.0 and blocked_rpm < 100.0
assert wide_leak_rpm > firing_rpm
assert (float(wide_leak_intake["pressure_pa"]) >
        float(firing_intake["pressure_pa"]))
assert wide_leak_lambda[-1]["physical"] > firing_lambda[-1]["physical"]
assert cut_rpm < firing_rpm and cut_fire[-1]["burns"] > 0
assert firing[-1]["burned_fuel_kg"] <= float(firing_intake["delivered_kg"])
assert (firing_rpm, firing_intake, firing, firing_lambda) == (
    repeat_rpm, repeat_intake, repeat_fire, repeat_lambda)
assert abs(firing_rpm - half_rpm) < 1.0
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
assert {values["diag_f84e"] for values in
        (firing_intake, blocked_intake, loaded_intake)} == {"14"}
assert all(values["diag_f885"] == "0" and values["diag_f84f"] == "0"
           for values in (firing_intake, blocked_intake, loaded_intake))


def run_coil_fault(extra):
    result = subprocess.run(
        base[:5] + ["--stop-ticks", "4000000", "--adc7-mv", "1232"] + extra,
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
restored_rpm, restored_events, _, restored_lambda = run_coil_fault(
    ["--coil-channel", "0", "--coil-disconnect-tick", "800000",
     "--coil-reconnect-tick", "2200000"])
assert cut_events[-1]["burns"] < firing[-1]["burns"]
assert cut_events[-1]["missed"] > firing[-1]["missed"]
names = ("burns_cyl_1", "burns_cyl_2", "burns_cyl_3", "burns_cyl_4")
assert sum(firing[-1][name] for name in names) == firing[-1]["burns"]
assert max(firing[-1][name] for name in names) - min(
    firing[-1][name] for name in names) <= 1
assert cut_events[-1]["burns_cyl_1"] == cut_events[-1]["burns_cyl_4"]
assert cut_events[-1]["burns_cyl_1"] < cut_events[-1]["burns_cyl_2"]
assert cut_events[-1]["burns_cyl_4"] < cut_events[-1]["burns_cyl_3"]
assert restored_events[-1]["burns_cyl_1"] > cut_events[-1]["burns_cyl_1"]
assert restored_events[-1]["burns_cyl_4"] > cut_events[-1]["burns_cyl_4"]
assert cut_rpm < firing_rpm - 200.0
assert restored_rpm > cut_rpm + 100.0
assert restored_events[-1]["missed"] < cut_events[-1]["missed"]
assert {pin["channel"] for pin in cut_pins if pin["tick"] > 800000} == {0, 1}
assert cut_lambda[-1]["physical"] < 1.0
assert cut_lambda[-1]["oxygen_equivalent"] > 1.0
assert cut_lambda[-1]["voltage_v"] < firing_lambda[-1]["voltage_v"]
assert cut_lambda[-1]["ram65"] < firing_lambda[-1]["ram65"]
assert restored_lambda[-1]["oxygen_equivalent"] < 1.0


def run_lambda_feedback(extra):
    args = base[:5] + ["--stop-ticks", "6000000", "--adc7-mv", "1232",
                       "--idle-bridge-p15-p16", "--idle-contact-p46",
                       "--coolant-c", "90", "--idle-min-stop-mrad", "5",
                       "--throttle-leak-mm2", "9", "--load-step-tick",
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
                 "3000000"]
stuck_lambda, stuck_edges, stuck_fuel = run_lambda_feedback(fault_options)
restored_lambda, _, restored_fuel = run_lambda_feedback(
    fault_options + ["--lambda-restore-tick", "4500000"])
assert free_lambda[:3] == stuck_lambda[:3] == restored_lambda[:3]
assert ([e for e in free_edges if e["tick"] < 3000000] ==
        [e for e in stuck_edges if e["tick"] < 3000000])
free_first = next(i for i, e in enumerate(free_edges)
                  if e["tick"] >= 3000000 and not e["high"])
stuck_first = next(i for i, e in enumerate(stuck_edges)
                   if e["tick"] >= 3000000 and not e["high"])
assert free_edges[free_first]["tick"] == stuck_edges[stuck_first]["tick"]
assert free_edges[free_first + 1]["tick"] == stuck_edges[stuck_first + 1]["tick"]
assert (stuck_edges[stuck_first + 3]["tick"] <
        free_edges[free_first + 3]["tick"])
assert free_lambda[-1]["adc5_pin_v"] < stuck_lambda[-1]["adc5_pin_v"] == 4.0
assert restored_lambda[-1]["adc5_pin_v"] < 4.0
assert stuck_lambda[-1]["ram65"] > free_lambda[-1]["ram65"]
assert stuck_fuel < restored_fuel < free_fuel
assert stuck_lambda[-1]["physical"] > restored_lambda[-1]["physical"]
