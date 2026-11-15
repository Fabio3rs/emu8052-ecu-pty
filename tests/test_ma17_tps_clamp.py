"""Original-ROM causal check for the ROM72A1h TPS fallback byte."""

import os
import subprocess
import unittest
from pathlib import Path

from tools.audit_ma17_tps_surface import parse_trace


ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "FiatTipo_MA17_dump_27c256.bin"
EMULATOR = ROOT / "build" / "emu8051-tty"
S88_ROM = (ROOT / "firmwares_modificados_ma17_tipo" /
           "tipo 1.6 alcool27c256 SUN 8817.bin")


class TpsClampTests(unittest.TestCase):
    def test_g_and_s88_share_high_adc0_segment_boundary(self):
        self.assertTrue(EMULATOR.exists(), "build the emulator before this test")
        for rom in (ROM, S88_ROM):
            for adc6, expected, five_segment in ((223, "27", False),
                                                  (224, "93", True)):
                with self.subTest(rom=rom.name, adc6=adc6):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith("MA17_")}
                    environment.update({
                        "MA17_STOP_TICKS": "1200000",
                        "MA17_CRANK_IMMEDIATE": "1", "MA17_TRACE_PC": "1",
                        "MA17_TRACE_MOVC": "1", "MA17_CRANK_RPM": "1000",
                        "MA17_ADC_CH0": "160", "MA17_ADC_CH2": "140",
                        "MA17_ADC_CH3": "34", "MA17_ADC_CH6": str(adc6),
                        "MA17_ADC_CH7": "63"})
                    run = subprocess.run([str(EMULATOR), str(rom), "--8052"],
                                         env=environment, capture_output=True,
                                         text=True, timeout=30, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1000:])
                    result = parse_trace(run.stderr, 1200000)
                    self.assertEqual(result["iram6f_hex"], expected)
                    self.assertEqual(bool(result["header_reads"]["7569"]),
                                     five_segment)

    def test_s88_repeats_point_return_effect_in_compatible_code(self):
        self.assertEqual(S88_ROM.read_bytes()[0x72A1], 0x34)
        self.assertTrue(EMULATOR.exists(), "build the emulator before this test")
        for supplied, expected in ((None, "27"), ("44", "37")):
            with self.subTest(supplied=supplied):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update({
                    "MA17_STOP_TICKS": "1200000", "MA17_CRANK_IMMEDIATE": "1",
                    "MA17_TRACE_PC": "1", "MA17_TRACE_MOVC": "1",
                    "MA17_CRANK_RPM": "1000", "MA17_ADC_CH0": "160",
                    "MA17_ADC_CH2": "140", "MA17_ADC_CH3": "34",
                    "MA17_ADC_CH6": "200", "MA17_ADC_CH7": "63"})
                if supplied:
                    environment["MA17_OVERRIDE_MOVC_AT"] = (
                        f"116F:72A1:{supplied}")
                run = subprocess.run([str(EMULATOR), str(S88_ROM), "--8052"],
                                     env=environment, capture_output=True,
                                     text=True, timeout=30, check=False)
                self.assertEqual(run.returncode, 0, run.stderr[-1000:])
                self.assertEqual(parse_trace(run.stderr, 1200000)["iram6f_hex"],
                                 expected)
                self.assertIn("[MOVC-SUMMARY] pc=116F", run.stderr)

    def test_single_movc_return_controls_fallback_iram6f(self):
        self.assertEqual(ROM.read_bytes()[0x72A1], 0x34)
        self.assertTrue(EMULATOR.exists(), "build the emulator before this test")
        for supplied, expected in ((None, "27"), ("34", "27"),
                                   ("44", "37"), ("24", "17")):
            with self.subTest(supplied=supplied):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith("MA17_")}
                environment.update({
                    "MA17_STOP_TICKS": "1200000", "MA17_CRANK_IMMEDIATE": "1",
                    "MA17_TRACE_PC": "1", "MA17_TRACE_MOVC": "1",
                    "MA17_CRANK_RPM": "1000", "MA17_ADC_CH0": "160",
                    "MA17_ADC_CH2": "140", "MA17_ADC_CH3": "34",
                    "MA17_ADC_CH6": "200", "MA17_ADC_CH7": "63"})
                if supplied:
                    environment["MA17_OVERRIDE_MOVC_AT"] = (
                        f"116F:72A1:{supplied}")
                run = subprocess.run([str(EMULATOR), str(ROM), "--8052"],
                                     env=environment, capture_output=True,
                                     text=True, timeout=30, check=False)
                self.assertEqual(run.returncode, 0, run.stderr[-1000:])
                self.assertEqual(parse_trace(run.stderr, 1200000)["iram6f_hex"],
                                 expected)
                self.assertRegex(run.stderr,
                                 r"\[MOVC-SUMMARY\] pc=116F .*"
                                 r"address=72A1 mapped=72A1 value=34 count=\d+")
        self.assertEqual(ROM.read_bytes()[0x72A1], 0x34)


if __name__ == "__main__":
    unittest.main()
