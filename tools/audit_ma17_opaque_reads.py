#!/usr/bin/env python3
"""Audit effective MOVC reads of catalogued nonpointer ROM intervals."""

import argparse
import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "build" / "ma17-analysis" / "variants"


def audit(catalog, trace_paths):
    rows = []
    for item in catalog["unclassified_nonpointer_intervals"]:
        start, end = int(item["start"], 16), int(item["end_exclusive"], 16)
        if not 0 <= start < end <= 0x8000:
            raise ValueError(f"invalid interval: {item['id']}")
        rows.append({"id": item["id"], "start": start, "end": end,
                     "files": set(), "occurrences": 0,
                     "by_rom": collections.Counter(),
                     "states": collections.Counter()})
    all_files = collections.Counter()
    traced_files = collections.Counter()
    for path in trace_paths:
        report = json.loads(Path(path).read_text())
        rom = report["firmware_sha256"]
        all_files[rom] += 1
        observation = report.get("movc_observation", {})
        if not observation.get("enabled", False):
            continue
        traced_files[rom] += 1
        for read in observation.get("reads", []):
            effective = int(read.get("mapped", read["address"]), 16)
            count = read["count"]
            for row in rows:
                if row["start"] <= effective < row["end"]:
                    row["files"].add(str(path))
                    row["occurrences"] += count
                    row["by_rom"][rom] += count
                    state = (read["pc"], read["opcode"], read["dptr"],
                             read["address"], f"{effective:04X}")
                    row["states"][state] += count
    return {
        "trace_files": sum(all_files.values()),
        "movc_enabled_trace_files": sum(traced_files.values()),
        "trace_files_by_rom": dict(sorted(all_files.items())),
        "movc_enabled_trace_files_by_rom": dict(sorted(traced_files.items())),
        "intervals": [{
            "id": row["id"], "start": f"0x{row['start']:04X}",
            "end_exclusive": f"0x{row['end']:04X}",
            "trace_files_with_reads": len(row["files"]),
            "occurrences": row["occurrences"],
            "occurrences_by_rom": dict(sorted(row["by_rom"].items())),
            "states": [dict(zip(("pc", "opcode", "dptr", "address", "mapped"), key),
                            occurrences=count)
                       for key, count in sorted(row["states"].items())],
        } for row in rows],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    catalog = json.loads((ROOT / "docs" / "MA17_CALIBRATION_CATALOG.json").read_text())
    paths = sorted(args.analysis_dir.rglob("execution.json"))
    report = audit(catalog, paths)
    output = args.output or args.analysis_dir / "opaque_read_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
