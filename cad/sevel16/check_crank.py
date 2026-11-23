"""B-rep clearance scan against stationary shapes, using a broad-phase filter."""
import json
import math
import FreeCAD as App
import Part
from config import OUTPUT, load, layout


def overlap(a, b):
    return all(getattr(a,axis+'Max') > getattr(b,axis+'Min') and
               getattr(b,axis+'Max') > getattr(a,axis+'Min') for axis in 'XYZ')


def scan(local_shape, stationary, height, angles):
    checks, collisions = [], []
    for theta in angles:
        moving = local_shape.copy()
        moving.Placement = App.Placement(App.Vector(0,0,-height),App.Rotation(App.Vector(1,0,0),theta))
        for name, fixed in stationary:
            filtered = not overlap(moving.BoundBox,fixed.BoundBox)
            common = None if filtered else moving.common(fixed)
            volume = 0 if common is None or common.isNull() else common.Volume
            row = {'theta_deg':theta,'pair':['Crankshaft',name],'volume_mm3':volume,
                   'bbox_filtered':filtered}
            checks.append(row)
            if volume > 1e-5:
                collisions.append(row)
    return {'status':'FAIL' if collisions else 'PASS','checks':checks,
            'collisions':collisions,'volume_tolerance_mm3':1e-5,
            'scope':'crank vs block and five caps only; other parts not yet built',
            'expected_contact_exceptions':[]}


def run(doc, angles=range(0,361,5), suffix=''):
    params, frame = load()
    local = doc.Crankshaft.Shape.copy()
    local.Placement = App.Placement()
    stationary = [(o.Name,o.Shape.copy()) for o in doc.Stationary.Group
                  if o.Name == 'Block' or o.Name.startswith('MainCap')]
    report = scan(local,stationary,layout(params,frame)['height'],angles)
    # Verify actual cylindrical faces at all five main and four throw centers.
    radii = [params['moving_nominal'][key]['value']/2
             for key in ['main_journal_diameter_mm','crankpin_diameter_mm']]
    surfaces = [f.Surface for f in local.Faces if isinstance(f.Surface,Part.Cylinder)]
    observed = [sum(abs(s.Radius-r)<1e-7 and abs(abs(s.Axis.x)-1)<1e-7 for s in surfaces)
                for r in radii]
    assert observed == [5,4], observed
    report['journal_cylindrical_faces'] = {'main':observed[0],'pin':observed[1]}
    report['document'] = doc.Name
    report['valid'] = local.isValid()
    path = OUTPUT/f'reports/{doc.Name}_crank_clearance{suffix}.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'samples':len(report['checks']),
                      'collisions':len(report['collisions']), 'file':str(path)}))
    return report
