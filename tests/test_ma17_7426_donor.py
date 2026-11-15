"""Counterfactuals for the variant-specific 7426h curve in original Fiat ROMs."""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "firmwares_modificados_ma17_tipo"


class Curve7426DonorTests(unittest.TestCase):
    def test_a_cells_change_cc3_in_g_and_s88_at_fixed_adc_state(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = (VARIANTS / "tipo 1.6 alcool27c256.bin").read_bytes()
        self.assertEqual(donor[0x742E:0x7430], bytes.fromhex("6A 70"))
        cases = (
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 1505, 1589,
             6009, 6345, "9D", "F1"),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 1429, 1508,
             5705, 6021, "51", "A0"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for firmware, base_cc3, donor_cc3, base_low, donor_low, base_r2, donor_r2 in cases:
                rom = firmware.read_bytes()
                self.assertEqual(rom[0x7008:0x700A], bytes.fromhex("74 26"))
                self.assertEqual(rom[0x742E:0x7430], bytes.fromhex("5A 60"))
                for use_donor, cc3, low, r2, upper87 in (
                        (False, base_cc3, base_low, base_r2, "5B"),
                        (True, donor_cc3, donor_low, donor_r2, "6B")):
                    with self.subTest(firmware=firmware.name, donor=use_donor):
                        output = Path(directory) / firmware.stem / str(use_donor)
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                            "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "232",
                            "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                            "MA17_TRACE_129D_PATH": "1"})
                        if use_donor:
                            environment["MA17_OVERRIDE_MOVC_AT"] = (
                                "532F:742E:6A,5333:742F:70")
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", "1000", "--stop-ticks", "2400000",
                             "--seconds", "30", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom).hexdigest())
                        self.assertEqual((report["cc3_observation"]["iram14_15_median"],
                                          report["cc3_observation"][
                                              "cc3_pin_model_median_low_width_ticks"]),
                                         (cc3, low))
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                                in lines if line.startswith("[129D-PATH]")
                                and "PC=12D9" in line]
                        self.assertTrue(path)
                        self.assertEqual((path[-1]["R5"], path[-1]["R6"],
                                          path[-1]["UIRAM87"], path[-1]["RAM4A"]),
                                         ("08", "30", upper87, "91"))
                        samples = [dict(re.findall(r"(\w+)=(\w+)", line))["R2"]
                                   for line in lines if line.startswith(
                                       "[INJECTION-FLOW]") and "PC=1DD8 " in line]
                        self.assertGreater(len(samples), 200)
                        self.assertEqual(Counter(samples).most_common(1)[0][0], r2)
                        overrides = [line for line in lines
                                     if line.startswith("[MOVC-OVERRIDE]")]
                        self.assertEqual(len(overrides), 2 if use_donor else 0)

    def test_a_cells_change_cc3_with_clear_coolant_fault_flags(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor = (VARIANTS / "tipo 1.6 alcool27c256.bin").read_bytes()
        self.assertEqual(donor[0x7429:0x742B], bytes.fromhex("2A 2D"))
        cases = (
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 863, 947,
             3441, 3777, "1B", "6F", 1861),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 821, 900,
             3273, 3589, "F1", "40", 1921),
        )
        with tempfile.TemporaryDirectory() as directory:
            for firmware, base_cc3, donor_cc3, base_low, donor_low, base_r2, donor_r2, p5 in cases:
                rom = firmware.read_bytes()
                self.assertEqual(rom[0x7008:0x700A], bytes.fromhex("74 26"))
                self.assertEqual(rom[0x7429:0x742B], bytes.fromhex("1A 1D"))
                for use_donor, cc3, low, r2, upper87 in (
                        (False, base_cc3, base_low, base_r2, "1A"),
                        (True, donor_cc3, donor_low, donor_r2, "2A")):
                    with self.subTest(firmware=firmware.name, donor=use_donor):
                        output = Path(directory) / firmware.stem / str(use_donor)
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                            "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "80",
                            "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                            "MA17_TRACE_129D_PATH": "1",
                            "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                        if use_donor:
                            environment["MA17_OVERRIDE_MOVC_AT"] = (
                                "532F:7429:2A,5333:742A:2D")
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", "1000", "--stop-ticks", "2400000",
                             "--seconds", "30", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom).hexdigest())
                        self.assertEqual((report["cc3_observation"]["iram14_15_median"],
                                          report["cc3_observation"][
                                              "cc3_pin_model_median_low_width_ticks"]),
                                         (cc3, low))
                        self.assertEqual(
                            [report["output_latches"][pin]["median_low_width_ticks"]
                             for pin in ("P5.0", "P5.1")], [p5, p5])
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        bounds = [dict(re.findall(r"(\w+)=(\w+)", line))
                                  for line in lines if line.startswith(
                                      "[POST-COOLANT-AXIS]") and "PC=477F" in line]
                        self.assertTrue(bounds)
                        self.assertEqual({(row["F28"], row["RAM63"])
                                          for row in bounds}, {("00", "50")})
                        path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                                in lines if line.startswith("[129D-PATH]")
                                and "PC=12D9" in line]
                        self.assertTrue(path)
                        self.assertEqual((path[-1]["R5"], path[-1]["R6"],
                                          path[-1]["UIRAM87"], path[-1]["RAM4A"]),
                                         ("03", "20", upper87, "0F"))
                        samples = [dict(re.findall(r"(\w+)=(\w+)", line))["R2"]
                                   for line in lines if line.startswith(
                                       "[INJECTION-FLOW]") and "PC=1DD8 " in line]
                        self.assertGreater(len(samples), 200)
                        self.assertEqual(Counter(samples).most_common(1)[0][0], r2)
                        overrides = [line for line in lines
                                     if line.startswith("[MOVC-OVERRIDE]")]
                        self.assertEqual(len(overrides), 2 if use_donor else 0)

    def test_a_cells_effect_persists_at_750_and_1500_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 750, 1044, 1146,
             4165, 4573, 17, 1863),
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 1500, 644, 704,
             2565, 2804, 13, 1824),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 750, 900, 987,
             3589, 3937, 17, 1863),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 1500, 721, 788,
             2873, 3141, 13, 1823),
        )
        with tempfile.TemporaryDirectory() as directory:
            for firmware, rpm, base_cc3, donor_cc3, base_low, donor_low, count, p5 in cases:
                rom = firmware.read_bytes()
                self.assertEqual(rom[0x7429:0x742B], bytes.fromhex("1A 1D"))
                for use_donor, cc3, low, upper87 in (
                        (False, base_cc3, base_low, "1A"),
                        (True, donor_cc3, donor_low, "2A")):
                    with self.subTest(firmware=firmware.name, rpm=rpm,
                                      donor=use_donor):
                        output = (Path(directory) / firmware.stem / str(rpm) /
                                  str(use_donor))
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH",
                                                              "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                            "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "80",
                            "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                            "MA17_TRACE_129D_PATH": "1",
                            "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                        if use_donor:
                            environment["MA17_OVERRIDE_MOVC_AT"] = (
                                "532F:7429:2A,5333:742A:2D")
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", str(rpm), "--stop-ticks", "2400000",
                             "--seconds", "30", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom).hexdigest())
                        self.assertEqual((report["cc3_observation"]["iram14_15_median"],
                                          report["cc3_observation"][
                                              "cc3_pin_model_median_low_width_ticks"]),
                                         (cc3, low))
                        self.assertEqual(
                            [report["output_latches"][pin]["median_low_width_ticks"]
                             for pin in ("P5.0", "P5.1")], [p5, p5])
                        reads = {(row["pc"], row["address"]): row["count"] for row
                                 in report["movc_observation"]["reads"]}
                        self.assertEqual(reads[("532F", "7429")], count)
                        self.assertEqual(reads[("5333", "742A")], count)
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        bounds = [dict(re.findall(r"(\w+)=(\w+)", line))
                                  for line in lines if line.startswith(
                                      "[POST-COOLANT-AXIS]") and "PC=477F" in line]
                        self.assertTrue(bounds)
                        self.assertEqual({row["F28"] for row in bounds}, {"00"})
                        path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                                in lines if line.startswith("[129D-PATH]")
                                and "PC=12D9" in line]
                        self.assertTrue(path)
                        self.assertEqual((path[-1]["R5"], path[-1]["R6"],
                                          path[-1]["UIRAM87"]),
                                         ("03", "20", upper87))

    def test_a_cells_effect_persists_at_2000_to_4000_rpm(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        cases = (
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 2000, 534, 582, 2124, 2316, 1818, 12),
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 3000, 399, 434, 1584, 1724, 1749, 11),
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 4000, 337, 365, 1325, 1437, 1793, 10),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 2000,
             633, 691, 2520, 2752, 1789, 12),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 3000,
             536, 585, 2133, 2328, 1785, 11),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 4000,
             515, 561, 2025, 2209, 1807, 10),
        )
        with tempfile.TemporaryDirectory() as directory:
            for firmware, rpm, base_cc3, donor_cc3, base_low, donor_low, p5, count in cases:
                rom = firmware.read_bytes()
                self.assertEqual(rom[0x7429:0x742B], bytes.fromhex("1A 1D"))
                for use_donor, cc3, low, upper87 in (
                        (False, base_cc3, base_low, "1A"),
                        (True, donor_cc3, donor_low, "2A")):
                    with self.subTest(firmware=firmware.name, rpm=rpm, donor=use_donor):
                        output = Path(directory) / firmware.stem / str(rpm) / str(use_donor)
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                            "MA17_ADC_CH2": "220", "MA17_ADC_CH3": "80",
                            "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                            "MA17_TRACE_129D_PATH": "1",
                            "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                        if use_donor:
                            environment["MA17_OVERRIDE_MOVC_AT"] = (
                                "532F:7429:2A,5333:742A:2D")
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", str(rpm), "--stop-ticks", "2400000",
                             "--seconds", "30", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom).hexdigest())
                        self.assertEqual((report["cc3_observation"]["iram14_15_median"],
                                          report["cc3_observation"][
                                              "cc3_pin_model_median_low_width_ticks"]),
                                         (cc3, low))
                        self.assertEqual([report["output_latches"][pin][
                            "median_low_width_ticks"] for pin in ("P5.0", "P5.1")],
                                         [p5, p5])
                        reads = {(row["pc"], row["address"]): row["count"] for row
                                 in report["movc_observation"]["reads"]}
                        self.assertEqual(reads[("532F", "7429")], count)
                        self.assertEqual(reads[("5333", "742A")], count)
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        bounds = [dict(re.findall(r"(\w+)=(\w+)", line))
                                  for line in lines if line.startswith(
                                      "[POST-COOLANT-AXIS]") and "PC=477F" in line]
                        self.assertTrue(bounds)
                        self.assertEqual({row["F28"] for row in bounds}, {"00"})
                        path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                                in lines if line.startswith("[129D-PATH]")
                                and "PC=12D9" in line]
                        self.assertTrue(path)
                        self.assertEqual((path[-1]["R5"], path[-1]["R6"],
                                          path[-1]["UIRAM87"], path[-1]["RAM4A"]),
                                         ("03", "20", upper87, "0F"))

    def test_a_cells_effect_at_two_other_adc3_segments(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        donor_rom = (VARIANTS / "tipo 1.6 alcool27c256.bin").read_bytes()
        cases = (
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 40, 0x7427,
             "13", "1A", "01", "B0", "07", "08", "18", 740, 809, 2948, 3225, 1861),
            (ROOT / "FiatTipo_MA17_dump_27c256.bin", 160, 0x742B,
             "35", "48", "05", "E0", "2E", "36", "46", 1155, 1241, 4609, 4953, 1861),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 40, 0x7427,
             "13", "1A", "01", "B0", "07", "08", "18", 704, 770, 2804, 3069, 1921),
            (VARIANTS / "tipo 1.6 alcool27c256 SUN 8817.bin", 160, 0x742B,
             "35", "48", "05", "E0", "2E", "36", "46", 1097, 1179, 4377, 4705, 1921),
        )
        with tempfile.TemporaryDirectory() as directory:
            for (firmware, adc3, address, first, second, r5, r6, ram4a,
                 base87, donor87, base_cc3, donor_cc3, base_low, donor_low, p5) in cases:
                rom = firmware.read_bytes()
                self.assertEqual(donor_rom[address:address + 2],
                                 bytes.fromhex(first + second))
                for use_donor, upper87, cc3, low in (
                        (False, base87, base_cc3, base_low),
                        (True, donor87, donor_cc3, donor_low)):
                    with self.subTest(firmware=firmware.name, adc3=adc3,
                                      donor=use_donor):
                        output = Path(directory) / firmware.stem / str(adc3) / str(use_donor)
                        environment = {key: value for key, value in os.environ.items()
                                       if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_",
                                                              "MA17_OVERRIDE_"))}
                        environment.update({
                            "MA17_ADC_CH0": "40", "MA17_ADC_CH6": "95",
                            "MA17_ADC_CH2": "220", "MA17_ADC_CH3": str(adc3),
                            "MA17_ADC_CH5": "40", "MA17_ADC_CH7": "63",
                            "MA17_TRACE_129D_PATH": "1",
                            "MA17_TRACE_POST_COOLANT_AXIS": "1"})
                        if use_donor:
                            environment["MA17_OVERRIDE_MOVC_AT"] = (
                                f"532F:{address:04X}:{first},"
                                f"5333:{address + 1:04X}:{second}")
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                             "--firmware", str(firmware), "--trace-movc",
                             "--no-kline-inject", "--crank-immediate",
                             "--rpm", "1000", "--stop-ticks", "2400000",
                             "--seconds", "30", "--output-dir", str(output)],
                            capture_output=True, text=True, env=environment,
                            timeout=40, check=False)
                        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                        report = json.loads((output / "execution.json").read_text())
                        self.assertEqual(report["firmware_sha256"],
                                         hashlib.sha256(rom).hexdigest())
                        self.assertEqual((report["cc3_observation"]["iram14_15_median"],
                                          report["cc3_observation"][
                                              "cc3_pin_model_median_low_width_ticks"]),
                                         (cc3, low))
                        self.assertEqual([report["output_latches"][pin][
                            "median_low_width_ticks"] for pin in ("P5.0", "P5.1")],
                                         [p5, p5])
                        reads = {(row["pc"], row["address"]): row["count"] for row
                                 in report["movc_observation"]["reads"]}
                        self.assertEqual(reads[("532F", f"{address:04X}")], 20)
                        self.assertEqual(reads[("5333", f"{address + 1:04X}")], 20)
                        lines = (output / "emulator-trace.log").read_text().splitlines()
                        bounds = [dict(re.findall(r"(\w+)=(\w+)", line))
                                  for line in lines if line.startswith(
                                      "[POST-COOLANT-AXIS]") and "PC=477F" in line]
                        self.assertTrue(bounds)
                        self.assertEqual({row["F28"] for row in bounds}, {"00"})
                        path = [dict(re.findall(r"(\w+)=(\w+)", line)) for line
                                in lines if line.startswith("[129D-PATH]")
                                and "PC=12D9" in line]
                        self.assertTrue(path)
                        self.assertEqual((path[-1]["R5"], path[-1]["R6"],
                                          path[-1]["RAM4A"], path[-1]["UIRAM87"]),
                                         (r5, r6, ram4a, upper87))


if __name__ == "__main__":
    unittest.main()
