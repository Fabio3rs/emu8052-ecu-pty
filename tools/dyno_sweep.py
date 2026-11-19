#!/usr/bin/env python3
"""ROM crank-dyno sweep under three assumed TDC references (GOAL_DYNO_ROM phase 6).

run:   dyno_sweep.py run BINARY ROM OUTDIR   -> sweep_tdc{117,120,123}.csv + manifest.json
plot:  dyno_sweep.py plot OUTDIR ISOLATED_CSV -> sweep.png + sweep_table.md (numbers read from CSVs)

Only the TDC reference changes between the three sweeps; fuel, leak, accessories, temperatures,
dt and ROM are identical. The result is the response of ROM + plant under each ASSUMED reference:
the highest power does not determine the physical TDC. LLM-written (Claude).
"""
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_manifest import write_manifest  # noqa: E402
from dyno_point import BASE_ARGS, SCENARIO, run_point, write_row  # noqa: E402,F401

TDCS = (117, 120, 123)
RPMS = (1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000)


def flat(row):
    return {k: (json.dumps(v) if isinstance(v, list) else v) for k, v in row.items()}


def run(binary, rom, outdir, workers=6):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = [(t, r) for t in TDCS for r in RPMS]
    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(lambda j: run_point(binary, rom, j[1], j[0], 40), jobs))
    for tdc in TDCS:
        rows = [flat(r) for (t, _), r in zip(jobs, results) if t == tdc]
        with open(outdir / f"sweep_tdc{tdc}.csv", "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write_manifest(outdir, tool="tools/dyno_sweep.py run", rom=str(rom),
                   args={"base": BASE_ARGS, "per_point": ["--dyno-scenario", "--tdc-reference-deg",
                                                          "<117|120|123>", "--dyno-point", "<rpm>",
                                                          "--dyno-cycles", "40"]},
                   scenario=SCENARIO, rpms=list(RPMS), tdc_deg=list(TDCS), dt_us="ROM tick (1 us)",
                   fuel="E22", leak_mm2=SCENARIO["throttle_leak_mm2"], accessories=True,
                   coolant_c=SCENARIO["coolant_c"], ambient_c=SCENARIO["ambient_c"],
                   pms_assumed_deg=list(TDCS))


def load(path):
    with open(path) as handle:
        return list(csv.DictReader(handle))


def plot(outdir, isolated):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    outdir = Path(outdir)
    iso = load(isolated)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
    for tdc, style in zip(TDCS, ("s-", "o-", "^-")):
        rows = [r for r in load(outdir / f"sweep_tdc{tdc}.csv") if r["state"] == "ACCEPTED"]
        rpm = [float(r["mean_rpm"]) for r in rows]
        ax[0].plot(rpm, [float(r["shaft_power_kw"]) for r in rows], style, label=f"ROM, PMS {tdc} deg")
        ax[1].plot(rpm, [float(r["shaft_torque_nm"]) for r in rows], style, label=f"ROM, PMS {tdc} deg")
    ax[0].plot([float(r["rpm"]) for r in iso], [float(r["power_kw"]) for r in iso], "k:",
               label="isolated dyno (MBT spark)")
    ax[1].plot([float(r["rpm"]) for r in iso], [float(r["torque_nm"]) for r in iso], "k:",
               label="isolated dyno (MBT spark)")
    ax[0].set(title="Shaft power", xlabel="rpm", ylabel="kW")
    ax[1].set(title="Shaft torque", xlabel="rpm", ylabel="N.m")
    for a in ax:
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    fig.suptitle("ROM crank dyno, E22, response under each ASSUMED TDC reference (not a TDC measurement)")
    fig.tight_layout()
    fig.savefig(outdir / "sweep.png", dpi=130)
    lines = ["| TDC ref | rpm | state | spark abs (deg, mod 180) | advance vs ref (deg) | "
             "power (kW) | torque (N.m) | lambda | RAM[69h] raw |", "|---|---|---|---|---|---|---|---|---|"]
    for tdc in TDCS:
        for r in load(outdir / f"sweep_tdc{tdc}.csv"):
            cyl = json.loads(r["spark_abs_deg_cyl"])
            spark = sum(c % 180.0 for c in cyl) / len(cyl) if cyl and any(cyl) else float("nan")
            state = r["state"] if r["state"] == "ACCEPTED" else f"INVALID:{r['reason']}"
            lines.append(f"| {tdc} | {float(r['mean_rpm']):.0f} | {state} | {spark:.2f} | "
                         f"{float(r['adv_mean_deg']):.2f} | {float(r['shaft_power_kw']):.2f} | "
                         f"{float(r['shaft_torque_nm']):.1f} | {float(r['lambda']):.3f} | "
                         f"{r['ram69_min']}-{r['ram69_max']} (end {r['ram69_end']}) |")
    (outdir / "sweep_table.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(*sys.argv[2:5])
    elif sys.argv[1] == "plot":
        plot(*sys.argv[2:4])
    else:
        sys.exit(__doc__)
