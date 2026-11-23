"""Pure timing geometry in the YZ plane; signed radii handle the back idler."""
import math
from config import layout


def wheels(params, frame):
    p = params['timing_visual_estimated']['value']
    c = params['casting_visual_estimated']['value']
    v = params['valvetrain_layout_estimated']['value']
    assert p['cam_teeth']==2*p['crank_teeth']
    assert all(isinstance(p[k],int) and p[k]>=12 for k in ('cam_teeth','crank_teeth','aux_teeth'))
    result = []
    for name,y,z,key in [('Cam',0,v['cam_axis_z_mm'],'cam_teeth'),
                         ('Aux',c['aux_y'],c['aux_z'],'aux_teeth'),
                         ('Crank',0,-layout(params,frame)['height'],'crank_teeth'),
                         ('Tensioner',p['tensioner_y_mm'],p['tensioner_z_mm'],None)]:
        pitch = p[key]*p['pitch_mm']/(2*math.pi) if key else p['tensioner_radius_mm']
        tip = pitch-p['tooth_tip_below_pitch_mm'] if key else pitch
        radius = tip+p['belt_visual_clearance_mm']+p['belt_thickness_mm']/2
        result.append({'name':name,'center':(y,z),'pitch_radius':pitch,'tip_radius':tip,
                       'path_radius':radius if key else -radius,'teeth':p[key] if key else None})
    return result


def path(params, frame):
    rows = wheels(params,frame)
    tangents = []
    for a,b in zip(rows,rows[1:]+rows[:1]):
        dy,dz = (b['center'][i]-a['center'][i] for i in range(2))
        distance = math.hypot(dy,dz)
        if distance<=abs(a['path_radius']-b['path_radius']):
            raise ValueError('Pulley centers cannot support the requested tangent')
        k = (a['path_radius']-b['path_radius'])/distance
        if abs(k)>=1:
            raise ValueError('Pulley circles have no requested common tangent')
        h = math.sqrt(1-k*k)
        normal = ((k*dy+h*dz)/distance,(k*dz-h*dy)/distance)
        points = [tuple(w['center'][j]+w['path_radius']*normal[j] for j in range(2)) for w in (a,b)]
        tangents.append({'from':a['name'],'to':b['name'],'normal':normal,'points':points})
    segments = []
    for i,w in enumerate(rows):
        incoming = tangents[i-1]['points'][1]
        outgoing = tangents[i]['points'][0]
        start = math.atan2(incoming[1]-w['center'][1],incoming[0]-w['center'][0])
        end = math.atan2(outgoing[1]-w['center'][1],outgoing[0]-w['center'][0])
        sign = 1 if w['path_radius']>0 else -1
        sweep = sign*((sign*(end-start))%(2*math.pi))
        if not 0<abs(sweep)<math.pi*1.8:
            raise ValueError('Degenerate or excessive pulley wrap')
        segments.append({'kind':'arc','wheel':w['name'],'center':w['center'],
                         'radius':abs(w['path_radius']),'start':start,'sweep':sweep,
                         'sign':sign,'points':[incoming,outgoing]})
        segments.append({'kind':'line',**tangents[i]})
    return segments


def rotations(theta, params):
    if not math.isfinite(theta):
        raise ValueError('Finite phase required')
    p = params['timing_visual_estimated']['value']
    crank_pitch = p['crank_teeth']*p['pitch_mm']/(2*math.pi)
    return {'aux':(theta*p['crank_teeth']/p['aux_teeth']+p['aux_phase_deg'])%360,
            'tensioner':(-theta*crank_pitch/p['tensioner_radius_mm']+p['tensioner_phase_deg'])%360}
