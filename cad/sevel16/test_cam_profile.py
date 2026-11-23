"""Check events and the actual support envelope of a flat tappet cam."""
import math
import unittest
from config import load
from cam_profile import support, lift, profile_point, profile_polygon
from kinematics import pose
from valvetrain_layout import valves


class CamTests(unittest.TestCase):
    def setUp(self):
        self.params,self.frame = load()

    def test_checking_events_and_operating_peaks(self):
        n = self.params['valve_timing_nominal']['value']
        base = self.params['cam_profile_estimated']['value']['base_radius_mm']
        for kind in ('intake','exhaust'):
            opening,closing = n[kind+'_events_deg']
            center = (opening+closing)/2
            for event in (opening,closing):
                h,_,_ = support(math.radians((event-center)/2),self.params)
                self.assertAlmostEqual(h-base,0.8,places=10)
            self.assertAlmostEqual(lift(center,kind,self.params),8.8-n[kind+'_lash_mm'])
            for theta in range(0,721,5):
                value = lift(theta,kind,self.params)
                self.assertGreaterEqual(value,0)
                self.assertLessEqual(value,8.8-n[kind+'_lash_mm']+1e-10)
                self.assertAlmostEqual(value,lift(theta+720,kind,self.params))

    def test_convex_envelope_contact_is_inside_tappet(self):
        samples = [math.radians(i/2) for i in range(720)]
        points = [profile_point(a,self.params) for a in samples]
        for angle in samples[::4]:
            h,dh,ddh = support(angle,self.params)
            self.assertGreater(h+ddh,0)  # positive radius of curvature
            self.assertLess(abs(dh),36.975/2)  # minimum manual tappet radius
            y,z = profile_point(angle,self.params)
            self.assertAlmostEqual(y*math.sin(angle)+z*math.cos(angle),h,places=10)
            self.assertLessEqual(max(y*math.sin(angle)+z*math.cos(angle) for y,z in points),h+1e-9)

    def test_phase_pair_is_not_valve_pair(self):
        zero = pose(0,self.params,self.frame)
        c1,c4 = zero['cylinders'][0],zero['cylinders'][3]
        self.assertAlmostEqual(c1['crown_z_mm'],c4['crown_z_mm'])
        self.assertEqual(c1['valve_lifts_mm'],{'intake':0,'exhaust':0})
        self.assertTrue(all(v>0 for v in c4['valve_lifts_mm'].values()))
        end = pose(720,self.params,self.frame)
        for a,b in zip(zero['cylinders'],end['cylinders']):
            self.assertEqual(a['valve_lifts_mm'],b['valve_lifts_mm'])

    def test_first_and_second_derivatives(self):
        epsilon = 1e-5
        for angle in (0.1,0.4,0.8,1.01,1.05,1.1,2.0):
            h,dh,ddh = support(angle,self.params)
            left = support(angle-epsilon,self.params)
            right = support(angle+epsilon,self.params)
            self.assertAlmostEqual((right[0]-left[0])/(2*epsilon),dh,places=4)
            self.assertAlmostEqual((right[1]-left[1])/(2*epsilon),ddh,places=3)

    def test_eight_lobe_orientation_matches_all_valves(self):
        rows = valves(self.params,self.frame)
        self.assertEqual(len(rows),8)
        timing = self.params['valve_timing_nominal']['value']
        base = self.params['cam_profile_estimated']['value']['base_radius_mm']
        for theta in range(0,721,5):
            state = pose(theta,self.params,self.frame)
            for row in rows:
                # Downward world normal transformed back through both X rotations.
                alpha = math.radians(180+state['cam_rx_deg']+row['lobe_local_rx_deg'])
                h,_,_ = support(alpha,self.params)
                measured = max(0,h-base-timing[row['kind']+'_lash_mm'])
                expected = state['cylinders'][row['cylinder']-1]['valve_lifts_mm'][row['kind']]
                self.assertAlmostEqual(measured,expected,places=9)

    def test_layout_and_spring_height_bounds(self):
        p = self.params['valvetrain_layout_estimated']['value']
        rows = valves(self.params,self.frame)
        for a,b in zip(rows,rows[1:]):
            self.assertGreater(b['axis_origin_mm'][0]-a['axis_origin_mm'][0],36.985)
        for spring in ('inner','outer'):
            closed = p['retainer_bottom_z_mm']-p[spring+'_spring_seat_z_mm']
            wire = p[spring+'_spring_wire_radius_mm']
            turns = p[spring+'_spring_turns']
            self.assertGreater(closed-8.4,2*wire*(turns+1))

    def test_discretized_cam_still_imposes_the_requested_motion(self):
        polygon = profile_polygon(self.params)
        worst = 0
        for i in range(3600):
            a = math.radians(i/10)
            h,_,_ = support(a,self.params)
            actual = max(y*math.sin(a)+z*math.cos(a) for y,z in polygon)
            self.assertLessEqual(actual,h+1e-8)
            worst = max(worst,h-actual)
        self.assertLess(worst,0.01)  # CAD preview criterion, not OEM tolerance
