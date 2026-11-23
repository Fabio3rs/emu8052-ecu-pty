"""Independent tangent, drive-ratio and auxiliary phase checks without FreeCAD."""
import copy
import math
import unittest
from config import load
from timing_layout import wheels, path, rotations
from kinematics import pose


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.params,self.frame = load()

    def test_closed_tangent_loop_and_back_wrap(self):
        segments = path(self.params,self.frame)
        self.assertEqual(len(segments),8)
        for a,b in zip(segments,segments[1:]+segments[:1]):
            self.assertLess(math.dist(a['points'][1],b['points'][0]),1e-10)
        sweep = 0
        for i,s in enumerate(segments):
            if s['kind']!='arc':
                continue
            sweep += s['sweep']
            self.assertEqual(s['sign'],-1 if s['wheel']=='Tensioner' else 1)
            for end,adjacent in [(0,segments[i-1]),(1,segments[(i+1)%8])]:
                radial = tuple(s['points'][end][j]-s['center'][j] for j in range(2))
                line = tuple(adjacent['points'][1][j]-adjacent['points'][0][j] for j in range(2))
                self.assertAlmostEqual(sum(radial[j]*line[j] for j in range(2)),0,places=8)
                self.assertAlmostEqual(math.hypot(*radial),s['radius'],places=10)
        self.assertAlmostEqual(sweep,2*math.pi,places=10)

    def test_transmission_uses_independent_auxiliary_ratio(self):
        params = copy.deepcopy(self.params)
        p = params['timing_visual_estimated']['value']
        p['aux_teeth'] = 25
        p['aux_phase_deg'] = 17
        for theta in range(0,721,5):
            result = rotations(theta,params)
            self.assertAlmostEqual(result['aux'],(theta*p['crank_teeth']/25+17)%360)
            state = pose(theta,params,self.frame)
            self.assertAlmostEqual(state['cam_rx_deg'],(theta/2)%360)
            self.assertAlmostEqual(state['timing_rx_deg']['aux'],(theta*p['crank_teeth']/25+17)%360)
        self.assertNotEqual(rotations(180,params)['aux'],90)
        self.assertAlmostEqual(rotations(900,params)['aux'],17)

    def test_tensioner_speed_has_opposite_sign(self):
        p = self.params['timing_visual_estimated']['value']
        pitch = p['crank_teeth']*p['pitch_mm']/(2*math.pi)
        result = rotations(1,self.params)['tensioner']
        self.assertAlmostEqual((360-result)*p['tensioner_radius_mm'],pitch)
        self.assertNotEqual(rotations(720,self.params)['tensioner'],rotations(0,self.params)['tensioner'])

    def test_invalid_layout_is_rejected(self):
        params = copy.deepcopy(self.params)
        p = params['timing_visual_estimated']['value']
        p['tensioner_y_mm'],p['tensioner_z_mm'] = 0,126
        with self.assertRaises(ValueError):
            path(params,self.frame)
        with self.assertRaises(ValueError):
            rotations(float('nan'),self.params)


if __name__=='__main__':
    unittest.main()
