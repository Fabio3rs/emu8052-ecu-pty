"""sevel-dyno sweep: CSV contract, determinism, physical sanity (goal fase 3).

Invariants only (no magic plant numbers): the sweep is deterministic, power
equals torque*rpm/9549.3, mass is conserved (lambda ~ commanded), and the
exported expected-curve columns exist so the spreadsheet can be compared.
"""
import csv
import io
import subprocess
import sys

dyno = sys.argv[1]
args = [dyno, "--rpm-min", "1500", "--rpm-max", "5500", "--rpm-step", "2000",
        "--cycles", "20"]


def run():
    r = subprocess.run(args, text=True, capture_output=True, timeout=120, check=True)
    return r.stdout, r.stderr


out1, err1 = run()
out2, _ = run()
assert out1 == out2, "dyno sweep must be deterministic"
rows = list(csv.DictReader(io.StringIO(out1)))
assert [int(float(r["rpm"])) for r in rows] == [1500, 3500, 5500], rows
for col in ("torque_nm", "power_kw", "ve_ambient", "map_kpa", "lambda", "bsfc_g_kwh",
            "expected_power_kw", "expected_torque_nm", "power_error_pct"):
    assert col in rows[0], col
for r in rows:
    n, t, p = float(r["rpm"]), float(r["torque_nm"]), float(r["power_kw"])
    assert abs(p - t * n / 9549.3) < 0.02, r              # F-37
    assert abs(float(r["lambda"]) - 1.0) < 0.05, r         # commanded lambda reached
    assert 0.2 < float(r["ve_ambient"]) <= 1.2, r
assert "[DYNO]" in err1
print("dyno sweep ok")
