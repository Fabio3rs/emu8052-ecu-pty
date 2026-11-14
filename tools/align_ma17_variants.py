#!/usr/bin/env python3
"""Find exact, uniquely anchored code spans across MA1.7 ROM revisions."""

import argparse
import collections
import hashlib
import json
from pathlib import Path

from roundtrip_8051 import classification


def code_positions(assembly, rom):
    owners = classification(assembly, rom)[3]
    return {address for address, line in owners.items()
            if not line.lower().startswith(("db ", "dw "))}


def unique_windows(rom, code, window, limit):
    found = {}
    repeated = set()
    for address in range(min(limit, len(rom)) - window + 1):
        if not all(offset in code for offset in range(address, address + window)):
            continue
        sample = rom[address:address + window]
        if sample in found:
            repeated.add(sample)
        else:
            found[sample] = address
    return {sample: address for sample, address in found.items()
            if sample not in repeated}


def align(reference, variant, reference_code, variant_code,
          window=32, min_span=64, limit=0x6E00):
    if window < 2 or min_span < window:
        raise ValueError("require window >= 2 and min_span >= window")
    left = unique_windows(reference, reference_code, window, limit)
    right = unique_windows(variant, variant_code, window, limit)
    anchors = sorted((address, right[sample] - address)
                     for sample, address in left.items() if sample in right)
    runs = []
    for address, delta in anchors:
        if runs and runs[-1][2] == delta and address <= runs[-1][1]:
            runs[-1] = (runs[-1][0], max(runs[-1][1], address + window), delta)
        else:
            runs.append((address, address + window, delta))
    selected = [(start, end, delta) for start, end, delta in runs
                if end - start >= min_span]
    for start, end, delta in selected:
        if reference[start:end] != variant[start + delta:end + delta]:
            raise ValueError(f"aligned bytes differ at 0x{start:04X}")
    histogram = collections.Counter(delta for _, delta in anchors)
    return {"window_bytes": window, "min_span_bytes": min_span,
            "code_limit_exclusive": f"0x{limit:04X}",
            "unique_anchors": len(anchors),
            "matched_span_bytes": sum(end - start for start, end, _ in selected),
            "delta_anchor_counts": {str(delta): count for delta, count in
                                    sorted(histogram.items())},
            "spans": [{"reference_start": f"0x{start:04X}",
                       "reference_end_exclusive": f"0x{end:04X}",
                       "variant_start": f"0x{start + delta:04X}",
                       "variant_end_exclusive": f"0x{end + delta:04X}",
                       "delta": delta, "bytes": end - start}
                      for start, end, delta in selected]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference_rom", type=Path)
    parser.add_argument("variant_rom", type=Path)
    parser.add_argument("--reference-asm", type=Path, required=True,
                        help="original disasm51 assembly from a verified round-trip")
    parser.add_argument("--variant-asm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = args.reference_rom.read_bytes()
    variant = args.variant_rom.read_bytes()
    reference_asm = args.reference_asm.read_text()
    variant_asm = args.variant_asm.read_text()
    result = align(reference, variant,
                   code_positions(reference_asm, reference),
                   code_positions(variant_asm, variant))
    result.update({"reference_rom": str(args.reference_rom),
                   "variant_rom": str(args.variant_rom),
                   "reference_sha256": hashlib.sha256(reference).hexdigest(),
                   "variant_sha256": hashlib.sha256(variant).hexdigest(),
                   "reference_asm_sha256": hashlib.sha256(reference_asm.encode()).hexdigest(),
                   "variant_asm_sha256": hashlib.sha256(variant_asm.encode()).hexdigest(),
                   "interpretation": "Exact code spans only; unmatched code remains unaligned."})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{len(result['spans'])} spans; {result['matched_span_bytes']} bytes; "
          f"{args.output}")


if __name__ == "__main__":
    main()
