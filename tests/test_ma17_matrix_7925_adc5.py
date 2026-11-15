"""Bound the 7925h donor effect across two raw ADC5 states."""

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


class Matrix7925Adc5Tests(unittest.TestCase):
    def test_adc5_bounds_table_effect_on_f80c_in_tps_release(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for raw, expected_reads, ram2c, low in ((40, 3164, "AA", "53"),
                                                    (200, 3172, "22", "00")):
                for donor in (False, True):
                    with self.subTest(adc5=raw, donor=donor):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                              "MA17_TRACE_", "MA17_CLEAR_",
                                                              "MA17_P4_"))}
                        environment.update(
                            MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                            MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                            MA17_ADC_CH5=str(raw), MA17_ADC_CH7="63",
                            MA17_ADC10_STEP_CH0="3267000:160",
                            MA17_ADC10_STEP_CH6="3267000:380",
                            MA17_TRACE_RAM5B_GATE="1")
                        if donor:
                            environment.update(
                                MA17_OVERRIDE_MOVC_MATRIX_BASE="7925",
                                MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                        output = Path(directory) / f"{raw}_{donor}"
                        run = subprocess.run(
                            [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                             "--firmware", str(G), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate", "--rpm",
                             "1000", "--stop-ticks", "4000000", "--seconds",
                             "30", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(G.read_bytes()).hexdigest())
                        self.assertEqual(report["movc_matrix_donor_sha256"],
                                         hashlib.sha256(A.read_bytes()).hexdigest()
                                         if donor else None)
                        self.assertEqual(sum(row["count"] for row in
                                             report["movc_observation"]["reads"]
                                             if 0x7925 <= int(row["mapped"], 16)
                                             < 0x7939), expected_reads)
                        log = (output / "emulator-trace.log").read_text()
                        rows = [dict(part.split("=", 1) for part in line.split()[1:])
                                for line in log.splitlines()
                                if line.startswith("[RAM5B-GATE]") and
                                "PC=183C" in line and
                                3295000 <= int(line.split("tick=")[1].split()[0])
                                <= 3296000]
                        self.assertEqual(len(rows), 1)
                        self.assertEqual((rows[0]["RAM2C"], rows[0]["R4"]),
                                         (ram2c, "3B" if donor else "13"))
                        if raw == 40:
                            self.assertEqual(rows[0]["R6"],
                                             "7B" if donor else low)
                        else:
                            self.assertEqual((rows[0]["R7"], rows[0]["R6"]),
                                             ("00", "00"))
                        reports[raw, donor] = report
        for raw, expected_f80c, expected_cc3 in ((40, ("98", "A2"), 4404),
                                                 (200, ("80", "80"), 4404)):
            for donor, last in ((False, expected_f80c[0]),
                                (True, expected_f80c[1])):
                report = reports[raw, donor]
                self.assertEqual(report["adaptation_xram_observation"]["F80C"]
                                 [-1]["after"], last)
                self.assertEqual(report["output_latches"]["P5.0"]
                                 ["median_low_width_ticks"], 1921)
                self.assertEqual(report["cc3_observation"]
                                 ["cc3_pin_model_median_low_width_ticks"],
                                 expected_cc3)
        self.assertEqual(reports[200, False]["adaptation_xram_observation"],
                         reports[200, True]["adaptation_xram_observation"])
        self.assertNotEqual(reports[40, False]["adaptation_xram_observation"],
                            reports[40, True]["adaptation_xram_observation"])

    def test_adc5_40_all_ram6e_reads_mediate_f80c_trajectory(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        arms = (("control", False, None, "98"),
                ("donor", True, None, "A2"),
                ("control_to_3b", False, "3B", "A2"),
                ("donor_to_13", True, "13", "98"))
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, donor, supplied, last in arms:
                with self.subTest(arm=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_CLEAR_",
                                                          "MA17_P4_"))}
                    environment.update(
                        MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH5="40", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="3267000:160",
                        MA17_ADC10_STEP_CH6="3267000:380")
                    if donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7925",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                    if supplied:
                        environment["MA17_OVERRIDE_RAM6E_READ"] = supplied
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
                    self.assertEqual(report["ram6e_read_override_hex"], supplied)
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(A.read_bytes()).hexdigest()
                                     if donor else None)
                    self.assertEqual(sum(row["count"] for row in
                                         report["movc_observation"]["reads"]
                                         if 0x7925 <= int(row["mapped"], 16)
                                         < 0x7939), 3164)
                    trajectory = report["adaptation_xram_observation"]["F80C"]
                    self.assertEqual(trajectory[-1]["after"], last)
                    reports[name] = report
        for left, right in (("control", "donor_to_13"),
                            ("donor", "control_to_3b")):
            for field in ("adaptation_xram_observation", "output_latches",
                          "cc3_observation", "engine_ram_observation"):
                self.assertEqual(reports[left][field], reports[right][field],
                                 (left, right, field))


if __name__ == "__main__":
    unittest.main()
