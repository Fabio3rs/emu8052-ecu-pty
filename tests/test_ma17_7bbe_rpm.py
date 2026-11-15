"""Check the conditional 7BBEh → RAM69h → modeled P5 path at two RPMs."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
A = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"


class Bank7bbeRpmTests(unittest.TestCase):
    def test_alcohol_donor_ram69_gate_and_p5_at_three_rpms(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (
            (750, False, None, "81", 884, 6096, 6094, 878),
            (750, True, None, "9C", 884, 6016, 6016, 878),
            (750, False, "9C", "81", 884, 6016, 6016, 878),
            (750, True, "81", "9C", 884, 6096, 6096, 878),
            (1000, False, None, "66", 650, 5868, 5880.5, 728),
            (1000, True, None, "9A", 650, 5908, 5908, 728),
            (2000, False, None, "35", 460, 4790, 4790, 390),
            (2000, True, None, "8A", 460, 4760, 4760, 390),
            (2000, False, "8A", "35", 460, 4760, 4760, 390),
            (2000, True, "35", "8A", 460, 4790, 4790, 390))
        g_hash = hashlib.sha256(G.read_bytes()).hexdigest()
        a_hash = hashlib.sha256(A.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            for rpm, donor, ram69, stored, reads, p50, p51, cc3 in cases:
                with self.subTest(rpm=rpm, donor=donor, ram69=ram69):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    for channel, value in enumerate((40, 130, 100, 20,
                                                     90, 40, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(value)
                    environment["MA17_OVERRIDE_RAM57"] = "1"
                    environment["MA17_TRACE_RAM31_GATE"] = "1"
                    environment["MA17_TRACE_TIMER1_PATH"] = "1"
                    if donor:
                        environment["MA17_OVERRIDE_MOVC_MATRIX_ROM"] = str(A)
                        environment["MA17_OVERRIDE_MOVC_MATRIX_BASE"] = "7BBE"
                    if ram69:
                        environment["MA17_OVERRIDE_RAM69"] = ram69
                    output = Path(directory) / f"{rpm}_{donor}_{ram69}"
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(G), "--no-kline-inject",
                         "--crank-immediate", "--rpm", str(rpm), "--trace-movc",
                         "--stop-ticks", "2400000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"], g_hash)
                    self.assertEqual(report["movc_matrix_donor_sha256"],
                                     a_hash if donor else None)
                    self.assertEqual(report["ram57_override_hex"], "1")
                    self.assertEqual(report["ram69_override_hex"], ram69)
                    self.assertEqual(report["stop_ticks_observed"], 2400000)
                    self.assertEqual(sum(row["count"] for row in
                                         report["movc_observation"]["reads"]
                                         if 0x7BBE <= int(row["mapped"], 16)
                                         < 0x7C36), reads)
                    self.assertEqual(report["engine_ram_observation"]["69"][-1]
                                     ["after"], stored)
                    for pin, width in (("P5.0", p50), ("P5.1", p51)):
                        self.assertEqual(report["output_latches"][pin]
                                         ["median_low_width_ticks"], width)
                    self.assertEqual(report["cc3_observation"]["iram14_15_median"],
                                     cc3)
                    log = (output / "emulator-trace.log").read_text(errors="replace")
                    gates = re.findall(
                        r"^\[RAM31-GATE\].*PC=049B RAM47=[0-9A-F]{2} "
                        r"RAM31=([0-9A-F]{2}) RAM69=([0-9A-F]{2}) "
                        r"A=([0-9A-F]{2}) .*F22=([0-9A-F]{2})$",
                        log, re.MULTILINE)
                    self.assertTrue(gates)
                    ram31, observed_ram69, result, flags = gates[-1]
                    effective_ram69 = ram69 or stored
                    self.assertEqual(observed_ram69, effective_ram69)
                    self.assertEqual(int(result, 16),
                                     ((int(effective_ram69, 16) >> 1) -
                                      int(ram31, 16)) & 0xFF)
                    self.assertEqual(bool(int(flags, 16) & 0x80),
                                     (int(effective_ram69, 16) >> 1) >
                                     int(ram31, 16))
                    reloads = re.findall(
                        r"^\[TIMER1-PATH\].*PC=0286 .*R34_35=([0-9A-F]{4})$",
                        log, re.MULTILINE)
                    self.assertTrue(reloads)
                    expected_reloads = {
                        (750, "81"): "E2FD", (750, "9C"): "B2FF",
                        (1000, "66"): "FFFF", (1000, "9A"): "E2FF",
                        (2000, "35"): "43FF", (2000, "8A"): "34FF"}
                    self.assertEqual(reloads[-1],
                                     expected_reloads[rpm, effective_ram69])


if __name__ == "__main__":
    unittest.main()
