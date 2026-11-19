"""ADC2/ADC3 NTC swap counterfactual (--exp swap_ntc=1): idle run + fault memory, then dyno points. LLM-written (Claude)."""
import json, os, subprocess, sys, tempfile, csv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
BASE = ['--physical-crank','--starter-ticks','495000','--stop-ticks','60000000','--adc7-mv','1232','--idle-bridge-p15-p16','--idle-contact-p46','--tps-bench-profile','--idle-motor-speed-mm-s','50','--idle-min-stop-mrad','5','--lambda-adc-gain','5','--dyno-scenario']
tmp = tempfile.mkdtemp()

def idle(c):
    name, extra = c
    st = os.path.join(tmp, name + '.bin')
    r = subprocess.run([BIN, ROM, *BASE, *extra], env={'PATH': os.environ['PATH'], 'MA17_XRAM_STATE_FILE': st}, capture_output=True, text=True, timeout=1500)
    pl = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"plant"')]
    th = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"thermal"')]
    d = open(st,'rb').read()[8:]
    late = [x for x in pl if x['tick'] > 40000000]
    rpms = [x['rpm'] for x in late]
    return dict(case=name, rpm_mean=round(sum(rpms)/max(1,len(rpms)),1), rpm_min=min(rpms or [0]), rpm_max=max(rpms or [0]),
                ram62=th[-1]['ram62'], ram63=th[-1]['ram63'], coolant_c=th[-1]['coolant_c'], iat_c=th[-1]['iat_c'],
                spark=round(sum(x['spark_deg'] for x in late)/max(1,len(late)),2), fault_bits=d[0x4E:0x51].hex(' '), counters=d[0x51:0x5C].hex(' '), windows=len(late))
cases = [('idle_base_90', []), ('idle_swap_90', ['--exp','swap_ntc=1']), ('idle_base_100', ['--coolant-c','100']), ('idle_swap_100', ['--coolant-c','100','--exp','swap_ntc=1'])]
with ThreadPoolExecutor(4) as ex: rows = list(ex.map(idle, cases))
for r in rows: print(r)
json.dump(rows, open(OUT + '_idle.json','w'), indent=1)
pts = []
for rpm in (1500, 3000, 6000):
    for name, extra in (('base', []), ('swap', ['--exp','swap_ntc=1']), ('swap_100C', ['--coolant-c','100','--exp','swap_ntc=1'])):
        try:
            r = run_point(BIN, ROM, rpm, extra=extra); r['case'] = name
        except Exception as e:
            r = dict(case=name, target_rpm=rpm, state='ERROR', reason=str(e)[:80])
        pts.append(r); print(name, rpm, r.get('state'), r.get('reason'), r.get('shaft_power_kw'), r.get('adv_mean_deg'), r.get('lambda'), r.get('iram62_dummy',''))
keys = ['case','target_rpm','state','reason','mean_rpm','shaft_power_kw','indicated_nm','adv_mean_deg','lambda','inj_mass_mg','coolant_c','air_c']
w = csv.DictWriter(open(OUT + '_points.csv','w',newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(pts)
