"""Validate the inclined fixed casting against the retained 720-degree assembly."""
import json
import math
import Part
from config import OUTPUT, load, layout
from check_auxiliary import sha, difference, volume
from timing_sweeps import bounds, overlaps
from carrier_interface_envelopes import build, lower_bound
from valvetrain_layout import valves


def run(doc, baseline):
    params,frame = load()
    previous = json.loads((OUTPUT/f'reports/{baseline.Name}.parameters.json').read_text())
    assert {k:params[k] for k in previous}==previous
    proof_path = OUTPUT/f'reports/{baseline.Name}_auxiliary_validation.json'
    proof = json.loads(proof_path.read_text())
    assert proof['status']=='PASS_AUXILIARY_INCREMENT'
    assert proof['source_sha256']==sha(baseline.FileName)
    assert doc.Phase.ThetaDeg==baseline.Phase.ThetaDeg==0
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    assert len(objects)==189 and all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in objects)
    unchanged = {}
    for obj in objects:
        old = baseline.getObject(obj.Name)
        assert old is not None
        for prop in ('PartId','MotionType','CylinderId','ValveKind','SpringKind','RestBase'):
            assert getattr(obj,prop,None)==getattr(old,prop,None),(obj.Name,prop)
        if obj.Name!='CamCarrier':
            delta = difference(obj.Shape,old.Shape)
            assert delta<1e-5,(obj.Name,delta)
            unchanged[obj.Name] = delta
    assert len(unchanged)==188
    cage = doc.CamCarrier.Shape
    box = bounds(cage)
    envelopes = build(doc,params,frame,box.ZMin)
    intersections,excluded = {},{}
    for name,envelope in envelopes.items():
        v = volume(cage.common(envelope)) if overlaps(cage,envelope) else 0.0
        assert v<1e-5,(name,v)
        intersections[name] = v
    for obj in objects:
        if obj.Name=='CamCarrier' or obj.Name in envelopes:
            continue
        b = bounds(obj.Shape)
        # X stays fixed for every motion in this assembly (including rod swing).
        xgap = max(b.XMin-box.XMax,box.XMin-b.XMax)
        if xgap>1e-7:
            excluded[obj.Name] = {'full_cycle_x_gap_mm':xgap}
        else:
            zmax = lower_bound(obj,params,frame)
            assert zmax<box.ZMin,(obj.Name,zmax,box.ZMin)
            excluded[obj.Name] = {'full_cycle_upper_z_mm':zmax,'gap_mm':box.ZMin-zmax}
    assert len(intersections)+len(excluded)==188
    cylinders = [f.Surface for f in cage.Faces if isinstance(f.Surface,Part.Cylinder)]
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    journal_radii = []
    for i,x in enumerate(layout(params,frame)['supports']):
        j = p['cam_diagram_indices_in_positive_x'][i]
        radius = n['cam_housing_diameters_diagram_order_mm'][j]/2
        found = [c for c in cylinders if abs(c.Axis.x)>1-1e-9 and abs(c.Radius-radius)<1e-7
                 and abs(c.Center.y)<1e-7 and abs(c.Center.z-p['cam_axis_z_mm'])<1e-7
                 and abs(c.Center.x-(x-p['cam_journal_width_mm']/2-1))<1e-7]
        assert found,('missing bearing surface',i)
        journal_radii.append(radius)
    for row in valves(params,frame):
        x,y,_ = row['axis_origin_mm']
        assert any(abs(c.Axis.z)>1-1e-9 and abs(c.Center.x-x)<1e-7 and abs(c.Center.y-y)<1e-7
                   and abs(c.Radius-n['tappet_housing_mm']/2)<1e-7 for c in cylinders),row['id']
    slopes = []
    for face in cage.Faces:
        if isinstance(face.Surface,Part.Plane) and face.Area>1000:
            normal = face.normalAt(0,0)
            if abs(normal.x)<1e-7 and abs(normal.z)>0.9:
                slopes.append(math.degrees(math.atan(-normal.y/normal.z)))
    for key in ('base_slope_y_deg','top_slope_y_deg'):
        assert any(abs(s-params['carrier_section_estimated']['value'][key])<1e-7 for s in slopes)
    report = {'status':'PASS_INCLINED_CARRIER_INCREMENT','source_sha256':sha(doc.FileName),
              'baseline_sha256':sha(baseline.FileName),'baseline_proof_sha256':sha(proof_path),
              'parameter_sha256':sha(OUTPUT/'parameters.json'),'datum_sha256':sha(OUTPUT/'datums/reference_frame.json'),
              'unchanged_parts_symmetric_difference_mm3':unchanged,
              'full_cycle_envelope_intersections_mm3':intersections,'continuous_separations':excluded,
              'cam_housing_radii_mm':journal_radii,'tappet_bores_checked':8,'plane_slopes_y_deg':slopes,
              'limits':['Only fixed cage changed; previous assembly collision proof retained',
                        'Angles, contour and scallop side remain provisional; no calibrated catalogue dimensions',
                        'Lower head casting and curved block transition remain unfinished']}
    (OUTPUT/f'reports/{doc.Name}_carrier_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'unchanged':len(unchanged),
                      'envelopes':len(intersections),'separations':len(excluded),'slopes':slopes}))
    return report
