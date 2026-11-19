#!/usr/bin/env python3
"""Fit the F-22 volumetric-efficiency curve parameters so the sevel-dyno WOT
sweep meets the goal targets (133 N.m @3000, 82 cv @5750-6000, CEE x1.1 shape).
Calibration helper, run inside the NativeLab. LLM-written (Claude)."""
import csv, io, subprocess, sys
import numpy as np
from scipy.optimize import minimize

dyno = sys.argv[1]
extra = sys.argv[2:]
names = ["eta_max", "cb", "nb", "z0", "kz"]
x0 = np.array([1.0, 0.30, 1800.0, 0.40, 9.0])
lo = np.array([0.8, 0.0, 500.0, 0.2, 1.0]); hi = np.array([1.6, 0.9, 9000.0, 0.7, 60.0])
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
    # Low-speed anchor: manifold-referenced eta_v at cranking speed stays near the
    # legacy 0.75 (estimativa; real VE at 400-500 rpm is 0.7-0.85). Without it the
    # WOT-only fit starves the engine during start (ctest LabRunner.Drivetrain*).
    n = 500.0
    eta500 = x[0] * (1.0 - x[1] * np.exp(-n / x[2]))
    c += 25.0 * (eta500 / 0.80 - 1.0) ** 2
    return c

res = minimize(cost, x0, method="Nelder-Mead", options={"maxiter": 600, "xatol": 1e-3, "fatol": 1e-7})
x = np.clip(res.x, lo, hi)
print("cost", res.fun)
for k, v in zip(names, x):
    print(f"{k}={v:.5g}")
for r in run(x):
    print(r["rpm"], r["torque_nm"], r["power_kw"], r["power_cv"], r["ve_ambient"], r["map_kpa"])
