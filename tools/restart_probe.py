"""Experiments 6 and 7 of CURVES_STUDY: warm reboot (retained XRAM) and cold reboot (XRAM wiped, POF=1)
mid-run, idle behaviour before/after, retained-XRAM diffs and dyno points after the reboot.
LLM-written (Claude)."""
import csv, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
BASE = ['--physical-crank','--starter-ticks','495000','--stop-ticks','60000000','--adc7-mv','1232','--idle-bridge-p15-p16','--idle-contact-p46','--tps-bench-profile','--idle-motor-speed-mm-s','50','--idle-min-stop-mrad','5','--lambda-adc-gain','5','--dyno-scenario']
tmp = tempfile.mkdtemp()

def idle(c):
    name, env = c
    st = os.path.join(tmp, name + '.bin')
    r = subprocess.run([BIN, ROM, *BASE], env={'PATH': os.environ['PATH'], 'MA17_XRAM_STATE_FILE': st, **env}, capture_output=True, text=True, timeout=1800)
    pl = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"plant"')]
    def win(a, b):
        k = [x for x in pl if a < x['tick'] <= b]; n = max(1, len(k))
        return dict(rpm=round(sum(x['rpm'] for x in k)/n, 1), spark=round(sum(x['spark_deg'] for x in k)/n, 2), lam=round(sum(x['lambda_cyl'] for x in k)/n, 3), fuel=round(sum(x['fuel_g_s'] for x in k)/n, 4), n=len(k))
    d = open(st, 'rb').read()[8:]
    return dict(case=name, before=win(22000000, 30000000), after=win(50000000, 60000000), log=[l for l in r.stderr.splitlines() if 'REBOOT' in l][:1], xram=d)

cases = [('no_reboot', {}), ('warm_reboot_30M', {'MA17_WARM_REBOOT_TICK': '30000000'}), ('cold_reboot_30M', {'MA17_COLD_REBOOT_TICK': '30000000'})]
with ThreadPoolExecutor(3) as ex: rows = list(ex.map(idle, cases))
base = rows[0]['xram']
out = []
for r in rows:
    diff = [i for i in range(len(base)) if base[i] != r['xram'][i]]
    out.append(dict(case=r['case'], before=r['before'], after=r['after'], reboot_log=r['log'], xram_diff_vs_no_reboot=[f'F{0x800+i:03X}:{base[i]:02X}->{r["xram"][i]:02X}' for i in diff][:40], xram_diff_count=len(diff)))
json.dump(out, open(OUT + '_idle.json', 'w'), indent=1)
for o in out: print(o['case'], o['before'], o['after'], o['reboot_log'], 'xram diffs:', o['xram_diff_count'])
rows2 = []
for rpm in (1500, 3000, 6000):
    for name, env in (('no_reboot', {}), ('warm_reboot_5M', {'MA17_WARM_REBOOT_TICK': '5000000'}), ('cold_reboot_5M', {'MA17_COLD_REBOOT_TICK': '5000000'})):
        try:
            r = run_point(BIN, ROM, rpm, env_extra=env); r['case'] = name
        except Exception as e:
            r = dict(case=name, target_rpm=rpm, state='ERROR', reason=str(e)[:80])
        rows2.append(r); print(name, rpm, r.get('state'), r.get('shaft_power_kw'), r.get('adv_mean_deg'), r.get('lambda'))
keys = ['case','target_rpm','state','reason','mean_rpm','shaft_power_kw','indicated_nm','adv_mean_deg','lambda','inj_mass_mg']
w = csv.DictWriter(open(OUT + '_points.csv', 'w', newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows2)
