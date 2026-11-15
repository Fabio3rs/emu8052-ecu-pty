"""Check the 7E8Eh curve plot inputs against the original ROMs."""

import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from plot_ma17_state_curve import ROMS, read_curves


class StateCurvePlotTests(unittest.TestCase):
    def test_six_original_roms_share_the_countdown_curve(self):
        curves, hashes = read_curves()
        self.assertEqual(set(curves), {"G", "A", "A+", "S88", "S37", "S36"})
        for name, path in ROMS.items():
            with self.subTest(rom=name):
                self.assertEqual(hashes[name], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(set(map(tuple, curves.values())),
                         {(1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 5, 3, 1, 1, 1)})


if __name__ == "__main__":
    unittest.main()
