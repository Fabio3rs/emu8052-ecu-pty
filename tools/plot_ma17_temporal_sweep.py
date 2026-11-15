#!/usr/bin/env python3
"""Plot paired ADC3 sweep/control traces against Fiat machine-cycle time."""

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CC3_EDGE = re.compile(r"^\[CC3-PIN\] tick=(\d+) .*?value=([01]) ")
FIAT_TICKS_PER_SECOND = 990000  # 11.88 MHz / 12, Fiat harness profile.


def load_run(directory):
    report = json.loads((directory / "execution.json").read_text())
    edges = []
    for line in (directory / "emulator-trace.log").read_text().splitlines():
        match = CC3_EDGE.match(line)
        if match:
            edges.append((int(match.group(1)), int(match.group(2))))
    pulses = [(tick, next_tick - tick)
              for (tick, level), (next_tick, next_level) in zip(edges, edges[1:])
              if level == 0 and next_level == 1]
    if not pulses:
        raise ValueError(f"no modeled CC3 pulses in {directory}")
    return report, pulses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sweep", type=Path)
    parser.add_argument("control", type=Path)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    sweep, sweep_pulses = load_run(args.sweep)
    control, control_pulses = load_run(args.control)
    if sweep["firmware_sha256"] != control["firmware_sha256"] or \
            sweep["stop_ticks_observed"] != control["stop_ticks_observed"] or \
            sweep["crank_target_rpm"] != control["crank_target_rpm"]:
        parser.error("runs must use the same ROM, stop tick and RPM")
    sweep_rate = sweep.get("machine_cycles_per_second", FIAT_TICKS_PER_SECOND)
    control_rate = control.get("machine_cycles_per_second", FIAT_TICKS_PER_SECOND)
    if sweep_rate != control_rate or sweep_rate <= 0:
        parser.error("runs must use the same positive machine-cycle clock rate")
    if sweep_rate != FIAT_TICKS_PER_SECOND:
        parser.error("this plot supports only the Fiat 11.88 MHz clock profile")
    stop = sweep["stop_ticks_observed"]
    initial = sweep["adc_10bit_input_values"][3]
    steps = sweep["adc_10bit_step_sequences"][3]
    if control["adc_10bit_step_sequences"][3] or not steps:
        parser.error("expected a sweep and a constant-ADC3 control")
    x = [0] + [step["tick"] / sweep_rate for step in steps]
    x.append(stop / sweep_rate)
    y = [initial] + [step["value"] for step in steps]
    y.append(y[-1])
    fig, (stimulus, output) = plt.subplots(
        2, 1, sharex=True, figsize=(10, 6), layout="constrained")
    stimulus.step(x, y, where="post", label="ADC3 sweep", color="#aa3b32")
    stimulus.axhline(control["adc_10bit_input_values"][3],
                     label="ADC3 control", color="#2c618a", linestyle="--")
    stimulus.set_ylabel("ADC3 input (10-bit raw)")
    stimulus.legend(loc="upper left")
    for label, pulses, color in (("sweep", sweep_pulses, "#aa3b32"),
                                 ("control", control_pulses, "#2c618a")):
        output.scatter([tick / sweep_rate for tick, _ in pulses],
                       [width * 1000 / sweep_rate for _, width in pulses], s=12,
                       label=label, color=color, alpha=0.8)
    output.set(xlabel="Fiat emulated time (s, 11.88 MHz crystal)",
               ylabel="Modeled CC3 low width (ms)")
    output.legend(loc="upper right")
    output.grid(alpha=0.25)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(args.output_prefix.with_suffix(f".{extension}"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
