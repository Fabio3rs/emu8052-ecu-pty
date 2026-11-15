#!/usr/bin/env python3
"""Plot Fiat MA1.7 CPU pin traces against two 60-2 crank revolutions.

The 60-2 wheel identifies crank phase modulo 360 degrees, not 4T stroke phase.
P5, P1.1 and CC3 labels describe modeled CPU signals, not ECU connector pins.
"""

import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PHASE = re.compile(r"^\[CRANK-PHASE\] tick=(\d+) tooth=0 rpm=(\d+)")
P5 = re.compile(r"^\[P5-LATCH\] instr=(\d+).* value=([0-9A-Fa-f]{2})")
P11 = re.compile(r"^\[P1\.1-LATCH\] instr=(\d+).* value=([01])")
CC3 = re.compile(r"^\[CC3-PIN\] tick=(\d+).* value=([01])")
CHANNELS = ("P5.0 latch", "P5.1 latch", "P1.1 latch", "CC3 output")


def read_trace(path):
    references, events = [], []
    for line in path.read_text(errors="replace").splitlines():
        if match := PHASE.match(line):
            references.append((int(match[1]), int(match[2])))
        elif match := P5.match(line):
            tick, value = int(match[1]), int(match[2], 16)
            events.extend((tick, name, (value >> bit) & 1)
                          for bit, name in enumerate(CHANNELS[:2]))
        elif match := P11.match(line):
            events.append((int(match[1]), CHANNELS[2], int(match[2])))
        elif match := CC3.match(line):
            events.append((int(match[1]), CHANNELS[3], int(match[2])))
    if len(references) < 3:
        raise ValueError("trace needs three tooth-0 references; enable "
                         "MA17_TRACE_CRANK_PHASE and run for at least two revolutions")
    return references, sorted(events)


def phase_at(tick, refs):
    for index in range(2):
        if tick <= refs[index + 1]:
            return 360 * (index + (tick - refs[index]) /
                          (refs[index + 1] - refs[index]))
    return 720


def plot(trace, output, revolution=-3):
    references, events = read_trace(trace)
    start = revolution if revolution >= 0 else len(references) + revolution
    if start < 0 or start + 2 >= len(references):
        raise ValueError("requested 720-degree window is outside captured revolutions")
    refs = [tick for tick, _ in references[start:start + 3]]
    if not refs[0] < refs[1] < refs[2]:
        raise ValueError("tooth-0 timestamps must increase")
    rows = []
    state = {name: None for name in CHANNELS}
    for tick, name, value in events:
        if tick < refs[0]:
            state[name] = value
        elif tick <= refs[2]:
            rows.append((tick, phase_at(tick, refs), name, value))
    output.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output.with_suffix(".csv")
    with csv_path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("tick", "crank_degrees_4t_window", "cpu_signal", "value"))
        writer.writerows(rows)
    figure, axes = plt.subplots(5, 1, figsize=(14, 8), sharex=True,
                                gridspec_kw={"height_ratios": [0.7, 1, 1, 1, 1]})
    for turn in (0, 1):
        axes[0].scatter([turn * 360 + tooth * 6 for tooth in range(58)],
                        [1] * 58, marker="|", color="black", s=60)
        for missing in (58, 59):
            axes[0].axvspan(turn * 360 + missing * 6,
                            turn * 360 + (missing + 1) * 6,
                            color="tab:red", alpha=0.18)
    axes[0].set_ylabel("60−2")
    axes[0].set_yticks([])
    counts = {}
    for axis, name in zip(axes[1:], CHANNELS):
        channel_rows = [(degree, value) for _, degree, channel, value in rows
                        if channel == name]
        values = ([state[name]] if state[name] is not None else [])
        points = ([0] if values else [])
        for degree, value in channel_rows:
            points.append(degree)
            values.append(value)
        if values:
            axis.step(points + [720], values + [values[-1]], where="post")
        axis.set_ylim(-0.25, 1.25)
        axis.set_yticks((0, 1))
        axis.set_ylabel(name)
        axis.grid(axis="x", alpha=0.3)
        counts[name] = len(channel_rows)
    for axis in axes:
        axis.axvline(360, color="tab:orange", ls="--", lw=1)
    axes[-1].set_xlim(0, 720)
    axes[-1].set_xticks(range(0, 721, 30))
    axes[-1].set_xlabel("Crank degrees across two revolutions (stroke phase unknown)")
    figure.suptitle("Fiat MA1.7 modeled CPU signals vs 60−2 wheel")
    figure.tight_layout()
    figure.savefig(output, dpi=160)
    plt.close(figure)
    report = {"trace": str(trace), "reference_ticks": refs,
              "rpm": references[start][1], "events": counts,
              "scope": "modeled CPU signals; no physical coil or injector assignment",
              "stroke_phase": "unknown; 60-2 supplies crank angle modulo 360 degrees"}
    output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="emulator-trace.log")
    parser.add_argument("--output", type=Path, required=True, help="PNG path")
    parser.add_argument("--revolution", type=int, default=-3,
                        help="first of three consecutive tooth-0 references")
    args = parser.parse_args()
    print(json.dumps(plot(args.trace, args.output, args.revolution), indent=2))


if __name__ == "__main__":
    main()
