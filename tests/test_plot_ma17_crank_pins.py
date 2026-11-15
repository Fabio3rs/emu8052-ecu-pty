"""Regression coverage for 60-2 reference alignment and CPU pin parsing."""

import tempfile
import unittest
from pathlib import Path

from tools.plot_ma17_crank_pins import CHANNELS, phase_at, read_trace


class CrankPinPlotTest(unittest.TestCase):
    def test_phase_and_port_events(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "trace.log"
            log.write_text(
                "[CRANK-PHASE] tick=100 tooth=0 rpm=850\n"
                "[P5-LATCH] instr=110 PC=00A8 value=02 RAM47=22\n"
                "[P1.1-LATCH] instr=120 source_PC=0433 value=0 RAM47=22\n"
                "[CC3-PIN] tick=130 PC=05D5 value=0 shadow=0\n"
                "[CRANK-PHASE] tick=160 tooth=0 rpm=850\n"
                "[CRANK-PHASE] tick=220 tooth=0 rpm=850\n")
            references, events = read_trace(log)
        self.assertEqual(references, [(100, 850), (160, 850), (220, 850)])
        self.assertEqual(events[:2], [(110, CHANNELS[0], 0),
                                      (110, CHANNELS[1], 1)])
        self.assertEqual(events[2:], [(120, CHANNELS[2], 0),
                                      (130, CHANNELS[3], 0)])
        self.assertEqual(phase_at(130, [100, 160, 220]), 180)
        self.assertEqual(phase_at(190, [100, 160, 220]), 540)

    def test_requires_two_complete_revolutions(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "trace.log"
            log.write_text("[CRANK-PHASE] tick=100 tooth=0 rpm=850\n")
            with self.assertRaisesRegex(ValueError, "three tooth-0"):
                read_trace(log)


if __name__ == "__main__":
    unittest.main()
