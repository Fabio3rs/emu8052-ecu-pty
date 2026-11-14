"""Check matrix plotting inputs against original ROM bytes."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compare_ma17_variants import EXPECTED, REFERENCE, VARIANTS
from plot_ma17_matrices import load_matrix, summarize


class MatrixPlotTests(unittest.TestCase):
    def test_s88_7581_is_uniform_raw_byte_shift(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7581, 15, 15)
        s88, _ = load_matrix(VARIANTS / EXPECTED[2], 0x7581, 15, 15)
        deltas, summary = summarize(gasoline, s88)
        self.assertEqual(summary["cells"], 225)
        self.assertEqual(summary["changed_cells"], 225)
        self.assertEqual(summary["constant_delta"], 21)
        self.assertTrue(all(value == 21 for row in deltas for value in row))

    def test_7f15_alcohol_changes_shape(self):
        gasoline, _ = load_matrix(REFERENCE, 0x7F15, 6, 10)
        alcohol, _ = load_matrix(VARIANTS / EXPECTED[0], 0x7F15, 6, 10)
        _, summary = summarize(gasoline, alcohol)
        self.assertEqual(summary["cells"], 60)
        self.assertEqual(summary["changed_cells"], 59)
        self.assertIsNone(summary["constant_delta"])
        self.assertLess(summary["delta_min"], 0)
        self.assertGreater(summary["delta_max"], 0)

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


if __name__ == "__main__":
    unittest.main()
