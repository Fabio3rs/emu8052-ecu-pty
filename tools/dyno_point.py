"""Run one ROM crank-dyno point and emit an identified CSV/JSON row (GOAL_DYNO_ROM phase 5).

The binary prints the measurement ({"type":"dyno_point"...}); this wrapper adds the
identification the binary cannot know cheaply (code commit, ROM SHA-256, full argument list,
scenario) so every row is reproducible. LLM-written (Claude).
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_manifest import ROOT, git_state, sha256  # noqa: E402

BASE_ARGS = ["--physical-crank", "--starter-ticks", "495000", "--stop-ticks", "90000000",
             "--adc7-mv", "1232", "--idle-bridge-p15-p16", "--idle-contact-p46",
             "--tps-bench-profile", "--idle-motor-speed-mm-s", "50", "--idle-min-stop-mrad", "5",
             "--lambda-adc-gain", "5"]
SCENARIO = {"ethanol_percent": 22, "throttle_leak_mm2": 9, "accessories": True,
            "coolant_c": 90.0, "ambient_c": 20.0}


def run_point(binary, rom, rpm, tdc_deg=120, cycles=40, timeout=900):
    args = [str(binary), str(rom), *BASE_ARGS, "--dyno-scenario",
            "--tdc-reference-deg", str(tdc_deg), "--dyno-point", str(rpm),
            "--dyno-cycles", str(cycles)]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    out = subprocess.run(args, env=env, text=True, capture_output=True, timeout=timeout,
                         check=True).stdout
    rows = [json.loads(l) for l in out.splitlines() if l.startswith('{"type":"dyno_point"')]
    assert len(rows) == 1, "expected exactly one dyno_point row"
    row = rows[0]
    row.pop("type")
    git = git_state()
    row.update(code_sha=git["commit"], code_dirty=bool(git["dirty_files"]),
               rom_sha256=sha256(rom), args=" ".join(args[2:]),
               scenario=json.dumps({**SCENARIO, "tdc_deg": tdc_deg}, sort_keys=True))
    return row


def write_row(row, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flat = {k: (json.dumps(v) if isinstance(v, list) else v) for k, v in row.items()}
    with open(path.with_suffix(".csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat))
        writer.writeheader()
        writer.writerow(flat)
    with open(path.with_suffix(".json"), "w") as handle:
        json.dump(row, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary")
    parser.add_argument("rom")
    parser.add_argument("--rpm", type=float, default=3000.0)
    parser.add_argument("--cycles", type=float, default=40)
    parser.add_argument("--tdc-deg", type=int, default=120)
    parser.add_argument("--out", required=True, help="path without extension")
    a = parser.parse_args()
    result = run_point(a.binary, a.rom, a.rpm, a.tdc_deg, a.cycles)
    write_row(result, a.out)
    print(result["state"], result["reason"], "rpm", result["mean_rpm"],
          "P_kW", result["shaft_power_kw"])
