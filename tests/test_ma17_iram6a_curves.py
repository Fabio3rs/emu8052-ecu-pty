"""Check the Fiat RAM6A curve selector against intact-firmware traces."""

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
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
EMULATOR = ROOT / "build/emu8051-tty"


class Iram6aCurveTraceTests(unittest.TestCase):
    def test_p46_selector_reads_both_curves_without_natural_f88e_difference(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        expected_hash = hashlib.sha256(ROM.read_bytes()).hexdigest()
        expected_writes = [("55A1", "55"), ("55A1", "AA"),
                           ("0A51", "00"), ("3E7D", "03"),
                           ("3E7D", "05"), ("3E7D", "64"),
                           ("3E7D", "05")]
        with tempfile.TemporaryDirectory() as directory:
            for force_low in (False, True):
                with self.subTest(force_low=force_low):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                        MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                        MA17_TRACE_XRAM_F88E="1")
                    if force_low:
                        environment["MA17_P4_6_FORCE_LOW"] = "1"
                    output = Path(directory) / str(force_low)
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(ROM), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "3000", "--stop-ticks", "3501100", "--seconds",
                         "30", "--output-dir", str(output)],
                        cwd=ROOT, env=environment, text=True,
                        capture_output=True, timeout=60, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"], expected_hash)
                    self.assertTrue(report["xram_f88e_trace_enabled"])
                    self.assertEqual(report["p4_6_force_low_experimental"],
                                     force_low)
                    all_reads = report["movc_observation"]["reads"]
                    selected_7e9d = [r for r in all_reads
                                     if r["dptr"] == "7E9D" and
                                     r["address"] in ("7EA6", "7EA7")]
                    if force_low:
                        self.assertEqual({r["address"]: r["count"]
                                          for r in selected_7e9d},
                                         {"7EA6": 131, "7EA7": 131})
                    else:
                        self.assertFalse(selected_7e9d)
                    reads = {(r["dptr"], r["address"]): r["count"]
                             for r in all_reads
                             if r["dptr"] in ("797A", "7982") and
                             r["address"] in ("7981", "7982", "7989", "798A")}
                    if force_low:
                        self.assertEqual(reads[("7982", "7989")], 194)
                        self.assertEqual(reads[("7982", "798A")], 194)
                    else:
                        self.assertEqual(reads[("797A", "7981")], 428)
                        self.assertEqual(reads[("797A", "7982")], 428)
                        self.assertNotIn(("7982", "7989"), reads)
                    branch_reads = [r for r in report["movc_observation"]["reads"]
                                    if r["dptr"] == "798A"]
                    self.assertEqual(sum(r["count"] for r in branch_reads
                                         if r["pc"] == "532F"),
                                     2 if force_low else 12)
                    self.assertIn("798C", {r["address"] for r in branch_reads})
                    writes = [re.search(r"PC=([0-9A-F]{4}) value=[0-9A-F]{2}->([0-9A-F]{2})", line).groups()
                              for line in (output / "emulator-trace.log").read_text().splitlines()
                              if line.startswith("[F88E-WRITE]")]
                    self.assertEqual(writes, expected_writes)

    def test_798b_read_changes_early_iram_pair_and_cc3_width(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        observations = []
        with tempfile.TemporaryDirectory() as directory:
            for donor in (False, True):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update(
                    MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                    MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                    MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                    MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                    MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                    MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                    MA17_TRACE_PC="1")
                if donor:
                    environment["MA17_OVERRIDE_MOVC_AT"] = "532F:798B:20"
                output = Path(directory) / str(donor)
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                     "--firmware", str(ROM), "--trace-movc",
                     "--no-kline-inject", "--crank-immediate", "--rpm",
                     "3000", "--stop-ticks", "3501100", "--seconds",
                     "30", "--output-dir", str(output)],
                    cwd=ROOT, env=environment, text=True,
                    capture_output=True, timeout=60, check=False)
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(ROM.read_bytes()).hexdigest())
                lines = (output / "emulator-trace.log").read_text().splitlines()
                self.assertEqual(any("[MOVC-OVERRIDE] PC=532F mapped=798B "
                                     "original=40 supplied=20" in line
                                     for line in lines), donor)
                writes = [line for line in lines if line.startswith("[ENGINE-RAM]")
                          and ("addr=59" in line or "addr=5A" in line)]
                pins = [(int(re.search(r"tick=(\d+)", line).group(1)),
                         int(re.search(r"value=(\d+)", line).group(1)))
                        for line in lines if line.startswith("[CC3-PIN]")]
                widths = [pins[i + 1][0] - pins[i][0]
                          for i in range(len(pins) - 1)
                          if pins[i][1] == 0 and pins[i + 1][1] == 1]
                entries = [line for line in lines if line.startswith("[CC3-ENTRY]")]
                observations.append((writes, widths, entries))
        native, donor = observations
        self.assertIn("tick=8559 addr=59 value=00->05 source_PC=1644",
                      native[0][0])
        self.assertIn("tick=59525 addr=59 value=05->04 source_PC=1644",
                      donor[0][1])
        self.assertIn("tick=59526 addr=5A value=00->38 source_PC=1646",
                      donor[0][2])
        self.assertEqual(native[1][:4], [5381, 5381, 5380, 1212])
        self.assertEqual(donor[1][:4], [4581, 4581, 4580, 1212])
        self.assertIn("IRAM14_15=0544", native[2][0])
        self.assertIn("IRAM14_15=047C", donor[2][0])


if __name__ == "__main__":
    unittest.main()
