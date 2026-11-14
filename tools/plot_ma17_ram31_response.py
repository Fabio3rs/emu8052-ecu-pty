#!/usr/bin/env python3
"""Plot the measured RAM31 to P5 response of the Fiat G emulator profile.

P5 latch intervals are emulator ticks, not physical coil dwell measurements.
"""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / "build/ma17-analysis/variants"
FIRMWARE = ROOT / "FiatTipo_MA17_dump_27c256.bin"
SAMPLES = {
    0x00: "ram31_response_1000_00",
    0x10: "ram31_response_1000_10",
    0x20: "ram31_response_1000_20",
    0x32: "ram31_response_1000_32",
    0x40: "ram31_response_1000_40",
    0x50: "ram31_response_1000_50",
    0x80: "ram31_response_1000_80",
}


def load_samples(capture_root, firmware):
    digest = hashlib.sha256(firmware.read_bytes()).hexdigest()
    samples = []
    periods = set()
    for value, name in SAMPLES.items():
        path = capture_root / name / "execution.json"
        if not path.exists() and value in (0x10, 0x32):
            path = capture_root / f"ram31_gate_trace_1000_{value:02X}" / "execution.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        expected = {"firmware_sha256": digest, "crank_target_rpm": 1000,
                    "stop_ticks_target": 2400000, "stop_ticks_observed": 2400000,
                    "adc7_input_value": 63, "ram57_override_hex": "0"}
        for key, wanted in expected.items():
            if report[key] != wanted:
                raise ValueError(f"{path}: {key}={report[key]!r}, expected {wanted!r}")
        if int(report["ram31_override_hex"], 16) != value:
            raise ValueError(f"{path}: wrong RAM31 override")
        output = report["output_latches"]["P5.0"]
        if output["low_starts"] < 3:
            raise ValueError(f"{path}: too few P5.0 intervals")
        periods.add(output["median_period_ticks"])
        samples.append((value, output["median_low_width_ticks"]))
    if len(periods) != 1:
        raise ValueError(f"inconsistent P5.0 periods: {sorted(periods)}")
    return samples, periods.pop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, default=CAPTURES)
    parser.add_argument("--firmware", type=Path, default=FIRMWARE)
    parser.add_argument("--output", type=Path,
                        default=CAPTURES / "ram31_p5_response.png")
    args = parser.parse_args()
    try:
        samples, period = load_samples(args.capture_root, args.firmware)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    values = [value for value, _ in samples]
    observed = [width for _, width in samples]
    predicted = [period * value / 512 for value in values]
    figure, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True,
                                constrained_layout=True,
                                gridspec_kw={"height_ratios": [3, 1]})
    axes[0].plot(values, observed, "o-", label="Mediana P5.0 emulada")
    axes[0].plot(values, predicted, "--", label="Ajuste local: período × RAM31 / 512")
    axes[0].set_ylabel("Largura baixa de P5.0 (ticks)")
    axes[0].legend()
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].plot(values, [actual - fit for actual, fit in zip(observed, predicted)],
                 "o-", color="#b44632")
    axes[1].set(xlabel="RAM[31h] entregue em 0490h (byte decimal)",
                ylabel="Resíduo (ticks)")
    for axis in axes:
        axis.grid(alpha=0.3)
    figure.suptitle("Fiat Tipo MA1.7 G: RAM[31h] → P5.0, 1.000 RPM; "
                   "piso em 00h")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)
    plt.close(figure)
    print(args.output)


if __name__ == "__main__":
    main()
