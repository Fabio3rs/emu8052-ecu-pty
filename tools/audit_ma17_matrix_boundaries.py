#!/usr/bin/env python3
"""Distinguish matrix or curve spill reads from selecting the next table."""

import argparse
import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "build/ma17-analysis/variants"


def audit(catalog, trace_paths, *, exclude_overrides=False, emulator_sha256=None,
          curve=False):
    matrices = {}
    table_starts = {int(item["start"], 16): item["id"]
                    for item in catalog["tables"] if "start" in item}
    dimensions, extent = ([10], 10) if curve else ([8, 15], 120)
    for item in catalog["tables"]:
        if item.get("dimensions") != dimensions:
            continue
        start, end = int(item["start"], 16), int(item["end_exclusive"], 16)
        if end - start != extent:
            if curve:
                continue  # A ten-value segment table also includes its header.
            raise ValueError(f"invalid {dimensions} extent: {item['id']}")
        matrices[start] = (item["id"], end)
    known_roms = set(catalog["rom_sha256"].values())
    selected = collections.Counter()
    crossings = collections.Counter()
    files = collections.defaultdict(set)
    considered = traced = 0
    for path in trace_paths:
        report = json.loads(Path(path).read_text())
        rom = report.get("firmware_sha256")
        if rom not in known_roms or (emulator_sha256 is not None and
                                    report.get("emulator_sha256") != emulator_sha256):
            continue
        if exclude_overrides and (report.get("movc_matrix_donor_sha256") or
                                  any(value not in (None, False, "")
                                      for key, value in report.items()
                                      if "override" in key)):
            continue
        considered += 1
        observation = report.get("movc_observation", {})
        if not observation.get("enabled", False):
            continue
        traced += 1
        for read in observation.get("reads", []):
            if read["opcode"] != "93":
                continue  # MOVC @A+PC does not use DPTR as a matrix base.
            base = int(read["dptr"], 16)
            if base not in matrices:
                continue
            address = int(read.get("mapped", read["address"]), 16)
            count = read["count"]
            selected[(base, rom)] += count
            if address != matrices[base][1]:
                continue
            key = (base, address, read["pc"], rom)
            crossings[key] += count
            files[key].add(str(path))
    return {
        "trace_files_considered": considered,
        "movc_enabled_trace_files": traced,
        "filter": {"exclude_overrides": exclude_overrides,
                   "emulator_sha256": emulator_sha256,
                   "dimensions": dimensions},
        "base_selected_reads": [
            {"table": matrices[base][0], "base": f"{base:04X}",
             "rom_sha256": rom, "count": count}
            for (base, rom), count in sorted(selected.items())],
        "one_past_reads": [
            {"source_table": matrices[base][0], "source_base": f"{base:04X}",
             "read_address": f"{address:04X}",
             "next_table": table_starts.get(address),
             "pc": pc, "rom_sha256": rom, "count": count,
             "trace_files": len(files[(base, address, pc, rom)]),
             "example": min(files[(base, address, pc, rom)])}
            for (base, address, pc, rom), count in sorted(crossings.items())],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--exclude-overrides", action="store_true")
    parser.add_argument("--emulator-sha256")
    parser.add_argument("--curve", action="store_true",
                        help="audit ten-byte curves instead of 8x15 matrices")
    args = parser.parse_args()
    catalog = json.loads((ROOT / "docs/MA17_CALIBRATION_CATALOG.json").read_text())
    report = audit(catalog, sorted(args.analysis_dir.rglob("execution.json")),
                   exclude_overrides=args.exclude_overrides,
                   emulator_sha256=args.emulator_sha256, curve=args.curve)
    name = "curve_boundary_audit.json" if args.curve else "matrix_boundary_audit.json"
    output = args.output or args.analysis_dir / name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
