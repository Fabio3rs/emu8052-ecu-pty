"""TPS2 threshold sweep, open-loop-bracketed enrichment check and the 75 C stall characterisation.
LLM-written (Claude)."""
import csv, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]

def pt(c):
    grp, label, rpm, extra = c
    try: r = run_point(BIN, ROM, rpm, extra=extra)
    except Exception as e: r = dict(state='ERROR', reason=str(e)[:60], target_rpm=rpm)
    r.update(group=grp, label=label); return r

def e(*kv):
    o = []
    for k in kv: o += ['--exp', k]
    return o
jobs = []
for v in (4.5, 4.6, 4.65, 4.7, 4.71, 4.72, 4.75, 4.8, 5.0):
    jobs.append(('tps2_sweep', f'{v}V', 3000, e('ntc_force_tick=12000000', f'tps2_force_v={v}')))
for rpm in (3000, 4500):
    for stuck in (0, 4500):
        for frac in (0.5, 0.7, 1.0):
            for force in (False, True):
                x = ['--lambda-stuck-tick', '2000000', '--lambda-stuck-mv', str(stuck)] + e(f'dyno_pedal_fraction={frac}')
                if force: x += e('ntc_force_tick=12000000', 'tps2_force_v=5.0')
                jobs.append(('enrich', f'adc5={stuck}mV pedal={frac} tps2={"5V" if force else "model"}', rpm, x))
for c in (65, 70, 72, 74, 75, 76, 78, 80, 85, 90):
    jobs.append(('coolant_stall', f'{c}C', 3000, ['--coolant-c', str(c)]))
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(pt, jobs))
keys = ['group','label','target_rpm','state','reason','mean_rpm','shaft_power_kw','indicated_nm','adv_mean_deg','lambda','inj_mass_mg','air_mg_cyl','fuel_g_s','iram60_tps2','iram6d','coolant_c']
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
for r in rows: print(r['group'], r['label'], r.get('target_rpm'), r.get('state'), r.get('reason'), r.get('shaft_power_kw'), r.get('adv_mean_deg'), r.get('lambda'), r.get('inj_mass_mg'), r.get('air_mg_cyl'), r.get('iram60_tps2'), r.get('iram6d'))
