"""Isolate the A-ROM last-row difference between its 7ED9h and 7F15h banks."""

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
LAST_ROW_CELLS = ((0x5333, 0x7F48), (0x532F, 0x7F4A), (0x5333, 0x7F4B))


class AlcoholBankPairTests(unittest.TestCase):
    def test_six_roms_direct_immediate_ram57_writers_are_zero_in_engine_code(self):
        roms = (G, *sorted((ROOT / "firmwares_modificados_ma17_tipo").glob("*.bin")))
        self.assertEqual(len(roms), 6)
        for path in roms:
            with self.subTest(rom=path.name):
                image = path.read_bytes()
                self.assertEqual(len(image), 32768)
                writes = [(address, image[address + 2])
                          for address in range(len(image) - 2)
                          if image[address:address + 2] == b"\x75\x57"]
                cycle_reset = 0x3B94 if path == G or "SUN 8817" in path.name else 0x3BC2
                self.assertEqual(writes, [(0x0B0F, 0), (cycle_reset, 0),
                                          (0x601D, 0x5A)])
                self.assertEqual(image[0x6078:0x607B], b"\x85\xF0\x57")

    def test_last_row_bank_delta_reaches_ram31_and_modeled_p5(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = A.read_bytes()
        self.assertTrue(all(donor[address - 0x3C] - donor[address] == 34
                            for _, address in LAST_ROW_CELLS))
        substitutions = ",".join(
            f"{pc:04X}:{address:04X}:{donor[address - 0x3C]:02X}"
            for pc, address in LAST_ROW_CELLS)
        with tempfile.TemporaryDirectory() as directory:
            for use_bank_zero, ram31, p5_width in (
                    (False, "10", 1861), (True, "32", 5792)):
                with self.subTest(use_bank_zero=use_bank_zero):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(
                        MA17_OVERRIDE_RAM57="1", MA17_ADC_CH7="63",
                        MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A),
                        MA17_OVERRIDE_MOVC_MATRIX_BASE="7F15")
                    if use_bank_zero:
                        environment["MA17_OVERRIDE_MOVC_AT"] = substitutions
                    output = Path(directory) / str(use_bank_zero)
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--trace-movc", "--trace-lookup", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "2400000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=40, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(G.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     hashlib.sha256(donor).hexdigest())
                    self.assertEqual(report["ram57_override_hex"], "1")
                    self.assertEqual(report["movc_override_at_hex"],
                                     substitutions if use_bank_zero else None)
                    reads = report["movc_observation"]["reads"]
                    self.assertEqual(sum(row["count"] for row in reads
                                         if 0x7F15 <= int(row["mapped"], 16) < 0x7F51),
                                     462)
                    self.assertEqual(report["engine_ram_observation"]["31"][-1]
                                     ["after"], ram31)
                    self.assertEqual(report["output_latches"]["P5.0"]
                                     ["median_low_width_ticks"], p5_width)
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     1422)


if __name__ == "__main__":
    unittest.main()
