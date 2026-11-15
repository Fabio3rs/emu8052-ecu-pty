"""Controlled full-boot reachability of the Fiat MA1.7 ROM matrix at 7E16h."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "FiatTipo_MA17_dump_27c256.bin"
A = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256.bin"
S88 = ROOT / "firmwares_modificados_ma17_tipo/tipo 1.6 alcool27c256 SUN 8817.bin"


class Matrix7e16ReachabilityTests(unittest.TestCase):
    def test_7e8e_single_movc_byte_controls_upper_8d_countdown(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        observed = {}
        with tempfile.TemporaryDirectory() as directory:
            for replacement, expected in ((None, "02"), ("03", "03")):
                with self.subTest(replacement=replacement):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_",
                                                          "MA17_ZERO_"))}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC10_STEP_CH0="1350000:720",
                        MA17_ADC10_STEP_CH6="200000:880,1350000:988",
                        MA17_ADC_CH2="100", MA17_ADC_CH3="80",
                        MA17_ADC_CH7="63", MA17_P4_6_FORCE_LOW="1",
                        MA17_TRACE_INDIRECT_IRAM_ADDRESS="8D")
                    if replacement:
                        environment["MA17_OVERRIDE_MOVC_AT"] = (
                            f"37BF:7E93:{replacement}")
                    output = Path(directory) / (replacement or "original")
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(G), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1500",
                         "--stop-ticks", "2200000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(G.read_bytes()).hexdigest())
                    self.assertEqual(report["movc_override_at_hex"],
                                     f"37BF:7E93:{replacement}" if replacement else None)
                    reads = report["indirect_iram_observation"]["reads"]
                    guard = {row["value"]: row["count"] for row in reads
                             if row["pc"] == "37C9" and row["opcode"] == "B7"}
                    positive = [f"{value:02X}" for value in
                                range(1, int(expected, 16) + 1)]
                    self.assertEqual(guard, {"00": 67 - int(expected, 16),
                                             **dict.fromkeys(positive, 1)})
                    self.assertEqual({row["value"] for row in reads
                                      if row["pc"] == "37DF" and row["opcode"] == "17"},
                                     set(positive))
                    self.assertEqual(report["cc3_observation"]["cc3_pin_model_median_low_width_ticks"],
                                     5881)
                    observed[replacement] = report
        control = observed[None]["output_latches"]
        changed = observed["03"]["output_latches"]
        self.assertEqual(control["P5.0"], changed["P5.0"])
        self.assertEqual(control["P5.1"]["median_low_width_ticks"],
                         changed["P5.1"]["median_low_width_ticks"])
        own = {row["width_ticks"]: row["count"]
               for row in control["P5.1"]["low_width_histogram"]}
        supplied = {row["width_ticks"]: row["count"]
                    for row in changed["P5.1"]["low_width_histogram"]}
        self.assertEqual(own.pop(1769), 1)
        self.assertEqual(supplied.pop(1768), 1)
        self.assertEqual(own, supplied)

    def test_7e8e_index_sets_upper_8d_countdown_differently_in_g_s88(self):
        emulator = ROOT / "build/emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        self.assertEqual(G.read_bytes()[0x7E8E:0x7E9D],
                         S88.read_bytes()[0x7E8E:0x7E9D])
        with tempfile.TemporaryDirectory() as directory:
            for firmware, mapped, initial, zero_count in (
                    (G, "7E93", "02", 65),
                    (S88, "7E95", "03", 64)):
                with self.subTest(firmware=firmware.name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_",
                                                          "MA17_ZERO_"))}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC10_STEP_CH0="1350000:720",
                        MA17_ADC10_STEP_CH6="200000:880,1350000:988",
                        MA17_ADC_CH2="100", MA17_ADC_CH3="80",
                        MA17_ADC_CH7="63", MA17_P4_6_FORCE_LOW="1",
                        MA17_TRACE_INDIRECT_IRAM_ADDRESS="8D")
                    output = Path(directory) / firmware.stem
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1500",
                         "--stop-ticks", "2200000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertNotIn("57", report["engine_ram_observation"])
                    movc = [row for row in report["movc_observation"]["reads"]
                            if row["pc"] == "37BF"]
                    self.assertEqual([(row["mapped"], row["value"], row["count"])
                                      for row in movc], [(mapped, initial, 1)])
                    reads = report["indirect_iram_observation"]["reads"]
                    at_guard = {row["value"]: row["count"] for row in reads
                                if row["pc"] == "37C9" and row["opcode"] == "B7"}
                    positive = [f"{value:02X}" for value in
                                range(1, int(initial, 16) + 1)]
                    self.assertEqual(at_guard,
                                     {"00": zero_count, **dict.fromkeys(positive, 1)})
                    self.assertEqual({row["value"] for row in reads
                                      if row["pc"] == "37DF" and row["opcode"] == "17"},
                                     set(positive))

    def test_7e8e_historical_steady_tps_access_is_absent_in_current_model(self):
        if not (ROOT / "build/emu8051-tty").exists():
            self.skipTest("built Fiat emulator is required")
        with tempfile.TemporaryDirectory() as directory:
            for firmware in (G, S88):
                with self.subTest(firmware=firmware.name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_",
                                                          "MA17_ZERO_"))}
                    for channel, raw in enumerate((40, 130, 100, 80,
                                                   90, 110, 95, 63)):
                        environment[f"MA17_ADC_CH{channel}"] = str(raw)
                    environment["MA17_TRACE_INDIRECT_IRAM_ADDRESS"] = "8D"
                    output = Path(directory) / firmware.stem
                    run = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                         "--stop-ticks", "3400000", "--seconds", "25",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=35, check=False)
                    self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["indirect_iram_observation"]["total_reads"], 0)
                    self.assertFalse(any(0x7E8E <= int(row["mapped"], 16) < 0x7E9D
                                         for row in report["movc_observation"]["reads"]))

    def test_alcohol_matrix_donor_changes_upper_ca_but_is_clamped(self):
        emulator = ROOT / "build/emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        self.assertEqual(G.read_bytes()[0x70CE:0x70D0], b"\x7e\x16")
        self.assertEqual(A.read_bytes()[0x70CE:0x70D0], b"\x7e\x16")
        results = {}
        with tempfile.TemporaryDirectory() as directory:
            for donor in (False, True):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                      "MA17_TRACE_", "MA17_P4_",
                                                      "MA17_ZERO_"))}
                environment.update(
                    MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                    MA17_ADC10_STEP_CH0="1350000:720",
                    MA17_ADC10_STEP_CH6="200000:880,1350000:988",
                    MA17_ADC_CH2="100", MA17_ADC_CH3="80",
                    MA17_ADC_CH7="63", MA17_P4_6_FORCE_LOW="1",
                    MA17_TRACE_7E16_GATE="1",
                    MA17_TRACE_UPPER_CA_CONSUMER="1")
                if donor:
                    environment.update(MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A),
                                       MA17_OVERRIDE_MOVC_MATRIX_BASE="7E16")
                output = Path(directory) / ("donor" if donor else "control")
                run = subprocess.run(
                    [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                     "--firmware", str(G), "--trace-movc", "--no-kline-inject",
                     "--crank-immediate", "--rpm", "1500", "--stop-ticks",
                     "2200000", "--seconds", "20", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(G.read_bytes()).hexdigest())
                self.assertEqual(report["emulator_sha256"],
                                 hashlib.sha256(emulator.read_bytes()).hexdigest())
                self.assertEqual(report["movc_matrix_donor_sha256"],
                                 hashlib.sha256(A.read_bytes()).hexdigest()
                                 if donor else None)
                log = (output / "emulator-trace.log").read_text()
                self.assertEqual("[MOVC-OVERRIDE] matrix=7E16..7E8D donor-ROM"
                                 in log, donor)
                rows = [dict(field.split("=", 1) for field in line.split()[1:])
                        for line in log.splitlines()
                        if line.startswith("[MATRIX-7E16-GATE]")]
                writes = [row for row in rows if row["PC"] == "384C"]
                self.assertEqual(len(writes), 80)
                self.assertEqual({row["R3"] for row in writes},
                                 {"52" if donor else "38"})
                reads = [row for row in report["movc_observation"]["reads"]
                         if 0x7E16 <= int(row["mapped"], 16) < 0x7E8E]
                self.assertEqual({(row["mapped"], row["value"], row["count"])
                                  for row in reads},
                                 {("7E66", "33", 80), ("7E67", "52", 80),
                                  ("7E75", "38", 80), ("7E76", "5B", 80)})
                consumers = [dict(field.split("=", 1)
                                  for field in line.split()[1:])
                             for line in log.splitlines()
                             if line.startswith("[UPPER-CA-CONSUMER]")]
                clamped = [row for row in consumers if row["PC"] == "39B2"
                           and int(row["tick"]) >= 1400000]
                self.assertGreater(len(clamped), 30)
                self.assertTrue(all(row["B"] == "05" and
                                    int(row["UCA"], 16) <= 5 for row in clamped))
                at_result = [row for row in consumers if row["PC"] == "39F4"
                             and int(row["tick"]) >= 1400000]
                self.assertGreater(len(at_result), 30)
                self.assertEqual({(row["R2"], row["B"], row["A"])
                                  for row in at_result}, {("97", "05", "9C")})
                results[donor] = (tuple(row["UCA"] for row in writes), report)
        self.assertNotEqual(results[False][0], results[True][0])
        self.assertEqual(sum(a != b for a, b in zip(results[False][0],
                                                   results[True][0])), 54)
        for pin in ("P5.0", "P5.1"):
            self.assertEqual(results[False][1]["output_latches"][pin]
                             ["median_low_width_ticks"],
                             results[True][1]["output_latches"][pin]
                             ["median_low_width_ticks"])
        self.assertEqual(results[False][1]["cc3_observation"]
                         ["cc3_pin_model_median_low_width_ticks"],
                         results[True][1]["cc3_observation"]
                         ["cc3_pin_model_median_low_width_ticks"])

    def test_alcohol_matrix_reaches_r2_when_adc2_lowers_clamp(self):
        results = {}
        with tempfile.TemporaryDirectory() as directory:
            for donor, zero_ca, ram69 in (
                    (False, False, None), (True, False, None),
                    (False, True, None), (True, True, None),
                    (False, False, "9C"), (True, False, "9C")):
                environment = {key: value for key, value in os.environ.items()
                               if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                      "MA17_TRACE_", "MA17_P4_",
                                                      "MA17_ZERO_"))}
                environment.update(
                    MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                    MA17_ADC10_STEP_CH0="1350000:720",
                    MA17_ADC10_STEP_CH6="200000:880,1350000:988",
                    MA17_ADC_CH2="200", MA17_ADC_CH3="80",
                    MA17_ADC_CH7="63", MA17_P4_6_FORCE_LOW="1",
                    MA17_TRACE_7E16_GATE="1",
                    MA17_TRACE_UPPER_CA_CONSUMER="1")
                if donor:
                    environment.update(MA17_OVERRIDE_MOVC_MATRIX_ROM=str(A),
                                       MA17_OVERRIDE_MOVC_MATRIX_BASE="7E16")
                if zero_ca:
                    environment["MA17_ZERO_UPPER_CA_AT_39B2"] = "1"
                if ram69:
                    environment["MA17_OVERRIDE_RAM69"] = ram69
                output = Path(directory) / f"donor_{donor}_zero_{zero_ca}_69_{ram69}"
                run = subprocess.run(
                    [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                     "--firmware", str(G), "--trace-movc", "--no-kline-inject",
                     "--crank-immediate", "--rpm", "1500", "--stop-ticks",
                     "2200000", "--seconds", "20", "--output-dir", str(output)],
                    capture_output=True, text=True, env=environment,
                    timeout=30, check=False)
                self.assertEqual(run.returncode, 0, run.stderr[-1500:])
                report = json.loads((output / "execution.json").read_text())
                self.assertEqual(report["firmware_sha256"],
                                 hashlib.sha256(G.read_bytes()).hexdigest())
                self.assertEqual(report["emulator_sha256"],
                                 hashlib.sha256((ROOT / "build/emu8051-tty")
                                                .read_bytes()).hexdigest())
                self.assertEqual(report["movc_matrix_donor_sha256"],
                                 hashlib.sha256(A.read_bytes()).hexdigest()
                                 if donor else None)
                self.assertEqual(report["upper_ca_zero_at_39b2_experimental"],
                                 zero_ca)
                self.assertEqual(report["ram69_override_hex"], ram69)
                log = (output / "emulator-trace.log").read_text()
                self.assertEqual("[MOVC-OVERRIDE] matrix=7E16..7E8D donor-ROM"
                                 in log, donor)
                self.assertEqual("[UPPER-CA-ZERO]" in log, zero_ca)
                self.assertEqual("[RAM69-OVERRIDE]" in log, ram69 is not None)
                writes = [line.split("UCA=")[1][:2]
                          for line in log.splitlines()
                          if line.startswith("[MATRIX-7E16-GATE]") and
                          "PC=384C" in line]
                self.assertEqual(len(writes), 80)
                consumers = [dict(field.split("=", 1)
                                  for field in line.split()[1:])
                             for line in log.splitlines()
                             if line.startswith("[UPPER-CA-CONSUMER]")]
                at_clamp = [row for row in consumers if row["PC"] == "39B2"
                            and int(row["tick"]) >= 1400000]
                at_result = [row for row in consumers if row["PC"] == "39F4"
                             and int(row["tick"]) >= 1400000]
                self.assertGreater(len(at_clamp), 30)
                self.assertGreater(len(at_result), 30)
                self.assertEqual({(row["B"], row["UC9"], row["UCB"])
                                  for row in at_clamp}, {("00", "00", "00")})
                if zero_ca:
                    self.assertEqual({row["UCA"] for row in at_clamp}, {"00"})
                self.assertTrue(all(row["B"] == row["UCA"] and
                                    int(row["A"], 16) ==
                                    int(row["R2"], 16) + int(row["B"], 16)
                                    for row in at_result))
                results[donor, zero_ca, ram69] = (writes, report)
        for zero_ca, ram69 in ((False, None), (True, None), (False, "9C")):
            self.assertEqual(sum(a != b for a, b in
                                 zip(results[False, zero_ca, ram69][0],
                                     results[True, zero_ca, ram69][0])), 54)
        own, donated = results[False, False, None][1], results[True, False, None][1]
        self.assertEqual(own["output_latches"]["P5.0"]
                         ["median_low_width_ticks"],
                         donated["output_latches"]["P5.0"]
                         ["median_low_width_ticks"])
        self.assertEqual(own["output_latches"]["P5.1"]
                         ["median_low_width_ticks"], 1775)
        self.assertEqual(donated["output_latches"]["P5.1"]
                         ["median_low_width_ticks"], 1784)
        self.assertEqual(own["cc3_observation"]
                         ["cc3_pin_model_median_low_width_ticks"],
                         donated["cc3_observation"]
                         ["cc3_pin_model_median_low_width_ticks"])
        zero_own, zero_donated = (results[False, True, None][1],
                                 results[True, True, None][1])
        for field in ("output_latches", "cc3_observation",
                      "cc3_p5_phase_observation", "engine_ram_observation",
                      "pc_coverage"):
            self.assertEqual(zero_own[field], zero_donated[field])
        self.assertEqual(zero_own["output_latches"]["P5.1"]
                         ["median_low_width_ticks"], 1767)
        fixed_own, fixed_donated = (results[False, False, "9C"][1],
                                    results[True, False, "9C"][1])
        for pin in ("P5.0", "P5.1"):
            self.assertEqual(fixed_own["output_latches"][pin]
                             ["median_low_width_ticks"], 1767)
            self.assertEqual(fixed_own["output_latches"][pin]
                             ["median_low_width_ticks"],
                             fixed_donated["output_latches"][pin]
                             ["median_low_width_ticks"])
        for key in ("34", "35"):
            self.assertEqual(fixed_own["engine_ram_observation"][key],
                             fixed_donated["engine_ram_observation"][key])
        self.assertNotEqual(fixed_own["engine_ram_observation"]["69"],
                            fixed_donated["engine_ram_observation"]["69"])

    def test_double_tps_step_selects_same_table_at_different_cells(self):
        emulator = ROOT / "build/emu8051-tty"
        if not emulator.exists():
            self.skipTest("built Fiat emulator is required")
        self.assertEqual(G.read_bytes()[0x7E16:0x7E8E],
                         S88.read_bytes()[0x7E16:0x7E8E])
        cases = (
            ("G_double_low", G, True, True, False,
             {("7E66", "33"): 80, ("7E67", "52"): 80,
              ("7E75", "38"): 80, ("7E76", "5B"): 80}),
            ("S88_double_low", S88, True, True, False,
             {("7E76", "5B"): 80, ("7E77", "66"): 80,
              ("7E85", "5A"): 80, ("7E86", "73"): 80}),
            ("G_axis_only", G, True, True, False,
             {("7E67", "52"): 80, ("7E68", "4D"): 80,
              ("7E76", "5B"): 80, ("7E77", "66"): 80}),
            ("G_two_donors", G, True, True, True,
             {("7E76", "5B"): 80, ("7E77", "66"): 80,
              ("7E85", "5A"): 80, ("7E86", "73"): 80}),
            ("G_double_default", G, False, True, False, {}),
            ("G_single_low", G, True, False, False, {}),
        )
        sequences = {}
        with tempfile.TemporaryDirectory() as directory:
            for name, firmware, p46_low, double_step, donor, expected in cases:
                with self.subTest(case=name):
                    environment = {key: value for key, value in os.environ.items()
                                   if not key.startswith(("MA17_ADC", "MA17_OVERRIDE_",
                                                          "MA17_TRACE_", "MA17_P4_"))}
                    environment.update(
                        MA17_ADC_CH0="40", MA17_ADC_CH6="95",
                        MA17_ADC10_STEP_CH0="1350000:720",
                        MA17_ADC10_STEP_CH6=("200000:880,1350000:988"
                                              if double_step else "1350000:988"),
                        MA17_ADC_CH2="100", MA17_ADC_CH3="80",
                        MA17_ADC_CH7="63", MA17_TRACE_7E16_GATE="1",
                        MA17_TRACE_RAM69="1",
                        MA17_TRACE_UPPER_CA_CONSUMER="1")
                    if p46_low:
                        environment["MA17_P4_6_FORCE_LOW"] = "1"
                    if name in ("G_axis_only", "G_two_donors"):
                        environment["MA17_OVERRIDE_MOVC_7580"] = "25"
                    if donor:
                        environment.update(MA17_OVERRIDE_MOVC_MATRIX_ROM=str(S88),
                                           MA17_OVERRIDE_MOVC_MATRIX_BASE="7581")
                    output = Path(directory) / name
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools/trace_ma17.py"),
                         "--firmware", str(firmware), "--trace-movc",
                         "--no-kline-inject", "--crank-immediate", "--rpm", "1500",
                         "--stop-ticks", "2200000", "--seconds", "20",
                         "--output-dir", str(output)],
                        capture_output=True, text=True, env=environment,
                        timeout=30, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                    report = json.loads((output / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["emulator_sha256"],
                                     hashlib.sha256(emulator.read_bytes()).hexdigest())
                    if donor:
                        self.assertEqual(report["movc_matrix_donor_sha256"],
                                         hashlib.sha256(S88.read_bytes()).hexdigest())
                    observed = {(row["mapped"], row["value"]): row["count"]
                                for row in report["movc_observation"]["reads"]
                                if 0x7E16 <= int(row["mapped"], 16) < 0x7E8E}
                    self.assertEqual(observed, expected)
                    lines = [line for line in (output / "emulator-trace.log")
                             .read_text().splitlines()
                             if line.startswith("[MATRIX-7E16-GATE]")]
                    if name in ("G_double_low", "S88_double_low"):
                        consumers = [dict(field.split("=", 1)
                                          for field in line.split()[1:])
                                     for line in (output / "emulator-trace.log")
                                     .read_text().splitlines()
                                     if line.startswith("[UPPER-CA-CONSUMER]")]
                        at_clamp = [row for row in consumers
                                    if row["PC"] == "39B2" and
                                    int(row["tick"]) >= 1400000]
                        at_result = [row for row in consumers
                                     if row["PC"] == "39F4" and
                                     int(row["tick"]) >= 1400000]
                        self.assertGreater(len(at_clamp), 30)
                        self.assertGreater(len(at_result), 30)
                        self.assertEqual({row["B"] for row in at_clamp}, {"05"})
                        self.assertEqual({row["UC8"] for row in at_clamp}, {"05"})
                        self.assertEqual({row["UCA"] for row in at_clamp},
                                         ({"00", "01", "02", "03"}
                                          if name == "G_double_low" else
                                          {"00", "01", "02", "03", "04", "05"}))
                        self.assertTrue(all(int(row["UCA"], 16) <=
                                            int(row["B"], 16) for row in at_clamp))
                        self.assertEqual({(row["R2"], row["B"], row["A"])
                                          for row in at_result},
                                         ({("97", "05", "9C")}
                                          if name == "G_double_low" else
                                          {("99", "05", "9E")}))
                    ram69_lines = [line for line in (output / "emulator-trace.log")
                                   .read_text().splitlines()
                                   if line.startswith("[RAM69-PATH]") and
                                   "PC=330D" in line and
                                   int(line.split("tick=")[1].split()[0]) >= 1500000]
                    def at(pc):
                        return [line for line in lines if f"PC={pc}" in line]
                    self.assertEqual(len(at("3701")), 1 if expected else 0)
                    self.assertEqual(len(at("3830")),
                                     81 if name == "G_axis_only" else
                                     (80 if expected else 0))
                    if expected:
                        self.assertEqual(len(at("384C")), 80)
                        expected_state = {
                            "G_double_low": ("43", "05", "B5", "50"),
                            "G_axis_only": ("44", "96", "C5", "51"),
                            "G_two_donors": ("4C", "96", "86", "60"),
                            "S88_double_low": ("4C", "96", "86", "60"),
                        }[name]
                        self.assertTrue(ram69_lines)
                        self.assertEqual({line.split("UAE=")[1][:2]
                                          for line in ram69_lines}, {expected_state[0]})
                        self.assertEqual({(line.split("UBC=")[1][:2],
                                           line.split("RAM68=")[1][:2],
                                           line.split("R5=")[1][:2])
                                          for line in at("3830")},
                                         {expected_state[1:]})
                        for line in at("3830"):
                            row = int(line.split("RAM68=")[1][:2], 16) & 0x0F
                            column = int(line.split("UBC=")[1][:2], 16) & 0x0F
                            self.assertEqual(int(line.split("R5=")[1][:2], 16),
                                             row * 15 + column)
                        if name == "G_axis_only":
                            continue  # One extra 3830h entry is not paired to 384Ch.
                        pending = None
                        paired_outputs = Counter()
                        paired_sequence = []
                        for line in lines:
                            if "PC=3830" in line:
                                self.assertIsNone(pending)
                                pending = tuple(line.split(key + "=")[1][:2]
                                                for key in ("UBC", "RAM68", "R5", "R1"))
                            elif "PC=384C" in line and pending is not None:
                                result_uca = line.split("UCA=")[1][:2]
                                paired_outputs[result_uca] += 1
                                paired_sequence.append((*pending, result_uca))
                                pending = None
                        self.assertIsNone(pending)
                        self.assertEqual(sum(paired_outputs.values()), 80)
                        self.assertEqual(dict(paired_outputs),
                                         ({"00": 37, "01": 18, "02": 19, "03": 6}
                                         if name == "G_double_low" else
                                         {"00": 18, "01": 10, "02": 11,
                                           "03": 10, "04": 12, "05": 19}))
                        sequences[name] = paired_sequence
                    if name == "G_double_low":
                        crossing = at("36FF")[-1]
                        self.assertEqual(crossing.split("UC5=")[1][:2], "53")
                        self.assertEqual(crossing.split("RAM70=")[1][:2], "DF")
                        self.assertTrue(int(crossing.split("PSW=")[1][:2], 16) & 0x80)
        self.assertEqual(sequences["G_two_donors"], sequences["S88_double_low"])
        self.assertNotEqual(sequences["G_double_low"], sequences["S88_double_low"])


if __name__ == "__main__":
    unittest.main()
