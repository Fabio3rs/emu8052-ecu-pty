"""Synthetic convex cam support: h(alpha) = base + C(alpha), not a polar radius.

alpha is a cam angle in radians from the lobe nose normal. A flat follower
touches at h*n+h'*n'. Derivatives are with respect to CAM radians.
"""
import math


def support(alpha, params):
    n = params['valve_timing_nominal']['value']
    p = params['cam_profile_estimated']['value']
    # Both documented checking durations are 222 crank degrees.
    durations = [n[k][1]-n[k][0] for k in ('intake_events_deg','exhaust_events_deg')]
    if abs(durations[0]-durations[1])>1e-9:
        raise ValueError('This symmetric baseline requires equal checking durations')
    half_window_cam = math.radians(durations[0]/4)
    offset = (n['cam_height_mm']-n['checking_lash_mm'])/(1-math.cos(half_window_cam))
    nose_radius = p['base_radius_mm']+n['cam_height_mm']-offset
    epsilon = p['smoothing_mm']
    if not 0 < epsilon < min(nose_radius,n['intake_lash_mm'],n['exhaust_lash_mm']):
        raise ValueError('Invalid smoothing or base radius')
    t = n['cam_height_mm']+offset*(math.cos(alpha)-1)
    dt, ddt = -offset*math.sin(alpha), -offset*math.cos(alpha)
    if t >= epsilon:
        c, dc, ddc = t, dt, ddt
    elif t <= -epsilon:
        c, dc, ddc = 0.0, 0.0, 0.0
    else:
        u = (t+epsilon)/(2*epsilon)
        weight = 3*u*u-2*u*u*u
        c = 2*epsilon*(u**3-0.5*u**4)
        dc = weight*dt
        ddc = 3*u*(1-u)/epsilon*dt*dt+weight*ddt
    return p['base_radius_mm']+c, dc, ddc


def lift(local_crank_deg, kind, params):
    n = params['valve_timing_nominal']['value']
    opening, closing = n[kind+'_events_deg']
    center = (opening+closing)/2
    alpha = math.radians((local_crank_deg-center)/2)
    h, _, _ = support(alpha,params)
    displacement = h-params['cam_profile_estimated']['value']['base_radius_mm']
    return max(0,displacement-n[kind+'_lash_mm'])


def profile_point(alpha, params):
    h, dh, _ = support(alpha,params)
    return (h*math.sin(alpha)+dh*math.cos(alpha),
            h*math.cos(alpha)-dh*math.sin(alpha))


def profile_polygon(params, chord_tolerance_mm=0.002):
    """Adaptive convex contact polygon; error must also be checked by projection.

    Midpoint subdivision is a sampling strategy, not by itself a rigorous bound.
    The downstream CAD validator measures the resulting follower displacement.
    """
    if not 0 < chord_tolerance_mm < 0.1:
        raise ValueError('Invalid profile discretization tolerance')
    points = []

    def subdivide(a, b, depth):
        pa,pb = profile_point(a,params),profile_point(b,params)
        middle = profile_point((a+b)/2,params)
        dx,dy = pb[0]-pa[0],pb[1]-pa[1]
        distance = abs(dx*(middle[1]-pa[1])-dy*(middle[0]-pa[0]))/math.hypot(dx,dy)
        if distance > chord_tolerance_mm:
            if depth>=16:
                raise ValueError('Cam discretization failed to converge')
            subdivide(a,(a+b)/2,depth+1)
            subdivide((a+b)/2,b,depth+1)
        else:
            points.append(pa)
    for i in range(24):
        subdivide(i*math.pi/12,(i+1)*math.pi/12,0)
    return points
