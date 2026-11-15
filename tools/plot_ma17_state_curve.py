#!/usr/bin/env python3
"""Plot the verified raw 7E8Eh state curve and its observed lookup cells."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from compare_ma17_variants import EXPECTED, REFERENCE, VARIANTS


START = 0x7E8E
LENGTH = 15
ROMS = {"G": REFERENCE, **dict(zip(("A", "A+", "S88", "S37", "S36"),
                                    (VARIANTS / name for name in EXPECTED)))}


def read_curves():
    curves = {}
    hashes = {}
    for name, path in ROMS.items():
        image = path.read_bytes()
        if len(image) != 32768 or int.from_bytes(image[0x70D4:0x70D6], "big") != START:
            raise ValueError(f"{path}: expected 32 KiB and 70D4h→7E8Eh")
        curves[name] = list(image[START:START + LENGTH])
        hashes[name] = hashlib.sha256(image).hexdigest()
    return curves, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=REFERENCE.parent / "build/ma17-analysis/variants/matrix_plots")
    args = parser.parse_args()
    curves, hashes = read_curves()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_dir / "curve_7e8e_all_variants"
    with stem.with_suffix(".csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("index", "rom_address", *ROMS))
        for index in range(LENGTH):
            writer.writerow((index, f"{START + index:04X}h",
                             *(values[index] for values in curves.values())))
    stem.with_suffix(".json").write_text(json.dumps({
        "pointer_slot": "70D4h", "start": "7E8Eh", "length": LENGTH,
        "variant_sha256": hashes, "values": curves,
        "observed_lookup_indices": {"G": [5], "S88": [7]},
        "observation_scope": "Experimental P4.6-low double-TPS-step trace; not a physical axis",
    }, indent=2) + "\n", encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
    ax.plot(range(LENGTH), curves["G"], marker="o", linewidth=2.5,
            color="#1765ad")
    for index, label, label_x, label_y in (
            (5, "G: índice 5 → 02h", 1.8, 4.8),
            (7, "S88: índice 7 → 03h", 8.2, 4.4)):
        ax.annotate(label, (index, curves["G"][index]), xytext=(label_x, label_y),
                    arrowprops={"arrowstyle": "->", "color": "#444"})
    ax.set(title="MA1.7 Fiat Tipo · curva ROM 7E8Eh (15 bytes; seis ROMs idênticas)",
           xlabel="Índice bruto de MOVC", ylabel="Byte bruto da ROM",
           xticks=range(LENGTH), ylim=(0, 5.5))
    ax.grid(alpha=0.25)
    fig.savefig(stem.with_suffix(".png"), dpi=170)
    plt.close(fig)
    print(f"plot: {stem.with_suffix('.png')}")
    print(f"all_six_identical: {len({tuple(v) for v in curves.values()}) == 1}")


if __name__ == "__main__":
    main()
