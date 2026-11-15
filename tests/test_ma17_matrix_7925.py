"""Trace the original 7925h lookup through its later 16-bit consumer."""

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


def late_rows(log, prefix, pc):
    return [dict(part.split("=", 1) for part in line.split()[1:])
            for line in log.splitlines()
            if line.startswith(prefix) and f"PC={pc}" in line and
            int(line.split("tick=")[1].split()[0]) >= 1400000]


class Matrix7925ConsumerTests(unittest.TestCase):
    def test_donor_reaches_r4_but_subtraction_saturates_5c_5d_to_zero(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        outputs = {}
        with tempfile.TemporaryDirectory() as directory:
            for donor, expected in ((False, "5C"), (True, "84")):
                with self.subTest(donor=donor):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_",
                                                          "MA17_CLEAR_"))}
                    environment.update(
                        MA17_ADC_CH0="180", MA17_ADC_CH6="247",
                        MA17_ADC_CH3="40", MA17_ADC_CH5="40",
                        MA17_ADC_CH7="63", MA17_TRACE_78XX_PATH="1",
                        MA17_TRACE_RAM5B_GATE="1")
                    if donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7925",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                    output = Path(directory) / ("donor" if donor else "control")
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(G), "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1500", "--stop-ticks",
                         "2400000", "--seconds", "20", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(G.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(A.read_bytes()).hexdigest()
                                     if donor else None)
                    log = (output / "emulator-trace.log").read_text()
                    writes = late_rows(log, "[78XX-PATH]", "3DC7")
                    loads = late_rows(log, "[RAM5B-GATE]", "183C")
                    branch = late_rows(log, "[RAM5B-GATE]", "1840")
                    results = late_rows(log, "[RAM5B-GATE]", "199A")
                    self.assertGreater(len(writes), 100)
                    self.assertGreater(len(loads), 50)
                    self.assertGreater(len(results), 50)
                    self.assertEqual({r["A"] for r in writes}, {expected})
                    self.assertEqual({r["R4"] for r in loads}, {expected})
                    self.assertEqual(len(branch), len(loads))
                    self.assertEqual({r["RAM2C"] for r in branch}, {"38"})
                    self.assertEqual({(r["R6"], r["R7"], r["RAM5C"],
                                       r["RAM5D"]) for r in results},
                                     {("00", "00", "00", "00")})
                    outputs[donor] = (report["output_latches"]["P5.0"],
                                      report["output_latches"]["P5.1"],
                                      report["cc3_observation"])
        self.assertEqual(outputs[False], outputs[True])

    def test_nonzero_input_is_canceled_by_5b_multiply_branch(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for donor, expected in ((False, "13"), (True, "3B")):
                with self.subTest(donor=donor):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_",
                                                          "MA17_CLEAR_"))}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH7="63", MA17_TRACE_RAM5B_GATE="1",
                        MA17_TRACE_78XX_PATH="1")
                    if donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7925",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                    output = Path(directory) / ("donor" if donor else "control")
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
                    log = (output / "emulator-trace.log").read_text()
                    starts = [r for r in late_rows(log, "[RAM5B-GATE]", "183C")
                              if (r["R7"], r["R6"]) == ("03", "C0")]
                    self.assertEqual(len(starts), 1)
                    self.assertEqual((starts[0]["R4"], starts[0]["RAM2C"],
                                      starts[0]["RAM5B"]), (expected, "A2", "1E"))
                    tick = int(starts[0]["tick"])
                    for pc in ("1843", "1846"):
                        rows = [r for r in late_rows(log, "[RAM5B-GATE]", pc)
                                if tick < int(r["tick"]) < tick + 30]
                        self.assertEqual(len(rows), 1)
                        self.assertEqual(rows[0]["R4"], expected)
                    results = [r for r in late_rows(log, "[RAM5B-GATE]", "199A")
                               if tick < int(r["tick"]) < tick + 50]
                    self.assertEqual(len(results), 1)
                    self.assertEqual(tuple(results[0][key] for key in
                                           ("R5", "R4", "R7", "R6")),
                                     ("03", "C0", "00", "00"))

    def test_one_instruction_gate_exposes_donor_result_in_5c_5d(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        outputs = {}
        with tempfile.TemporaryDirectory() as directory:
            for donor, r4, low in ((False, "13", "AD"), (True, "3B", "85")):
                with self.subTest(donor=donor):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_",
                                                          "MA17_CLEAR_"))}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH7="63", MA17_TRACE_RAM5B_GATE="1",
                        MA17_CLEAR_RAM2C_BIT7_ONCE_AT_1840="1")
                    if donor:
                        environment.update(
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7925",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A))
                    output = Path(directory) / ("donor" if donor else "control")
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(G), "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--stop-ticks",
                         "4000000", "--seconds", "30", "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertTrue(report["ram2c_bit7_clear_once_at_1840_experimental"])
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(G.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(A.read_bytes()).hexdigest()
                                     if donor else None)
                    log = (output / "emulator-trace.log").read_text()
                    self.assertEqual(log.count("[RAM2C-BIT7-GATE]"), 1)
                    self.assertIn("original=A2 R7:R6=03C0", log)
                    results = [r for r in late_rows(log, "[RAM5B-GATE]", "199A")
                               if 3284900 <= int(r["tick"]) <= 3285000]
                    self.assertEqual(len(results), 1)
                    self.assertEqual(tuple(results[0][k] for k in
                                           ("RAM2C", "R4", "R5", "R7", "R6")),
                                     ("A2", r4, "00", "03", low))
                    writes = [r for r in late_rows(log, "[RAM5B-GATE]", "19B6")
                              if 3284900 <= int(r["tick"]) <= 3285000]
                    self.assertEqual(len(writes), 1)
                    self.assertEqual((writes[0]["RAM5C"], writes[0]["RAM5D"]),
                                     ("03", low))
                    outputs[donor] = (report["output_latches"],
                                      report["cc3_observation"])
        self.assertEqual(outputs[False], outputs[True])


if __name__ == "__main__":
    unittest.main()
