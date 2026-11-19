"""Dynamic inventory of every ROM write into the retained XRAM page F800h-FBFFh across scenarios (MA17_XRAM_WRITE_PROFILE).
Classifies addresses by how often their value changes; low-change addresses are the state / adaptation candidates.
LLM-written (Claude)."""
import csv, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
tmp = tempfile.mkdtemp()
BASE = ['--physical-crank','--starter-ticks','495000','--adc7-mv','1232','--idle-bridge-p15-p16','--idle-contact-p46','--tps-bench-profile','--idle-motor-speed-mm-s','50','--idle-min-stop-mrad','5','--lambda-adc-gain','5','--dyno-scenario']
def e(*kv):
    o = []
    for k in kv: o += ['--exp', k]
    return o
scen = {  # name -> (kind, args)
 'idle_30M': ('cli', ['--stop-ticks','30000000']),
 'idle_cold_20C': ('cli', ['--stop-ticks','40000000','--coolant-c','20']),
 'idle_cold_50C': ('cli', ['--stop-ticks','40000000','--coolant-c','50']),
 'part_load_45Nm': ('cli', ['--stop-ticks','60000000','--pedal-step-tick','3000000','--pedal-mm','14','--load-step-tick','3000000','--load-nm','45']),
 'ect_open': ('cli', ['--stop-ticks','30000000','--ect-open-tick','8000000']),
 'air_open': ('cli', ['--stop-ticks','30000000']+e('air_open_tick=8000000')),
 'tps2_step_fault': ('cli', ['--stop-ticks','30000000','--tps2-high-tick','8000000']),
 'idle_contact_open': ('cli', ['--stop-ticks','30000000','--idle-contact-open-tick','8000000']),
 'idle_motor_disc': ('cli', ['--stop-ticks','30000000','--idle-motor-disconnect-tick','8000000']),
 'lambda_lean_stuck': ('cli', ['--stop-ticks','30000000','--lambda-stuck-tick','8000000','--lambda-stuck-mv','0']),
 'lambda_rich_stuck': ('cli', ['--stop-ticks','30000000','--lambda-stuck-tick','8000000','--lambda-stuck-mv','4500']),
 'wot_1500': ('pt', 1500), 'wot_3000': ('pt', 3000), 'wot_6000': ('pt', 6000),
}
def run(item):
    name, (kind, a) = item
    prof = os.path.join(tmp, name + '.csv')
    env = {'MA17_XRAM_WRITE_PROFILE': prof}
    if kind == 'cli':
        subprocess.run([BIN, ROM, *BASE, *a], env={'PATH': os.environ['PATH'], **env}, capture_output=True, text=True, timeout=1800)
    else:
        run_point(BIN, ROM, a, env_extra=env)
    return name, list(csv.DictReader(open(prof))) if os.path.exists(prof) else []
with ThreadPoolExecutor(8) as ex: results = list(ex.map(run, scen.items()))
agg = {}
for name, rows in results:
    for r in rows:
        d = agg.setdefault(r['address'], dict(writes=0, max_changes=0, scen=set(), pcs=set()))
        d['writes'] += int(r['writes']); d['max_changes'] = max(d['max_changes'], int(r['changes'])); d['scen'].add(name)
        d['pcs'].update(r['pcs'].split())
rows = []
for a in sorted(agg):
    d = agg[a]; mc = d['max_changes']
    cls = 'scratch/per-cycle' if mc > 5000 else ('dynamic' if mc > 200 else ('slow state / adaptation candidate' if mc > 2 else 'init-only or near-constant'))
    rows.append(dict(address=a, total_writes=d['writes'], max_value_changes_per_run=mc, scenarios=len(d['scen']), writer_pcs=' '.join(sorted(d['pcs'])), class_=cls))
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=list(rows[0]))
w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows), 'addresses written;', dict(Counter(r['class_'] for r in rows)), 'scenarios', [n for n, r in results if r])
