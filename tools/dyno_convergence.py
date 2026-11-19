#!/usr/bin/env python3
"""dt convergence of the isolated dyno (GOAL_DYNO_ROM phase 0.3 / 1.5).

dt in {100, 25, 10, 1} us x {MBT, 30 deg fixed, 36 deg fixed} x rpm 3000..6000 step 1000,
E22, leak 9 mm2, 40 cycles. Writes <out>/convergence.csv and <out>/manifest.json.

Usage: dyno_convergence.py <sevel-dyno> <out-dir>
LLM-written (Claude).
"""
import csv
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_manifest import write_manifest  # noqa: E402

dyno, out = sys.argv[1], Path(sys.argv[2])
DTS = (100, 25, 10, 1)
MODES = (("MBT", []), ("fixed30", ["--fixed-spark", "--spark-btdc-deg", "30"]),
         ("fixed36", ["--fixed-spark", "--spark-btdc-deg", "36"]))
COMMON = ["--ethanol", "22", "--throttle-leak-mm2", "9", "--cycles", "40",
          "--rpm-min", "3000", "--rpm-max", "6000", "--rpm-step", "1000"]
rows = []
for dt in DTS:
    for mode, extra in MODES:
        text = subprocess.run([dyno, *COMMON, "--dt-us", str(dt), *extra],
                              capture_output=True, text=True, check=True).stdout
        for r in csv.DictReader(io.StringIO(text)):
            rows.append({"dt_us": dt, "mode": mode, "rpm": int(float(r["rpm"])),
                         "power_kw": float(r["power_kw"]), "torque_nm": float(r["torque_nm"]),
                         "ve_ambient": float(r["ve_ambient"]), "lambda": float(r["lambda"]),
                         "map_kpa": float(r["map_kpa"]), "spark_deg": float(r["spark_deg"])})
out.mkdir(parents=True, exist_ok=True)
with open(out / "convergence.csv", "w", newline="") as handle:
    w = csv.DictWriter(handle, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
write_manifest(out, tool="tools/dyno_convergence.py", binary=dyno, dt_us=list(DTS),
               modes=[m for m, _ in MODES], fuel="E22", leak_mm2=9, cycles=40,
               accessories=False, tdc_reference_deg=120, ambient="100 kPa / 20 C",
               args=COMMON)
print("wrote", out / "convergence.csv")
