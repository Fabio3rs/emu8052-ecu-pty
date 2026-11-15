#!/usr/bin/env python3
"""Plot A/S37 original-opcode transfer through directory curve 7EBBh."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from plot_ma17_matrices import ROM_PATHS, ram47_axis_raw


def load_transfer(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["raw_ram47", "a_third", "s37_third"]:
            raise ValueError("unexpected third-curve CSV columns")
        rows = list(reader)
    if len(rows) != 256:
        raise ValueError("third-curve sweep must cover 256 inputs")
    a, s37 = [], []
    for raw, row in enumerate(rows):
        if int(row["raw_ram47"]) != raw:
            raise ValueError(f"missing or unordered RAM47h value {raw}")
        values = [int(row[key]) for key in ("a_third", "s37_third")]
        if any(not 0 <= value <= 255 for value in values):
            raise ValueError(f"output outside byte range at {raw}")
        a.append(values[0])
        s37.append(values[1])
    return a, s37


def summarize(a, s37):
    starts_a = ram47_axis_raw(ROM_PATHS["A"])
    starts_s37 = ram47_axis_raw(ROM_PATHS["S37"])
    offsets = {x - y for x, y in zip(starts_a[1:], starts_s37[1:])}
    if len(offsets) != 1:
        raise ValueError("nonuniform segment-axis offset")
    offset = offsets.pop()
    if not 0 <= offset < 256:
        raise ValueError("invalid segment-axis offset")
    direct = [raw for raw in range(256) if a[raw] != s37[raw]]
    shifted = [raw for raw in range(256 - offset)
               if a[raw + offset] != s37[raw]]
    return {"raw_inputs": 256, "direct_mismatched_inputs": len(direct),
            "direct_first_mismatch": direct[0] if direct else None,
            "direct_last_mismatch": direct[-1] if direct else None,
            "axis_offset_a_minus_s37": offset,
            "translated_inputs_checked": 256 - offset,
            "translated_mismatched_inputs": len(shifted),
            "translated_mismatch_inputs": shifted,
            "rom_sha256_at_plot_time": {
                name: hashlib.sha256(ROM_PATHS[name].read_bytes()).hexdigest()
                for name in ("A", "S37")},
            "scope": "original 1386h producer and 3329h->3384h reader with RAM57h=2, RAM2Bh.7=0, prepared guards"}


def render(a, s37, offset, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    axis.plot(range(256), a, label="A · 7EBBh", color="#1765ad")
    axis.plot(range(256), s37, label="S37 · 7EBBh", color="#d66220")
    axis.plot(range(256 - offset), a[offset:],
              label=f"A(x+{offset}) · alinhamento após primeiro segmento",
              color="#7d3c98", linestyle=":")
    axis.fill_between(range(256), a, s37, color="#8b5fa3", alpha=0.22)
    axis.set(title="MA1.7 A/S37 · terceira curva 7EBBh\n"
                   "Opcodes originais em estado preparado; sem escala física validada",
             xlabel="RAM47h bruto (0–255)", ylabel="R2 após interpolação (byte)",
             xlim=(0, 255), ylim=(0, 255))
    axis.grid(alpha=0.25)
    axis.legend()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path,
                        help="CSV from MA17_7EBB_SWEEP_CSV with the C++ test")
    args = parser.parse_args()
    a, s37 = load_transfer(args.csv)
    report = summarize(a, s37)
    report["sweep_csv_sha256"] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    plot = args.csv.with_suffix(".png")
    render(a, s37, report["axis_offset_a_minus_s37"], plot)
    args.csv.with_suffix(".json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"plot: {plot}")


if __name__ == "__main__":
    main()
