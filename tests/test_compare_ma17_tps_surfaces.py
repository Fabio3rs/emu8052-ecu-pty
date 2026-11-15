"""Synthetic comparison checks for matched TPS surface experiments."""

import copy
import unittest

from tools.compare_ma17_tps_surfaces import compare


class CompareTpsSurfacesTests(unittest.TestCase):
    def test_reports_one_changed_cell_and_rejects_mismatched_stimuli(self):
        base = {"variant": "G", "rom_sha256": "rom-g",
                "emulator_sha256": "emulator", "rpm": 1000,
                "stop_ticks": 4000000, "fixed_adc": {"2": 140},
                "adc_defaults_unset_channels": {},
                "adc0_values": [40], "adc6_values": [95, 235],
                "point_override": None,
                "cases": [
                    {"adc0": 40, "adc6": 95, "iram6f_hex": "52",
                     "header_reads": {"755C": 386, "7569": 0},
                     "alternative_branch_reached": False,
                     "alternate_formula_sample": None},
                    {"adc0": 40, "adc6": 235, "iram6f_hex": "1B",
                     "header_reads": {"755C": 1, "7569": 385},
                     "alternative_branch_reached": True,
                     "alternate_formula_sample": {"r2": "28", "r3": "1A",
                                                  "value": "1B", "ram28": "00",
                                                  "formula_matches": True}}]}
        other = copy.deepcopy(base)
        other["variant"] = "S88"
        other["rom_sha256"] = "rom-s88"
        other["cases"][1]["iram6f_hex"] = "1C"
        result = compare(base, other)
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["matching_cases_by_field"]["iram6f_hex"], 1)
        self.assertEqual(result["differences"][0]["adc6"], 235)
        other["stop_ticks"] = 2000000
        with self.assertRaises(ValueError):
            compare(base, other)


if __name__ == "__main__":
    unittest.main()
