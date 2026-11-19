"""TPS track consistency (CURVES_STUDY): a stepped TPS2 force while track 1 is still low (a contradiction) latches the
0602h/1Eh TPS fault and the ROM falls back to a 26 degree advance; a continuous or late (track 1 already high) track 2
that reaches 4.5-5.0 V is not a fault and leaves advance, lambda and power unchanged. LLM-written (Claude)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from dyno_point import run_point  # noqa: E402

binary, rom = sys.argv[1:3]
tmp = tempfile.mkdtemp()


def point(name, extra):
    state = os.path.join(tmp, name + ".bin")
    row = run_point(binary, rom, 3000, extra=extra, timeout=600, env_extra={"MA17_XRAM_STATE_FILE": state})
    xram = open(state, "rb").read()[8:]
    assert row["state"] == "ACCEPTED", (name, row["state"], row["reason"])
    return row, xram[0x4E:0x51]


base, base_f = point("base", [])
assert base_f == b"\0\0\0", base_f
curve, curve_f = point("curve", ["--exp", "tps2_end_v=5.0"])
late, late_f = point("late", ["--exp", "ntc_force_tick=12500000", "--exp", "tps2_force_v=5.0"])
early, early_f = point("early", ["--exp", "ntc_force_tick=8000000", "--exp", "tps2_force_v=5.0"])
for row, faults in ((curve, curve_f), (late, late_f)):
    assert faults == b"\0\0\0", faults
    assert abs(row["adv_mean_deg"] - base["adv_mean_deg"]) < 0.05, (row["adv_mean_deg"], base["adv_mean_deg"])
    assert abs(row["shaft_power_kw"] - base["shaft_power_kw"]) < 0.1, row["shaft_power_kw"]
assert early_f[1] & 0x04, early_f  # F84F.2 = TPS2 fault
assert early["adv_mean_deg"] > base["adv_mean_deg"] + 5.0, early["adv_mean_deg"]  # fallback advance
print("tps2 consistency ok: base %.2f deg, early-fault %.2f deg" % (base["adv_mean_deg"], early["adv_mean_deg"]))
