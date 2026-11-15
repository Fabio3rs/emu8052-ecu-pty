"""Check the RAM47h transfer plot input and summary."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from plot_ma17_curve_transfer import COLUMNS, load_transfer, summarize
from plot_ma17_matrices import ROM_PATHS, ram47_axis_raw
from plot_ma17_third_curve_transfer import load_transfer as load_third_transfer
from plot_ma17_third_curve_transfer import summarize as summarize_third


class CurveTransferTests(unittest.TestCase):
    def test_a_s37_producer_and_reader_code_windows_match(self):
        a = ROM_PATHS["A"].read_bytes()
        s37 = ROM_PATHS["S37"].read_bytes()
        windows = ((0x01AB, 0x01C0), (0x0DD2, 0x0E05),
                   (0x0E35, 0x0EB0), (0x1386, 0x139E),
                   (0x3329, 0x3333), (0x3384, 0x33D3),
                   (0x533C, 0x538D), (0x53E4, 0x540C))
        for start, end in windows:
            with self.subTest(start=f"{start:04X}h"):
                self.assertEqual(a[start:end], s37[start:end])
        self.assertNotEqual(ram47_axis_raw(ROM_PATHS["A"]),
                            ram47_axis_raw(ROM_PATHS["S37"]))

    def test_full_sweep_and_first_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sweep.csv"
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("raw_ram47", *COLUMNS))
                for raw in range(256):
                    writer.writerow((raw, 153, 152 if raw == 22 else 153,
                                     153, 153))
            values = load_transfer(path)
            report = summarize(values)
            self.assertEqual(report["default_mismatched_inputs"], 1)
            self.assertEqual(report["default_first_mismatch"], 22)
            self.assertEqual(report["alternate_mismatched_inputs"], 0)

    def test_rejects_missing_raw_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "short.csv"
            path.write_text("raw_ram47," + ",".join(COLUMNS) + "\n0,1,1,1,1\n")
            with self.assertRaisesRegex(ValueError, "256"):
                load_transfer(path)

    def test_axis_translation_matches_shifted_transfer(self):
        a = [max(40, 153 - raw // 2) for raw in range(256)]
        values = {"a_default": a,
                  "s37_default": [a[min(raw + 20, 255)]
                                  for raw in range(256)],
                  "a_alternate": [153] * 256,
                  "s37_alternate": [153] * 256}
        report = summarize(values)
        self.assertEqual(report["axis_offset_a_minus_s37"], 20)
        self.assertEqual(report["translated_inputs_checked"], 236)
        self.assertEqual(report["translated_default_mismatches"], 0)

    def test_third_curve_first_segment_breaks_translation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "third.csv"
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("raw_ram47", "a_third", "s37_third"))
                for raw in range(256):
                    writer.writerow((raw, raw, min(raw + 20, 255)
                                     if raw >= 5 else raw))
            a, s37 = load_third_transfer(path)
            report = summarize_third(a, s37)
            self.assertEqual(report["axis_offset_a_minus_s37"], 20)
            self.assertEqual(report["translated_mismatch_inputs"], [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
