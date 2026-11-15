#!/usr/bin/env python3
"""Map raw TPS ADC pairs to IRAM6F and the two ROM segment headers."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROMS = {"G": ROOT / "FiatTipo_MA17_dump_27c256.bin",
        "S88": ROOT / "firmwares_modificados_ma17_tipo" /
               "tipo 1.6 alcool27c256 SUN 8817.bin"}
ADC0 = (40, 80, 120, 160, 200)
ADC6 = (95, 130, 165, 200, 235)
RAM6F = re.compile(r"^\[SENSOR-RAM\].*addr=6F value=[0-9A-F]{2}->([0-9A-F]{2})", re.M)
HEADER = re.compile(r"^\[MOVC-SUMMARY\] pc=527D opcode=93 "
                    r"dptr=(755C|7569) .* count=(\d+)$", re.M)
ALTERNATE = re.compile(r"^\[TPS-FLOW\] tick=(\d+) PC=11B6 "
                       r"R2=([0-9A-F]{2}) R3=([0-9A-F]{2}) .* "
                       r"A=([0-9A-F]{2}) .* RAM28=([0-9A-F]{2})", re.M)


def parse_trace(stderr, stop_ticks):
    if f"[TRACE-STOP] ticks={stop_ticks}" not in stderr:
        raise ValueError("trace did not reach the requested tick")
    values = RAM6F.findall(stderr)
    if not values:
        raise ValueError("IRAM6F was not observed")
    reads = {"755C": 0, "7569": 0}
    for address, count in HEADER.findall(stderr):
        reads[address] += int(count)
    if not any(reads.values()):
        raise ValueError("neither segment header was read")
    samples = ALTERNATE.findall(stderr)
    sample = None
    if samples:
        tick, r2, r3, value, ram28 = samples[0]
        calculated = max(0, min(255, int(r2, 16) + 13) - int(r3, 16))
        sample = {"tick": int(tick), "r2": r2, "r3": r3, "value": value,
                  "ram28": ram28, "formula_matches": calculated == int(value, 16)}
    return {"iram6f_hex": values[-1], "header_reads": reads,
            "alternative_branch_reached": "[PC-HIT] 11A8" in stderr,
            "alternate_formula_sample": sample}


def plot_surface(cases, output_path, adc0_values, adc6_values,
                 point_override=None, variant="G"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_pair = {(case["adc0"], case["adc6"]): case for case in cases}
    values = [[int(by_pair[a0, a6]["iram6f_hex"], 16)
               for a6 in adc6_values] for a0 in adc0_values]
    figure, axis = plt.subplots(figsize=(8.4, 5.5))
    image = axis.imshow(values, origin="lower", vmin=0, vmax=255,
                        cmap="viridis", aspect="auto")
    axis.set_xticks(range(len(adc6_values)), adc6_values)
    axis.set_yticks(range(len(adc0_values)), adc0_values)
    axis.set_xlabel("ADC6 bruto (byte alto, estímulo digital)")
    axis.set_ylabel("ADC0 bruto (byte alto, estímulo digital)")
    title = f"Fiat {variant}: IRAM[6Fh] e cabeçalho selecionado, 1000 RPM"
    axis.set_title(title + (" (MOVC substituído)" if point_override else ""))
    for row, a0 in enumerate(adc0_values):
        for column, a6 in enumerate(adc6_values):
            case = by_pair[a0, a6]
            mode = "5" if case["header_reads"]["7569"] else "11"
            axis.text(column, row, f"{case['iram6f_hex']}\n{mode}",
                      ha="center", va="center", color="white", fontsize=9)
    figure.colorbar(image, ax=axis, label="IRAM[6Fh] bruto (u8)")
    figure.text(0.02, 0.01, "Células: valor hexadecimal / segmentos 5 ou 11. "
                "Sem calibração física dos sensores.", fontsize=8)
    figure.tight_layout(rect=(0, 0.04, 1, 1))
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def audit(output_dir, stop_ticks, adc0_values=ADC0, adc6_values=ADC6,
          point_override=None, variant="G"):
    rom = ROMS[variant]
    executable = ROOT / "build" / "emu8051-tty"
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for adc0 in adc0_values:
        for adc6 in adc6_values:
            settings = {"MA17_STOP_TICKS": str(stop_ticks),
                        "MA17_CRANK_IMMEDIATE": "1", "MA17_TRACE_PC": "1",
                        "MA17_TRACE_MOVC": "1", "MA17_CRANK_RPM": "1000",
                        "MA17_TRACE_TPS_AFTER_TICK": str(stop_ticks // 2),
                        "MA17_ADC_CH0": str(adc0), "MA17_ADC_CH2": "140",
                        "MA17_ADC_CH3": "34", "MA17_ADC_CH6": str(adc6),
                        "MA17_ADC_CH7": "63"}
            if point_override:
                settings["MA17_OVERRIDE_MOVC_AT"] = point_override
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith("MA17_")}
            environment.update(settings)
            run = subprocess.run([str(executable), str(rom), "--8052"],
                                 env=environment, capture_output=True,
                                 text=True, timeout=60, check=False)
            if run.returncode:
                raise RuntimeError(f"ADC0/6={adc0}/{adc6}: exit {run.returncode}")
            observation = parse_trace(run.stderr, stop_ticks)
            log = f"adc0_{adc0}_adc6_{adc6}.stderr.log"
            (output_dir / log).write_text(run.stderr)
            cases.append({"adc0": adc0, "adc6": adc6, "stderr_log": log,
                          **observation})
        print(f"ADC0={adc0}: {len(cases)} cases complete", flush=True)
    result = {"hardware_profile": f"Fiat {variant} 11.88 MHz digital stimulus",
              "variant": variant,
              "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
              "emulator_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "rpm": 1000, "stop_ticks": stop_ticks,
              "fixed_adc": {"2": 140, "3": 34, "7": 63},
              "adc_defaults_unset_channels": {"1": 130, "4": 90, "5": 110},
              "point_override": point_override,
              "adc0_values": list(adc0_values),
              "adc6_values": list(adc6_values), "cases": cases}
    (output_dir / "tps_surface.json").write_text(json.dumps(result, indent=2) + "\n")
    plot_surface(cases, output_dir / "tps_surface.png",
                 adc0_values, adc6_values, point_override, variant)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--variant", choices=ROMS, default="G")
    parser.add_argument("--stop-ticks", type=int, default=4000000)
    parser.add_argument("--adc0-values", default=",".join(map(str, ADC0)))
    parser.add_argument("--adc6-values", default=",".join(map(str, ADC6)))
    parser.add_argument("--point-override", help="MOVC PC:ADDRESS:VALUE in hex")
    args = parser.parse_args()
    if args.stop_ticks <= 0:
        parser.error("--stop-ticks must be positive")
    try:
        adc0_values = tuple(int(value) for value in args.adc0_values.split(","))
        adc6_values = tuple(int(value) for value in args.adc6_values.split(","))
    except ValueError:
        parser.error("ADC value lists must contain comma-separated integers")
    if any(not values or len(set(values)) != len(values) or
           any(value < 4 or value > 247 for value in values)
           for values in (adc0_values, adc6_values)):
        parser.error("ADC values must be distinct and within 4..247")
    if args.point_override and not re.fullmatch(
            r"[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{2}",
            args.point_override):
        parser.error("--point-override must be PC:ADDRESS:VALUE in hex")
    output_dir = args.output_dir or (ROOT / "build" / "ma17-analysis" /
                                    "variants" /
                                    ("tps_surface_current" if args.variant == "G"
                                     else "tps_surface_s88_current"))
    result = audit(output_dir, args.stop_ticks, adc0_values, adc6_values,
                   args.point_override, args.variant)
    print(f"cases={len(result['cases'])} "
          f"five_segment={sum(c['header_reads']['7569'] > 0 for c in result['cases'])}")


if __name__ == "__main__":
    main()
