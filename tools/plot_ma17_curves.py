#!/usr/bin/env python3
"""Plot raw Fiat Tipo MA1.7 ROM curves without assigning physical units."""

import argparse
import hashlib
from pathlib import Path
from xml.sax.saxutils import escape

from compare_ma17_variants import EXPECTED, REFERENCE, VARIANTS


PROFILES = (("G", REFERENCE),
            ("A", VARIANTS / EXPECTED[0]),
            ("A+", VARIANTS / EXPECTED[1]),
            ("S88", VARIANTS / EXPECTED[2]),
            ("S37", VARIANTS / EXPECTED[3]),
            ("S36", VARIANTS / EXPECTED[4]))
CURVES = ((0x750C, "2Fh.5=1; T2CON.1=0"),
          (0x7520, "2Fh.5=0"))
COLORS = ("#1765ad", "#d66220", "#6c4f9a", "#17806a")


def render(images):
    width, height = 1200, 620
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
             f'height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fffdf9"/>',
             '<style>text{font-family:DejaVu Sans,Arial,sans-serif;fill:#1f2933}'
             '.title{font-size:22px;font-weight:700}.sub{font-size:13px}'
             '.panel{font-size:17px;font-weight:700}.axis{font-size:12px}'
             '.legend{font-size:13px}</style>',
             '<text x="44" y="40" class="title">MA1.7 Fiat Tipo: curvas brutas 750Ch e 7520h</text>',
             '<text x="44" y="63" class="sub">Pontos são bytes da ROM; linhas ligam índices adjacentes. Eixos físicos ainda não identificados.</text>']
    for panel, (start, condition) in enumerate(CURVES):
        left = 76 + panel * 582
        top, plot_width, plot_height = 126, 474, 356
        groups = {}
        for name, data in images.items():
            groups.setdefault(data[start:start + 10], []).append(name)
        ordered = sorted(groups.items(), key=lambda item: "G" not in item[1])
        lines.append(f'<text x="{left}" y="101" class="panel">ROM {start:04X}h · {escape(condition)}</text>')
        for value in (0, 64, 128, 192, 255):
            y = top + plot_height * (255 - value) / 255
            lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_width}" '
                         f'y2="{y:.1f}" stroke="#dce3e8"/>')
            lines.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" '
                         f'class="axis">{value}</text>')
        lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" '
                     f'y2="{top+plot_height}" stroke="#465560"/>')
        lines.append(f'<line x1="{left}" y1="{top+plot_height}" '
                     f'x2="{left+plot_width}" y2="{top+plot_height}" stroke="#465560"/>')
        for index in range(10):
            x = left + plot_width * index / 9
            lines.append(f'<text x="{x:.1f}" y="{top+plot_height+19}" '
                         f'text-anchor="middle" class="axis">{index}</text>')
        lines.append(f'<text x="{left+plot_width/2}" y="{top+plot_height+39}" '
                     'text-anchor="middle" class="axis">Índice da curva (R5)</text>')
        for group_index, (values, names) in enumerate(ordered):
            color = COLORS[group_index]
            points = [(left + plot_width * index / 9,
                       top + plot_height * (255 - value) / 255)
                      for index, value in enumerate(values)]
            coordinates = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
            lines.append(f'<polyline points="{coordinates}" fill="none" '
                         f'stroke="{color}" stroke-width="3"/>')
            legend = escape("/".join(names))
            lines.append(f'<line x1="{left+group_index*215}" y1="555" '
                         f'x2="{left+25+group_index*215}" y2="555" '
                         f'stroke="{color}" stroke-width="3"/>')
            lines.append(f'<text x="{left+32+group_index*215}" y="559" '
                         f'class="legend">{legend}</text>')
            for index, ((x, y), value) in enumerate(zip(points, values)):
                lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" '
                             f'fill="{color}"><title>{legend}: índice {index}, '
                             f'ROM[{start+index:04X}h]={value:02X}h ({value})'
                             '</title></circle>')
    lines.append('<text x="44" y="598" class="sub">Fonte: seis dumps originais de 32 KiB; G = gasolina, A/A+ = álcool. S88/S37/S36 seguem G nestas curvas.</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def render_png(images, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True,
                                constrained_layout=True)
    for axis, (start, condition) in zip(axes, CURVES):
        groups = {}
        for name, data in images.items():
            groups.setdefault(data[start:start + 10], []).append(name)
        ordered = sorted(groups.items(), key=lambda item: "G" not in item[1])
        for group_index, (values, names) in enumerate(ordered):
            axis.plot(range(10), list(values), marker="o", linewidth=2.5,
                      color=COLORS[group_index], label="/".join(names))
        axis.set(title=f"ROM {start:04X}h · {condition}",
                 xlabel="Índice da curva (R5)", xlim=(-0.2, 9.2),
                 ylim=(0, 255), xticks=range(10))
        axis.grid(alpha=0.3)
        axis.legend(loc="lower right")
    axes[0].set_ylabel("Byte bruto da ROM (0–255)")
    figure.suptitle("Bosch MA1.7 Fiat Tipo: curvas 750Ch e 7520h", fontsize=16)
    figure.savefig(destination, dpi=170)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=REFERENCE.parent / "build/ma17-analysis/variants/curves_750c_7520.svg")
    parser.add_argument("--png", action="store_true",
                        help="also render PNG with matplotlib (available in /usr/bin/python3)")
    args = parser.parse_args()
    images = {}
    for name, path in PROFILES:
        data = path.read_bytes()
        if len(data) != 32768:
            parser.error(f"{path}: expected 32768 bytes, got {len(data)}")
        images[name] = data
        print(f"{name}: {hashlib.sha256(data).hexdigest()}  {path}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(images), encoding="utf-8")
    print(f"plot: {args.output}")
    if args.png:
        png = args.output.with_suffix(".png")
        render_png(images, png)
        print(f"plot: {png}")


if __name__ == "__main__":
    main()
