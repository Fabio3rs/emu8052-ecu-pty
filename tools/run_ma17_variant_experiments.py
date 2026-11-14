#!/usr/bin/env python3
"""Repeat controlled gasoline/SUN 8817 ROM experiments in the Fiat harness."""

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

from compare_ma17_variants import REFERENCE, VARIANTS, compare


ROOT = Path(__file__).resolve().parents[1]
SUN8817 = VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin"
SCENARIOS = (("rpm750", 750, {}),
             ("rpm1000", 1000, {}),
             ("rpm2000", 2000, {}),
             ("adc1_40", 1000, {1: 40}),
             ("gate63_baseline", 1000, {7: 63}),
             ("gate63_air_adc2_40", 1000, {2: 40, 7: 63}),
             ("gate63_coolant_adc3_40", 1000, {3: 40, 7: 63}),
             ("gate63_tps_40_95", 1000, {0: 40, 6: 95, 7: 63}),
             ("gate63_tps_120_180", 1000, {0: 120, 6: 180, 7: 63}))
TEMPERATURE_SCENARIOS = tuple(
    (f"air_adc2_{raw}", 1000, {2: raw, 7: 63})
    for raw in (20, 80, 160, 220)) + tuple(
    (f"coolant_adc3_{raw}", 1000, {3: raw, 7: 63})
    for raw in (20, 80, 160, 220))


def last_value(report, address):
    changes = report["engine_ram_observation"].get(address, [])
    return changes[-1]["after"] if changes else None


def last_sensor(report, address):
    changes = report.get("sensor_ram_observation", {}).get(address, [])
    return changes[-1]["after"] if changes else None


def summarize(report, scenario, variant, ranges):
    reads = report["movc_observation"]["reads"]
    regions = []
    for start, end in ranges:
        matching = [row for row in reads if start <= int(row["mapped"], 16) < end]
        regions.append({"start": f"0x{start:04X}",
                        "end_exclusive": f"0x{end:04X}",
                        "movc_reads": sum(row["count"] for row in matching),
                        "read_sites": sorted({row["pc"] for row in matching})})
    return {"scenario": scenario, "variant": variant,
            "firmware_sha256": report["firmware_sha256"],
            "stop_ticks": report.get("stop_ticks_observed"),
            "rpm": report["crank_target_rpm"],
            "adc0": report["adc_input_values"][0],
            "adc1": report["adc_input_values"][1],
            "adc2": report["adc_input_values"][2],
            "adc3": report["adc_input_values"][3],
            "adc6": report["adc_input_values"][6],
            "adc7": report["adc_input_values"][7],
            "complete_revolutions": report["wheel_observation"]["complete_revolutions"],
            "p5_0_low_width_ticks": report["output_latches"]["P5.0"]["median_low_width_ticks"],
            "p5_1_low_width_ticks": report["output_latches"]["P5.1"]["median_low_width_ticks"],
            "iram31": last_value(report, "31"), "iram69": last_value(report, "69"),
            "iram7d": last_value(report, "7D"),
            "iram7c": last_value(report, "7C"),
            "iram4e": last_value(report, "4E"),
            "iram78": last_value(report, "78"),
            "iram7a": last_value(report, "7A"),
            "iram48": last_value(report, "48"),
            "iram62": last_sensor(report, "62"),
            "iram63": last_sensor(report, "63"),
            "iram65": last_sensor(report, "65"),
            "iram6f": last_sensor(report, "6F"),
            "cc3_scheduling_samples": report["cc3_observation"]["iram14_15_scheduling_samples"],
            "injection_flow_pairs": report["injection_flow_observation"]["paired_checks"],
            "injection_flow_unchanged_pairs": report["injection_flow_observation"][
                "unchanged_r2r3_pairs"],
            "cc3_raw_iram14_15_median": report["cc3_observation"].get("iram14_15_median"),
            "cc3_pin_low_width_median_ticks": report["cc3_observation"].get(
                "cc3_pin_model_median_low_width_ticks"),
            "cc3_p5_phase_median_ticks": report.get("cc3_p5_phase_observation", {}).get(
                "cc3_low_after_p5_low_median_ticks"),
            "movc_total_reads": report["movc_observation"]["total_reads"],
            "matrix_7581_reads": sum(row["count"] for row in reads
                                     if 0x7581 <= int(row["mapped"], 16) < 0x7662),
            "lookup_total_calls": report.get("lookup_observation", {}).get("total_calls", 0),
            "lookup_states": report.get("lookup_observation", {}).get("states", []),
            "changed_region_reads": regions}


def experiment_environment(adc_settings):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                          "MA17_ADC10_STEP_CH",
                                          "MA17_OVERRIDE_"))}
    for channel, value in adc_settings.items():
        environment[f"MA17_ADC_CH{channel}"] = str(value)
    return environment


def run_case(firmware, variant, scenario, rpm, adc_settings, seconds,
             stop_ticks, destination, ranges):
    output = destination / scenario / variant
    output.mkdir(parents=True, exist_ok=True)
    environment = experiment_environment(adc_settings)
    command = [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
               "--firmware", str(firmware), "--trace-movc", "--trace-lookup",
               "--seconds", str(seconds),
               "--stop-ticks", str(stop_ticks),
               "--no-kline-inject", "--crank-immediate", "--rpm", str(rpm),
               "--output-dir", str(output)]
    process = subprocess.run(command, cwd=ROOT, env=environment,
                             capture_output=True, text=True, timeout=seconds + 20)
    if process.returncode:
        raise RuntimeError(f"{scenario}/{variant}: {process.stderr or process.stdout}")
    report = json.loads((output / "execution.json").read_text())
    if report["wheel_observation"]["complete_revolutions"] < 10:
        raise RuntimeError(f"{scenario}/{variant}: insufficient complete revolutions")
    result = summarize(report, scenario, variant, ranges)
    result["execution_report"] = os.path.relpath(output / "execution.json", ROOT)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=15,
                        help="maximum wall seconds per case")
    parser.add_argument("--stop-ticks", type=int, default=2400000,
                        help="same emulated tick count for every case")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "build" / "ma17-analysis" / "variants" / "experiments")
    parser.add_argument("--temperature-grid", action="store_true",
                        help="vary raw ADC2/ADC3 independently at fixed RPM and ADC7")
    args = parser.parse_args()
    if args.seconds <= 0 or args.stop_ticks <= 0:
        parser.error("--seconds and --stop-ticks must be positive")
    if REFERENCE.read_bytes()[:0x7580] != SUN8817.read_bytes()[:0x7580]:
        raise SystemExit("gasoline and SUN 8817 code prefixes no longer match")
    comparison = compare(REFERENCE.read_bytes(), SUN8817.read_bytes())
    ranges = [(row["start"], row["end_exclusive"])
              for row in comparison["changed_intervals"]]
    destination = args.output_dir.resolve()
    results = []
    scenarios = TEMPERATURE_SCENARIOS if args.temperature_grid else SCENARIOS
    for scenario, rpm, adc_settings in scenarios:
        for variant, firmware in (("gasoline", REFERENCE), ("sun8817", SUN8817)):
            row = run_case(firmware, variant, scenario, rpm, adc_settings,
                           args.seconds, args.stop_ticks, destination, ranges)
            results.append(row)
            print(f"{scenario}/{variant}: P5.0={row['p5_0_low_width_ticks']} "
                  f"IRAM31={row['iram31']} revs={row['complete_revolutions']}")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "experiments.json").write_text(json.dumps(results, indent=2) + "\n")
    fields = ("scenario", "variant", "firmware_sha256", "stop_ticks", "rpm", "adc0", "adc1",
              "adc2", "adc3", "adc6", "adc7", "iram62", "iram63", "iram65",
              "iram6f", "iram48", "cc3_scheduling_samples",
              "injection_flow_pairs", "injection_flow_unchanged_pairs",
              "cc3_raw_iram14_15_median", "cc3_pin_low_width_median_ticks",
              "cc3_p5_phase_median_ticks",
              "complete_revolutions", "p5_0_low_width_ticks",
              "p5_1_low_width_ticks", "iram31", "iram69", "iram7c", "iram7d",
              "iram4e", "iram78", "iram7a",
              "movc_total_reads", "matrix_7581_reads", "lookup_total_calls",
              "execution_report")
    with (destination / "experiments.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in results)


if __name__ == "__main__":
    main()
