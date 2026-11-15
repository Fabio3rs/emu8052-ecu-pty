#!/usr/bin/env python3
"""Plot modeled CC3 edge timing differences for matched Fiat-profile runs."""

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


EDGE = re.compile(r"^\[CC3-PIN\] tick=(\d+) .*?value=([01]) ")
FIAT_TICKS_PER_SECOND = 990000  # 11.88 MHz crystal / 12.


def load_run(directory):
    report = json.loads((directory / "execution.json").read_text())
    edges = [tuple(map(int, match.groups()))
             for line in (directory / "emulator-trace.log").read_text().splitlines()
             if (match := EDGE.match(line))]
    if not edges:
        raise ValueError(f"no modeled CC3 edges in {directory}")
    return report, edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--arm", action="append", required=True,
                        metavar="LABEL=TRACE_DIR")
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    reference, reference_edges = load_run(args.reference)
    reference_rate = reference.get("machine_cycles_per_second", FIAT_TICKS_PER_SECOND)
    if reference_rate != FIAT_TICKS_PER_SECOND:
        parser.error("this plot supports only the Fiat 11.88 MHz clock profile")
    x = [tick / reference_rate for tick, _ in reference_edges]
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)
    for specification in args.arm:
        label, separator, directory = specification.partition("=")
        if not separator or not label or not directory:
            parser.error("--arm expects LABEL=TRACE_DIR")
        report, edges = load_run(Path(directory))
        if report.get("machine_cycles_per_second", FIAT_TICKS_PER_SECOND) != reference_rate:
            parser.error(f"unmatched machine-cycle clock rate: {label}")
        if report["stop_ticks_observed"] != reference["stop_ticks_observed"] or \
                report["crank_target_rpm"] != reference["crank_target_rpm"] or \
                len(edges) != len(reference_edges) or \
                [level for _, level in edges] != [level for _, level in reference_edges]:
            parser.error(f"unmatched event sequence: {label}")
        ax.plot(x, [tick - ref_tick for (tick, _), (ref_tick, _) in
                    zip(edges, reference_edges)], marker=".", markersize=3,
                linewidth=0.8, label=label)
    ax.set(xlabel="Fiat emulated time (s, 11.88 MHz crystal)",
           ylabel="CC3 edge delay vs reference (ticks)")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(args.output_prefix.with_suffix(f".{extension}"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
