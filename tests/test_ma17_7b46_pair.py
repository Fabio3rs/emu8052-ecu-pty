"""Fiat G/S88 matrix interpolation interaction at one tested ADC state."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
G_ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
S88_ROM = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"
CELLS = (("532F", "7B46"), ("5333", "7B47"),
         ("532F", "7B78"), ("5333", "7B79"),
         ("534B", "7B87"), ("5350", "7B88"),
         ("532F", "7B91"), ("5333", "7B92"),
         ("534B", "7BA0"), ("5350", "7BA1"))


class MatrixPairTests(unittest.TestCase):
    def test_upstream_pair_opens_second_interpolation_and_four_returns_match_s88(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = S88_ROM.read_bytes()
        cells = ",".join(f"{pc}:{address}:{donor[int(address, 16)]:02X}"
                         for pc, address in CELLS)
        expected = (("g", G_ROM, False, False, False, False, "00", 20),
                    ("7580", G_ROM, True, False, False, False, "00", 20),
                    ("7581", G_ROM, False, True, False, False, "00", 20),
                    ("both", G_ROM, True, True, False, False, "C0", 112),
                    ("cells", G_ROM, True, True, True, False, "C0", 112),
                    ("four", G_ROM, True, True, True, True, "C0", 112),
                    ("s88", S88_ROM, False, False, False, False, "C0", 112))
        reports = {}
        with tempfile.TemporaryDirectory() as directory:
            for (name, firmware, use_7580, use_7581, use_cells,
                 use_7b45, r4, second) in expected:
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(MA17_ADC_CH0="100", MA17_ADC_CH2="100",
                                       MA17_ADC_CH3="20", MA17_ADC_CH5="40",
                                       MA17_ADC_CH6="155", MA17_ADC_CH7="63",
                                       MA17_TRACE_MATRIX_PATH="1")
                    if use_7580:
                        environment["MA17_OVERRIDE_MOVC_7580"] = "25"
                    if use_7581:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(S88_ROM)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7581"
                    if use_cells:
                        environment["MA17_OVERRIDE_MOVC_AT"] = cells
                    if use_7b45:
                        environment["MA17_OVERRIDE_MOVC_7B45"] = "0D"
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(firmware), "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000", "--trace-movc",
                         "--stop-ticks", "1200000", "--seconds", "15",
                         "--output-dir", str(output)],
                        env=environment, capture_output=True, text=True,
                        timeout=25, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1000:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["machine_cycles_per_second"], 990000)
                    selectors = [line for line in
                                 (output / "emulator-trace.log").read_text().splitlines()
                                 if "[MATRIX-SELECTOR]" in line and "PC=3356" in line]
                    self.assertEqual(len(selectors), 113)
                    self.assertGreaterEqual(sum(f"R4={r4}" in line for line in selectors),
                                            92)
                    reads = report["movc_observation"]["reads"]
                    for pc in ("532F", "5333"):
                        self.assertEqual(sum(row["count"] for row in reads
                                             if row["dptr"] == "7B46" and
                                             row["pc"] == pc), 113)
                    for pc in ("534B", "5350"):
                        self.assertEqual(sum(row["count"] for row in reads
                                             if row["dptr"] == "7B46" and
                                             row["pc"] == pc), second)
                    reports[name] = report
        self.assertEqual(reports["cells"]["engine_ram_observation"]["69"][-1]["after"],
                         reports["s88"]["engine_ram_observation"]["69"][-1]["after"])
        self.assertEqual(reports["cells"]["pc_coverage"], reports["s88"]["pc_coverage"])
        for field in ("output_latches", "cc3_observation",
                      "engine_ram_observation", "pc_coverage"):
            self.assertEqual(reports["four"][field], reports["s88"][field])


if __name__ == "__main__":
    unittest.main()
