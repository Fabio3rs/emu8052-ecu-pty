"""Distinguish a natural adjacent-cell MOVC from selecting its next curve."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROMS = (
    ROOT / "FiatTipo_MA17_dump_27c256.bin",
    ROOT / "firmwares_modificados_ma17_tipo" /
    "tipo 1.6 alcool27c256 SUN 8817.bin",
)
DONOR = "5333:7430:40,5333:7534:62"


class CurveBoundaryTests(unittest.TestCase):
    def test_zero_fraction_masks_value_but_signed_helper_changes_timing(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rom in ROMS:
                observations = {}
                for arm in ("native", "supplied00"):
                    with self.subTest(rom=rom.name, arm=arm):
                        environment = {
                            key: value for key, value in os.environ.items()
                            if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                   "MA17_TRACE_", "MA17_P4_"))
                        }
                        environment.update(
                            MA17_ADC_CH0="40", MA17_ADC_CH3="80",
                            MA17_ADC_CH7="63",
                            MA17_ADC10_STEP_CH6="200000:880",
                            MA17_P4_6_FORCE_LOW="1",
                            MA17_TRACE_799E_BOUNDARY="1")
                        if arm == "supplied00":
                            environment["MA17_OVERRIDE_MOVC_AT"] = \
                                "5333:79A8:00"
                        output = Path(directory) / f"{rom.stem}-{arm}"
                        result = subprocess.run(
                            [sys.executable,
                             str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(rom), "--no-kline-inject",
                             "--crank-immediate", "--rpm", "6000",
                             "--stop-ticks", "2400000", "--seconds", "25",
                             "--trace-movc", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=30, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1000:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom.read_bytes()).hexdigest())
                        self.assertTrue(report["curve_799e_boundary_trace_enabled"])
                        trace = (output / "emulator-trace.log").read_text()
                        samples = [dict(re.findall(r"(\w+)=([0-9A-F]+)", line))
                                   for line in trace.splitlines()
                                   if line.startswith("[CURVE-799E-BOUNDARY]")]
                        self.assertGreaterEqual(len(samples), 3)
                        self.assertEqual([row["PC"] for row in samples[:3]],
                                         ["5333", "5338", "533B"])
                        self.assertEqual({row["R6"] for row in samples[:3]},
                                         {"00"})
                        self.assertEqual({row["R2"] for row in samples[:3]},
                                         {"28"})
                        self.assertEqual(samples[2]["A"], "00")
                        if arm == "supplied00":
                            self.assertIn("[MOVC-OVERRIDE] PC=5333 "
                                          "mapped=79A8 original=47 supplied=00",
                                          trace)
                        observations[arm] = (samples, report)
                native, control = observations["native"]
                supplied, donor = observations["supplied00"]
                self.assertEqual((native[1]["A"], supplied[1]["A"]),
                                 ("1F", "D8"))
                self.assertEqual((int(native[2]["tick"])
                                  - int(native[1]["tick"]),
                                  int(supplied[2]["tick"])
                                  - int(supplied[1]["tick"])), (7, 13))
                self.assertEqual(control["cc3_observation"]
                                 ["iram14_15_median"],
                                 donor["cc3_observation"]["iram14_15_median"])

    def test_next_curve_first_cell_is_read_without_selecting_next_bank(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for rom in ROMS:
                reports = {}
                edge_events = {}
                for arm in ("current", "donor"):
                    with self.subTest(rom=rom.name, arm=arm):
                        environment = {
                            key: value for key, value in os.environ.items()
                            if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                   "MA17_TRACE_", "MA17_P4_"))
                        }
                        environment.update(MA17_ADC_CH3="220", MA17_ADC_CH7="63")
                        if arm == "donor":
                            environment["MA17_OVERRIDE_MOVC_AT"] = DONOR
                        output = Path(directory) / f"{rom.stem}-{arm}"
                        command = [sys.executable,
                                   str(ROOT / "tools" / "trace_ma17.py"),
                                   "--firmware", str(rom), "--no-kline-inject",
                                   "--crank-immediate", "--rpm", "1000",
                                   "--stop-ticks", "2400000", "--seconds", "25",
                                   "--trace-movc", "--output-dir", str(output)]
                        result = subprocess.run(
                            command, capture_output=True, text=True,
                            env=environment, timeout=30, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1000:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom.read_bytes()).hexdigest())
                        self.assertEqual(report["engine_ram_observation"]["4E"]
                                         [-1]["after"], "09")
                        reads = {row["address"]: row for row in
                                 report["movc_observation"]["reads"]
                                 if row["pc"] == "5333" and
                                 row["address"] in ("7430", "7534")}
                        self.assertEqual(set(reads), {"7430", "7534"})
                        self.assertEqual((reads["7430"]["dptr"],
                                          reads["7534"]["dptr"]),
                                         ("7426", "752A"))
                        self.assertEqual((reads["7430"]["acc"],
                                          reads["7534"]["acc"]), ("0A", "0A"))
                        expected = 582 if rom == ROMS[0] else 581
                        self.assertEqual((reads["7430"]["count"],
                                          reads["7534"]["count"]), (20, expected))
                        if arm == "donor":
                            log = (output / "emulator-trace.log").read_text()
                            self.assertIn("[MOVC-OVERRIDE] PC=5333 mapped=7430 "
                                          "original=26 supplied=40", log)
                            self.assertIn("[MOVC-OVERRIDE] PC=5333 mapped=7534 "
                                          "original=40 supplied=62", log)
                        else:
                            log = (output / "emulator-trace.log").read_text()
                        edge_events[arm] = [
                            (int(re.search(r"tick=(\d+)", line).group(1)),
                             int(re.search(r"value=(\d+)", line).group(1)))
                            for line in log.splitlines()
                            if line.startswith("[CC3-PIN]")]
                        reports[arm] = report
                current, donor = reports["current"], reports["donor"]
                self.assertEqual(edge_events["current"], edge_events["donor"])
                for address in ("4E", "79", "7B", "4D"):
                    self.assertEqual(current["engine_ram_observation"].get(address),
                                     donor["engine_ram_observation"].get(address))
                for key in ("iram14_15_median", "cc3_pin_model_low_starts",
                            "cc3_pin_model_median_low_width_ticks"):
                    self.assertEqual(current["cc3_observation"][key],
                                     donor["cc3_observation"][key])


if __name__ == "__main__":
    unittest.main()
