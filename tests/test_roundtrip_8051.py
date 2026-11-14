"""Binary round-trip regressions for the MCS-51 toolchain."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "roundtrip_8051.py"


class RoundtripTests(unittest.TestCase):
    def run_roundtrip(self, firmware, *options):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(firmware), "--output-dir", directory,
                 *options], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads((Path(directory) / "report.json").read_text())
            rebuilt = next(Path(directory).glob("*.rebuilt.bin")).read_bytes()
            assembly = next(p for p in Path(directory).glob("*.asm")
                            if not p.name.endswith(".disasm51.asm")).read_text()
            self.assertEqual(rebuilt, firmware.read_bytes())
            self.assertEqual(report["mismatched_bytes"], 0)
            self.assertTrue(report["sha256_equal"])
            self.assertEqual(report["original_size"], report["rebuilt_size"])
            self.assertEqual(report["original_sha256"], hashlib.sha256(rebuilt).hexdigest())
            self.assertGreater(report["code_bytes"], 0)
            return report, assembly

    def test_fiat_tipo_ma17(self):
        report, assembly = self.run_roundtrip(ROOT / "FiatTipo_MA17_dump_27c256.bin")
        self.assertEqual(report["original_size"], 32768)
        self.assertEqual(report["code_bytes"], 23420)
        self.assertEqual(report["data_bytes"], 4117)
        self.assertEqual(report["unclassified_bytes"], 5231)
        self.assertIn("djnz 6Bh", assembly)
        self.assertIn("S0RELL DATA 0AAh", assembly)
        self.assertIn("XPAGE DATA 091h", assembly)
        self.assertIn("SYSCON DATA 0B1h", assembly)
        self.assertIn("ADDATH DATA 0D9h", assembly)
        self.assertIn("ADDATL DATA 0DAh", assembly)
        self.assertNotIn("DAPR DATA", assembly)
        self.assertIn("mov ADDATL, A", assembly)
        self.assertIn("push XPAGE", assembly)
        self.assertIn("mov SYSCON, #02h", assembly)

    def test_renault_clio_ma17(self):
        firmware = ROOT / "Renault_Clio_1.6__0261204510_1037355887_Bosch_1997_.ori"
        report, assembly = self.run_roundtrip(firmware)
        self.assertEqual(report["original_size"], 65536)
        self.assertGreater(report["code_bytes"], 20000)
        self.assertNotIn("XPAGE DATA", assembly)

    def test_emulator_rejects_foreign_rom_without_explicit_override(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.exists():
            self.skipTest("build/emu8051-tty is required for profile test")
        firmware = ROOT / "Renault_Clio_1.6__0261204510_1037355887_Bosch_1997_.ori"
        env = dict(os.environ, MA17_ALLOW_FOREIGN_ROM="0")
        result = subprocess.run([str(emulator), str(firmware), "--8052"],
                                capture_output=True, text=True, env=env, timeout=5)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Refusing Fiat hardware emulation", result.stderr)

    def test_emulator_uses_xpage_to_reach_rpm_capture(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
             "--seconds", "1.2", "--no-kline-inject", "--crank-immediate"],
            capture_output=True, text=True,
            env={key: value for key, value in os.environ.items()
                 if key != "MA17_ADC_CH7"})
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads((ROOT / "build" / "ma17-analysis" / "execution.json").read_text())
        self.assertEqual(report["adc7_input_value"], 105)
        self.assertGreater(report["event_counts"].get("[ISR-IEX3]", 0), 0)
        self.assertEqual(report["wheel_observation"]["teeth_per_revolution"], [58])
        self.assertEqual(report["wheel_observation"]["gaps_per_revolution"], [2])
        self.assertTrue(any(change["after"] == "28" for change in
                            report["rpm_observation"]["ram47_changes"]))
        log = (ROOT / "build" / "ma17-analysis" / "emulator-trace.log").read_text()
        self.assertIn("P5.0/1=01", log)
        self.assertIn("P5.0/1=02", log)
        for channel in ("P5.0", "P5.1"):
            latch = report["output_latches"][channel]
            self.assertGreaterEqual(latch["low_starts"], 2)
            self.assertAlmostEqual(latch["median_period_ticks"], 59400, delta=3000)
            self.assertGreater(latch["median_low_width_ticks"], 0)
        sequence = report["output_latches"]["sequence"]
        self.assertTrue(sequence["alternating"])
        self.assertAlmostEqual(sequence["median_between_channels_ticks"],
                               29700, delta=3000)
        cc3 = report["cc3_observation"]
        self.assertGreater(cc3["entry_samples"], 0)
        self.assertEqual(cc3["entry_samples"], cc3["guarded_entry_samples"])
        self.assertEqual(cc3["entry_pcs"], ["058E"])
        self.assertEqual(cc3["p1_3_shadow_edges"], 0)
        self.assertEqual(cc3["cc3_pin_model_edges"], 0)

    def test_adc7_threshold_controls_cc3_path(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        for adc7, guarded in ((64, False), (65, True)):
            with self.subTest(adc7=adc7):
                env = dict(os.environ, MA17_ADC_CH7=str(adc7))
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", "10", "--stop-ticks", "1200000",
                     "--no-kline-inject", "--crank-immediate"],
                    capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                report = json.loads((ROOT / "build" / "ma17-analysis" /
                                     "execution.json").read_text())
                self.assertEqual(report["adc7_input_value"], adc7)
                cc3 = report["cc3_observation"]
                self.assertGreater(cc3["entry_samples"], 0)
                self.assertEqual(cc3["guarded_entry_samples"],
                                 cc3["entry_samples"] if guarded else 0)
                phase = report["cc3_p5_phase_observation"]
                if guarded:
                    self.assertEqual(cc3["p1_3_shadow_edges"], 0)
                    self.assertEqual(cc3["cc3_pin_model_edges"], 0)
                    self.assertEqual(cc3["compare_match_candidates"], 0)
                    self.assertEqual(phase["paired_half_cycles"], 0)
                else:
                    self.assertGreater(cc3["p1_3_shadow_edges"], 0)
                    self.assertGreater(cc3["cc3_pin_model_edges"], 0)
                    self.assertGreater(cc3["compare_match_candidates"], 0)
                    self.assertAlmostEqual(cc3["cc3_pin_model_median_period_ticks"],
                                           29700, delta=3000)
                    self.assertGreater(cc3["cc3_pin_model_paired_pulses"], 0)
                    self.assertGreater(phase["paired_half_cycles"], 0)
                    self.assertAlmostEqual(
                        phase["cc3_low_after_p5_low_median_ticks"], 1994, delta=50)
                    self.assertLessEqual(
                        abs(cc3["cc3_pin_model_width_minus_4x_raw_median_ticks"]), 15)
                    self.assertEqual(cc3["p1_3_shadow_median_low_width_ticks"], 4)

    def test_scanner_sensor_addresses_follow_distinct_adc_channels(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        for channel, address in ((0, "60"), (1, "61"), (2, "62"),
                                 (3, "A8"), (6, "66")):
            with self.subTest(channel=channel), tempfile.TemporaryDirectory() as directory:
                env = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_ADC_CH")}
                env[f"MA17_ADC_CH{channel}"] = "40"
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", "1.5", "--no-kline-inject", "--crank-immediate",
                     "--output-dir", directory],
                    capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                report = json.loads((Path(directory) / "execution.json").read_text())
                self.assertEqual(report["adc_input_values"][channel], 40)
                changes = report["sensor_ram_observation"]
                self.assertEqual(changes[address][-1]["after"], "28")
                self.assertEqual(changes[address][-1]["source_pc"], "0744")
                if channel == 1:
                    self.assertEqual(report["engine_ram_observation"]["7D"][-1]
                                     ["source_pc"], "404B")
                if channel == 3:
                    self.assertEqual(changes["63"][-1]["after"], "28")
                    self.assertEqual(changes["63"][-1]["source_pc"], "4756")

    def test_temperature_adc10_stimuli_reach_distinct_firmware_bytes(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        with tempfile.TemporaryDirectory() as directory:
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                          "MA17_OVERRIDE_"))}
            env.update(MA17_ADC_CH2="40", MA17_ADC_CH3="40",
                       MA17_ADC10_CH2="321", MA17_ADC10_CH3="642",
                       MA17_ADC_CH7="63")
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--seconds", "8", "--stop-ticks", "2400000", "--rpm", "1000",
                 "--no-kline-inject", "--crank-immediate", "--output-dir", directory],
                capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads((Path(directory) / "execution.json").read_text())
            self.assertEqual(report["adc_10bit_input_values"][2:4], [321, 642])
            self.assertEqual(report["adc_input_values"][2:4], [80, 160])
            changes = report["sensor_ram_observation"]
            self.assertEqual(changes["62"][-1]["after"], "50")
            self.assertEqual(changes["63"][-1]["after"], "A1")
            self.assertEqual(changes["62"][-1]["source_pc"], "0744")
            self.assertEqual(changes["63"][-1]["source_pc"], "4756")

    def test_coolant_adc_step_preserves_raw_channel_and_preprocessing_boundary(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        firmwares = (ROOT / "FiatTipo_MA17_dump_27c256.bin",
                     ROOT / "firmwares_modificados_ma17_tipo" /
                     "tipo 1.6 alcool27c256 SUN 8817.bin")
        for firmware in firmwares:
            observations = {}
            for final_adc3, processed in ((204, "33"), (208, "11")):
                with self.subTest(firmware=firmware.name, final_adc3=final_adc3), \
                        tempfile.TemporaryDirectory() as directory:
                    env = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                                  "MA17_ADC10_STEP_CH", "MA17_OVERRIDE_"))}
                    env.update(MA17_ADC10_CH2="400", MA17_ADC10_CH3="160",
                               MA17_ADC10_STEP_CH3=f"800000:{final_adc3}",
                               MA17_ADC_CH7="63")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                         "--firmware", str(firmware), "--seconds", "15",
                         "--stop-ticks", "2400000", "--rpm", "1000", "--trace-movc",
                         "--no-kline-inject", "--crank-immediate",
                         "--output-dir", directory],
                        capture_output=True, text=True, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    report = json.loads((Path(directory) / "execution.json").read_text())
                    self.assertEqual(report["firmware_sha256"],
                                     hashlib.sha256(firmware.read_bytes()).hexdigest())
                    self.assertEqual(report["adc_10bit_step_sequences"][3],
                                     [{"tick": 800000, "value": final_adc3}])
                    changes = report["sensor_ram_observation"]
                    self.assertEqual(changes["A8"][-1]["after"], f"{final_adc3 >> 2:02X}")
                    self.assertEqual(changes["A8"][-1]["source_pc"], "0744")
                    self.assertEqual(changes["63"][-1]["after"], processed)
                    self.assertEqual(changes["63"][-1]["source_pc"], "4756")
                    self.assertEqual(changes["62"][-1]["after"], "64")
                    self.assertEqual(changes["62"][-1]["source_pc"], "0744")
                    selected = {row["mapped"] for row in report["movc_observation"]["reads"]
                                if row["pc"] == "52A2"}
                    self.assertEqual("73D8" in selected, final_adc3 == 204)
                    observations[final_adc3] = report
            self.assertEqual(observations[204]["engine_ram_observation"]["4E"][-1]
                             ["after"], "42")
            self.assertEqual(observations[208]["engine_ram_observation"]["4E"][-1]
                             ["after"], "00")
            self.assertGreater(observations[204]["cc3_observation"]["iram14_15_median"],
                               observations[208]["cc3_observation"]["iram14_15_median"])

    def test_air_gate_report_counts_original_firmware_decisions(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        with tempfile.TemporaryDirectory() as directory:
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("MA17_ADC_CH", "MA17_ADC10_CH",
                                          "MA17_OVERRIDE_"))}
            env.update(MA17_TRACE_AIR_716C_GATE="1", MA17_ADC_CH7="63")
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                 "--seconds", "8", "--stop-ticks", "400000", "--rpm", "1000",
                 "--no-kline-inject", "--crank-immediate", "--output-dir", directory],
                capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads((Path(directory) / "execution.json").read_text())
            gate = report["air_gate_observation"]
            self.assertTrue(gate["enabled"])
            self.assertGreater(gate["pc_counts"]["3CB7"], 0)
            self.assertGreater(gate["pc_counts"]["3D0C"], 0)
            self.assertEqual(gate["2e6_set_at_3cb7"], 0)
            self.assertEqual(gate["r2_below_6f_at_3cb7"], 0)
            self.assertEqual(gate["carry_set_at_3d0c"], 0)
            self.assertFalse(gate["sample_limit_reached"])

    def test_battery_adc_changes_timer1_output_path(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        firmware = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
        self.assertEqual(int.from_bytes(firmware[0x70AA:0x70AC], "big"), 0x7B32)
        self.assertEqual(int.from_bytes(firmware[0x70AC:0x70AE], "big"), 0x7B3E)
        self.assertEqual(firmware[0x7B32], 0x47)
        self.assertEqual(firmware[0x7B3E], 0x7D)
        reports = {}
        for adc1 in (40, 130):
            with tempfile.TemporaryDirectory() as directory:
                env = {key: value for key, value in os.environ.items()
                       if not key.startswith("MA17_ADC_CH")}
                env.update(MA17_ADC_CH1=str(adc1), MA17_ADC_CH7="63")
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", "2", "--rpm", "1000", "--no-kline-inject",
                     "--crank-immediate", "--output-dir", directory],
                    capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                reports[adc1] = json.loads((Path(directory) / "execution.json").read_text())
        low, normal = reports[40], reports[130]
        self.assertEqual(low["sensor_ram_observation"]["61"][-1]["after"], "28")
        self.assertEqual(normal["sensor_ram_observation"]["61"][-1]["after"], "82")
        for address in ("7D", "31", "34"):
            self.assertNotEqual(low["engine_ram_observation"][address][-1]["after"],
                                normal["engine_ram_observation"][address][-1]["after"])
        self.assertGreater(low["output_latches"]["P5.0"]["median_low_width_ticks"],
                           2 * normal["output_latches"]["P5.0"]
                           ["median_low_width_ticks"])

    def test_tps_tracks_change_derived_scanner_bytes(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        scenarios = (("baseline", {}, ("27", "0D")),
                     ("track2", {0: 40}, ("52", "1B")),
                     ("track1", {6: 180}, ("A7", "37")),
                     ("both_low", {0: 40, 6: 40}, ("27", "0D")),
                     ("both_high", {0: 180, 6: 180}, ("27", "0D")))
        for name, overrides, expected in scenarios:
            with tempfile.TemporaryDirectory() as directory:
                env = {key: item for key, item in os.environ.items()
                       if not key.startswith("MA17_ADC_CH")}
                env["MA17_ADC_CH7"] = "63"
                env.update({f"MA17_ADC_CH{channel}": str(value)
                            for channel, value in overrides.items()})
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", "1.2", "--no-kline-inject", "--crank-immediate",
                     "--output-dir", directory], capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                report = json.loads((Path(directory) / "execution.json").read_text())
                changes = report["sensor_ram_observation"]
                self.assertEqual(tuple(changes[address][-1]["after"]
                                       for address in ("6F", "70")), expected, name)
                self.assertEqual(changes["70"][-1]["source_pc"], "11D1")
                self.assertEqual(changes["6F"][-1]["source_pc"], "11D4")
                flow = (Path(directory) / "emulator-trace.log").read_text()
                if name in ("baseline", "both_low", "both_high"):
                    self.assertTrue(any("PC=1175" in line and "R4=34" in line and
                                        "RAM28=06" in line and "DPTR=7200" in line
                                        for line in flow.splitlines()), name)
                    fault = report["fault_xram_observation"]
                    self.assertEqual(fault["F885"][-1]["after"], "06")
                    self.assertEqual(fault["F885"][-1]["source_pc"], "41F7")
                    self.assertEqual(fault["F84F"][-1]["after"], "06")
                    self.assertEqual(fault["F84F"][-1]["source_pc"], "4200")
                else:
                    self.assertNotIn("F84F", report["fault_xram_observation"])

    def test_crank_rpm_scales_firmware_capture_and_p5_period(self):
        if not (ROOT / "build" / "emu8051-tty").exists():
            self.skipTest("build/emu8051-tty is required for dynamic firmware test")
        for rpm, duration, rpm_byte, period in ((750, 2, "1E", 79200),
                                                (2000, 1.2, "50", 29700)):
            with self.subTest(rpm=rpm), tempfile.TemporaryDirectory() as directory:
                env = dict(os.environ, MA17_ADC_CH7="63")
                result = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--seconds", str(duration), "--rpm", str(rpm),
                     "--no-kline-inject", "--crank-immediate",
                     "--output-dir", directory],
                    capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                report = json.loads((Path(directory) / "execution.json").read_text())
                self.assertEqual(report["crank_target_rpm"], rpm)
                wheel = report["wheel_observation"]
                self.assertGreater(wheel["complete_revolutions"], 0)
                self.assertEqual(wheel["teeth_per_revolution"], [58])
                self.assertEqual(wheel["gaps_per_revolution"], [2])
                self.assertEqual(wheel["ticks_per_tooth"], [990000 // rpm])
                self.assertTrue(any(change["after"] == rpm_byte for change in
                                    report["rpm_observation"]["ram47_changes"]))
                for channel in ("P5.0", "P5.1"):
                    self.assertAlmostEqual(
                        report["output_latches"][channel]["median_period_ticks"],
                        period, delta=1000)
                self.assertTrue(report["output_latches"]["sequence"]["alternating"])
                cc3 = report["cc3_observation"]
                self.assertGreater(cc3["cc3_pin_model_paired_pulses"], 0)
                self.assertAlmostEqual(cc3["cc3_pin_model_median_period_ticks"],
                                       period / 2, delta=1000)
                self.assertLessEqual(
                    max(abs(value) for value in
                        cc3["cc3_pin_model_width_minus_4x_raw_range_ticks"]), 15)

    def test_modular_ma17_keeps_every_byte(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "modularize_ma17.py")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["roundtrip"], "PASS")
        self.assertEqual(report["mismatched_bytes"], 0)
        self.assertEqual(len(report["modules"]), 6)
        self.assertEqual((report["code_bytes"], report["data_bytes"],
                          report["unclassified_bytes"]), (23420, 4120, 5228))
        self.assertEqual([(item["start"], item["end"], item["bytes"])
                          for item in report["ambiguous_db_regions"]],
                         [("0x5269", "0x5278", 16), ("0x53DA", "0x5418", 63)])
        master = (ROOT / "build" / "ma17-analysis" / "modular" / "ma17.asm").read_text()
        self.assertEqual(master.count("$include"), 7)  # registers + six address modules
        kline = (ROOT / "build" / "ma17-analysis" / "modular" /
                 "02_kline_and_low_level_io.inc").read_text()
        self.assertIn("dispatch_kline_request_04_output_sequence:\n", kline)
        self.assertIn("stage_f5_command_04_progress_response:\n", kline)
        self.assertIn("\tljmp stage_f5_command_04_progress_response\n", kline)
        tables = (ROOT / "build" / "ma17-analysis" / "modular" /
                  "05_tables_and_calibration.inc").read_text()
        self.assertIn("fault_bit_indexed_triplet_table:\n", tables)
        for label in ("rpm47_segment_pointer", "battery_ratio7d_segment_pointer",
                      "rpm47_cumulative_segment_table",
                      "battery_ratio7d_cumulative_segment_table"):
            self.assertIn(f"{label}:\n", tables)
        self.assertIn("fault_bit_indexed_triplet_table:\ndptr_6E27:\n\tdb 0FFh", tables)
        fault_table = tables.split("fault_bit_indexed_triplet_table:\n", 1)[1].split(
            "kline_collection_table_1:", 1)[0]
        self.assertEqual(fault_table.count("\tdb "), 27)
        self.assertNotIn("org\t", fault_table)
        self.assertIn("db 002h, 006h, 01Fh\t; [6E4Bh] code_le16=0602h status=1Fh",
                      fault_table)
        self.assertIn("db 003h, 003h, 003h\t; [6E75h] code_le16=0303h status=03h",
                      fault_table)
        rom = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
        for offset in range(0x6E27, 0x6E78, 3):
            low, high, status = rom[offset:offset + 3]
            code = low | (high << 8)  # scanner errorPacketToString, lines 574-576
            self.assertIn(
                f"[{offset:04X}h] code_le16={code:04X}h status={status:02X}h",
                fault_table)
        self.assertEqual(rom[0x6E2D:0x6E30], bytes.fromhex("02 04 1E"))
        self.assertEqual(rom[0x6E3C:0x6E3F], bytes.fromhex("02 19 0B"))
        for address in ("6E27", "7109", "7163", "7FF5"):
            self.assertIn(f"dptr_{address}:\n\tdb 0FFh", tables)
        self.assertIn("kline_collection_table_1:", tables)

        self.assertIn("kline_collection_table_2:", tables)
        for start, end, label, next_label in (
                (0x6E78, 0x6E8C, "kline_collection_table_1:",
                 "kline_collection_table_2:"),
                (0x6E8C, 0x6EA0, "kline_collection_table_2:", "org\t7000h")):
            rows = tables.split(label, 1)[1].split(next_label, 1)[0]
            self.assertEqual(rows.count("\tdb "), 10)
            for address in range(start, end, 2):
                selector, location = rom[address:address + 2]
                mode = "IRAM" if selector == 0 else "MOVX"
                self.assertIn(
                    f"db 0{selector:02X}h, 0{location:02X}h\t; "
                    f"[{address:04X}h] mode={mode} address={location:02X}h "
                    f"selector={selector:02X}h", rows)
        kline = (ROOT / "build" / "ma17-analysis" / "modular" /
                 "02_kline_and_low_level_io.inc").read_text()
        self.assertIn("#kline_collection_table_1", kline)
        self.assertIn("#kline_collection_table_2", kline)
        engine = (ROOT / "build" / "ma17-analysis" / "modular" /
                  "01_boot_and_engine_control.inc").read_text()
        self.assertIn("derive_iram31_from_rpm47_battery_ratio7d:", engine)
        self.assertIn("mov DPTR, #battery_ratio7d_segment_pointer", engine)
        self.assertIn("update_cc3_guard_from_xram_dd:", engine)
        self.assertIn("gate_r4_r2_by_iram63_70_47:\njump_4095:", engine)
        self.assertIn("copy_fault_triplet_indexed_by_r3_r7:\njump_4329:", engine)
        self.assertIn("copy_fault_triplet_indexed_by_r6_r7_mark_bit7:\njump_44BB:", engine)
        self.assertIn("cjne R4, #01h, jump_44CE", engine)
        self.assertIn("\tsetb ACC.7\n", engine)
        self.assertEqual(engine.count("mov DPTR, #fault_bit_indexed_triplet_table"), 2)
        self.assertIn("compare_xram_byte_with_rom_and_flag_mismatch:", engine)
        self.assertEqual(engine.count("lcall copy_rom_byte_at_dptr_to_xram_r0"), 10)
        self.assertEqual(engine.count("lcall interpolate_adjacent_code_table_bytes"), 23)
        self.assertEqual(engine.count("lcall xor_xram_r0_with_rom_dptr"), 9)
        interrupts = (ROOT / "build" / "ma17-analysis" / "modular" /
                      "00_interrupts_and_timer_control.inc").read_text()
        for alias in ("reset_vector_to_0850", "ext0_decrement_iram6b_skip_zero",
                      "timer0_vector_to_0630", "timer1_vector_to_p5_toggle",
                      "serial0_disable_es0_set_s0con70", "timer2_vector_begin_service",
                      "clear_tf2_enable_eal_reti", "iex3_vector_to_00b0",
                      "iex5_vector_to_05e4_bank0", "iex6_vector_p13_ccen_service"):
            self.assertIn(alias + ":", interrupts)
        self.assertIn("iex3_capture_sync_state_machine:", interrupts)
        self.assertIn("ljmp iex3_capture_sync_state_machine", interrupts)
        self.assertEqual(interrupts.count("lcall service_serial0_state_machine_from_xram"), 1)
        self.assertIn("timer0_vector_to_0630:\n\torl TH0, #0F8h", interrupts)
        self.assertIn("iex5_vector_to_05e4_bank0:\n\tpush PSW", interrupts)
        for alias, address in (("shared_reti_at_035d", "035D"),
                               ("shared_reti_at_084f", "084F")):
            self.assertEqual(interrupts.count("lcall " + alias), 1)
            self.assertIn(alias + ":\njump_" + address + ":\n\treti", interrupts)
        self.assertEqual(interrupts.count("acall lookup_tf0_adc_pattern_by_r6_nibble"), 1)
        self.assertIn("lookup_tf0_adc_pattern_by_r6_nibble:\n", interrupts)
        self.assertEqual(interrupts.count("lcall capture_timer2_elapsed_to_iram"), 6)
        arithmetic = (ROOT / "build" / "ma17-analysis" / "modular" /
                      "03_arithmetic_and_memory.inc").read_text()
        self.assertIn("ambiguous DB 5269h..5278h", arithmetic)
        self.assertIn("ambiguous DB 53DAh..5418h", arithmetic)
        self.assertIn("capture_timer2_elapsed_to_iram:", arithmetic)
        self.assertIn("xor_xram_r0_with_rom_dptr:", arithmetic)
        self.assertIn("accumulate_signed_sample_and_check_thresholds:", arithmetic)
        self.assertEqual(engine.count("lcall accumulate_signed_sample_and_check_thresholds"), 6)
        self.assertEqual(engine.count("lcall copy_xram_r1_to_xram_r0_count_r6"), 6)
        self.assertIn("copy_xram_r1_to_xram_r0_count_r6:", arithmetic)
        self.assertIn("find_table_segment_from_be_pointer:", arithmetic)
        self.assertIn("find_cumulative_table_segment_and_fraction:", arithmetic)
        self.assertEqual(engine.count("lcall find_table_segment_from_be_pointer"), 12)
        self.assertEqual(arithmetic.count("lcall find_cumulative_table_segment_and_fraction"), 1)
        self.assertEqual(engine.count("lcall interpolate_cumulative_table_from_be_pointer"), 6)
        self.assertIn("interpolate_cumulative_table_from_be_pointer:", arithmetic)
        for alias, calls in (("find_table_segment_index_from_be_pointer", 2),
                             ("interpolate_rom_pair_from_packed_a", 9),
                             ("clear_r4_then_interpolate_indexed_code_table", 3),
                             ("interpolate_indexed_code_table_using_r4", 3),
                             ("interpolate_rom_table_from_be_pointer", 9)):
            self.assertEqual(engine.count("lcall " + alias), calls)
            self.assertIn(alias + ":", arithmetic)
        self.assertEqual(engine.count("lcall compute_min_copy_count_for_xram_00_40"), 2)
        self.assertEqual(engine.count("lcall compute_min_copy_count_for_xram_7f_40"), 2)
        self.assertIn("compute_min_copy_count_for_xram_00_40:", engine)
        self.assertIn("compute_min_copy_count_for_xram_7f_40:", engine)
        for alias in ("set_2c2_217_then_multiply_iram5b",
                      "multiply_iram5b_by_32_to_r5r4",
                      "classify_xram_r1_against_rom_thresholds_6a_6b"):
            self.assertEqual(engine.count("lcall " + alias), 2)
            self.assertIn(alias + ":", engine)
        self.assertEqual(engine.count("lcall dispatch_xram_c8_state_1_to_8"), 1)
        self.assertIn("dispatch_xram_c8_state_1_to_8:", engine)
        for alias in ("initialize_xram_ac_af_pattern_when_t2i1_clear",
                      "interpolate_rom_pair_from_packed_r5",
                      "test_xram_r1_through_b_with_55_aa",
                      "test_xram_range_55aa_preserve_with_fe_ff",
                      "load_dptr_7200_via_jump"):
            self.assertEqual(engine.count("lcall " + alias), 1)
        self.assertIn("interpolate_rom_pair_from_packed_r5:", arithmetic)
        self.assertIn("test_xram_r1_through_b_with_55_aa:", arithmetic)
        self.assertIn("test_xram_range_55aa_preserve_with_fe_ff:", arithmetic)
        self.assertIn("load_dptr_7200_via_jump:", arithmetic)
        self.assertEqual(engine.count("lcall load_dptr_from_be_pointer_table_index_iram57"), 1)
        self.assertEqual(arithmetic.count("lcall load_dptr_from_be_pointer_table_index_iram57"), 1)
        self.assertIn("load_dptr_from_be_pointer_table_index_iram57:", arithmetic)
        self.assertEqual(engine.count("lcall compute_q8_ratio_a_over_r5"), 3)
        self.assertIn("compute_q8_ratio_a_over_r5:", arithmetic)
        self.assertEqual(engine.count("lcall divide_u16_a_r3_by_r4_r5_eight_steps"), 2)
        self.assertEqual(engine.count("lcall restoring_divide_with_r1_steps"), 1)
        self.assertIn("divide_u16_a_r3_by_r4_r5_eight_steps:", arithmetic)
        self.assertIn("restoring_divide_with_r1_steps:", arithmetic)
        for alias, calls in (("decrement_xram3e_unless_205_and_update_iram1f", 3),
                             ("update_packed_xram_r0_state_from_r2", 5),
                             ("write_xram3e_and_set_r0_low_nibble", 3),
                             ("adjust_xram_r1_using_rom_offset25", 2),
                             ("clear_r4_then_update_xram24", 4),
                             ("update_xram24_by_r4r3r2_and_flags", 1),
                             ("scale_a_by_rom_offset0f_shr4_saturate", 1),
                             ("consume_up_to_five_xram3e_into_iram1f", 2),
                             ("select_packed_table_indices_from_xram91_or_iram4e", 3),
                             ("compare_xram_r0_to_rom_bound_reversed_subtraction", 3),
                             ("test_xram_range_55aa_r0_to_b", 3),
                             ("test_xram_block_55aa_count_r6", 2),
                             ("subtract_r0_from_a_floor_zero_and_set_f0", 4)):
            self.assertEqual(engine.count("lcall " + alias), calls)
            self.assertIn(alias + ":", arithmetic)
        self.assertEqual(engine.count("lcall adjust_r2_by_bounded_rom_delta"), 2)
        self.assertEqual(engine.count("lcall scale_u16_r3r2_by_rom_offsetbc_round_q8"), 1)
        self.assertEqual(arithmetic.count("lcall scale_u16_r3r2_by_rom_offsetbc_round_q8"), 1)
        self.assertIn("adjust_r2_by_bounded_rom_delta:", arithmetic)
        self.assertIn("scale_u16_r3r2_by_rom_offsetbc_round_q8:", arithmetic)
        self.assertEqual(engine.count("lcall set_flags_and_load_rom_offset14_to_iram5e"), 7)
        self.assertEqual(engine.count("lcall compare_xram_r0_to_rom_bound_by_sign"), 6)
        self.assertIn("set_flags_and_load_rom_offset14_to_iram5e:", arithmetic)
        self.assertIn("compare_xram_r0_to_rom_bound_by_sign:", arithmetic)
        kline = (ROOT / "build" / "ma17-analysis" / "modular" /
                 "02_kline_and_low_level_io.inc").read_text()
        self.assertIn("initialize_xram_ac_af_pattern_when_t2i1_clear:", kline)
        self.assertIn("service_serial0_state_machine_from_xram:", kline)
        self.assertEqual(kline.count("lcall enter_diagnostic_mode_after_slow_baud_guard"), 1)
        self.assertIn("clear_xram_b0_cc_and_write_02_18_header:", kline)
        self.assertEqual(kline.count("lcall clear_xram_b0_cc_and_write_02_18_header"), 1)
        self.assertIn("clear_error_state_xram_on_command_05:", kline)
        self.assertEqual(kline.count("lcall clear_error_state_xram_on_command_05"), 1)
        self.assertEqual(kline.count("lcall write_xram_pair_r2_r3_at_r1"), 5)
        self.assertIn("write_xram_pair_r2_r3_at_r1:", kline)
        for alias, calls in (("stop_serial0_and_store_session_status", 5),
                             ("copy_rom_to_xram_after_r1_count_r4", 2),
                             ("update_serial_timeout_c8_and_event_ca", 1),
                             ("mask_upper_iram8a_to_bit0", 1),
                             ("copy_iram_r1_to_xram_r0_when_t2i1_clear", 4),
                             ("clear_xram_c8_event_and_mask_iram8a", 4)):
            self.assertEqual(kline.count("lcall " + alias), calls)
            self.assertIn(alias + ":", kline)
        diagnostics = (ROOT / "build" / "ma17-analysis" / "modular" /
                       "04_diagnostics_and_adc.inc").read_text()
        self.assertIn("enter_diagnostic_mode_after_slow_baud_guard:", diagnostics)
        for alias in ("accumulate_rom32_to_iram3b3a_if_227",
                      "pack_port_bits_and_226_into_iram_r1"):
            self.assertEqual(diagnostics.count("lcall " + alias), 1)
        self.assertIn("pack_port_bits_and_226_into_iram_r1:", diagnostics)
        self.assertIn("accumulate_rom32_to_iram3b3a_if_227:", arithmetic)
        self.assertEqual(diagnostics.count("lcall diagnostic_mirror_p1_p4_inputs_to_outputs"), 6)
        self.assertIn("diagnostic_mirror_p1_p4_inputs_to_outputs:", diagnostics)
        self.assertEqual(kline.count("lcall copy_xram_r0_to_iram_r1_count_r5"), 3)
        self.assertIn("copy_xram_r0_to_iram_r1_count_r5:", kline)
        self.assertEqual(arithmetic.count("lcall multiply_i8_a_by_u8_b_to_i16_ab"), 3)
        self.assertEqual(engine.count("lcall multiply_i8_a_by_u8_b_to_i16_ab"), 1)
        self.assertIn("multiply_i8_a_by_u8_b_to_i16_ab:", arithmetic)
        self.assertEqual(diagnostics.count("lcall diag_guard_marker57_sp_and_disable_ea"), 3)
        self.assertEqual(diagnostics.count("lcall copy_rom_to_iram13_with_diag_guard"), 3)
        for alias, calls in (("prepare_diag_response_buffer_by_state", 3),
                             ("configure_timer2_d8ef_for_diag_mode", 1),
                             ("test_xram_pages_f8_to_fb_with_aa55", 1),
                             ("set_diag_state5_and_prepare_buffer", 1),
                             ("delay_a_loops_toggle_p57_and_feed_watchdog", 3),
                             ("clear_diag_flag215_on_serial_timer_window", 2)):
            self.assertEqual(diagnostics.count("lcall " + alias), calls)
            self.assertIn(alias + ":", diagnostics)
        self.assertIn("diag_guard_marker57_sp_and_disable_ea:", diagnostics)
        self.assertIn("copy_rom_to_iram13_with_diag_guard:", diagnostics)
        self.assertEqual(interrupts.count("lcall compare_half_interval54_55_to_52_53"), 4)
        self.assertEqual(interrupts.count("lcall compare_half_interval52_53_to_54_55"), 2)
        self.assertEqual(interrupts.count("lcall save_timer2_capture_triplet_to_iram_r1"), 2)
        self.assertIn("save_timer2_capture_triplet_to_iram_r1:", arithmetic)
        self.assertIn("compare_half_interval54_55_to_52_53:", arithmetic)
        self.assertIn("compare_half_interval52_53_to_54_55:", arithmetic)

    def test_fault_triplet_grouping_rejects_missing_source_byte(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from modularize_ma17 import group_fault_triplets, group_sensor_pairs
        firmware = ROOT / "FiatTipo_MA17_dump_27c256.bin"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(SCRIPT), str(firmware),
                                     "--output-dir", directory], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            source = (Path(directory) /
                      "FiatTipo_MA17_dump_27c256.disasm51.asm").read_text()
        line = next(line for line in source.splitlines() if "[6E29h]" in line)
        with self.assertRaisesRegex(ValueError, "missing/extra bytes"):
            group_fault_triplets(source.replace(line + "\n", "", 1),
                                 firmware.read_bytes())
        line = next(line for line in source.splitlines() if "[6E79h]" in line)
        with self.assertRaisesRegex(ValueError, "missing/extra bytes"):
            group_sensor_pairs(source.replace(line + "\n", "", 1),
                               firmware.read_bytes(), 0x6E78, 0x6E8C, "dptr_6E8C:")

    def test_modular_assembly_edits_change_only_selected_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generated = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "modularize_ma17.py"),
                 "--output-dir", directory], capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stderr + generated.stdout)
            edits = (
                ("01_boot_and_engine_control.inc",
                 "jump_0850:\n\tmov WDTREL, #0F3h",
                 "jump_0850:\n\tmov WDTREL, #0F2h"),
                ("05_tables_and_calibration.inc",
                 "db 002h, 006h, 01Fh\t; [6E4Bh]",
                 "db 002h, 006h, 01Eh\t; [6E4Bh]"),
                ("05_tables_and_calibration.inc",
                 "db 000h, 063h\t; [6E78h]",
                 "db 000h, 064h\t; [6E78h]"),
            )
            for filename, before, after in edits:
                path = output / filename
                contents = path.read_text()
                self.assertEqual(contents.count(before), 1)
                path.write_text(contents.replace(before, after, 1))
            assembled = subprocess.run(
                [str(ROOT / "asm51" / "asm51"), "-n", "-f", "bin", "-o",
                 "edited.bin", "ma17.asm"], cwd=output, capture_output=True, text=True)
            self.assertEqual(assembled.returncode, 0, assembled.stderr)
            original = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
            edited = (output / "edited.bin").read_bytes()
            self.assertEqual(len(edited), len(original))
            self.assertEqual([i for i, pair in enumerate(zip(original, edited))
                              if pair[0] != pair[1]], [0x0852, 0x6E4D, 0x6E79])
            self.assertEqual((edited[0x0852], edited[0x6E4D], edited[0x6E79]),
                             (0xF2, 0x1E, 0x64))

    def test_scanner_collection_tables_match_rom(self):
        rom = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
        table1 = bytes.fromhex("00 63 00 66 00 47 00 62 F8 0C F8 6C F8 6F F8 3D 00 61 F8 69")
        table2 = bytes.fromhex("00 63 00 66 00 70 00 2F F8 72 F8 6C F8 6F F8 40 00 61 F8 69")
        self.assertEqual(rom[0x6E78:0x6E8C], table1)
        self.assertEqual(rom[0x6E8C:0x6EA0], table2)

    def test_ida_inventory_is_tied_to_firmware_hash(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "inventory_ma17.py")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        inventory = json.loads((ROOT / "build" / "ma17-analysis" / "inventory.json").read_text())
        rom = (ROOT / "FiatTipo_MA17_dump_27c256.bin").read_bytes()
        self.assertEqual(inventory["rom_sha256"], hashlib.sha256(rom).hexdigest())
        self.assertEqual(inventory["metrics"]["unresolved_references"], 0)
        loads = inventory["dptr_immediate_loads"]
        self.assertEqual(inventory["metrics"]["dptr_immediate_loads"], len(loads))
        self.assertEqual(inventory["metrics"]["data_bytes"], 4117)
        self.assertEqual(inventory["metrics"]["unclassified_bytes"], 5231)
        pc_movc = [int(row["address"], 16) for row in inventory["instructions"]
                   if row["mnemonic"] == "movc" and
                   "@A+PC" in row["operands"].upper()]
        self.assertEqual(pc_movc, [0x06E1, 0x1304, 0x57A9])
        self.assertEqual(inventory["metrics"]["pc_relative_movc_sites"], len(pc_movc))
        self.assertTrue(all(rom[int(region["start"], 16):int(region["end"], 16) + 1]
                            == bytes.fromhex("ff") * region["bytes"]
                            for region in inventory["unclassified_regions"]))
        table_load = next(row for row in loads if row["site"] == "0x4E92")
        self.assertEqual(table_load["value"], "0x6E78")
        self.assertEqual(table_load["target_class"], "data")
        self.assertFalse({"0x326B", "0x5269", "0x53DA", "0x56B9"}
                         & {row["value"] for row in loads})
        functions = inventory["functions"]
        confirmed = {item["semantic_alias"] for item in functions
                     if item["confidence"] == "confirmed_code"}
        self.assertIn("write_xram_b8_triplet", confirmed)
        self.assertIn("multiply_u16_r3r2_by_u8_a", confirmed)
        self.assertIn("interpolate_adjacent_code_table_bytes", confirmed)
        self.assertEqual(inventory["metrics"]["functions_with_confirmed_code_alias"],
                         len(confirmed))
        self.assertEqual(inventory["metrics"]["functions_unreviewed"],
                         sum(item["confidence"] == "unreviewed" for item in functions))
        erased = {item["address"] for item in functions
                  if item["confidence"] == "confirmed_erased"}
        self.assertEqual(erased, {"0x0013", "0x004B", "0x005B", "0x0083"})
        self.assertEqual(inventory["metrics"]["functions_erased_slots"], 4)
        self.assertTrue(all(item["flow_reachable_instruction_starts"] == 0
                            for item in functions if item["address"] in erased))

    def test_branches_data_and_erased_tail(self):
        rom = bytearray([0xFF] * 64)
        rom[:3] = bytes([0x02, 0x00, 0x10])  # LJMP 0010h
        rom[0x10:0x19] = bytes([0x74, 0x03, 0xB4, 0x03, 0x02,
                                0xD8, 0xFE, 0x01, 0x20])
        rom[0x20:0x24] = bytes([0x11, 0x30, 0x80, 0xFE])  # ACALL, SJMP
        rom[0x30] = 0x22  # RET; final byte of ROM stays erased
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "branches.bin"
            firmware.write_bytes(rom)
            report, assembly = self.run_roundtrip(firmware)
        self.assertEqual(report["original_size"], 64)
        self.assertIn("ajmp", assembly)
        self.assertIn("acall", assembly)
        self.assertIn("cjne", assembly)
        self.assertIn("djnz", assembly)
        self.assertIn("db 0FFh", assembly)

    def test_indirect_big_endian_words(self):
        rom = bytearray([0xFF] * 64)
        rom[:3] = bytes([0x02, 0x00, 0x10])
        rom[0x10:0x14] = bytes([0x90, 0x00, 0x20, 0x73])  # DPTR; JMP @A+DPTR
        rom[0x20:0x24] = bytes([0x00, 0x30, 0x00, 0x34])
        rom[0x30] = rom[0x34] = 0x22
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "indirect.bin"
            firmware.write_bytes(rom)
            report, assembly = self.run_roundtrip(firmware, "--indirect", "0x20:0x24")
        self.assertEqual(report["original_size"], 64)
        self.assertIn("dw", assembly)
        self.assertIn("jmp @A + DPTR", assembly)

    def test_labeled_erased_data_byte_is_editable(self):
        rom = bytearray([0xFF] * 64)
        rom[:3] = bytes([0x02, 0x00, 0x10])
        rom[0x10:0x15] = bytes([0x90, 0x00, 0x20, 0x93, 0x22])
        rom[0x21] = 0x42
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "labeled_ff.bin"
            firmware.write_bytes(rom)
            report, assembly = self.run_roundtrip(firmware)
        self.assertEqual(report["roundtrip"], "PASS")
        self.assertIn("dptr_0020:\n\tdb 0FFh", assembly)
        self.assertIn("\tdb 0FFh\t; [0020h]", assembly)
        self.assertIn("\tdb 42h\t; [0021h]", assembly)

    def test_page_jump_and_mov_direct_operand_order(self):
        rom = bytearray([0xFF] * 0x830)
        rom[:3] = bytes([0x02, 0x07, 0xFE])
        rom[0x7FE:0x800] = bytes([0x01, 0x12])  # AJMP 0812h, next page
        rom[0x812:0x817] = bytes([0x85, 0x20, 0x21, 0x80, 0xFE])
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "page.bin"
            firmware.write_bytes(rom)
            _, assembly = self.run_roundtrip(firmware)
        self.assertIn("mov 21h, 20h", assembly)
        self.assertIn("ajmp", assembly)

    def test_disassembler_offset_maps_absolute_target_to_rom(self):
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory) / "mapped.bin"
            firmware.write_bytes(bytes([0x02, 0x01, 0x06, 0xFF, 0xFF, 0xFF, 0x22]))
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(ROOT / "disasm51" / "src")
            result = subprocess.run(
                [str(ROOT / ".venv" / "bin" / "disasm51"), "--offset", "0x100",
                 str(firmware)], capture_output=True, text=True, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("jump_0006:", result.stdout)
        self.assertIn("ljmp jump_0006", result.stdout)


if __name__ == "__main__":
    unittest.main()
