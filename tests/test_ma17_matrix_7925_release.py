"""Natural TPS release exposes the Fiat 7925h matrix consumer."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
A = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"


def pc_row(log, pc, first_tick, last_tick):
    rows = [dict(part.split("=", 1) for part in line.split()[1:])
            for line in log.splitlines()
            if line.startswith("[RAM5B-GATE]") and f"PC={pc}" in line and
            first_tick <= int(line.split("tick=")[1].split()[0]) <= last_tick]
    if len(rows) != 1:
        raise AssertionError((pc, len(rows)))
    return rows[0]


class Matrix7925ReleaseTests(unittest.TestCase):
    def test_tps_release_and_ram6e_read_cross_reproduce_f80c_trajectory(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        arms = {
            "control": (False, None, "13", "6D"),
            "donor": (True, None, "3B", "45"),
            "control_to_3b": (False, "3B", "3B", "45"),
            "donor_to_13": (True, "13", "13", "6D"),
        }
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, (donor, override, r4, low) in arms.items():
                with self.subTest(arm=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_CLEAR_",
                                                          "MA17_P4_"))}
                    environment.update(
                        MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="3267000:160",
                        MA17_ADC10_STEP_CH6="3267000:380",
                        MA17_TRACE_RAM5B_GATE="1",
                        MA17_TRACE_RAM5B_WRITE_AFTER_TICK="3200000")
                    if donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7925",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                    if override:
                        environment["MA17_OVERRIDE_RAM6E_READ"] = override
                    output = Path(directory) / name
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(G), "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--stop-ticks",
                         "4000000", "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(G.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(A.read_bytes()).hexdigest()
                                     if donor else None)
                    self.assertEqual(report["ram6e_read_override_hex"], override)
                    self.assertFalse(report["ram2c_bit7_clear_once_at_1840_experimental"])
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x7925 <= int(row["mapped"], 16)
                                         < 0x7939), 3160)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertIn("old=52 new=1E", log)
                    if override:
                        self.assertIn(f"supplied={override}", log)
                    mid = pc_row(log, "199A", 3284800, 3285000)
                    self.assertEqual((mid["RAM2C"], mid["RAM5B"],
                                      mid["R7"], mid["R6"]),
                                     ("22", "1E", "06", "80"))
                    before = pc_row(log, "183C", 3295000, 3296000)
                    self.assertEqual((before["RAM2C"], before["R7"],
                                      before["R6"], before["R4"]),
                                     ("22", "06", "80", r4))
                    self.assertNotIn("PC=1843", "\n".join(
                        line for line in log.splitlines()
                        if line.startswith("[RAM5B-GATE]") and
                        "tick=3295" in line))
                    result = pc_row(log, "199A", 3295000, 3296000)
                    write = pc_row(log, "19B6", 3295000, 3296000)
                    self.assertEqual((result["R7"], result["R6"],
                                      write["RAM5C"], write["RAM5D"]),
                                     ("06", low, "06", low))
                    reports[name] = report
        for left, right in (("control", "donor_to_13"),
                            ("donor", "control_to_3b")):
            for field in ("adaptation_xram_observation", "output_latches",
                          "cc3_observation", "engine_ram_observation"):
                self.assertEqual(reports[left][field], reports[right][field],
                                 (left, right, field))
        control = reports["control"]["adaptation_xram_observation"]["F80C"]
        donor = reports["donor"]["adaptation_xram_observation"]["F80C"]
        self.assertEqual(next(r["tick"] for r in control if r["after"] == "8B"),
                         3356561)
        self.assertEqual(next(r["tick"] for r in donor if r["after"] == "8B"),
                         3315882)


if __name__ == "__main__":
    unittest.main()
