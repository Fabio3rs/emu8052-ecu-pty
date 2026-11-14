"""Checks for structured comparison of controlled MA1.7 trace reports."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_ma17_variant_experiments import (experiment_environment, last_value,
                                          summarize)


class VariantExperimentTests(unittest.TestCase):
    def test_temperature_grid_does_not_inherit_overrides(self):
        inherited = {"MA17_ADC_CH2": "247", "MA17_ADC10_CH3": "1023",
                     "MA17_ADC10_STEP_CH2": "200000:160",
                     "MA17_OVERRIDE_RAM57": "1", "MA17_KEEP_TEST": "yes"}
        with patch.dict(os.environ, inherited):
            environment = experiment_environment({2: 20, 7: 63})
        self.assertEqual(environment["MA17_ADC_CH2"], "20")
        self.assertEqual(environment["MA17_ADC_CH7"], "63")
        self.assertNotIn("MA17_ADC10_CH3", environment)
        self.assertNotIn("MA17_ADC10_STEP_CH2", environment)
        self.assertNotIn("MA17_OVERRIDE_RAM57", environment)
        self.assertEqual(environment["MA17_KEEP_TEST"], "yes")

    def test_counterfactual_interventions_are_reported(self):
        emulator = ROOT / "build" / "emu8051-tty"
        if not emulator.is_file():
            self.skipTest("build the emulator before running the integration test")
        cases = (("MA17_OVERRIDE_RPM_SELECTOR", "rpm_selector_override_hex",
                  "15", "[RPM-SELECTOR-OVERRIDE] RAM47=28 BC=15"),
                 ("MA17_OVERRIDE_RAM69", "ram69_override_hex",
                  "89", "[RAM69-OVERRIDE] RAM47=28 RAM69=89"),
                 ("MA17_OVERRIDE_RAM31", "ram31_override_hex",
                  "50", "[RAM31-OVERRIDE] RAM47=28 RAM31=50"))
        for variable, report_key, value, marker in cases:
            with self.subTest(variable=variable), tempfile.TemporaryDirectory() as directory:
                environment = os.environ.copy()
                environment[variable] = value
                process = subprocess.run(
                    [sys.executable, str(ROOT / "tools" / "trace_ma17.py"),
                     "--no-kline-inject", "--crank-immediate", "--rpm", "1000",
                     "--stop-ticks", "350000", "--seconds", "10",
                     "--output-dir", directory],
                    cwd=ROOT, env=environment, capture_output=True, text=True,
                    timeout=20, check=False)
                self.assertEqual(process.returncode, 0, process.stderr)
                report = json.loads((Path(directory) / "execution.json").read_text())
                self.assertEqual(report["emulator_sha256"], hashlib.sha256(
                    emulator.read_bytes()).hexdigest())
                log = (Path(directory) / "emulator-trace.log").read_text()
                self.assertEqual(report[report_key], value)
                self.assertTrue(marker in log, f"{variable} was not applied")

    def test_summary_preserves_ranges_and_measured_values(self):
        report = {
            "firmware_sha256": "a" * 64,
            "crank_target_rpm": 1000,
            "adc_input_values": [120, 40, 100, 80, 90, 110, 95, 105],
            "wheel_observation": {"complete_revolutions": 35},
            "output_latches": {"P5.0": {"median_low_width_ticks": 10334},
                               "P5.1": {"median_low_width_ticks": 10334}},
            "engine_ram_observation": {
                "31": [{"after": "10"}, {"after": "59"}],
                "4E": [{"after": "18"}],
                "78": [{"after": "F3"}],
                "7A": [{"after": "F7"}],
                "7C": [{"after": "C0"}],
                "7D": [{"after": "73"}]},
            "sensor_ram_observation": {
                "62": [{"after": "64"}], "63": [{"after": "50"}],
                "65": [{"after": "6E"}], "6F": [{"after": "53"}]},
            "cc3_observation": {"iram14_15_scheduling_samples": 5,
                                "iram14_15_median": 1514,
                                "cc3_pin_model_median_low_width_ticks": 6045},
            "injection_flow_observation": {"paired_checks": 8,
                                            "unchanged_r2r3_pairs": 7},
            "cc3_p5_phase_observation": {
                "cc3_low_after_p5_low_median_ticks": 1993},
            "movc_observation": {"total_reads": 12, "reads": [
                {"pc": "5289", "mapped": "7B45", "count": 7},
                {"pc": "532F", "mapped": "7B46", "count": 3},
                {"pc": "06E1", "mapped": "06E3", "count": 2}]},
        }
        self.assertIsNone(last_value(report, "69"))
        row = summarize(report, "adc1_40", "gasoline",
                        [(0x7B45, 0x7B46), (0x7B46, 0x7B47)])
        self.assertEqual(row["iram31"], "59")
        self.assertEqual(row["iram7d"], "73")
        self.assertEqual(row["iram7c"], "C0")
        self.assertEqual(row["iram4e"], "18")
        self.assertEqual((row["iram78"], row["iram7a"]), ("F3", "F7"))
        self.assertEqual(row["iram6f"], "53")
        self.assertEqual((row["iram62"], row["iram63"], row["iram65"]),
                         ("64", "50", "6E"))
        self.assertEqual((row["adc2"], row["adc3"]), (100, 80))
        self.assertEqual(row["cc3_scheduling_samples"], 5)
        self.assertEqual((row["injection_flow_pairs"],
                          row["injection_flow_unchanged_pairs"]), (8, 7))
        self.assertEqual(row["cc3_raw_iram14_15_median"], 1514)
        self.assertEqual(row["cc3_pin_low_width_median_ticks"], 6045)
        self.assertEqual(row["cc3_p5_phase_median_ticks"], 1993)
        self.assertEqual(row["matrix_7581_reads"], 0)
        self.assertEqual(row["p5_0_low_width_ticks"], 10334)
        self.assertEqual([item["movc_reads"] for item in row["changed_region_reads"]],
                         [7, 3])
        self.assertEqual(row["changed_region_reads"][0]["read_sites"], ["5289"])


if __name__ == "__main__":
    unittest.main()
