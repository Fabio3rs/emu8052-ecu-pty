"""Synthetic regression for matrix base attribution in MOVC reports."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.audit_ma17_matrix_boundaries import audit


class MatrixBoundaryAuditTests(unittest.TestCase):
    def test_curve_one_past_read_is_not_next_curve_selection(self):
        catalog = {"rom_sha256": {"G": "rom-g"}, "tables": [
            {"id": "first", "start": "0x752A", "end_exclusive": "0x7534",
             "dimensions": [10]},
            {"id": "second", "start": "0x7534", "end_exclusive": "0x753E",
             "dimensions": [10]},
            {"id": "following_header", "start": "0x753E",
             "end_exclusive": "0x7544", "dimensions": [3]},
            {"id": "headered_segment", "start": "0x73D4",
             "end_exclusive": "0x73E0", "dimensions": [10]}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.json"
            path.write_text(json.dumps({"firmware_sha256": "rom-g",
                "emulator_sha256": "emu", "movc_observation": {"enabled": True,
                "reads": [
                    {"opcode": "93", "pc": "5333", "dptr": "752A",
                     "address": "7534", "mapped": "7534", "count": 7},
                    {"opcode": "93", "pc": "532F", "dptr": "7534",
                     "address": "7534", "mapped": "7534", "count": 2},
                    {"opcode": "93", "pc": "5333", "dptr": "7534",
                     "address": "753E", "mapped": "753E", "count": 1}]}}))
            report = audit(catalog, [path], curve=True)
        self.assertEqual(report["filter"]["dimensions"], [10])
        self.assertEqual([(row["table"], row["count"])
                          for row in report["base_selected_reads"]],
                         [("first", 7), ("second", 3)])
        self.assertEqual([(row["source_table"], row["next_table"],
                           row["count"]) for row in report["one_past_reads"]],
                         [("first", "second", 7),
                          ("second", "following_header", 1)])

    def test_one_past_read_is_not_next_matrix_selection(self):
        catalog = {"rom_sha256": {"G": "rom-g"}, "tables": [
            {"id": "first", "start": "0x7B46", "end_exclusive": "0x7BBE",
             "dimensions": [8, 15]},
            {"id": "second", "start": "0x7BBE", "end_exclusive": "0x7C36",
             "dimensions": [8, 15]}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = {"firmware_sha256": "rom-g", "emulator_sha256": "emu",
                    "movc_observation": {"enabled": True, "reads": [
                        {"opcode": "93", "pc": "5350", "dptr": "7B46",
                         "address": "7BBE", "mapped": "7BBE", "count": 3},
                        {"opcode": "93", "pc": "532F", "dptr": "7BBE",
                         "address": "7BBE", "mapped": "7BBE", "count": 5},
                        {"opcode": "83", "pc": "6000", "dptr": "7B46",
                         "address": "7BBE", "mapped": "7BBE", "count": 7}]}}
            (root / "base.json").write_text(json.dumps(base))
            overridden = {**base, "ram57_override_hex": "01"}
            (root / "override.json").write_text(json.dumps(overridden))
            untraced = {**base, "movc_observation": {"enabled": False}}
            (root / "untraced.json").write_text(json.dumps(untraced))
            report = audit(catalog, sorted(root.glob("*.json")),
                           exclude_overrides=True, emulator_sha256="emu")
        self.assertEqual(report["trace_files_considered"], 2)
        self.assertEqual(report["movc_enabled_trace_files"], 1)
        self.assertEqual([(row["table"], row["count"])
                          for row in report["base_selected_reads"]],
                         [("first", 3), ("second", 5)])
        self.assertEqual([(row["source_table"], row["next_table"],
                           row["pc"], row["count"])
                          for row in report["one_past_reads"]],
                         [("first", "second", "5350", 3)])


if __name__ == "__main__":
    unittest.main()
