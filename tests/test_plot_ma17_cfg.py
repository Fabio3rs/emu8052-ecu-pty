"""Regression checks for static CFG extraction from the editable assembly."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from plot_ma17_cfg import MODULAR, ROM, build_graph, filter_observed_paths, read_assembly


class ControlFlowGraphTests(unittest.TestCase):
    def test_36de_gate_uses_real_assembly_destinations(self):
        labels, code = read_assembly(MODULAR / "ma17.asm", ROM.read_bytes())
        blocks, edges = build_graph(code, labels, 0x36DE, 0x371D)
        self.assertIn(0x36DE, blocks)
        self.assertIn((0x36DE, 0x3710, "taken"), edges)
        self.assertIn((0x36E1, 0x3739, "taken"), edges)
        self.assertIn((0x36E1, 0x36E4, "next"), edges)
        self.assertIn((0x36EA, 0x3701, "taken"), edges)

    def test_indirect_jump_is_marked_unresolved(self):
        code = {0x100: ("jmp @A + DPTR", 0x101),
                0x101: ("mov A, #01h", 0x103)}
        blocks, edges = build_graph(code, {}, 0x100, 0x103)
        self.assertEqual(set(blocks), {0x100, 0x101})
        self.assertIn((0x100, "indirect", "indirect"), edges)
        self.assertNotIn((0x100, 0x101, "next"), edges)

    def test_pc_filter_keeps_all_static_routes_between_observations(self):
        code = {0x100: ("jnz branch", 0x102),
                0x102: ("mov A, #01h", 0x104),
                0x104: ("sjmp done", 0x106),
                0x106: ("mov A, #02h", 0x108),
                0x108: ("ret", 0x109)}
        blocks, edges = build_graph(code, {"branch": 0x106, "done": 0x108},
                                    0x100, 0x109)
        filtered, routes, segments = filter_observed_paths(blocks, edges, [0x100, 0x108])
        self.assertEqual(set(filtered), {0x100, 0x102, 0x106, 0x108})
        self.assertIn((0x100, 0x106, "taken"), routes)
        self.assertIn((0x100, 0x102, "next"), routes)
        self.assertEqual(segments[0]["status"], "possible")
        _, _, impossible = filter_observed_paths(blocks, edges, [0x108, 0x100])
        self.assertEqual(impossible[0]["status"], "no_static_path_in_view")


if __name__ == "__main__":
    unittest.main()
