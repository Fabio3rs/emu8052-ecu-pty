#!/usr/bin/env python3
"""Compare physical RPM, RAM47*25 and the P1.1 pulse period (Lote E, UI-15).

Runs the CLI in several regimes with MA17_TRACE_PORT_LATCHES=1 and reads the
[P11-OBS] lines (every P1.1 transition: physical angle/rpm, RAM46/47).
usage: p11_tach_trace.py <emu8051-tty> <rom.bin> <out-dir>
"""
import csv, math, os, statistics, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sevel_preset import BENCH_LEAK_MM2

TICKS_PER_S = 990000.0
BASE = ["--8052", "--physical-crank", "--starter-ticks", "495000", "--adc7-mv", "1232",
        "--idle-bridge-p15-p16", "--idle-contact-p46", "--coolant-c", "90",
        "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", str(BENCH_LEAK_MM2), "--lambda-adc-gain", "5"]
# name: (extra args, stop tick, (window start, window end))
SCENARIOS = {
    "start": ([], 1500000, (300000, 900000)),
    "idle": ([], 6000000, (3000000, 6000000)),
    "load24": (["--load-nm", "24", "--load-step-tick", "3000000"], 8000000, (5000000, 8000000)),
    "pedal12": (["--pedal-step-tick", "3000000", "--pedal-rise-ticks", "990000", "--pedal-mm", "12"], 12000000, (8000000, 12000000)),
    "pedal20": (["--pedal-step-tick", "3000000", "--pedal-rise-ticks", "990000", "--pedal-mm", "20"], 12000000, (8000000, 12000000)),
    "pedal28": (["--pedal-step-tick", "3000000", "--pedal-rise-ticks", "990000", "--pedal-mm", "28"], 12000000, (8000000, 12000000)),
    "pedal40": (["--pedal-step-tick", "3000000", "--pedal-rise-ticks", "990000", "--pedal-mm", "40"], 12000000, (8000000, 12000000)),
}


def run(name, binary, rom):
    extra, stop, window = SCENARIOS[name]
    env = dict(os.environ, MA17_TRACE_PORT_LATCHES="1")
    done = subprocess.run([binary, rom, *BASE, *extra, "--stop-ticks", str(stop)],
                          env=env, capture_output=True, text=True, timeout=600)
    rows, previous = [], None
    for line in done.stderr.splitlines():
        if not line.startswith("[P11-OBS]"):
            continue
        f = dict(item.split("=") for item in line.split()[1:])
        tick, high = int(f["tick"]), int(f["high"])
        if high != 1:
            continue  # one row per rising edge
        angle = float(f["angle"])
        if previous is not None and window[0] <= tick <= window[1]:
            period = tick - previous[0]
            revs = (angle - previous[1]) / (2 * math.pi)
            p11_rpm = 60.0 / ((period / TICKS_PER_S) * 2.0)  # 2 pulses/rev hypothesis
            phys = float(f["physical_rpm"])
            rows.append({"scenario": name, "tick": tick, "p11_period_ticks": period,
                         "revs_per_pulse": round(revs, 4), "physical_rpm": round(phys, 3),
                         "ram47_x25": int(f["ram47"]) * 25, "p11_rpm_2ppr": round(p11_rpm, 3),
                         "ratio_physical_over_p11": round(phys / p11_rpm, 4)})
        previous = (tick, angle)
    return name, rows, done.returncode


def main():
    binary, rom, out = sys.argv[1:4]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        results = list(pool.map(lambda n: run(n, binary, rom), SCENARIOS))
    fields = ["scenario", "tick", "p11_period_ticks", "revs_per_pulse", "physical_rpm",
              "ram47_x25", "p11_rpm_2ppr", "ratio_physical_over_p11"]
    with open(out / "p11_tach_trace.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fields); writer.writeheader()
        for _, rows, _ in results:
            writer.writerows(rows)
    lines = ["scenario,rising_edges,phys_rpm_median,ram47x25_median,revs_per_pulse_min,revs_per_pulse_median,revs_per_pulse_max,ratio_median,distinct_half_rev_intervals"]
    for name, rows, code in results:
        assert code == 0 and rows, (name, code, len(rows))
        revs = [r["revs_per_pulse"] for r in rows]
        halves = sorted({round(x * 2) / 2 for x in revs})
        lines.append(",".join(map(str, [name, len(rows),
            round(statistics.median(r["physical_rpm"] for r in rows), 1),
            round(statistics.median(r["ram47_x25"] for r in rows), 1),
            min(revs), round(statistics.median(revs), 3), max(revs),
            round(statistics.median(r["ratio_physical_over_p11"] for r in rows), 3),
            "|".join(map(str, halves))])))
    (out / "p11_summary.csv").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
