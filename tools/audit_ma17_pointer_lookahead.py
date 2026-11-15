#!/usr/bin/env python3
"""Audit direct DPTR selections and adjacent MOVC reads in MA1.7 traces."""

import argparse
import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "build" / "ma17-analysis" / "variants"


def audit(catalog, trace_paths):
    """Count observed MOVC @A+DPTR states per provisional pointer interval."""
    slots = {}
    for candidate in catalog["candidates"]:
        bounds = {(int(version["start"], 16),
                   int(version["candidate_end_exclusive"], 16))
                  for version in candidate["versions"]}
        if len(bounds) != 1:
            raise ValueError(f"variant intervals differ for {candidate['pointer_slot']}")
        start, end = bounds.pop()
        if not start < end:
            raise ValueError(f"invalid interval for {candidate['pointer_slot']}")
        slots[candidate["pointer_slot"]] = {
            "start": start, "end_exclusive": end,
            "direct_base": {"files": set(), "occurrences": 0, "states": {},
                            "files_by_rom": collections.defaultdict(set),
                            "occurrences_by_rom": collections.Counter()},
            "cross_boundary": {"files": set(), "occurrences": 0, "states": {},
                               "files_by_rom": collections.defaultdict(set),
                               "occurrences_by_rom": collections.Counter()},
        }

    trace_count = 0
    traces_by_rom = collections.Counter()
    for path in trace_paths:
        trace_count += 1
        trace = json.loads(path.read_text())
        rom_hash = trace["firmware_sha256"]
        traces_by_rom[rom_hash] += 1
        observation = trace.get("movc_observation", {})
        for read in observation.get("reads", []):
            if read["opcode"].upper() != "93":
                continue  # MOVC @A+PC does not use DPTR.
            dptr = int(read["dptr"], 16)
            address = int(read["address"], 16)
            count = read["count"]
            for row in slots.values():
                if dptr == row["start"]:
                    kind = "direct_base"
                elif row["start"] <= address < row["end_exclusive"]:
                    kind = "cross_boundary"
                else:
                    continue
                bucket = row[kind]
                bucket["files"].add(str(path))
                bucket["files_by_rom"][rom_hash].add(str(path))
                bucket["occurrences"] += count
                bucket["occurrences_by_rom"][rom_hash] += count
                state = (read["pc"], read["dptr"], read["address"], read["value"])
                bucket["states"][state] = bucket["states"].get(state, 0) + count

    result = {"trace_files": trace_count,
              "trace_files_by_rom": dict(sorted(traces_by_rom.items())),
              "slots": []}
    for pointer_slot, row in sorted(slots.items()):
        record = {"pointer_slot": pointer_slot,
                  "start": f"0x{row['start']:04X}",
                  "end_exclusive": f"0x{row['end_exclusive']:04X}"}
        for kind in ("direct_base", "cross_boundary"):
            bucket = row[kind]
            record[kind] = {
                "trace_files": len(bucket["files"]),
                "occurrences": bucket["occurrences"],
                "by_rom": {
                    rom_hash: {"trace_files": len(bucket["files_by_rom"][rom_hash]),
                               "occurrences": bucket["occurrences_by_rom"][rom_hash]}
                    for rom_hash in sorted(traces_by_rom)},
                "states": [
                    {"pc": pc, "dptr": dptr, "address": address,
                     "value": value, "occurrences": count}
                    for (pc, dptr, address, value), count
                    in sorted(bucket["states"].items())],
            }
        result["slots"].append(record)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    catalog = json.loads((args.analysis_dir / "provisional_pointer_catalog.json").read_text())
    paths = sorted(args.analysis_dir.rglob("execution.json"))
    report = audit(catalog, paths)
    output = args.output or args.analysis_dir / "pointer_lookahead_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
