#!/usr/bin/env python3
"""Fit the high-speed VE correction (hs_gain, base curve fixed) so the sevel-dyno WOT
sweep meets the goal targets (133 N.m @3000, 82 cv @5750-6000, CEE x1.1 shape).
Calibration helper, run inside the NativeLab. LLM-written (Claude)."""
import csv, io, subprocess, sys
import numpy as np
from scipy.optimize import minimize

dyno = sys.argv[1]
rest = sys.argv[2:]
out_dir = None
if "--out" in rest:  # --out DIR writes fit_result.json (before/after, cost, per-point deviation)
    i = rest.index("--out")
    out_dir = rest[i + 1]
    rest = rest[:i] + rest[i + 2:]
extra = rest
names = ["hs_gain"]  # single-parameter high-speed correction (base curve held fixed)
x0 = np.array([0.0])  # defaults before the refit
lo = np.array([-0.2]); hi = np.array([0.3])
TARGET = {1500: 115, 2000: 126, 2500: 134, 3000: 133, 3500: 132, 4000: 126,
          4500: 117, 5000: 109, 5500: 102, 6000: 96.3, 6500: 84}
W = {3000: 4.0, 6000: 4.0, 5500: 2.0}

def run(x):
    args = [dyno, "--rpm-min", "1500", "--rpm-max", "6500", "--rpm-step", "500",
            "--cycles", "20"] + extra
    for k, v in zip(names, x):
        args += ["--set", f"{k}={v}"]
    out = subprocess.run(args, text=True, capture_output=True, check=True).stdout
    return list(csv.DictReader(io.StringIO(out)))

def cost(x):
    x = np.clip(x, lo, hi)
    rows = run(x)
    c = 0.0
    for r in rows:
        n = int(float(r["rpm"]))
        c += W.get(n, 1.0) * ((float(r["torque_nm"]) - TARGET[n]) / TARGET[n]) ** 2
    return c

res = minimize(cost, x0, method="Nelder-Mead", options={"maxiter": 200, "xatol": 1e-5, "fatol": 1e-9})
x = np.clip(res.x, lo, hi)
print("cost", res.fun)
if out_dir:
    import json, os
    os.makedirs(out_dir, exist_ok=True)
    rows = run(x)
    result = {
        "parameters_before": dict(zip(names, [float(v) for v in x0])),
        "parameters_after": dict(zip(names, [float(v) for v in x])),
        "cost_final": float(res.fun),
        "note": "VE is unknown: this is a fit to the targets, not a validation",
        "points": [{"rpm": int(float(r["rpm"])), "torque_nm": float(r["torque_nm"]),
                    "target_nm": TARGET[int(float(r["rpm"]))],
                    "deviation_pct": 100.0 * (float(r["torque_nm"]) / TARGET[int(float(r["rpm"]))] - 1.0),
                    "power_kw": float(r["power_kw"]), "ve_ambient": float(r["ve_ambient"])}
                   for r in rows],
    }
    with open(os.path.join(out_dir, "fit_result.json"), "w") as handle:
        json.dump(result, handle, indent=2)
for k, v in zip(names, x):
    print(f"{k}={v:.5g}")
for r in run(x):
    print(r["rpm"], r["torque_nm"], r["power_kw"], r["power_cv"], r["ve_ambient"], r["map_kpa"])
