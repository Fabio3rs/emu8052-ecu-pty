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
ROM_PATHS = {"G": REFERENCE, **VARIANT_PATHS}
RPM_AXIS_MATRICES = {0x7ED9, 0x7F15, 0x7F51}
RAM47_AXIS_CURVES = {0x7E9D, 0x7EAC, 0x7EBB}
PLOT_MATRICES = (*MATRICES, *((start, 8, 15) for start in
                             (0x7B46, 0x7BBE, 0x7C36, 0x7CAE,
                              0x7D26, 0x7D9E)),
                 *((start, 1, 15) for start in (0x7E9D, 0x7EAC, 0x7EBB)))


def rpm_axis_nominal(path):
    """Return 7B32h segment starts under the tested Fiat 25 RPM/count scale."""
    rom = path.read_bytes()
    if int.from_bytes(rom[0x70AA:0x70AC], "big") != 0x7B32 or \
            rom[0x7B32:0x7B34] != b"\x47\x0a":
        raise ValueError(f"{path}: expected 70AAh -> 7B32h RPM segment table")
    increments = rom[0x7B34:0x7B3E]
    if len(increments) != 10 or not all(increments) or sum(increments) > 255:
        raise ValueError(f"{path}: invalid 7B32h RPM segment increments")
    starts = [0] + [256 - sum(increments[index:])
                    for index in range(1, len(increments))]
    return [raw * 25 for raw in starts]


def ram47_axis_raw(path):
    """Return 7570h segment starts in the ROM's own raw RAM47h units."""
    rom = path.read_bytes()
    if int.from_bytes(rom[0x7046:0x7048], "big") != 0x7570 or \
            rom[0x7570:0x7572] != b"\x47\x0f":
        raise ValueError(f"{path}: expected 7046h -> 7570h RAM47h axis")
    increments = rom[0x7572:0x7581]
    starts = [0] + [256 - sum(increments[index:])
                    for index in range(1, len(increments))]
    if len(increments) != 15 or not all(increments) or \
            not all(0 <= a < b <= 255 for a, b in zip(starts, starts[1:])):
        raise ValueError(f"{path}: invalid 7570h RAM47h segments")
    return starts


def second_axis_raw(path):
    """Return the 7B3Eh row source and original-code raw segment starts."""
    rom = path.read_bytes()
    selector, count = rom[0x7B3E:0x7B40]
    if int.from_bytes(rom[0x70AC:0x70AE], "big") != 0x7B3E or \
            selector not in (0x7D, 0xAF) or count != 6:
        raise ValueError(f"{path}: unexpected 70ACh -> 7B3Eh row axis")
    increments = rom[0x7B40:0x7B46]
    if len(increments) != count or not all(increments) or sum(increments) > 255:
        raise ValueError(f"{path}: invalid 7B3Eh row increments")
    starts = [0] + [256 - sum(increments[index:])
                    for index in range(1, count)]
    return {"source": "upper IRAM[AFh]" if selector == 0xAF else "IRAM[7Dh]",
            "row_start_raw": starts}


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
    pairs = [(own, other) for a, b in zip(reference, variant)
             for own, other in zip(a, b)]
    uncapped = {other - own for a, b in zip(reference, variant)
                for own, other in zip(a, b) if other < 255}
    saturated_add = next(iter(uncapped)) if len(uncapped) == 1 else None
    if saturated_add is not None and (saturated_add < 0 or not all(
            other == min(255, own + saturated_add)
            for a, b in zip(reference, variant)
            for own, other in zip(a, b))):
        saturated_add = None
    unchanged_prefix = next((index for index, (own, other) in enumerate(pairs)
                             if own != other), len(pairs))
    suffix = pairs[unchanged_prefix:]
    suffix_offsets = {other - own for own, other in suffix if 0 < other < 255}
    suffix_shift = next(iter(suffix_offsets)) if len(suffix_offsets) == 1 else None
    if (unchanged_prefix == 0 or len(suffix) < 2 or suffix_shift in (None, 0)
            or not all(other == max(0, min(255, own + suffix_shift))
                       for own, other in suffix)):
        suffix_shift = None
    return deltas, {"cells": len(flat), "changed_cells": sum(value != 0 for value in flat),
                    "delta_min": min(flat), "delta_max": max(flat),
                    "constant_delta": flat[0] if len(set(flat)) == 1 else None,
                    "saturated_add_delta": saturated_add,
                    "unchanged_prefix_cells": unchanged_prefix,
                    "suffix_clamped_add_delta": suffix_shift}


def render(reference, variant, deltas, start, name, output,
           reference_name="G", reference_start=None,
           column_rpm=None, reference_rows=None, variant_rows=None,
           column_raw=None, reference_axis=None, variant_axis=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    rows, columns = len(reference), len(reference[0])
    column_labels = column_rpm if column_rpm is not None else column_raw
    x_label = ("Início da coluna (RPM nominal)" if column_rpm is not None
               else "Início da coluna (RAM47h bruto)" if column_raw is not None
               else "Coluna (índice bruto)")
    reference_label = f"{reference_name} · {reference_start:04X}h"
    variant_label = f"{name} · {start:04X}h"
    figure, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    for axis, values, title, row_axis, raw_axis in (
            (axes[0, 0], reference, reference_label, reference_rows,
             reference_axis),
            (axes[0, 1], variant, variant_label, variant_rows,
             variant_axis)):
        image = axis.imshow(values, origin="lower", cmap="viridis", vmin=0,
                            vmax=255, interpolation="nearest", aspect="auto")
        axis.set(title=title,
                 xlabel="Início da coluna (RAM47h bruto)" if raw_axis else x_label,
                 ylabel=(f"{row_axis['source']} · início bruto"
                         if row_axis else "Linha (índice bruto)"))
        axis.set_xticks(range(columns))
        if raw_axis is not None or column_labels is not None:
            axis.set_xticklabels(raw_axis if raw_axis is not None else
                                 column_labels, rotation=45)
        axis.set_yticks(range(rows))
        if row_axis:
            axis.set_yticklabels(row_axis["row_start_raw"])
        figure.colorbar(image, ax=axis, label="Byte ROM (0–255)")
    scale = max(1, *(abs(value) for row in deltas for value in row))
    image = axes[1, 0].imshow(deltas, origin="lower", cmap="RdBu_r",
                              norm=TwoSlopeNorm(vmin=-scale, vcenter=0, vmax=scale),
                              interpolation="nearest", aspect="auto")
    axes[1, 0].set(title=f"{variant_label} − {reference_label}",
                   xlabel=x_label,
                   ylabel="Linha (índice bruto)")
    axes[1, 0].set_xticks(range(columns))
    if column_labels is not None:
        axes[1, 0].set_xticklabels(column_labels, rotation=45)
    axes[1, 0].set_yticks(range(rows))
    figure.colorbar(image, ax=axes[1, 0], label="Diferença de bytes")
    for values, label, color in ((reference, reference_label, "#1765ad"),
                                 (variant, variant_label, "#d66220")):
        profile = values[0] if rows == 1 else [sum(row) / columns
                                                for row in values]
        axes[1, 1].plot(range(len(profile)), profile, marker="o",
                        label=label, color=color)
    axes[1, 1].set(title="Silhueta: byte por célula" if rows == 1
                   else "Silhueta: média bruta por linha",
                   xlabel=x_label if rows == 1 else "Linha",
                   ylabel="Byte ROM" if rows == 1 else "Média dos bytes",
                   xticks=range(columns if rows == 1 else rows), ylim=(0, 255))
    axes[1, 1].grid(alpha=0.3)
    if rows == 1 and column_labels is not None:
        axes[1, 1].set_xticklabels(column_labels, rotation=45)
    axes[1, 1].legend()
    same_axis = ((column_rpm is not None or column_raw is not None) and
                 reference_rows == variant_rows)
    subtitle = ("Mesmos eixos brutos; colunas discretas; sem unidade de saída confirmada"
                if same_axis else
                "Limites RAM47h diferentes; delta por índice, não pela mesma entrada bruta"
                if reference_axis is not None and variant_axis is not None else
                "Colunas discretas; delta por índice, não pela mesma entrada física"
                if column_labels is not None else
                "Índices e bytes brutos; sem unidades físicas confirmadas")
    figure.suptitle(f"MA1.7 · matrizes ROM {reference_start:04X}h / "
                    f"{start:04X}h · {rows}×{columns}\n{subtitle}")
    figure.savefig(output, dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=lambda value: int(value, 0), default=0x7581,
                        choices=[start for start, _, _ in PLOT_MATRICES])
    parser.add_argument("--variant", choices=ROM_PATHS, default="S88")
    parser.add_argument("--reference-variant", choices=ROM_PATHS, default="G")
    parser.add_argument("--reference-matrix", type=lambda value: int(value, 0),
                        choices=[start for start, _, _ in PLOT_MATRICES])
    parser.add_argument("--output-dir", type=Path,
                        default=REFERENCE.parent / "build/ma17-analysis/variants/matrix_plots")
    args = parser.parse_args()
    start, rows, columns = next(item for item in PLOT_MATRICES
                                if item[0] == args.matrix)
    reference_start = args.reference_matrix if args.reference_matrix is not None else start
    reference_dims = next(item[1:] for item in PLOT_MATRICES
                          if item[0] == reference_start)
    if reference_dims != (rows, columns):
        parser.error("reference and variant matrices must have the same dimensions")
    reference_path = ROM_PATHS[args.reference_variant]
    reference, reference_sha = load_matrix(reference_path, reference_start,
                                           rows, columns)
    variant_path = ROM_PATHS[args.variant]
    variant, variant_sha = load_matrix(variant_path, start, rows, columns)
    deltas, summary = summarize(reference, variant)
    column_rpm = None
    column_raw = reference_axis = variant_axis = None
    reference_rows = variant_rows = None
    if start in RPM_AXIS_MATRICES and reference_start in RPM_AXIS_MATRICES:
        column_rpm = rpm_axis_nominal(reference_path)
        if rpm_axis_nominal(variant_path) != column_rpm:
            raise ValueError("RPM segment axes differ between compared ROMs")
        reference_rows = second_axis_raw(reference_path)
        variant_rows = second_axis_raw(variant_path)
    if start in RAM47_AXIS_CURVES and reference_start in RAM47_AXIS_CURVES:
        reference_axis = ram47_axis_raw(reference_path)
        variant_axis = ram47_axis_raw(variant_path)
        if reference_axis == variant_axis:
            column_raw = reference_axis
    summary.update(matrix_start=f"{start:04X}h",
                   reference_matrix_start=f"{reference_start:04X}h",
                   reference_variant=args.reference_variant, rows=rows, columns=columns,
                   reference_sha256=reference_sha, variant_sha256=variant_sha,
                   variant=args.variant, column_start_nominal_rpm=column_rpm,
                   column_start_raw_ram47=column_raw,
                   reference_column_start_raw_ram47=reference_axis,
                   variant_column_start_raw_ram47=variant_axis,
                   reference_row_axis=reference_rows, variant_row_axis=variant_rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = args.reference_variant.lower().replace("+", "plus")
    other = args.variant.lower().replace("+", "plus")
    stem = f"matrix_{start:04x}_{base}_vs_{other}"
    if reference_start != start:
        stem = f"matrix_{reference_start:04x}_{base}_vs_{start:04x}_{other}"
    plot = args.output_dir / f"{stem}.png"
    render(reference, variant, deltas, start, args.variant, plot,
           args.reference_variant, reference_start, column_rpm,
           reference_rows, variant_rows, column_raw,
           reference_axis, variant_axis)
    with (args.output_dir / f"{stem}.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("row", "column", "column_start_nominal_rpm",
                         "reference_column_start_raw_ram47",
                         "variant_column_start_raw_ram47",
                         "reference_row_start_raw", "variant_row_start_raw",
                         "reference_rom_address", "rom_address",
                         args.reference_variant, args.variant, "delta"))
        for row in range(rows):
            for column in range(columns):
                writer.writerow((row, column, column_rpm[column] if column_rpm else "",
                                 reference_axis[column] if reference_axis else "",
                                 variant_axis[column] if variant_axis else "",
                                 reference_rows["row_start_raw"][row]
                                 if reference_rows else "",
                                 variant_rows["row_start_raw"][row]
                                 if variant_rows else "",
                                 f"{reference_start + row * columns + column:04X}h",
                                 f"{start + row * columns + column:04X}h",
                                 reference[row][column], variant[row][column],
                                 deltas[row][column]))
    (args.output_dir / f"{stem}.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"plot: {plot}")


if __name__ == "__main__":
    main()
