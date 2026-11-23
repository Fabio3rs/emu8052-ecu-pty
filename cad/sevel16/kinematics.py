"""Absolute, stateless poses in the master frame (mm and degrees).

Positive X rotation sends +Z toward -Y. Zero is C1 compression TDC.
This module imports no FreeCAD or GUI code. Valve lift uses a synthetic cam.
"""
import math
from config import layout
from cam_profile import lift
from timing_layout import rotations as timing_rotations

COMPRESSION_TDC = (0, 540, 180, 360)


def pose(theta_deg, params, frame):
    if not math.isfinite(theta_deg):
        raise ValueError('theta_deg must be finite')
    g = layout(params, frame)
    length = params['moving_geometry_estimated']['value']['rod_length_mm']
    cam_phase = params['cam_profile_estimated']['value']['global_phase_deg']
    cylinders = []
    for i, x in enumerate(g['centers']):
        cycle = (theta_deg-COMPRESSION_TDC[i]) % 720
        phi = math.radians(cycle % 360)
        q = [x, -g['radius']*math.sin(phi), -g['height']+g['radius']*math.cos(phi)]
        dz = math.sqrt(length*length-q[1]*q[1])
        pin = [x, 0.0, q[2]+dz]
        beta = math.degrees(math.atan2(q[1], dz))
        cylinders.append({'cylinder': i+1, 'cycle_deg': cycle,
                          'crankpin_mm': q, 'piston_pin_mm': pin,
                          'rod_rx_deg': beta, 'crown_z_mm': pin[2]+g['compression_height'],
                          'valve_lifts_mm':{kind:lift(cycle+2*cam_phase,kind,params)
                                            for kind in ('intake','exhaust')},
                          'stroke_label': ('expansion','exhaust','intake','compression')[int(cycle//180)]})
    return {'theta_deg': theta_deg, 'crank_rx_deg': theta_deg % 360,
            'crank_pivot_mm': [0,0,-g['height']],
            'cam_rx_deg': ((theta_deg % 720)/2+cam_phase)%360, 'cylinders': cylinders,
            'timing_rx_deg':timing_rotations(theta_deg,params) if 'timing_visual_estimated' in params else {}}


def transform_rod_point(point, cylinder):
    """Independent of a CAD matrix: rotate local vector, then translate once."""
    a = math.radians(cylinder['rod_rx_deg'])
    x, y, z = point
    q = cylinder['crankpin_mm']
    return [q[0]+x, q[1]+math.cos(a)*y-math.sin(a)*z,
            q[2]+math.sin(a)*y+math.cos(a)*z]
