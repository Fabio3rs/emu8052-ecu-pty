"""Both TPS tracks at their stated end values (track 1 -> VCC above 24 deg, track 2 -> V at 90 deg). LLM-written (Claude)."""
import csv, os, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
tmp = tempfile.mkdtemp()
def job(c):
    v1, v2, rpm = c
    st = os.path.join(tmp, f'{v1}_{v2}_{rpm}.bin')
    extra = []
    if v1 != 'model': extra += ['--exp', f'tps1_end_v={v1}']
    if v2 != 'model': extra += ['--exp', f'tps2_end_v={v2}']
    try: r = run_point(BIN, ROM, rpm, extra=extra, env_extra={'MA17_XRAM_STATE_FILE': st})
    except Exception as e: r = dict(state='ERROR', reason=str(e)[:60], target_rpm=rpm)
    x = open(st, 'rb').read()[8:] if os.path.exists(st) else b'\0' * 0x400
    r.update(t1_end=v1, t2_end=v2, faults=x[0x4E:0x51].hex(' ')); return r
grid = [(a, b, r) for a in ('model', 4.9, 5.0) for b in ('model', 4.8, 5.0) for r in (3000, 6000)]
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(job, grid))
keys = ['t1_end','t2_end','target_rpm','state','reason','shaft_power_kw','adv_mean_deg','lambda','inj_mass_mg','iram66_tps1','iram60_tps2','iram6d','faults']
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
for r in rows: print(r['t1_end'], r['t2_end'], int(r['target_rpm']), r['state'], r.get('shaft_power_kw'), r.get('adv_mean_deg'), r.get('lambda'), r.get('iram66_tps1'), r.get('iram60_tps2'), r.get('iram6d'), r['faults'])
