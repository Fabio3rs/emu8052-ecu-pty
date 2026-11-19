"""Causal checks: (1) what a stepped TPS2 force changes in retained XRAM; (2) 721Dh threshold patch on a TEMPORARY ROM
copy against the 70-80 C stall. The original ROM file is never modified. LLM-written (Claude)."""
import csv, json, os, shutil, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_point import run_point
BIN, ROM, OUT = sys.argv[1:4]
tmp = tempfile.mkdtemp()
rom = bytearray(open(ROM, 'rb').read())
print('ROM[721D] =', hex(rom[0x721D & 0x7FFF]), 'size', len(rom))
def patched(name, off, val):
    p = os.path.join(tmp, name + '.bin'); b = bytearray(rom); b[off] = val; open(p, 'wb').write(b); return p
def e(*kv):
    o = []
    for k in kv: o += ['--exp', k]
    return o
sts = {n: os.path.join(tmp, n + '.state') for n in ('base', 'f45', 'f50', 'f0')}
jobs = [('xram', 'base', ROM, 3000, [], {'MA17_XRAM_STATE_FILE': sts['base']}),
        ('xram', 'tps2_force_4.5V_step', ROM, 3000, e('ntc_force_tick=12000000', 'tps2_force_v=4.5'), {'MA17_XRAM_STATE_FILE': sts['f45']}),
        ('xram', 'tps2_force_5.0V_step', ROM, 3000, e('ntc_force_tick=12000000', 'tps2_force_v=5.0'), {'MA17_XRAM_STATE_FILE': sts['f50']}),
        ('xram', 'tps2_force_0.5V_step', ROM, 3000, e('ntc_force_tick=12000000', 'tps2_force_v=0.5'), {'MA17_XRAM_STATE_FILE': sts['f0']})]
for tag, val in (('721D=00', 0x00), ('721D=FF', 0xFF), ('721D=60', 0x60)):
    pr = patched(tag.replace('=', '_'), 0x721D, val)
    for c in (70, 75, 80, 90):
        jobs.append(('patch_721D', f'{tag} coolant={c}C', pr, 3000, ['--coolant-c', str(c)], {}))
for c in (70, 75, 80):
    jobs.append(('patch_721D', f'original coolant={c}C', ROM, 3000, ['--coolant-c', str(c)], {}))
def run(j):
    grp, label, rom_path, rpm, extra, env = j
    try: r = run_point(BIN, rom_path, rpm, extra=extra, env_extra=env)
    except Exception as ex: r = dict(state='ERROR', reason=str(ex)[:60], target_rpm=rpm)
    r.update(group=grp, label=label); return r
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(run, jobs))
base = open(sts['base'], 'rb').read()[8:]
diffs = {}
for n, p in sts.items():
    if n == 'base' or not os.path.exists(p): continue
    d = open(p, 'rb').read()[8:]
    diffs[n] = [f'F{0x800 + i:03X}:{base[i]:02X}->{d[i]:02X}' for i in range(len(d)) if d[i] != base[i]]
json.dump(diffs, open(OUT + '_xram.json', 'w'), indent=1)
keys = ['group','label','target_rpm','state','reason','shaft_power_kw','adv_mean_deg','lambda','iram60_tps2','iram6d']
w = csv.DictWriter(open(OUT + '.csv', 'w', newline=''), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
for r in rows: print(r['group'], r['label'], r.get('state'), r.get('reason'), r.get('shaft_power_kw'), r.get('adv_mean_deg'), r.get('lambda'), r.get('iram6d'))
for n, v in diffs.items(): print(n, len(v), ' '.join(v[:50]))
