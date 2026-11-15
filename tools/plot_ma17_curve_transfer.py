#!/usr/bin/env python3
"""Plot the original-opcode A/S37 RAM47h -> 7E9Dh/7EACh transfer sweep."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from plot_ma17_matrices import ROM_PATHS, ram47_axis_raw


COLUMNS = ("a_default", "s37_default", "a_alternate", "s37_alternate")


def load_transfer(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["raw_ram47", *COLUMNS]:
            raise ValueError("unexpected sweep CSV columns")
        rows = list(reader)
    if len(rows) != 256:
        raise ValueError("sweep must cover all 256 raw RAM47h values")
    values = {column: [] for column in COLUMNS}
    for raw, row in enumerate(rows):
        if int(row["raw_ram47"]) != raw:
            raise ValueError(f"missing or unordered RAM47h value {raw}")
        for column in COLUMNS:
            value = int(row[column])
            if not 0 <= value <= 255:
                raise ValueError(f"{column} outside byte range at {raw}")
            values[column].append(value)
    return values


def summarize(values):
    differences = [raw for raw in range(256)
                   if values["a_default"][raw] != values["s37_default"][raw]]
    alternate_differences = [raw for raw in range(256)
                             if values["a_alternate"][raw] !=
                             values["s37_alternate"][raw]]
    a_axis = ram47_axis_raw(ROM_PATHS["A"])
    s37_axis = ram47_axis_raw(ROM_PATHS["S37"])
    offsets = {a - s37 for a, s37 in zip(a_axis[1:], s37_axis[1:])}
    axis_offset = offsets.pop() if len(offsets) == 1 else None
    shifted_mismatches = (sum(values["s37_default"][raw] !=
                              values["a_default"][raw + axis_offset]
                              for raw in range(256 - axis_offset))
                          if axis_offset is not None and 0 <= axis_offset < 256
                          else None)
    return {"raw_inputs": 256, "default_mismatched_inputs": len(differences),
            "default_first_mismatch": differences[0] if differences else None,
            "default_last_mismatch": differences[-1] if differences else None,
            "alternate_mismatched_inputs": len(alternate_differences),
            "axis_offset_a_minus_s37": axis_offset,
            "translated_inputs_checked": 256 - axis_offset
            if axis_offset is not None and 0 <= axis_offset < 256 else None,
            "translated_default_mismatches": shifted_mismatches,
            "rom_sha256_at_plot_time": {
                name: hashlib.sha256(ROM_PATHS[name].read_bytes()).hexdigest()
                for name in ("A", "S37")},
            "scope": "original 1386h producer and 3329h->3384h reader; prepared guards and bank flag; raw digital input"}


def render(values, output, axis_offset):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    raw = range(256)
    figure, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    axis.plot(raw, values["a_default"], label="A · 7E9Dh", color="#1765ad")
    axis.plot(raw, values["s37_default"], label="S37 · 7E9Dh", color="#d66220")
    if axis_offset is not None and 0 <= axis_offset < 256:
        axis.plot(range(256 - axis_offset),
                  values["a_default"][axis_offset:],
                  label=f"A(x+{axis_offset}) · eixo alinhado",
                  color="#7d3c98", linestyle=":", linewidth=1.5)
    axis.plot(raw, values["a_alternate"], label="A/S37 · 7EACh",
              color="#327d55", linestyle="--")
    axis.fill_between(raw, values["a_default"], values["s37_default"],
                      color="#8b5fa3", alpha=0.22, label="Diferença do banco padrão")
    axis.set(xlabel="RAM47h bruto (0–255)", ylabel="R2 após interpolação (byte)",
             xlim=(0, 255), ylim=(0, 255),
             title="MA1.7 A/S37 · transferência digital das curvas 7E9Dh/7EACh\n"
                   "Opcodes originais em estado preparado; sem escala física validada")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.savefig(output, dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path,
                        help="CSV from MA17_7E9D_SWEEP_CSV with the C++ test")
    args = parser.parse_args()
    values = load_transfer(args.csv)
    report = summarize(values)
    report["sweep_csv_sha256"] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    plot = args.csv.with_suffix(".png")
    render(values, plot, report["axis_offset_a_minus_s37"])
    args.csv.with_suffix(".json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"plot: {plot}")


if __name__ == "__main__":
    main()
