"""Detached-shape validation of new head parts against the retained assembly."""
from itertools import combinations
from check_auxiliary import volume
from timing_sweeps import bounds, overlaps


def scan(shapes,envelopes):
    checks,failures = [],[]
    for name,shape in shapes.items():
        assert shape.isValid() and len(shape.Solids)==1,name
        box = bounds(shape)
        for other,item in envelopes.items():
            if 'maximum_z' in item:
                gap = box.ZMin-item['maximum_z']
                assert gap>0,(name,other,gap)
                checks.append({'pair':[name,other],'method':item['method'],'gap_mm':gap})
            elif 'minimum_z' in item:
                gap = item['minimum_z']-box.ZMax
                assert gap>0,(name,other,gap)
                checks.append({'pair':[name,other],'method':item['method'],'gap_mm':gap})
            else:
                intersection = volume(shape.common(item['shape'])) if overlaps(shape,item['shape']) else 0.0
                checks.append({'pair':[name,other],'method':item['method'],'intersection_mm3':intersection})
                if intersection>1e-5:
                    failures.append(checks[-1])
    for (a,x),(b,y) in combinations(shapes.items(),2):
        intersection = volume(x.common(y)) if overlaps(x,y) else 0.0
        checks.append({'pair':[a,b],'method':'new fixed parts','intersection_mm3':intersection})
        if intersection>1e-5:
            failures.append(checks[-1])
    return {'status':'FAIL_HEAD_INCREMENT' if failures else 'PASS_HEAD_INCREMENT_GEOMETRY',
            'pairs_checked':len(checks),'checks':checks,'failures':failures,
            'tolerance_mm3':1e-5,'scope':'Three fixed additions versus all 189 retained parts; continuous bounds'}
