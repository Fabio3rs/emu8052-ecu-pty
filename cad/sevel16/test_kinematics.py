"""Run with python -m unittest discover -s cad/sevel16 -p 'test_*.py'."""
import copy
import math
import unittest
from config import load, layout
from kinematics import pose, transform_rod_point, COMPRESSION_TDC


class SliderCrankTests(unittest.TestCase):
    def setUp(self):
        self.params, self.frame = load()

    def test_full_cycle_connections_and_periods(self):
        length = self.params['moving_geometry_estimated']['value']['rod_length_mm']
        angles = sorted(set(range(0,721,5)) | {0.001,179.999,180.001,359.999,719.999})
        for angle in angles:
            a, b, c = [pose(angle+d,self.params,self.frame) for d in (0,360,720)]
            for p, p360, p720 in zip(a['cylinders'],b['cylinders'],c['cylinders']):
                self.assertAlmostEqual(math.dist(p['crankpin_mm'],p['piston_pin_mm']),length,places=10)
                tip = transform_rod_point([0,0,length],p)
                self.assertLess(math.dist(tip,p['piston_pin_mm']),1e-10)
                self.assertLess(math.dist(p['piston_pin_mm'],p360['piston_pin_mm']),1e-10)
                self.assertLess(math.dist(p['piston_pin_mm'],p720['piston_pin_mm']),1e-10)
                self.assertAlmostEqual(p['cycle_deg'],p720['cycle_deg'],places=10)
            self.assertAlmostEqual(a['cylinders'][0]['crown_z_mm'],a['cylinders'][3]['crown_z_mm'])
            self.assertAlmostEqual(a['cylinders'][1]['crown_z_mm'],a['cylinders'][2]['crown_z_mm'])
            self.assertAlmostEqual(a['cam_rx_deg'],c['cam_rx_deg'])
            self.assertAlmostEqual((b['cam_rx_deg']-a['cam_rx_deg'])%360,180)
            self.assertEqual(a,pose(angle,self.params,self.frame))

    def test_stroke_and_height_closure(self):
        for i, tdc in enumerate(COMPRESSION_TDC):
            top = pose(tdc,self.params,self.frame)['cylinders'][i]['crown_z_mm']
            bottom = pose(tdc+180,self.params,self.frame)['cylinders'][i]['crown_z_mm']
            self.assertAlmostEqual(top,-0.5)
            self.assertAlmostEqual(top-bottom,67.4)

    def test_stroke_variant_is_not_cached(self):
        variant = copy.deepcopy(self.params)
        variant['dimensions']['stroke_mm']['value'] = 70
        top = pose(0,variant,self.frame)['cylinders'][0]['crown_z_mm']
        bottom = pose(180,variant,self.frame)['cylinders'][0]['crown_z_mm']
        self.assertAlmostEqual(top-bottom,70)
        self.assertAlmostEqual(top,-0.5)
        self.assertAlmostEqual(layout(self.params,self.frame)['radius'],33.7)

    def test_reject_invalid_input(self):
        for theta in [float('nan'),float('inf')]:
            with self.assertRaises(ValueError):
                pose(theta,self.params,self.frame)
        self.params['moving_geometry_estimated']['value']['pin_offset_mm'] = 1
        with self.assertRaises(ValueError):
            pose(0,self.params,self.frame)
