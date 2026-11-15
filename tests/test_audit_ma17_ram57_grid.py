"""Synthetic parsing checks for the bounded RAM57 grid audit."""

import unittest

from tools.audit_ma17_ram57_grid import parse_trace


class Ram57GridTests(unittest.TestCase):
    def test_keeps_reader_reachability_separate_from_selector_changes(self):
        log = ("[ENGINE-RAM] tick=7 addr=57 value=00->01 source_PC=1234\n"
               "[PC-HIT] 1378\n[TRACE-STOP] ticks=100\n")
        result = parse_trace(log, 100)
        self.assertTrue(result["reader_1378_reached"])
        self.assertEqual(result["ram57_changes"], [
            {"tick": 7, "before": "00", "after": "01", "source_pc": "1234"}])
        with self.assertRaises(ValueError):
            parse_trace(log, 200)


if __name__ == "__main__":
    unittest.main()
