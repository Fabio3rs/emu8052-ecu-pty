"""A/B matrix of identified single-variable interventions on the ROM crank dyno
(CURVES_STUDY / SEVEL_ROM_POWER_GAP_INVESTIGATION). Every row carries the code SHA, ROM SHA and
the exact --exp arguments. LLM-written (Claude)."""
import argparse
import csv
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point  # noqa: E402

KEYS = ["state", "reason", "target_rpm", "mean_rpm", "shaft_power_kw", "shaft_torque_nm",
        "indicated_nm", "friction_nm", "pumping_nm", "accessory_nm", "adv_mean_deg", "lambda",
        "inj_mass_mg", "ve_ambient", "air_mg_cyl", "fuel_g_s", "mbt_mean_deg", "eta_i_mean", "xr_mean", "spark_strength_mean", "spark_strength_min", "ram69_end", "iram66_tps1", "iram47_rpm", "iram61_vbat", "iram65_adc5", "xram_f8e8", "iram60_tps2", "iram6d", "brake_saturated_s", "energy_residual_rel", "bmep_bar",
        "code_sha", "code_dirty", "rom_sha256"]

def exp(*kv):
    out = []
    for item in kv:
        out += ["--exp", item]
    return out

EXPERIMENTS = {
    "E0_original": [],
    "A1_alt_off": exp("acc_alt_scale=0"),
    "A2_pump_off": exp("acc_pump_scale=0"),
    "A3_acc_off": exp("acc_alt_scale=0", "acc_pump_scale=0"),
    "A4_pump_x0.04": exp("acc_pump_scale=0.04"),
    "I1_mbt": exp("adv_force_mbt=1"),
    "I2_mbt-5": exp("adv_force_mbt=1", "adv_offset_deg=5"),
    "I3_mbt-10": exp("adv_force_mbt=1", "adv_offset_deg=10"),
    "L1_legacy_spark": exp("spark_torque_legacy=1"),
    "H1_settle_6M": exp("dyno_settle_ticks=6000000"),
    "H2_settle_24M": exp("dyno_settle_ticks=24000000"),
    "C2_legacy_pump_and_spark": exp("acc_pump_scale=25", "spark_torque_legacy=1"),
    "C1_acc_off_mbt": exp("acc_alt_scale=0", "acc_pump_scale=0", "adv_force_mbt=1"),
}

def one(job):
    name, extra, rpm, binary, rom = job
    row = run_point(binary, rom, rpm, extra=extra)
    row["experiment"] = name
    row["exp_args"] = " ".join(extra)
    return row

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("binary"); ap.add_argument("rom"); ap.add_argument("--out", required=True)
    ap.add_argument("--rpms", default="1500,3000,4500,6000")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    names = [n for n in EXPERIMENTS if not a.only or n in a.only.split(",")]
    jobs = [(n, EXPERIMENTS[n], float(r), a.binary, a.rom) for n in names for r in a.rpms.split(",")]
    with ProcessPoolExecutor(a.workers) as pool:
        rows = list(pool.map(one, jobs))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    cols = ["experiment", "exp_args"] + KEYS
    with open(a.out, "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    for r in rows:
        print(r["experiment"], r["target_rpm"], r["state"], r["shaft_power_kw"], r["indicated_nm"], r["accessory_nm"], r["adv_mean_deg"])
