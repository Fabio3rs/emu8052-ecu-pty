#!/usr/bin/env python3
"""Plot verified MA1.7 matrix geometry and raw per-cell ROM differences."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from compare_ma17_variants import EXPECTED, MATRICES, REFERENCE, VARIANTS


VARIANT_PATHS = dict(zip(("A", "A+", "S88", "S37", "S36"),
                         (VARIANTS / name for name in EXPECTED)))


def load_matrix(path, start, rows, columns):
    rom = path.read_bytes()
    if len(rom) != 32768:
        raise ValueError(f"{path}: expected 32768 bytes, got {len(rom)}")
    values = [list(rom[start + row * columns:
                       start + (row + 1) * columns]) for row in range(rows)]
    return values, hashlib.sha256(rom).hexdigest()


def summarize(reference, variant):
    deltas = [[other - own for own, other in zip(a, b)]
              for a, b in zip(reference, variant)]
    flat = [value for row in deltas for value in row]
    return deltas, {"cells": len(flat), "changed_cells": sum(value != 0 for value in flat),
                    "delta_min": min(flat), "delta_max": max(flat),
                    "constant_delta": flat[0] if len(set(flat)) == 1 else None}


def render(reference, variant, deltas, start, name, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    rows, columns = len(reference), len(reference[0])
    figure, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    for axis, values, title in ((axes[0, 0], reference, "Gasolina G"),
                                (axes[0, 1], variant, name)):
        image = axis.imshow(values, origin="lower", cmap="viridis", vmin=0,
                            vmax=255, interpolation="nearest", aspect="auto")
        axis.set(title=title, xlabel="Coluna (índice bruto)", ylabel="Linha (índice bruto)")
        axis.set_xticks(range(columns))
        axis.set_yticks(range(rows))
        figure.colorbar(image, ax=axis, label="Byte ROM (0–255)")
    scale = max(1, *(abs(value) for row in deltas for value in row))
    image = axes[1, 0].imshow(deltas, origin="lower", cmap="RdBu_r",
                              norm=TwoSlopeNorm(vmin=-scale, vcenter=0, vmax=scale),
                              interpolation="nearest", aspect="auto")
    axes[1, 0].set(title=f"{name} − G", xlabel="Coluna (índice bruto)",
                   ylabel="Linha (índice bruto)")
    axes[1, 0].set_xticks(range(columns))
    axes[1, 0].set_yticks(range(rows))
    figure.colorbar(image, ax=axes[1, 0], label="Diferença de bytes")
    for values, label, color in ((reference, "G", "#1765ad"),
                                 (variant, name, "#d66220")):
        averages = [sum(row) / columns for row in values]
        axes[1, 1].plot(range(rows), averages, marker="o", label=label,
                        color=color)
    axes[1, 1].set(title="Silhueta: média bruta por linha", xlabel="Linha",
                   ylabel="Média dos bytes", xticks=range(rows), ylim=(0, 255))
    axes[1, 1].grid(alpha=0.3)
    axes[1, 1].legend()
    figure.suptitle(f"MA1.7 · matriz ROM {start:04X}h · {rows}×{columns}\n"
                    "Índices e bytes brutos; sem unidades físicas confirmadas")
    figure.savefig(output, dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=lambda value: int(value, 0), default=0x7581,
                        choices=[start for start, _, _ in MATRICES])
    parser.add_argument("--variant", choices=VARIANT_PATHS, default="S88")
    parser.add_argument("--output-dir", type=Path,
                        default=REFERENCE.parent / "build/ma17-analysis/variants/matrix_plots")
    args = parser.parse_args()
    start, rows, columns = next(item for item in MATRICES if item[0] == args.matrix)
    reference, reference_sha = load_matrix(REFERENCE, start, rows, columns)
    variant_path = VARIANT_PATHS[args.variant]
    variant, variant_sha = load_matrix(variant_path, start, rows, columns)
    deltas, summary = summarize(reference, variant)
    summary.update(matrix_start=f"{start:04X}h", rows=rows, columns=columns,
                   reference_sha256=reference_sha, variant_sha256=variant_sha,
                   variant=args.variant)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"matrix_{start:04x}_g_vs_{args.variant.lower().replace('+', 'plus')}"
    plot = args.output_dir / f"{stem}.png"
    render(reference, variant, deltas, start, args.variant, plot)
    with (args.output_dir / f"{stem}.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("row", "column", "rom_address", "G", args.variant, "delta"))
        for row in range(rows):
            for column in range(columns):
                writer.writerow((row, column, f"{start + row * columns + column:04X}h",
                                 reference[row][column], variant[row][column],
                                 deltas[row][column]))
    (args.output_dir / f"{stem}.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"plot: {plot}")


if __name__ == "__main__":
    main()
