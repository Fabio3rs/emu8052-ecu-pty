"""(A) ratiometric TPS validation, (B) percent-of-track linear curves, (C) TPS / idle-sensor fault cut-off above ~1500 rpm.
LLM-written (Claude)."""
import csv, os, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
tmp = tempfile.mkdtemp()
def e(*kv):
    o = []
    for k in kv: o += ['--exp', k]
    return o
jobs = []
for rpm in (3000, 6000):
    jobs.append(('A_ratio', 'supply 5.0 V (reference)', rpm, []))
    for v in (4.7, 5.3):
        jobs.append(('A_ratio', f'supply {v} V, ADC Vref follows (ratiometric)', rpm, e(f'tps_supply_v={v}')))
        jobs.append(('A_ratio', f'supply {v} V, ADC Vref fixed 5.0 V', rpm, e(f'tps_supply_v={v}', 'tps_ratiometric=0')))
for rpm in (1500, 3000, 6000):
    jobs.append(('B_linear', 'percent-of-track curves (T1 0-24 deg, T2 18-90 deg)', rpm, e('tps_linear_fraction=1')))
faults = {
 'tps_both_open_0V': ['--tps-open-tick', '2000000', '--tps-open-mv', '0'],
 'tps_both_open_5V': ['--tps-open-tick', '2000000', '--tps-open-mv', '5000'],
 'tps_both_open_2.5V': ['--tps-open-tick', '2000000', '--tps-open-mv', '2500'],
 'tps1_forced_high_from_idle': ['--tps1-high-tick', '2000000'],
 'tps2_forced_high_from_idle': ['--tps2-high-tick', '2000000'],
 'idle_contact_open': ['--idle-contact-open-tick', '2000000'],
 'idle_contact_closed': ['--idle-contact-closed-tick', '2000000'],
 'idle_motor_disconnected': ['--idle-motor-disconnect-tick', '2000000'],
 'idle_contact_open+tps2_high': ['--idle-contact-open-tick', '2000000', '--tps2-high-tick', '2000000'],
}
for name, x in faults.items():
    for rpm in (1500, 3000):
        jobs.append(('C_fault', name, rpm, x))
def job(c):
    grp, label, rpm, extra = c
    st = os.path.join(tmp, f'{abs(hash((grp, label, rpm)))}.bin')
    try: r = run_point(BIN, ROM, rpm, extra=extra, timeout=900, env_extra={'MA17_XRAM_STATE_FILE': st})
    except Exception as ex: r = dict(state='ERROR', reason=str(ex)[:60], target_rpm=rpm)
    x = open(st, 'rb').read()[8:] if os.path.exists(st) else b'\0' * 0x400
    r.update(group=grp, label=label, faults=x[0x4E:0x51].hex(' ')); return r
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(job, jobs))
keys = ['group','label','target_rpm','state','reason','mean_rpm','shaft_power_kw','adv_mean_deg','lambda','inj_mass_mg','iram66_tps1','iram60_tps2','iram6d','faults']
w = csv.DictWriter(open(OUT, 'w', newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
for r in rows: print(r['group'], r['label'], int(r['target_rpm']), r['state'], r.get('reason'), r.get('shaft_power_kw'), r.get('adv_mean_deg'), r.get('lambda'), r.get('iram66_tps1'), r.get('iram60_tps2'), r.get('faults'))
