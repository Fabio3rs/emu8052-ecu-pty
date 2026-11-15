"""Verify Fiat matrix end reads and their timing effect at a TPS step."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"
EMULATOR = ROOT / "build/emu8051-tty"


class MatrixBoundaryTests(unittest.TestCase):
    def test_last_column_extra_read_has_zero_fraction_but_branch_timing(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        reports = {}
        traces = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, override in (("native", None),
                                   ("same_sign", "5350:7BBE:A0,5350:7D26:A0"),
                                   ("negative", "5350:7BBE:00")):
                env = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_")}
                env.update(MA17_ADC_CH0="40", MA17_ADC_CH3="4",
                           MA17_ADC_CH5="40", MA17_ADC_CH6="95",
                           MA17_ADC_CH7="63",
                           MA17_ADC10_STEP_CH0="800000:720",
                           MA17_ADC10_STEP_CH6="800000:988",
                           MA17_TRACE_MATRIX_PATH="1",
                           MA17_TRACE_PC_WINDOW="809200:809300")
                if override:
                    env["MA17_OVERRIDE_MOVC_AT"] = override
                output = Path(directory) / name
                command = [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                           "--firmware", str(ROM), "--no-kline-inject",
                           "--crank-immediate", "--rpm", "6000",
                           "--stop-ticks", "2400000", "--seconds", "30",
                           "--trace-movc", "--trace-lookup",
                           "--output-dir", str(output)]
                result = subprocess.run(command, cwd=ROOT, env=env,
                                        capture_output=True, text=True,
                                        timeout=40, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                reports[name] = json.loads((output / "execution.json").read_text())
                traces[name] = (output / "emulator-trace.log").read_text()
        native, same, negative = (reports[name] for name in
                                  ("native", "same_sign", "negative"))
        for report in reports.values():
            self.assertEqual(report["firmware_sha256"],
                             hashlib.sha256(ROM.read_bytes()).hexdigest())
            self.assertEqual(report["emulator_sha256"], native["emulator_sha256"])
            self.assertEqual(report["stop_ticks_observed"], 2400000)
            reads = {(row["pc"], row["mapped"]): row["count"]
                     for row in report["movc_observation"]["reads"]
                     if row["pc"] == "5350" and row["mapped"] in ("7BBE", "7D26")}
            self.assertEqual(reads, {("5350", "7BBE"): 1,
                                     ("5350", "7D26"): 155})
        self.assertIn("PC=3356", traces["native"])
        self.assertIn("R5=68 R6=00", traces["native"])
        self.assertIn("[MOVC-OVERRIDE] PC=5350 mapped=7BBE original=A1 supplied=A0",
                      traces["same_sign"])
        self.assertIn("[MOVC-OVERRIDE] PC=5350 mapped=7D26 original=A1 supplied=A0",
                      traces["same_sign"])
        for key in ("pc_coverage", "output_latches", "cc3_observation",
                    "engine_ram_observation", "lookup_observation"):
            self.assertEqual(native[key], same[key], key)
        self.assertIn("[PC-WINDOW] tick=809251 PC=524D", traces["negative"])
        self.assertNotIn("[PC-WINDOW] tick=809251 PC=524D", traces["native"])
        first_69 = lambda report: next(row["tick"] for row in
            report["engine_ram_observation"]["69"] if row["tick"] > 800000)
        self.assertEqual(first_69(negative) - first_69(native), 6)
        self.assertEqual(native["output_latches"]["P5.0"]["median_low_width_ticks"],
                         negative["output_latches"]["P5.0"]["median_low_width_ticks"])
        self.assertNotEqual(native["output_latches"]["P5.0"]["low_width_histogram"],
                            negative["output_latches"]["P5.0"]["low_width_histogram"])


if __name__ == "__main__":
    unittest.main()
