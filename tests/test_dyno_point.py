"""ROM crank-dyno point at 3000 rpm WOT (GOAL_DYNO_ROM 5.5): accepted, within +-1 %, brake not
saturated, steady, energy ledger closed, ignition/lambda recorded, and deterministic.
LLM-written (Claude)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from dyno_point import run_point  # noqa: E402

binary, rom = sys.argv[1:3]
a = run_point(binary, rom, 3000, 120, 40, timeout=600)
b = run_point(binary, rom, 3000, 120, 40, timeout=600)
assert a["state"] == "ACCEPTED", (a["state"], a["reason"])
assert abs(a["mean_rpm"] - 3000) / 3000 < 0.01, a["mean_rpm"]
assert a["brake_saturated_s"] == 0.0 and a["brake_peak_nm"] < 399, a
assert a["kinetic_over_brake"] < 0.01, a["kinetic_over_brake"]
assert abs(a["energy_residual_rel"]) < 0.005, a["energy_residual_rel"]
assert a["cycles"] == 40 and a["sparks"] >= 150, a["sparks"]
assert 0.8 < a["lambda"] < 1.3, a["lambda"]
assert 0.0 < a["adv_mean_deg"] < 45.0 and a["adv_min_deg"] <= a["adv_mean_deg"] <= a["adv_max_deg"]
assert len(a["spark_abs_deg_cyl"]) == 4 and all(0 <= x < 720 for x in a["spark_abs_deg_cyl"])
assert a["ram69_end"] > 0 and a["throttle_rad"] > 1.57
assert len(a["rom_sha256"]) == 64 and len(a["code_sha"]) in (0, 40) and "dyno-point" in a["args"]
# determinism: same code, ROM and arguments give the identical measurement
for key in a:
    if key in ("code_dirty",):
        continue
    assert a[key] == b[key], (key, a[key], b[key])
print(f"dyno point ok: {a['mean_rpm']:.1f} rpm, brake {a['brake_mean_nm']:.1f} N.m, "
      f"shaft {a['shaft_power_kw']:.2f} kW, lambda {a['lambda']:.3f}, adv {a['adv_mean_deg']:.2f}")
