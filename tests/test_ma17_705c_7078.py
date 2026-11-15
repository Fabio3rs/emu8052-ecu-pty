"""Trace the original Fiat 705Ch matrix and 7078h curve to XRAM."""

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


class Curve705c7078Tests(unittest.TestCase):
    def test_cell_read_interventions_change_separate_xram_fields(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        image = ROM.read_bytes()
        self.assertEqual(image[0x705C:0x705E], bytes.fromhex("78 59"))
        self.assertEqual(image[0x7078:0x707A], bytes.fromhex("79 4d"))
        cases = (
            ("F800", "3E05", "532F:785C:20", "40", "7859",
             ["5A", "53", "46", "A3", "46"],
             ["5A", "53", "36", "A3", "36"]),
            ("F88D", "3E61", "532F:794D:20", "5A", "794D",
             ["CD", "94", "9A", "94"],
             ["CD", "F7", "9A", "F7"]),
        )
        with tempfile.TemporaryDirectory() as directory:
            for address, pc, override, original, dptr, native, donor in cases:
                with self.subTest(address=address):
                    observations = []
                    for substitute in (False, True):
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith("MA17_")}
                        environment.update(
                            MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                            MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                            MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                            MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                            MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                            MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                            MA17_P4_6_FORCE_LOW="1",
                            MA17_TRACE_XRAM_ADDRESS=address)
                        if substitute:
                            environment["MA17_OVERRIDE_MOVC_AT"] = override
                        output = Path(directory) / f"{address}-{substitute}"
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                             "--firmware", str(ROM), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate", "--rpm",
                             "3000", "--stop-ticks", "3501100", "--seconds",
                             "30", "--output-dir", str(output)],
                            cwd=ROOT, env=environment, text=True,
                            capture_output=True, timeout=60, check=False)
                        self.assertEqual(result.returncode, 0,
                                         result.stderr[-1000:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(image).hexdigest())
                        self.assertEqual(report["xram_trace_address_hex"], address)
                        self.assertTrue(any(r["dptr"] == dptr
                                            for r in report["movc_observation"]["reads"]))
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        self.assertEqual(any(
                            f"[MOVC-OVERRIDE] PC=532F mapped={override[5:9]} "
                            f"original={original} supplied=20" in line
                            for line in lines), substitute)
                        values = [re.search(r"value=[0-9A-F]{2}->([0-9A-F]{2})",
                                            line).group(1)
                                  for line in lines
                                  if line.startswith("[XRAM-ADDRESS-WRITE]")
                                  and f"PC={pc} " in line]
                        observations.append(values)
                    self.assertEqual(observations, [native, donor])


if __name__ == "__main__":
    unittest.main()
