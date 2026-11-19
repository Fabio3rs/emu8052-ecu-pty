"""Idle speed vs a forced NTC voltage on ADC3 (IRAM 63h, coolant) or ADC2 (IRAM 62h, air), one channel at a time.
LLM-written (Claude)."""
import json, os, subprocess, sys, csv
from concurrent.futures import ThreadPoolExecutor
BIN, ROM, OUT = sys.argv[1:4]
BASE = ['--physical-crank','--starter-ticks','495000','--stop-ticks','48000000','--adc7-mv','1232','--idle-bridge-p15-p16','--idle-contact-p46','--tps-bench-profile','--idle-motor-speed-mm-s','50','--idle-min-stop-mrad','5','--lambda-adc-gain','5','--dyno-scenario']

def run(c):
    ch, v = c
    extra = [] if ch == 'none' else ['--exp','ntc_force_tick=1','--exp',f'{ch}_force_v={v}']
    r = subprocess.run([BIN, ROM, *BASE, *extra], env={'PATH': os.environ['PATH']}, capture_output=True, text=True, timeout=1800)
    pl = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"plant"')]
    th = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"thermal"')]
    late = [x for x in pl if x['tick'] > 36000000]
    n = max(1, len(late))
    return dict(channel=ch, volts=v, ram62=th[-1]['ram62'], ram63=th[-1]['ram63'],
                rpm=round(sum(x['rpm'] for x in late)/n, 1), fuel_g_s=round(sum(x['fuel_g_s'] for x in late)/n, 4),
                spark_deg=round(sum(x['spark_deg'] for x in late)/n, 2), lambda_cyl=round(sum(x['lambda_cyl'] for x in late)/n, 3), windows=len(late))

vs = [0.4, 0.6, 0.8, 1.0, 1.4, 1.8, 2.2, 2.8, 3.5]
cases = [('none', 0)] + [('ect', v) for v in vs] + [('air', v) for v in vs]
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(run, cases))
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for r in rows: print(r)
