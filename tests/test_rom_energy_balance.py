"""ROM free idle: the plant energy ledger closes (GOAL_DYNO_ROM 3.5/3.6). LLM-written (Claude).

|energy_residual_rel| < 0.5 % in every late window, and the mean shaft power over consecutive
windows is |P| < 0.3 kW (free idle with accessories: nothing leaves the shaft, the speed is
steady). The old "brake torque ~ 0" criterion was J*domega/dt, i.e. tautological.
"""
import json
import os
import statistics
import subprocess
import sys

binary, rom = sys.argv[1:3]
out = subprocess.run(
    [binary, rom, "--physical-crank", "--starter-ticks", "495000", "--stop-ticks", "30000000",
     "--adc7-mv", "1232", "--idle-bridge-p15-p16", "--idle-contact-p46", "--tps-bench-profile",
     "--idle-motor-speed-mm-s", "50", "--idle-min-stop-mrad", "5", "--throttle-leak-mm2", "9",
     "--lambda-adc-gain", "5", "--coolant-c", "90", "--tdc-reference-deg", "117",
     "--accessory-load"],
    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")}, text=True, capture_output=True,
    timeout=300, check=True).stdout
rows = [json.loads(l) for l in out.splitlines() if l.startswith('{"type":"plant"')]
# The line is republished every second while a 20-cycle window lasts longer; window_id says so.
unique = {}
for r in rows:
    if r["tick"] > 12_000_000:
        unique.setdefault(r["window_id"], r)
late = list(unique.values())
assert len(late) >= 8, (len(rows), len(late))
for r in late:
    assert abs(r["energy_residual_rel"]) < 0.005, r
    assert r["tick_end"] > r["tick_start"] and r["window_id"] > 0, r
ids = [r["window_id"] for r in rows]
assert ids == sorted(ids), "window ids must never go backwards"
for a, b in zip(late, late[1:]):
    assert b["tick_start"] >= a["tick_end"] - 1, (a, b)  # windows do not overlap
mean_power = statistics.mean(r["shaft_kw"] for r in late)
assert abs(mean_power) < 0.3, mean_power
assert all(r["brake_absorbed_nm"] == 0.0 for r in late)  # free idle: no external brake
print(f"rom energy balance ok: {len(late)} windows, mean shaft power {mean_power:.3f} kW, "
      f"max |residual| {max(abs(r['energy_residual_rel']) for r in late):.2e}")
