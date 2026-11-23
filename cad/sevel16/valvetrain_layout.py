"""Provisional head interfaces and shared phase map for CAD and animation."""
from config import layout
from kinematics import COMPRESSION_TDC


def valves(params, frame):
    p = params['valvetrain_layout_estimated']['value']
    n = params['valvetrain_nominal']['value']
    timing = params['valve_timing_nominal']['value']
    base = params['cam_profile_estimated']['value']['base_radius_mm']
    if p['valve_axis_tilt_deg'] != 0:
        raise ValueError('This baseline currently supports parallel Z valve axes only')
    kinds = [('exhaust','intake'),('intake','exhaust'),('exhaust','intake'),('intake','exhaust')]
    rows = []
    for i,x in enumerate(layout(params,frame)['centers']):
        for sign,kind in zip((-1,1),kinds[i]):
            opening,closing = timing[kind+'_events_deg']
            peak_crank = (opening+closing)/2+COMPRESSION_TDC[i]
            shim_top = p['cam_axis_z_mm']-base-timing[kind+'_lash_mm']
            tappet_top = shim_top-n['shim_mm']
            stem_top = tappet_top-p['tappet_wall_mm']
            rows.append({'id':f'C{i+1}_{kind}','cylinder':i+1,'kind':kind,
                         'axis_origin_mm':[x+sign*p['valve_offset_x_mm'],p['valve_y_mm'],p['valve_face_closed_z_mm']],
                         'axis':[0,0,1],'shim_top_closed_z_mm':shim_top,
                         'tappet_top_closed_z_mm':tappet_top,
                         'tappet_bottom_closed_z_mm':tappet_top-p['tappet_height_mm'],
                         'stem_top_closed_z_mm':stem_top,
                         'lobe_local_rx_deg':(180-peak_crank/2)%360,
                         'peak_local_crank_deg':(opening+closing)/2})
    return rows
