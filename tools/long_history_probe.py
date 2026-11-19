"""Long-history experiment: ~5 simulated minutes of idle (300 M ticks), retained XRAM saved, then WOT points
started from that state vs from a fresh state. LLM-written (Claude)."""
import csv, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point, BASE_ARGS
BIN, ROM, OUT = sys.argv[1:4]
tmp = tempfile.mkdtemp(); st = os.path.join(tmp, 'long.bin')
args = [BIN, ROM, '--physical-crank','--starter-ticks','495000','--stop-ticks','300000000','--adc7-mv','1232','--idle-bridge-p15-p16','--idle-contact-p46','--tps-bench-profile','--idle-motor-speed-mm-s','50','--idle-min-stop-mrad','5','--lambda-adc-gain','5','--dyno-scenario']
r = subprocess.run(args, env={'PATH': os.environ['PATH'], 'MA17_XRAM_STATE_FILE': st}, capture_output=True, text=True, timeout=7200)
pl = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"plant"')]
th = [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"type":"thermal"')]
traj = []
for a in range(0, 300000000, 50000000):
    k = [x for x in pl if a < x['tick'] <= a + 50000000]
    if k: traj.append(dict(window_M=f'{a//1000000}-{(a+50000000)//1000000}', rpm=round(sum(x['rpm'] for x in k)/len(k),1), spark=round(sum(x['spark_deg'] for x in k)/len(k),2), lam=round(sum(x['lambda_cyl'] for x in k)/len(k),3), fuel=round(sum(x['fuel_g_s'] for x in k)/len(k),4), coolant_c=round(th[min(len(th)-1,(a+50000000)//990000-1)]['coolant_c'],1)))
d = open(st,'rb').read()[8:]
rows = []
for rpm in (1500, 3000, 6000):
    for name, env in (('fresh', {}), ('after_5min_idle', {'MA17_XRAM_STATE_FILE': os.path.join(tmp, f'p{rpm}.bin')})):
        if name != 'fresh': shutil.copy(st, env['MA17_XRAM_STATE_FILE'])
        try: p = run_point(BIN, ROM, rpm, env_extra=env); p['case'] = name
        except Exception as e: p = dict(case=name, target_rpm=rpm, state='ERROR', reason=str(e)[:80])
        rows.append(p); print(name, rpm, p.get('state'), p.get('shaft_power_kw'), p.get('adv_mean_deg'), p.get('lambda'), flush=True)
json.dump(dict(trajectory=traj, retained_f84e_50=d[0x4E:0x51].hex(' '), f80c=d[0x0C], f83d=d[0x3D], f86c=d[0x6C], f86f=d[0x6F], f869=d[0x69], f8e8=d[0xE8], f8e9=d[0xE9]), open(OUT + '_idle.json','w'), indent=1)
keys = ['case','target_rpm','state','reason','mean_rpm','shaft_power_kw','indicated_nm','adv_mean_deg','lambda','inj_mass_mg']
w = csv.DictWriter(open(OUT + '_points.csv','w',newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
print(traj)
