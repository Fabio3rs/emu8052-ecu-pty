"""Independent checks of missing-slot spacing and phase/sensor decoupling."""
import copy
import math
import unittest
from config import load
from trigger_layout import slots, crossing_angles, crossing_intervals, axial_layout


class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.params,self.frame = load()

    def test_60_minus_2_preserves_nominal_grid(self):
        present = slots(self.params)
        self.assertEqual(present,list(range(58)))
        gaps = crossing_intervals(self.params,6000)
        self.assertEqual(len(gaps['angle_gaps_deg']),58)
        self.assertEqual(gaps['angle_gaps_deg'].count(6),57)
        self.assertEqual(gaps['angle_gaps_deg'].count(18),1)
        self.assertAlmostEqual(sum(gaps['time_gaps_s']),0.01,places=12)
        self.assertAlmostEqual(max(gaps['time_gaps_s']),0.0005,places=12)
        self.assertAlmostEqual(min(gaps['time_gaps_s']),1/6000,places=12)

    def test_sensor_and_mounting_phase_are_independent(self):
        params = copy.deepcopy(self.params)
        original = crossing_angles(params)
        p = params['trigger_pattern_estimated']['value']
        p['wheel_phase_deg'] += 23
        self.assertEqual(crossing_angles(params),sorted((a-23)%360 for a in original))
        p['sensor_angle_deg'] += 17
        self.assertEqual(crossing_angles(params),sorted((a-6)%360 for a in original))
        params['accessory_visual_estimated']['value']['groove_depth_mm'] += 1
        self.assertEqual(crossing_angles(params),sorted((a-6)%360 for a in original))

    def test_gap_can_cross_slot_zero(self):
        params = copy.deepcopy(self.params)
        params['trigger_pattern_estimated']['value']['missing_slots'] = [59,0]
        self.assertEqual(slots(params),list(range(1,59)))
        self.assertEqual(max(crossing_intervals(params,6000)['angle_gaps_deg']),18)

    def test_invalid_patterns_are_rejected(self):
        for missing in ([0,0],[0,2],[],[60],[1.5]):
            params = copy.deepcopy(self.params)
            params['trigger_pattern_estimated']['value']['missing_slots'] = missing
            with self.assertRaises(ValueError):
                slots(params)
        for rpm in (0,-1,math.inf,math.nan):
            with self.assertRaises(ValueError):
                crossing_intervals(self.params,rpm)

    def test_stack_is_separate_from_timing_belt(self):
        ax = axial_layout(self.params)
        self.assertLess(ax['nut_front'],ax['washer_front'])
        self.assertLess(ax['washer_front'],ax['pulley_front'])
        self.assertLess(ax['pulley_front'],ax['wheel_front'])
        self.assertLess(ax['wheel_front'],ax['back'])
        timing = self.params['timing_visual_estimated']['value']
        self.assertEqual(ax['back'],timing['pulley_center_x_mm']-timing['pulley_width_mm']/2)


if __name__=='__main__':
    unittest.main()
