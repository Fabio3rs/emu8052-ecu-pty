"""Pure missing-tooth grid, angular conventions and geometric center crossings."""
import math


def slots(params):
    p = params['trigger_pattern_estimated']['value']
    if not all(math.isfinite(p[k]) for k in ('wheel_phase_deg','sensor_angle_deg')):
        raise ValueError('Finite wheel and sensor phases required')
    n,missing = p['nominal_slots'],p['missing_slots']
    if not isinstance(n,int) or n<4 or len(set(missing))!=len(missing):
        raise ValueError('Invalid nominal slot grid')
    if not missing or len(missing)>=n-1 or any(not isinstance(i,int) or not 0<=i<n for i in missing):
        raise ValueError('Invalid missing slots')
    if sum((i-1)%n not in missing for i in missing)!=1:
        raise ValueError('Missing slots must form one consecutive gap')
    if not 0<p['tooth_width_angle_deg']<360/n:
        raise ValueError('Tooth width must be smaller than nominal pitch')
    return [i for i in range(n) if i not in missing]


def radial(angle_deg, radius):
    a = math.radians(angle_deg)
    return (-radius*math.sin(a),radius*math.cos(a))


def crossing_angles(params):
    p = params['trigger_pattern_estimated']['value']
    return sorted((p['sensor_angle_deg']-p['wheel_phase_deg']-i*360/p['nominal_slots'])%360
                  for i in slots(params))


def crossing_intervals(params, rpm):
    if not math.isfinite(rpm) or rpm<=0:
        raise ValueError('Positive finite RPM required')
    angles = crossing_angles(params)
    gaps = [(b-a)%360 for a,b in zip(angles,angles[1:]+angles[:1])]
    return {'angle_gaps_deg':gaps,'time_gaps_s':[gap/360*60/rpm for gap in gaps]}


def axial_layout(params):
    t = params['timing_visual_estimated']['value']
    p = params['accessory_visual_estimated']['value']
    back = t['pulley_center_x_mm']-t['pulley_width_mm']/2
    wheel_front = back-p['wheel_width_mm']
    pulley_front = wheel_front-p['pulley_width_mm']
    return {'back':back,'wheel_front':wheel_front,'pulley_front':pulley_front,
            'sensor_x':(back+wheel_front)/2,
            'washer_front':pulley_front-p['washer_width_mm'],
            'nut_front':pulley_front-p['washer_width_mm']-p['nut_width_mm']}
