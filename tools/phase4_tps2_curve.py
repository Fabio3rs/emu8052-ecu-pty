"""Continuous track-2 TPS curve counterfactual (--exp tps2_end_v): track 2 reaches V at 90 degrees. LLM-written (Claude)."""
import csv, os, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
tmp = tempfile.mkdtemp()
def job(c):
    v, rpm = c
    st = os.path.join(tmp, f'{v}_{rpm}.bin')
    try: r = run_point(BIN, ROM, rpm, extra=['--exp', f'tps2_end_v={v}'], env_extra={'MA17_XRAM_STATE_FILE': st})
    except Exception as e: r = dict(state='ERROR', reason=str(e)[:60], target_rpm=rpm)
    x = open(st, 'rb').read()[8:] if os.path.exists(st) else b'\0' * 0x400
    r.update(end_v=v, faults=x[0x4E:0x51].hex(' ')); return r
rows = []
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(job, [(v, r) for v in (4.5, 4.65, 4.7, 4.75, 4.8, 5.0) for r in (1500, 3000, 4500, 6000)]))
keys = ['end_v','target_rpm','state','reason','shaft_power_kw','indicated_nm','adv_mean_deg','lambda','inj_mass_mg','iram60_tps2','iram6d','faults']
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
for r in rows: print(r['end_v'], int(r['target_rpm']), r['state'], r.get('shaft_power_kw'), r.get('adv_mean_deg'), r.get('lambda'), r.get('iram60_tps2'), r.get('iram6d'), r['faults'])
