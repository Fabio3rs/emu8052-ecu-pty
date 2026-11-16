"""Compare candidate P5 spark phase with the Fiat idle timing specification."""

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import subprocess


def run(binary, firmware, reference_deg, rom_hash):
    args = [binary, firmware, "--physical-crank", "--starter-ticks", "495000",
            "--stop-ticks", "20000000", "--adc7-mv", "1232",
            "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
            "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
            "--load-step-tick", "800000", "--load-nm", "24",
            "--lambda-adc-gain", "5", "--tdc-reference-deg", str(reference_deg)]
    result = subprocess.run(args, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
                            capture_output=True, text=True, timeout=90, check=True)
    lines = result.stdout.splitlines()
    pins = [json.loads(line) for line in lines
            if line.startswith('{"type":"ignition_pin"')]
    pins = [pin for pin in pins if pin["high"] and 15000000 <= pin["tick"] < 20000000
            and 800 <= pin["rpm"] <= 900]
    samples = [json.loads(line) for line in lines
               if line.startswith('{"type":"lambda"')]
    samples = [sample for sample in samples if sample["tick"] >= 15000000]
    crank = re.search(r"\[PHYSICAL-CRANK\] [^\n]*rpm=([0-9.]+)", result.stdout)
    diagnostic = re.search(r"\[PHYSICAL-DIAG\] ([^\n]+)", result.stdout)
    if not pins or not samples or not crank or not diagnostic:
        raise ValueError("missing idle edges, lambda samples or final summary")
    diag = dict(field.split("=") for field in diagnostic.group(1).split())
    advance = [((reference_deg - math.degrees(pin["angle_rad"]) % 180.0 + 90.0)
                % 180.0) - 90.0 for pin in pins]
    return {"tdc_reference_deg": reference_deg, "rom_sha256": rom_hash,
            "candidate_p5_advance_deg": round(statistics.median(advance), 2),
            "p5_edges_800_900rpm": len(pins),
            "final_rpm": float(crank.group(1)),
            "lambda_min_15_20s": min(sample["physical"] for sample in samples),
            "lambda_max_15_20s": max(sample["physical"] for sample in samples),
            "f84e": int(diag["f84e"]), "f85e": int(diag["f85e"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary")
    parser.add_argument("firmware")
    parser.add_argument("--reference-deg", type=int, action="append", dest="references")
    options = parser.parse_args()
    references = options.references if options.references is not None else [116, 118, 120]
    if any(not 0 <= reference <= 719 for reference in references):
        parser.error("reference degrees must be in 0..719")
    with open(options.firmware, "rb") as firmware:
        rom_hash = hashlib.file_digest(firmware, "sha256").hexdigest()
    for reference in references:
        print(json.dumps(run(options.binary, options.firmware, reference, rom_hash),
                         sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
