"""Synthetic coverage for nonpointer MOVC effective-address auditing."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.audit_ma17_opaque_reads import audit


class OpaqueReadAuditTests(unittest.TestCase):
    def test_counts_mapped_dptr_and_pc_reads_separately_from_untraced_files(self):
        catalog = {"unclassified_nonpointer_intervals": [
            {"id": "first", "start": "0x6EAB", "end_exclusive": "0x6FCA"},
            {"id": "second", "start": "0x7199", "end_exclusive": "0x71F0"}]}
        with tempfile.TemporaryDirectory() as directory:
            traced = Path(directory) / "traced.json"
            untraced = Path(directory) / "untraced.json"
            traced.write_text(json.dumps({"firmware_sha256": "rom-a",
                "movc_observation": {"enabled": True, "reads": [
                    {"pc": "1234", "opcode": "93", "dptr": "6EA0",
                     "address": "EEAB", "mapped": "6EAB", "count": 3},
                    {"pc": "5678", "opcode": "83", "dptr": "0000",
                     "address": "7199", "mapped": "7199", "count": 2},
                    {"pc": "9999", "opcode": "93", "dptr": "7000",
                     "address": "7000", "mapped": "7000", "count": 5}]} }))
            untraced.write_text(json.dumps({"firmware_sha256": "rom-b",
                                              "movc_observation": {"enabled": False}}))
            report = audit(catalog, [traced, untraced])
        self.assertEqual(report["trace_files"], 2)
        self.assertEqual(report["movc_enabled_trace_files"], 1)
        self.assertEqual(report["movc_enabled_trace_files_by_rom"], {"rom-a": 1})
        self.assertEqual([(row["occurrences"], row["states"][0]["mapped"])
                          for row in report["intervals"]], [(3, "6EAB"), (2, "7199")])
        self.assertEqual(report["intervals"][0]["states"][0]["address"], "EEAB")


if __name__ == "__main__":
    unittest.main()
