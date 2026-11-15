"""Synthetic checks for effective MOVC header selection in TPS grids."""

import unittest

from tools.audit_ma17_tps_surface import parse_trace


class TpsSurfaceTests(unittest.TestCase):
    def test_counts_headers_separately_and_requires_completed_trace(self):
        log = ("[SENSOR-RAM] tick=1 addr=6F value=00->27 source_PC=11B6\n"
               "[SENSOR-RAM] tick=2 addr=6F value=27->93 source_PC=11B6\n"
               "[MOVC-SUMMARY] pc=527D opcode=93 dptr=755C acc=00 "
               "address=755C mapped=755C value=6F count=1\n"
               "[MOVC-SUMMARY] pc=527D opcode=93 dptr=7569 acc=00 "
               "address=7569 mapped=7569 value=6F count=385\n"
               "[TPS-FLOW] tick=2000000 PC=11B6 R2=A0 R3=1A R4=E0 "
               "B=E0 A=93 PSW=08 RAM28=00 RAM2E=C4\n"
               "[PC-HIT] 11A8\n[TRACE-STOP] ticks=4000000\n")
        result = parse_trace(log, 4000000)
        self.assertEqual(result["iram6f_hex"], "93")
        self.assertEqual(result["header_reads"], {"755C": 1, "7569": 385})
        self.assertTrue(result["alternative_branch_reached"])
        self.assertTrue(result["alternate_formula_sample"]["formula_matches"])
        self.assertEqual(result["alternate_formula_sample"]["value"], "93")
        with self.assertRaises(ValueError):
            parse_trace(log, 2000000)
        with self.assertRaises(ValueError):
            parse_trace("[TRACE-STOP] ticks=4000000", 4000000)


if __name__ == "__main__":
    unittest.main()
