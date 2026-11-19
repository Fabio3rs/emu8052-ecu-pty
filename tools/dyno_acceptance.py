#!/usr/bin/env python3
"""Regenerate the full-load artifacts with a manifest (GOAL_DYNO_ROM phase 2.2).

Runs `sevel-dyno --preset acceptance`, draws docs/dyno_wot.png with tools/plot_dyno.py and copies
everything to <dest>/ with manifest.json. Usage: dyno_acceptance.py <sevel-dyno> <dest>
LLM-written (Claude)."""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dyno_manifest import write_manifest  # noqa: E402

dyno, dest = sys.argv[1], Path(sys.argv[2])
root = Path(__file__).resolve().parents[1]
docs = root / "docs"
args = ["--preset", "acceptance", "--out-dir", str(docs), "--throttle-leak-mm2", "9"]
subprocess.run([dyno, *args], check=True, capture_output=True)
subprocess.run([sys.executable, str(root / "tools/plot_dyno.py"), str(docs / "dyno_wot_e22.csv"),
                str(docs / "dyno_wot_e0.csv"), str(docs / "dyno_wot.png")], check=True)
dest.mkdir(parents=True, exist_ok=True)
for name in ("dyno_summary.csv", "dyno_wot_e0.csv", "dyno_wot_e22.csv", "dyno_wot.png"):
    shutil.copy(docs / name, dest / name)
write_manifest(dest, tool="tools/dyno_acceptance.py", binary=dyno, args=args, dt_us=100,
               fuel="E22 and E0 (both files)", leak_mm2=9, accessories=False, cycles=40,
               tdc_reference_deg=120, ambient="100 kPa / 20 C",
               note="VE curve is a fit (fase2/fit_result.json), not a validation")
print("wrote", dest)
