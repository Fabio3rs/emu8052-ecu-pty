#!/usr/bin/env python3
"""Reproduce a bounded G/S88 RAM57 selector sweep in the Fiat harness."""

import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROMS = {
    "G": ROOT / "FiatTipo_MA17_dump_27c256.bin",
    "S88": ROOT / "firmwares_modificados_ma17_tipo" /
           "tipo 1.6 alcool27c256 SUN 8817.bin",
}
CHANGE = re.compile(r"^\[ENGINE-RAM\] tick=(\d+) addr=57 "
                    r"value=([0-9A-F]{2})->([0-9A-F]{2}) "
                    r"source_PC=([0-9A-F]{4})$", re.M)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_trace(stderr, stop_ticks):
    marker = f"[TRACE-STOP] ticks={stop_ticks}"
    if marker not in stderr:
        raise ValueError(f"missing {marker}")
    return {
        "reader_1378_reached": "[PC-HIT] 1378" in stderr,
        "ram57_changes": [
            {"tick": int(tick), "before": before, "after": after,
             "source_pc": pc}
            for tick, before, after, pc in CHANGE.findall(stderr)],
    }


def audit(output_dir, stop_ticks):
    executable = ROOT / "build" / "emu8051-tty"
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for name, rpm, tps, adc3 in itertools.product(
            ROMS, (1000, 3000), ((40, 95), (180, 247)), (20, 232)):
        rom = ROMS[name]
        case_id = f"{name}_rpm{rpm}_tps{tps[0]}_{tps[1]}_adc3_{adc3}"
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_")}
        environment.update({
            "MA17_STOP_TICKS": str(stop_ticks),
            "MA17_CRANK_IMMEDIATE": "1", "MA17_TRACE_PC": "1",
            "MA17_CRANK_RPM": str(rpm),
            "MA17_ADC_CH0": str(tps[0]), "MA17_ADC_CH2": "160",
            "MA17_ADC_CH3": str(adc3), "MA17_ADC_CH6": str(tps[1]),
            "MA17_ADC_CH7": "63",
        })
        run = subprocess.run([str(executable), str(rom), "--8052"],
                             env=environment, capture_output=True,
                             text=True, timeout=60, check=False)
        (output_dir / f"{case_id}.stderr.log").write_text(run.stderr)
        if run.returncode:
            raise RuntimeError(f"{case_id}: emulator exited {run.returncode}")
        observed = parse_trace(run.stderr, stop_ticks)
        cases.append({"id": case_id, "rom": name, "rpm": rpm,
                      "tps_adc0_adc6": list(tps), "adc3": adc3,
                      "stderr_log": f"{case_id}.stderr.log", **observed})
    result = {
        "hardware_profile": "experimental Fiat 11.88 MHz harness; G/S88 only",
        "emulator_sha256": sha256(executable),
        "rom_sha256": {name: sha256(path) for name, path in ROMS.items()},
        "stop_ticks": stop_ticks,
        "adc_defaults_unset_channels": {"1": 130, "4": 90, "5": 110},
        "fixed_adc": {"2": 160, "7": 63},
        "kline_injection": False,
        "cases": cases,
    }
    (output_dir / "ram57_grid.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "build" / "ma17-analysis" / "variants" /
                                "ram57_grid_current")
    parser.add_argument("--stop-ticks", type=int, default=2400000)
    args = parser.parse_args()
    if args.stop_ticks <= 0:
        parser.error("--stop-ticks must be positive")
    result = audit(args.output_dir, args.stop_ticks)
    print(f"cases={len(result['cases'])} "
          f"reader_reached={sum(c['reader_1378_reached'] for c in result['cases'])} "
          f"ram57_changes={sum(len(c['ram57_changes']) for c in result['cases'])}")


if __name__ == "__main__":
    main()
