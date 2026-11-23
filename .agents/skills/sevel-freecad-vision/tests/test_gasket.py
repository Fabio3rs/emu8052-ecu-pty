"""Smoke tests for the included example, without invoking FreeCAD itself."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

class GasketExampleTests(unittest.TestCase):
    def test_existing_example_files(self):
        d = ROOT/'assets/demo'
        g = json.loads((d/'head_gasket_geometry.json').read_text())
        r = json.loads((d/'head_gasket_report.json').read_text())
        self.assertEqual(4, len(g['bores']))
        self.assertEqual(39, len(g['other_holes']))
        self.assertEqual(43, r['head_gasket_holes_total'])
        self.assertTrue(0.60 < g['estimated_scale_mm_per_pixel'] < 0.65)
        self.assertGreater(len(g['outline_points_mm_image_y_down']), 20)
        doc = ET.parse(d/'head_gasket_analytic.svg')
        ns={'s': 'http://www.w3.org/2000/svg'}
        self.assertEqual(4, len(doc.findall('.//s:circle', ns)))
        self.assertEqual(40, len(doc.findall('.//s:path', ns)))  # 1 outer + 39 other
        for b in g['bores']:
            self.assertAlmostEqual(b['diameter_mm'], 86.4)
            self.assertAlmostEqual(b['center_mm_image_y_down'][1], 0.0)
        self.assertTrue(g['deskew_enabled'])

    def test_from_png_reproduces_main_counts(self):
        with TemporaryDirectory() as t:
            subprocess.run([sys.executable, str(ROOT/'scripts/gasket_extract.py'),
                            str(ROOT/'assets/source_head_gasket.png'),
                            '--output', t, '--nominal-bore-mm', '86.4'], check=True, capture_output=True)
            r = json.loads((Path(t)/'head_gasket_report.json').read_text())
            self.assertEqual(r['analytic_bore_count'], 4)
            self.assertEqual(r['other_holes_count'], 39)

if __name__ == '__main__':
    unittest.main()
