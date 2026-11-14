#!/usr/bin/env python3
"""Plot observed Fiat Tipo MA1.7 lambda state and CC3 schedules.

The axes are emulator instruction counts and raw digital values. No sensor
voltage, mixture, injector pulse width, or physical temperature is inferred.
"""

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / "build/ma17-analysis/variants"
CC3 = re.compile(r"^\[CC3-ENTRY\] instr=(\d+).*IRAM14_15=([0-9A-Fa-f]{4})")


def read_capture(directory):
    report = json.loads((directory / "execution.json").read_text(encoding="utf-8"))
    changes = report["adaptation_xram_observation"]["F80C"]
    adaptation = [(int(change["tick"]), int(change["after"], 16))
                  for change in changes if change["source_pc"] != "55A1"]
    schedules = []
    with (directory / "emulator-trace.log").open(encoding="utf-8") as log:
        for line in log:
            match = CC3.match(line)
            if match:
                schedules.append((int(match[1]), int(match[2], 16)))
    if not adaptation or not schedules:
        raise ValueError(f"{directory}: missing F80C or CC3 observations")
    return report, adaptation, schedules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, default=CAPTURES)
    parser.add_argument("--output", type=Path,
                        default=CAPTURES / "lambda_adc3_20_tps40_95_response.png")
    args = parser.parse_args()
    captures = {}
    for name in ("low", "high"):
        directory = args.capture_root / f"lambda_adc3_20_tps40_95_{name}"
        captures[name] = read_capture(directory)
    low, high = (captures[name][0] for name in ("low", "high"))
    for field in ("firmware_sha256", "crank_target_rpm", "stop_ticks_target",
                  "adc7_input_value"):
        if low[field] != high[field]:
            parser.error(f"captures differ in {field}")
    if any(a != b for index, (a, b) in enumerate(zip(
            low["adc_input_values"], high["adc_input_values"])) if index != 5):
        parser.error("captures differ in an ADC input other than ADC5")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True,
                                constrained_layout=True)
    for name, color in (("low", "#1765ad"), ("high", "#d66220")):
        report, adaptation, schedules = captures[name]
        adc5 = report["adc_input_values"][5]
        label = f"ADC5={adc5} ({name})"
        axes[0].step([tick / 1e6 for tick, _ in adaptation],
                     [value for _, value in adaptation], where="post",
                     label=label, color=color, linewidth=1.8)
        axes[1].plot([tick / 1e6 for tick, _ in schedules],
                     [value for _, value in schedules], ".-", label=label,
                     color=color, markersize=3, linewidth=1)
    axes[0].set(ylabel="XRAM F8:0Ch (byte)", ylim=(-5, 260))
    axes[1].set(xlabel="Instruções executadas (milhões)",
                ylabel="IRAM 14h:15h no agendamento CC3 (bruto)")
    for axis in axes:
        axis.grid(alpha=0.3)
        axis.legend()
    figure.suptitle("Fiat Tipo MA1.7 G: resposta digital a ADC5, TPS 40/95, ADC3=20")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)
    plt.close(figure)
    print(args.output)


if __name__ == "__main__":
    main()
