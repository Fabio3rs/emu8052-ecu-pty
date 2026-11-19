"""Phase-4 probes: sensor / WOT recognition, thermal state, warm restarts with retained XRAM,
closed-loop lambda response. Writes docs/dyno/investigation/phase4.csv. LLM-written (Claude)."""
import csv
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point  # noqa: E402

KEYS = ["state", "reason", "target_rpm", "mean_rpm", "shaft_power_kw", "indicated_nm", "throttle_rad",
        "coolant_c", "air_c", "adv_mean_deg", "lambda", "inj_mass_mg", "inj_width_ms", "ram69_end",
        "iram66_tps1", "iram47_rpm", "iram61_vbat", "iram65_adc5", "xram_f8e8", "iram60_tps2", "iram6d", "air_mg_cyl",
        "spark_strength_mean", "code_sha", "rom_sha256"]


def exp(*kv):
    out = []
    for item in kv:
        out += ["--exp", item]
    return out


def job(args):
    group, label, rpm, extra, env, binary, rom = args
    row = run_point(binary, rom, rpm, extra=extra, env_extra=env)
    row.update(group=group, label=label, extra=" ".join(extra), env=" ".join(f"{k}={v}" for k, v in env.items()))
    return row


def main(binary, rom, out):
    rows = []
    with ProcessPoolExecutor(6) as pool:
        jobs = []
        for rpm in (3000, 6000):  # pedal fraction: does the ROM change decisions near WOT?
            for frac in (0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0):
                jobs.append(("pedal", f"pedal={frac}", rpm, exp(f"dyno_pedal_fraction={frac}"), {}, binary, rom))
        for rpm in (3000, 6000):  # thermal state
            for c in (60, 75, 105):
                jobs.append(("coolant", f"coolant={c}", rpm, ["--coolant-c", str(c)], {}, binary, rom))
        for rpm in (3000, 6000):  # closed-loop lambda: held ADC5 (rich / near / lean), from tick 2 M
            for mv in (1000, 2600, 4000):
                jobs.append(("lambda_forced", f"adc5={mv}mV", rpm,
                             ["--lambda-stuck-tick", "2000000", "--lambda-stuck-mv", str(mv)], {}, binary, rom))
        for rpm in (1500, 3000, 4500, 6000):  # counterfactual: ADC0 (IRAM 60h) forced to the 5 V reference at the pedal step
            jobs.append(("tps2_forced", "tps2=5V@12M", rpm, ["--tps2-high-tick", "12000000"], {}, binary, rom))
            jobs.append(("tps2_forced_base", "original", rpm, [], {}, binary, rom))
        rows += list(pool.map(job, jobs))
    # Warm restarts: chain of points, each loading the retained XRAM saved by the previous run.
    tmp = tempfile.mkdtemp()
    state = os.path.join(tmp, "state.bin")
    env = {"MA17_XRAM_STATE_FILE": state}
    chain = [("fresh_saved", 3000), ("warm_after_3000", 6000), ("warm_after_6000", 1500),
             ("warm_after_1500", 3000), ("warm_repeat_3000", 3000)]
    for label, rpm in chain:
        r = job(("warm_chain", label, rpm, [], env, binary, rom))
        rows.append(r)
    cols = ["group", "label", "extra", "env"] + KEYS
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r["group"], r["label"], r["target_rpm"], r["state"], r["reason"], r["shaft_power_kw"], r["adv_mean_deg"], r["lambda"], r["iram66_tps1"], r["xram_f8e8"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
