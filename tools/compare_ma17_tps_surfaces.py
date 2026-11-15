#!/usr/bin/env python3
"""Compare two reproduced TPS ADC surfaces with the same stimuli and emulator."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "build" / "ma17-analysis" / "variants"
SCENARIO_KEYS = ("rpm", "stop_ticks", "fixed_adc",
                 "adc_defaults_unset_channels", "adc0_values", "adc6_values",
                 "point_override", "emulator_sha256")
OBSERVATION_KEYS = ("iram6f_hex", "header_reads",
                    "alternative_branch_reached")


def formula_state(case):
    sample = case.get("alternate_formula_sample")
    if sample is None:
        return None
    return {key: sample[key] for key in
            ("r2", "r3", "value", "ram28", "formula_matches")}


def compare(left, right):
    for key in SCENARIO_KEYS:
        if left.get(key) != right.get(key):
            raise ValueError(f"scenario differs at {key}")
    left_cases = {(case["adc0"], case["adc6"]): case
                  for case in left["cases"]}
    right_cases = {(case["adc0"], case["adc6"]): case
                   for case in right["cases"]}
    if (len(left_cases) != len(left["cases"]) or
            len(right_cases) != len(right["cases"])):
        raise ValueError("duplicate ADC pair")
    if left_cases.keys() != right_cases.keys():
        raise ValueError("ADC pair sets differ")
    matches = {key: 0 for key in (*OBSERVATION_KEYS, "alternate_formula_sample")}
    differences = []
    for adc0, adc6 in sorted(left_cases):
        a, b = left_cases[adc0, adc6], right_cases[adc0, adc6]
        changed = {}
        for key in OBSERVATION_KEYS:
            if a[key] == b[key]:
                matches[key] += 1
            else:
                changed[key] = {"left": a[key], "right": b[key]}
        first, second = formula_state(a), formula_state(b)
        if first == second:
            matches["alternate_formula_sample"] += 1
        else:
            changed["alternate_formula_sample"] = {
                "left": first, "right": second}
        if changed:
            differences.append({"adc0": adc0, "adc6": adc6,
                                "observations": changed})
    return {"left_variant": left.get("variant", "G"),
            "right_variant": right.get("variant", "G"),
            "left_rom_sha256": left["rom_sha256"],
            "right_rom_sha256": right["rom_sha256"],
            "emulator_sha256": left["emulator_sha256"],
            "case_count": len(left_cases), "matching_cases_by_field": matches,
            "differences": differences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", type=Path,
                        default=VARIANTS / "tps_surface_current" / "tps_surface.json")
    parser.add_argument("--right", type=Path,
                        default=VARIANTS / "tps_surface_s88_current" /
                                "tps_surface.json")
    parser.add_argument("--output", type=Path,
                        default=VARIANTS / "tps_surface_g_s88_comparison.json")
    args = parser.parse_args()
    result = compare(json.loads(args.left.read_text()),
                     json.loads(args.right.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"cases={result['case_count']} differences={len(result['differences'])}")


if __name__ == "__main__":
    main()
