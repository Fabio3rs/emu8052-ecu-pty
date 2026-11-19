"""Phase 6 artifacts are complete and self-consistent (GOAL_DYNO_ROM 6). LLM-written (Claude).
Reads the committed CSVs only; regenerate with tools/dyno_sweep.py."""
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "docs" / "dyno" / "rom"
manifest = json.load(open(root / "manifest.json"))
for key in ("code", "rom_sha256", "args", "scenario", "leak_mm2", "accessories", "coolant_c",
            "fuel", "pms_assumed_deg", "rpms"):
    assert key in manifest, key
assert len(manifest["rom_sha256"]) == 64 and manifest["pms_assumed_deg"] == [117, 120, 123]
for tdc in (117, 120, 123):
    rows = list(csv.DictReader(open(root / f"sweep_tdc{tdc}.csv")))
    assert len(rows) == len(manifest["rpms"]), (tdc, len(rows))
    for r in rows:
        assert r["state"] in ("ACCEPTED", "INVALID"), r["state"]
        assert json.loads(r["scenario"])["tdc_deg"] == tdc
        assert len(r["rom_sha256"]) == 64
        if r["state"] == "ACCEPTED":
            assert abs(float(r["energy_residual_rel"])) < 0.005
            assert abs(float(r["mean_rpm"]) - float(r["target_rpm"])) / float(r["target_rpm"]) < 0.01
        else:
            assert r["reason"] != "none"
assert (root / "sweep.png").stat().st_size > 10_000
assert "ACCEPTED" in (root / "sweep_table.md").read_text()
print("sweep artifacts ok")
