"""Exercise the Fiat 70DCh segment lookup and modeled XRAM F8:F2 write."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
EMULATOR = ROOT / "build/emu8051-tty"


class Segment79e0Tests(unittest.TestCase):
    def test_adc3_segment_boundaries_and_single_read_intervention(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        image = ROM.read_bytes()
        self.assertEqual(image[0x70DC:0x70DE], bytes.fromhex("79 e0"))
        self.assertEqual(image[0x79E0:0x79E8],
                         bytes.fromhex("63 03 1e 2a 8d 72 7a 81"))
        cases = [(72, "79E5", "72", {"79E2", "79E3", "79E4"}, False),
                 (73, "79E6", "7A", {"79E3", "79E4"}, False),
                 (114, "79E6", "7A", {"79E3", "79E4"}, False),
                 (115, "79E7", "81", {"79E4"}, False),
                 (80, "79E6", "72", {"79E3", "79E4"}, True)]
        with tempfile.TemporaryDirectory() as directory:
            for adc3, address, output_value, increments, donor in cases:
                with self.subTest(adc3=adc3, donor=donor):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3=str(adc3),
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                        MA17_TRACE_PC="1", MA17_TRACE_XRAM_F8F2="1")
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_AT"] = "28A9:79E6:72"
                    output = Path(directory) / f"{adc3}-{donor}"
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(ROM), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm",
                         "3000", "--stop-ticks", "250000", "--seconds",
                         "30", "--output-dir", str(output)],
                        cwd=ROOT, env=environment, text=True,
                        capture_output=True, timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1000:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(image).hexdigest())
                    self.assertTrue(report["xram_f8f2_trace_enabled"])
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual({r["address"] for r in reads
                                      if r["pc"] == "28A9"}, {address})
                    self.assertEqual({r["address"] for r in reads
                                      if r["pc"] == "52DD" and
                                      r["dptr"] == "79E1"}, increments)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    self.assertTrue(any(f"addr=63 value=E7->{adc3:02X} " in line
                                        and "source_PC=4756" in line
                                        for line in lines))
                    self.assertTrue(any("[F8F2-WRITE]" in line and
                                        f"PC=28AF value=00->{output_value}" in line
                                        for line in lines))
                    self.assertEqual(any("[MOVC-OVERRIDE] PC=28A9 mapped=79E6 "
                                         "original=7A supplied=72" in line
                                         for line in lines), donor)


if __name__ == "__main__":
    unittest.main()
