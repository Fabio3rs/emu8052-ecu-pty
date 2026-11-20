"""Base fuel map shape versus load and speed, bracketed by the two lambda-loop extremes (ADC5 held lean / rich).
lambda_base ~ midpoint of the two bounds; a full-load enrichment would pull both bounds below 1 at high pedal.
LLM-written (Claude)."""
import csv, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
def job(c):
    rpm, frac, mv = c
    try:
        r = run_point(BIN, ROM, rpm, extra=['--lambda-stuck-tick', '2000000', '--lambda-stuck-mv', str(mv), '--exp', f'dyno_pedal_fraction={frac}'], timeout=1200)
    except Exception as e:
        r = dict(state='ERROR', reason=str(e)[:60])
    r.update(rpm=rpm, pedal=frac, adc5_mv=mv); return r
grid = [(r, f, mv) for r in (1500, 2000, 3000, 4000, 5000, 6000) for f in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0) for mv in (0, 4500)]
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(job, grid))
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=['rpm','pedal','adc5_mv','state','reason','lambda','air_mg_cyl','inj_mass_mg','shaft_power_kw','throttle_rad','iram60_tps2'], extrasaction='ignore')
w.writeheader(); w.writerows(rows)
print(sum(r['state'] == 'ACCEPTED' for r in rows), '/', len(rows), 'accepted')
