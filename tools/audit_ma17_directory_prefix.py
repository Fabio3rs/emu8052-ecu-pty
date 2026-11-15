#!/usr/bin/env python3
"""Audit effective MOVC reads of the two-byte ROM directory prefix."""

import argparse
import collections
import json
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "build/ma17-analysis/variants"


def audit(root):
    reports = sorted(root.rglob("execution.json"))
    by_firmware = collections.Counter()
    enabled = 0
    hits = []
    for path in reports:
        data = json.loads(path.read_text())
        observation = data.get("movc_observation") or {}
        rows = observation.get("reads") or []
        if not rows:
            continue
        enabled += 1
        firmware = data.get("firmware_sha256") or "unknown"
        by_firmware[firmware] += 1
        for row in rows:
            address = row.get("address", row.get("mapped"))
            if address in ("7000", "7001"):
                hits.append({"report": str(path.relative_to(root)),
                             "firmware_sha256": firmware,
                             "pc": row.get("pc"), "address": address,
                             "count": row.get("count", 1)})
    return {"scope": "effective MOVC addresses in available execution.json reports",
            "execution_files": len(reports), "movc_reports": enabled,
            "reports_by_firmware_sha256": dict(sorted(by_firmware.items())),
            "prefix_read_occurrences": sum(hit["count"] for hit in hits),
            "prefix_read_rows": hits,
            "limitation": "Negative observations do not exclude untested paths or external readers"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"execution_files": result["execution_files"],
                      "movc_reports": result["movc_reports"],
                      "prefix_read_occurrences": result["prefix_read_occurrences"]}))


if __name__ == "__main__":
    main()
