from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_reference_frame', SKILL_ROOT / 'scripts/build_reference_frame.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReferenceFrameTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((SKILL_ROOT / 'assets/reference_parameters.example.json').read_text())

    def test_four_centers_and_bore_gaps(self):
        frame, gate = mod.calculate(self.data)
        self.assertEqual([p['x'] for p in frame['bore_circle_centers_mm']], [0, 93, 189, 282])
        self.assertEqual(frame['edge_gaps_nominal_mm'], [6.6, 9.6, 6.6])
        self.assertEqual(frame['cylinder_bore_diameter_mm'], 86.4)
        self.assertEqual(frame['crank_radius_mm_derived'], 33.7)
        self.assertEqual(gate['status'], 'PASS_PROVISIONAL_FOR_VISUAL_ONLY')
        self.assertFalse(gate['cad_fabrication_approved'])

    def test_confirmed_gate_requires_target_source(self):
        for entry in self.data['dimensions']['center_spacings_mm']:
            entry['evidence'] = 'MEASURED_TARGET'
            entry['source'] = 'caliper measurement by owner, sample reference only'
        _frame, gate = mod.calculate(self.data)
        self.assertEqual(gate['status'], 'PASS_CONFIRMED')

    def test_overlap_rejected(self):
        self.data['dimensions']['center_spacings_mm'][0]['value'] = 50
        with self.assertRaisesRegex(ValueError, 'overlap'):
            mod.calculate(self.data)

    def test_missing_source_rejected(self):
        self.data['dimensions']['center_spacings_mm'][1]['source'] = ''
        with self.assertRaisesRegex(ValueError, 'source missing'):
            mod.calculate(self.data)

    def test_svg_physical_dimensions_and_repeatability(self):
        frame, _gate = mod.calculate(self.data)
        svg = mod.make_svg(frame)
        self.assertEqual(svg.count('<circle '), 4)
        self.assertIn('mm', svg)
        self.assertEqual(svg, mod.make_svg(frame))
        self.assertIn('PASS_PROVISIONAL_FOR_VISUAL_ONLY', svg)


if __name__ == '__main__':
    unittest.main()
