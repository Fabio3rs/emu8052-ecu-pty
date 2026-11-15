"""Native Fiat G/S88 MOVC calibration contributions to modeled CC3."""

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
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
S88 = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"
TRACE = ROOT / "tools/trace_ma17.py"
EMULATOR = ROOT / "build/emu8051-tty"
CELLS_7B46 = (
    ("532F", 0x7B46), ("532F", 0x7B4F),
    ("532F", 0x7B73), ("532F", 0x7BA9),
    ("5333", 0x7B47), ("5333", 0x7B50),
    ("5333", 0x7B74), ("5333", 0x7BAA),
    ("534B", 0x7B5E), ("534B", 0x7B82),
    ("534B", 0x7BB8), ("5350", 0x7B5F),
    ("5350", 0x7B83), ("5350", 0x7BB9),
)


class NativeCalibrationPairTests(unittest.TestCase):
    def test_7b46_closes_one_late_cc3_difference_at_3000_rpm(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        g_bytes, s88_bytes = G.read_bytes(), S88.read_bytes()
        self.assertEqual(g_bytes[0x7580], 0x10)
        self.assertEqual(s88_bytes[0x7580], 0x25)
        self.assertEqual({(s88_bytes[address] - g_bytes[address]) & 0xFF
                          for _, address in CELLS_7B46}, {8})
        point_override = ",".join(
            f"{pc}:{address:04X}:{g_bytes[address]:02X}"
            for pc, address in CELLS_7B46)
        expected = {
            "g": (G, 363, "0000", "5F"),
            "pair": (S88, 364, "00CF", "67"),
            "pair_7b45": (S88, 364, "00CF", "67"),
            "pair_7b46": (S88, 363, "0000", "5F"),
            "pair_7b4f": (S88, 364, "00CF", "62"),
            "pair_7b5e": (S88, 364, "00CF", "64"),
            "pair_lower": (S88, 363, "0000", "5F"),
        }
        schedules = {}
        with tempfile.TemporaryDirectory() as directory:
            for arm, (firmware, starts, late_value, ram69) in expected.items():
                with self.subTest(arm=arm):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                        MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                        MA17_TRACE_CC3_AFTER_TICK="2500000",
                        MA17_TRACE_78XX_PATH="1",
                        MA17_TRACE_PC_WINDOW="3551850:3552025",
                        MA17_TRACE_78XX_AFTER_TICK="3500000")
                    if arm != "g":
                        environment.update(
                            MA17_OVERRIDE_MOVC_7580="10",
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7581",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(G))
                    if arm == "pair_7b45":
                        environment["MA17_OVERRIDE_MOVC_7B45"] = "05"
                    if arm == "pair_7b46":
                        environment["MA17_OVERRIDE_MOVC_AT"] = point_override
                    if arm in ("pair_7b4f", "pair_7b5e", "pair_lower"):
                        addresses = {"pair_7b4f": (0x7B4F,),
                                     "pair_7b5e": (0x7B5E,),
                                     "pair_lower": (0x7B4F, 0x7B5E)}[arm]
                        environment["MA17_OVERRIDE_MOVC_AT"] = ",".join(
                            f"{pc}:{address:04X}:{g_bytes[address]:02X}"
                            for pc, address in CELLS_7B46
                            if address in addresses)
                    output = Path(directory) / arm
                    run = subprocess.run(
                        [sys.executable, str(TRACE), "--firmware", str(firmware),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "4000000", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        cwd=ROOT, timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["trace_78xx_after_tick"], "3500000")
                    self.assertEqual(report["pc_trace_window"],
                                     "3551850:3552025")
                    self.assertEqual(report["cc3_observation"]
                                     ["cc3_pin_model_low_starts"], starts)
                    self.assertEqual(report["engine_ram_observation"]
                                     ["69"][-1]["after"], ram69)
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    if arm in ("g", "pair", "pair_lower"):
                        pc_ticks = {}
                        for line in lines:
                            match = re.match(
                                r"\[PC-WINDOW\] tick=(\d+) PC=([0-9A-F]{4})",
                                line)
                            if match:
                                pc_ticks.setdefault(match[2], int(match[1]))
                                self.assertLessEqual(int(match[1]), 3552025)
                                self.assertGreaterEqual(int(match[1]), 3551850)
                        expected_ticks = ({"1CB7": 3551877,
                                           "000B": 3551896,
                                           "1CD4": 3552010} if arm == "pair"
                                          else {"1CB7": 3551873,
                                                "1CD4": 3551892,
                                                "000B": 3551897})
                        for pc, tick in expected_ticks.items():
                            self.assertEqual(pc_ticks[pc], tick)
                    math_lines = [line for line in lines
                                  if line.startswith("[78XX-MATH]")]
                    self.assertTrue(math_lines)
                    self.assertTrue(all(int(re.search(r"tick=(\d+)", line)[1])
                                        >= 3500000 for line in math_lines))
                    entries = [line for line in lines
                               if line.startswith("[CC3-ENTRY]")]
                    schedules[arm] = [re.search(r"IRAM14_15=([0-9A-F]{4})",
                                                line)[1] for line in entries]
                    self.assertEqual(len(entries), 152)
                    self.assertEqual(schedules[arm][107], late_value)
                    gate = next(line for line in lines
                                if line.startswith("[78XX-MATH]")
                                and "PC=1EA9" in line
                                and 3552000 < int(re.search(r"tick=(\d+)", line)[1])
                                < 3553000)
                    self.assertIn("R2=C8 R3=00" if arm in
                                  ("g", "pair_7b46", "pair_lower")
                                  else "R2=CF R3=00", gate)
        self.assertEqual(schedules["g"], schedules["pair_7b46"])
        self.assertEqual(schedules["g"], schedules["pair_lower"])
        self.assertEqual(sum(a != b for a, b in
                             zip(schedules["g"], schedules["pair"])), 1)

    def test_7a_read_order_mediates_late_cc3_gate(self):
        if not EMULATOR.exists():
            self.skipTest("built Fiat emulator is required")
        expected = {
            "g": (G, None, "8D", "C5 B=0D", "C8", "0000"),
            "g_read85": (G, "85", "8D", "FD B=0C", "CF", "00CF"),
            "s88_pair": (S88, None, "85", "FD B=0C", "CF", "00CF"),
            "s88_read8d": (S88, "8D", "85", "C5 B=0D", "C8", "0000"),
        }
        with tempfile.TemporaryDirectory() as directory:
            for arm, (firmware, supplied, stored,
                      product, candidate, interval) in expected.items():
                with self.subTest(arm=arm):
                    environment = {key: value for key, value in
                                   os.environ.items() if not key.startswith("MA17_")}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH1="130",
                        MA17_ADC_CH2="140", MA17_ADC_CH3="34",
                        MA17_ADC_CH4="90", MA17_ADC_CH5="110",
                        MA17_ADC_CH6="95", MA17_ADC_CH7="63",
                        MA17_ADC10_STEP_CH0="800000:720,3274600:160",
                        MA17_ADC10_STEP_CH6="800000:988,3274600:380",
                        MA17_TRACE_CC3_AFTER_TICK="2500000",
                        MA17_TRACE_78XX_PATH="1",
                        MA17_TRACE_78XX_AFTER_TICK="3500000")
                    if firmware == S88:
                        environment.update(
                            MA17_OVERRIDE_MOVC_7580="10",
                            MA17_OVERRIDE_MOVC_MATRIX_BASE="7581",
                            MA17_OVERRIDE_MOVC_MATRIX_ROM=str(G))
                    if supplied is not None:
                        environment.update(
                            MA17_OVERRIDE_IRAM_READ_AT=f"1CD4:7A:{supplied}",
                            MA17_OVERRIDE_IRAM_READ_AFTER_TICK="3551800")
                    output = Path(directory) / arm
                    run = subprocess.run(
                        [sys.executable, str(TRACE), "--firmware", str(firmware),
                         "--trace-movc", "--no-kline-inject",
                         "--crank-immediate", "--rpm", "3000",
                         "--stop-ticks", "3560500", "--seconds", "30",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        cwd=ROOT, timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["iram_read_override_after_tick"],
                                     "3551800" if supplied is not None else None)
                    writes = [row for row in report["engine_ram_observation"]["7A"]
                              if 3551000 < row["tick"] < 3553000]
                    self.assertEqual([(row["before"], row["after"],
                                       row["source_pc"]) for row in writes],
                                     [("8D", "85", "07B3")])
                    lines = (output / "emulator-trace.log").read_text().splitlines()
                    read = next(line for line in lines
                                if line.startswith("[78XX-CONSUMER]")
                                and "PC=1CD4" in line
                                and 3551800 < int(re.search(r"tick=(\d+)", line)[1])
                                < 3552100)
                    self.assertIn(f"RAM7A={stored}", read)
                    read_tick = int(re.search(r"tick=(\d+)", read)[1])
                    self.assertEqual(read_tick < writes[0]["tick"],
                                     firmware == G)
                    if supplied is not None:
                        overrides = [line for line in lines if line.startswith(
                            "[IRAM-READ-OVERRIDE]")]
                        self.assertEqual(len(overrides), 1)
                        self.assertIn(f"stored={stored} supplied={supplied}",
                                      overrides[0])
                    product_line = next(line for line in lines
                                        if line.startswith("[78XX-CONSUMER]")
                                        and "PC=1CDF" in line
                                        and 3551800 < int(re.search(
                                            r"tick=(\d+)", line)[1]) < 3552100)
                    self.assertIn(f"A={product}", product_line)
                    gate = next(line for line in lines
                                if line.startswith("[78XX-MATH]")
                                and "PC=1EA9" in line
                                and 3552000 < int(re.search(r"tick=(\d+)", line)[1])
                                < 3553000)
                    self.assertIn(f"R2={candidate} R3=00", gate)
                    entry = next(line for line in lines
                                 if line.startswith("[CC3-ENTRY]")
                                 and "instr=3560295" in line)
                    self.assertIn(f"IRAM14_15={interval}", entry)


if __name__ == "__main__":
    unittest.main()
