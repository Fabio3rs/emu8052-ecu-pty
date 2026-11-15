"""Check matrix plotting inputs against original ROM bytes."""

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compare_ma17_variants import EXPECTED, REFERENCE, VARIANTS
from plot_ma17_matrices import (PLOT_MATRICES, load_matrix, main,
                                ram47_axis_raw, rpm_axis_nominal,
                                second_axis_raw, summarize)


class MatrixPlotTests(unittest.TestCase):
    def test_cli_compares_two_banks_within_original_G(self):
        with tempfile.TemporaryDirectory() as directory:
            args = ["plot_ma17_matrices.py", "--reference-variant", "G",
                    "--reference-matrix", "0x7B46", "--matrix", "0x7BBE",
                    "--variant", "G", "--output-dir", directory]
            with mock.patch.object(sys, "argv", args), \
                    mock.patch("plot_ma17_matrices.render"), \
                    contextlib.redirect_stdout(io.StringIO()):
                main()
            summary = json.loads((Path(directory) /
                                  "matrix_7b46_g_vs_7bbe_g.json").read_text())
            self.assertEqual((summary["reference_variant"], summary["variant"]),
                             ("G", "G"))
            self.assertEqual(summary["changed_cells"], 118)
            self.assertTrue((Path(directory) /
                             "matrix_7b46_g_vs_7bbe_g.csv").exists())

    def test_six_adjacent_eight_by_fifteen_matrices_follow_verified_pointers(self):
        starts = (0x7B46, 0x7BBE, 0x7C36, 0x7CAE, 0x7D26, 0x7D9E)
        slots = (0x709C, 0x709E, 0x70A0, 0x70B6, 0x70B8, 0x70BA)
        for path in (REFERENCE, *(VARIANTS / name for name in EXPECTED)):
            with self.subTest(rom=path.name):
                image = path.read_bytes()
                self.assertEqual([int.from_bytes(image[slot:slot + 2], "big")
                                  for slot in slots], list(starts))
                self.assertEqual(image[0x70CE:0x70D0], b"\x7e\x16")
                for start in starts:
                    self.assertIn((start, 8, 15), PLOT_MATRICES)
                    values, _ = load_matrix(path, start, 8, 15)
                    self.assertEqual(len(values), 8)
                    self.assertEqual(sum(map(len, values)), 120)

    def test_alcohol_7bbe_flattens_raw_row_means(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7BBE, 8, 15)
        alcohol, _ = load_matrix(VARIANTS / EXPECTED[0], 0x7BBE, 8, 15)
        _, summary = summarize(gasoline, alcohol)
        self.assertEqual((summary["changed_cells"], summary["delta_min"],
                          summary["delta_max"]), (118, 0, 93))
        g_means = [sum(row) / 15 for row in gasoline]
        a_means = [sum(row) / 15 for row in alcohol]
        self.assertGreater(min(a_means), max(g_means))
        self.assertLess(max(a_means) - min(a_means),
                        max(g_means) - min(g_means))
        first_bank, _ = load_matrix(VARIANTS / EXPECTED[0], 0x7B46, 8, 15)
        self.assertEqual(summarize(first_bank, alcohol)[1]["changed_cells"], 88)

    def test_7cae_s88_and_s37_keep_shape_with_uniform_offsets(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7CAE, 8, 15)
        s88, _ = load_matrix(VARIANTS / EXPECTED[2], 0x7CAE, 8, 15)
        s37, _ = load_matrix(VARIANTS / EXPECTED[3], 0x7CAE, 8, 15)
        for first, second, shift in ((gasoline, s88, 8),
                                     (gasoline, s37, 22),
                                     (s88, s37, 14)):
            with self.subTest(shift=shift):
                deltas, summary = summarize(first, second)
                self.assertEqual(summary["cells"], 120)
                self.assertEqual(summary["changed_cells"], 120)
                self.assertEqual(summary["constant_delta"], shift)
                self.assertTrue(all(value == shift for row in deltas
                                    for value in row))

    def test_7eac_single_row_plot_preserves_constant_variant_curve(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7EAC, 1, 15)
        self.assertEqual(gasoline[0],
                         [0x92, 0x9C, 0x9C, 0x88, 0x79, 0x74, 0x68,
                          0x68, 0x63, 0x5D, 0x57, 0x52, 0x52, 0x52, 0x52])
        for name in EXPECTED[:2] + EXPECTED[3:]:
            with self.subTest(rom=name):
                values, _ = load_matrix(VARIANTS / name, 0x7EAC, 1, 15)
                self.assertEqual(values, [[0x99] * 15])
                default, _ = load_matrix(VARIANTS / name, 0x7E9D, 1, 15)
                _, summary = summarize(default, values)
                self.assertEqual(summary["changed_cells"], 11)
                self.assertEqual(summary["unchanged_prefix_cells"], 4)
                self.assertEqual((summary["delta_min"], summary["delta_max"]),
                                 (0, 113))
        with tempfile.TemporaryDirectory() as directory:
            args = ["plot_ma17_matrices.py", "--matrix", "0x7EAC",
                    "--variant", "A", "--output-dir", directory]
            with mock.patch.object(sys, "argv", args), \
                    contextlib.redirect_stdout(io.StringIO()):
                main()
            prefix = Path(directory) / "matrix_7eac_g_vs_a"
            self.assertTrue(prefix.with_suffix(".png").is_file())
            self.assertEqual(json.loads(prefix.with_suffix(".json").read_text())
                             ["changed_cells"], 15)
            self.assertEqual(json.loads(prefix.with_suffix(".json").read_text())
                             ["column_start_raw_ram47"],
                             [0, 25, 32, 40, 50, 60, 72, 88, 104, 120,
                              140, 160, 186, 212, 240])
            self.assertEqual(len(prefix.with_suffix(".csv").read_text().splitlines()),
                             16)

    def test_7eac_raw_ram47_axis_differs_between_a_and_s37(self):
        baseline = [0, 25, 32, 40, 50, 60, 72, 88, 104, 120,
                    140, 160, 186, 212, 240]
        s88 = [0, 4, 11, 19, 29, 39, 51, 67, 83, 99,
               119, 139, 165, 191, 219]
        s37 = [0, 5, 12, 20, 30, 40, 52, 68, 84, 100,
               120, 140, 166, 192, 220]
        paths = (REFERENCE, *(VARIANTS / name for name in EXPECTED))
        for path, expected in zip(paths,
                                  (baseline, baseline, baseline, s88, s37, s37)):
            with self.subTest(rom=path.name):
                self.assertEqual(ram47_axis_raw(path), expected)
        with tempfile.TemporaryDirectory() as directory:
            args = ["plot_ma17_matrices.py", "--matrix", "0x7E9D",
                    "--reference-variant", "A", "--variant", "S37",
                    "--output-dir", directory]
            with mock.patch.object(sys, "argv", args), \
                    contextlib.redirect_stdout(io.StringIO()):
                main()
            prefix = Path(directory) / "matrix_7e9d_a_vs_s37"
            self.assertTrue(prefix.with_suffix(".png").is_file())
            report = json.loads(prefix.with_suffix(".json").read_text())
            self.assertEqual(report["changed_cells"], 0)
            self.assertIsNone(report["column_start_raw_ram47"])
            self.assertEqual(report["reference_column_start_raw_ram47"], baseline)
            self.assertEqual(report["variant_column_start_raw_ram47"], s37)
            with prefix.with_suffix(".csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 15)
            self.assertEqual(rows[3]["reference_column_start_raw_ram47"], "40")
            self.assertEqual(rows[3]["variant_column_start_raw_ram47"], "20")

    def test_second_axis_7b3e_source_and_boundaries_by_rom(self):
        gasoline = [0, 141, 188, 220, 243, 251]
        sun88 = [0, 133, 180, 212, 235, 243]
        sun37 = [0, 119, 166, 198, 221, 229]
        cases = ((REFERENCE, "IRAM[7Dh]", gasoline),
                 (VARIANTS / EXPECTED[0], "upper IRAM[AFh]", gasoline),
                 (VARIANTS / EXPECTED[1], "upper IRAM[AFh]", gasoline),
                 (VARIANTS / EXPECTED[2], "IRAM[7Dh]", sun88),
                 (VARIANTS / EXPECTED[3], "IRAM[7Dh]", sun37),
                 (VARIANTS / EXPECTED[4], "IRAM[7Dh]", sun37))
        for path, source, starts in cases:
            with self.subTest(path=path.name):
                self.assertEqual(second_axis_raw(path),
                                 {"source": source, "row_start_raw": starts})

    def test_rpm_axis_7b32_matches_all_six_original_roms(self):
        expected = [0, 200, 400, 700, 1300, 2175, 3200, 4200, 5200, 6375]
        for path in (REFERENCE, *(VARIANTS / name for name in EXPECTED)):
            with self.subTest(path=path.name):
                self.assertEqual(rpm_axis_nominal(path), expected)

    def test_s88_7581_is_uniform_raw_byte_shift(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7581, 15, 15)
        s88, _ = load_matrix(VARIANTS / EXPECTED[2], 0x7581, 15, 15)
        deltas, summary = summarize(gasoline, s88)
        self.assertEqual(summary["cells"], 225)
        self.assertEqual(summary["changed_cells"], 225)
        self.assertEqual(summary["constant_delta"], 21)
        self.assertTrue(all(value == 21 for row in deltas for value in row))

    def test_s88_alternative_matrices_keep_prefix_then_shift(self):
        sun = VARIANTS / EXPECTED[2]
        for start, shift in ((0x7662, 26), (0x7743, 8)):
            with self.subTest(start=hex(start)):
                gasoline, _ = load_matrix(REFERENCE, start, 15, 15)
                s88, _ = load_matrix(sun, start, 15, 15)
                source = [value for row in gasoline for value in row]
                target = [value for row in s88 for value in row]
                self.assertEqual(target[:14], source[:14])
                self.assertEqual(target[14:],
                                 [min(255, value + shift) for value in source[14:]])
                _, summary = summarize(gasoline, s88)
                self.assertEqual(summary["changed_cells"], 211)
                self.assertEqual(summary["unchanged_prefix_cells"], 14)
                self.assertEqual(summary["suffix_clamped_add_delta"], shift)

    def test_7f15_alcohol_changes_shape(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7F15, 6, 10)
        alcohol, _ = load_matrix(VARIANTS / EXPECTED[0], 0x7F15, 6, 10)
        _, summary = summarize(gasoline, alcohol)
        self.assertEqual(summary["cells"], 60)
        self.assertEqual(summary["changed_cells"], 59)
        self.assertIsNone(summary["constant_delta"])
        self.assertIsNone(summary["saturated_add_delta"])
        self.assertLess(summary["delta_min"], 0)
        self.assertGreater(summary["delta_max"], 0)

    def test_alcohol_7ed9_and_7f51_are_saturated_byte_shifts(self):
        for start, shift in ((0x7ED9, 34), (0x7F51, 38)):
            gasoline, _ = load_matrix(REFERENCE, start, 6, 10)
            for name in EXPECTED[:2]:
                with self.subTest(start=hex(start), variant=name):
                    alcohol, _ = load_matrix(VARIANTS / name, start, 6, 10)
                    _, summary = summarize(gasoline, alcohol)
                    self.assertEqual(summary["cells"], 60)
                    self.assertEqual(summary["changed_cells"], 60)
                    self.assertIsNone(summary["constant_delta"])
                    self.assertEqual(summary["saturated_add_delta"], shift)

    def test_alcohol_selector_one_differs_only_in_last_nine_cells(self):
        for name in EXPECTED[:2]:
            with self.subTest(variant=name):
                path = VARIANTS / name
                bank_zero, _ = load_matrix(path, 0x7ED9, 6, 10)
                bank_one, _ = load_matrix(path, 0x7F15, 6, 10)
                deltas, summary = summarize(bank_zero, bank_one)
                self.assertEqual(summary["changed_cells"], 9)
                self.assertEqual([value for row in deltas for value in row],
                                 [0] * 51 + [-34] * 9)
                self.assertEqual(summary["unchanged_prefix_cells"], 51)
                self.assertEqual(summary["suffix_clamped_add_delta"], -34)

    def test_s37_and_s36_second_bank_repeats_first_bank(self):
        gasoline = REFERENCE.read_bytes()
        self.assertNotEqual(gasoline[0x7ED9:0x7F15],
                            gasoline[0x7F15:0x7F51])
        for name in EXPECTED[3:]:
            with self.subTest(rom=name):
                image = (VARIANTS / name).read_bytes()
                self.assertEqual(image[0x7ED9:0x7F15],
                                 image[0x7F15:0x7F51])
                self.assertEqual(image[0x7F15:0x7F51],
                                 gasoline[0x7ED9:0x7F15])

    def test_7d9e_variant_offsets_preserve_terminal_cells(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7D9E, 8, 15)
        source = [value for row in gasoline for value in row]
        for name, shift, prefix in ((EXPECTED[2], 8, 117),
                                    (EXPECTED[3], 22, 116),
                                    (EXPECTED[4], 22, 116)):
            with self.subTest(variant=name):
                variant, _ = load_matrix(VARIANTS / name, 0x7D9E, 8, 15)
                target = [value for row in variant for value in row]
                self.assertEqual(target[:prefix],
                                 [value + shift for value in source[:prefix]])
                self.assertEqual(target[prefix:], source[prefix:])
                _, summary = summarize(gasoline, variant)
                self.assertEqual(summary["changed_cells"], prefix)

    def test_s88_7d26_7d9e_internal_differences_include_terminal_tail(self):
        gasoline = REFERENCE.read_bytes()
        s88 = (VARIANTS / EXPECTED[2]).read_bytes()
        def differing_indices(image):
            return [index for index in range(120)
                    if image[0x7D26 + index] != image[0x7D9E + index]]

        last_columns = [14 + row * 15 for row in range(7)]
        self.assertEqual(differing_indices(gasoline), last_columns)
        self.assertEqual(differing_indices(s88), last_columns + [117, 118, 119])


if __name__ == "__main__":
    unittest.main()
