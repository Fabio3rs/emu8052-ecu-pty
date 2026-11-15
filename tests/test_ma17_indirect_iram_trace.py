"""Check indirect upper IRAM tracing around the Fiat 7CAEh matrix path."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
S88 = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"
EMULATOR = ROOT / "build/emu8051-tty"


class IndirectIramTraceTests(unittest.TestCase):
    def test_a4_is_written_but_not_read_in_tested_g_matrix_state(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for address, donor, expected_a4, expected_p5 in (
                    ("A4", False, "9A", 1861),
                    ("A4", True, "A2", 1921),
                    ("92", False, "9A", 1861)):
                with self.subTest(address=address, donor=donor):
                    env = {key: value for key, value in os.environ.items()
                           if not key.startswith("MA17_")}
                    env.update(MA17_TRACE_INDIRECT_IRAM_ADDRESS=address,
                               MA17_ADC_CH0="180", MA17_ADC_CH2="100",
                               MA17_ADC_CH3="80", MA17_ADC_CH6="247",
                               MA17_ADC_CH7="63")
                    if donor:
                        env.update(MA17_OVERRIDE_MOVC_MATRIX_ROM=str(S88),
                                   MA17_OVERRIDE_MOVC_MATRIX_BASE="7CAE")
                    output = Path(directory) / f"{address}_{donor}"
                    command = [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                               "--firmware", str(G), "--no-kline-inject",
                               "--crank-immediate", "--rpm", "1000",
                               "--stop-ticks", "2400000", "--seconds", "30",
                               "--output-dir", str(output)]
                    if donor:
                        command.append("--trace-movc")
                    result = subprocess.run(command, cwd=ROOT, env=env,
                                            capture_output=True, text=True,
                                            timeout=40, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(G.read_bytes()).hexdigest())
                    self.assertEqual(report["stop_ticks_observed"], 2400000)
                    self.assertEqual(report["engine_ram_observation"]["A4"]
                                     [-1]["after"], expected_a4)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], expected_p5)
                    trace = (output / "emulator-trace.log").read_text()
                    reads = [line for line in trace.splitlines()
                             if line.startswith("[INDIRECT-IRAM-READ]")]
                    observation = report["indirect_iram_observation"]
                    self.assertEqual(observation["target_address"], address)
                    self.assertEqual(len(observation["reads"]), len(reads))
                    if address == "92":
                        self.assertTrue(any("pc=33BC opcode=E7 address=92"
                                            in line for line in reads))
                        self.assertGreater(observation["total_reads"], 0)
                    else:
                        self.assertEqual(reads, [])
                        self.assertEqual(observation["total_reads"], 0)


if __name__ == "__main__":
    unittest.main()
