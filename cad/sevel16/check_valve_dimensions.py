"""Measure valve-train interfaces from the assembled final B-reps."""
import json
import hashlib
from pathlib import Path
import FreeCAD as App
import Part
from config import OUTPUT, load, layout
from check_dimensions import cylinders
from kinematics import pose
from valvetrain_layout import valves


def run(doc):
    params,frame = load()
    p,n = params['valvetrain_layout_estimated']['value'],params['valvetrain_nominal']['value']
    state = pose(doc.Phase.ThetaDeg,params,frame)
    rows = []
    for row in valves(params,frame):
        x,y,_ = row['axis_origin_mm']
        actual = {}
        for label,key in [('Valve',row['kind']+'_head_mm'),('Valve','stem_mm'),
                          ('Guide','guide_inner_mm'),('Guide','guide_outer_mm'),('Tappet','tappet_mm')]:
            shape = doc.getObject(row['id']+'_'+label).Shape
            faces = cylinders(shape,n[key]/2,App.Vector(0,0,1))
            assert faces,(row['id'],key)
            assert all(abs(f.Center.x-x)<1e-7 and abs(f.Center.y-y)<1e-7 for f in faces)
            actual[key] = 2*faces[0].Radius
        lift = state['cylinders'][row['cylinder']-1]['valve_lifts_mm'][row['kind']]
        gaps = {}
        for kind in ('inner','outer'):
            shape = doc.getObject(row['id']+'_'+kind.title()+'Spring').Shape
            seat = doc.getObject(row['id']+'_'+kind.title()+'SpringSeat').Shape
            retainer = doc.getObject(row['id']+'_Retainer').Shape
            # Untessellated spline bounds can exceed the spring by over 1 mm.
            # Measure exact extrema and corroborate with the actual solid interfaces.
            bounds = shape.optimalBoundingBox(False)
            lower = bounds.ZMin-seat.BoundBox.ZMax
            upper = retainer.BoundBox.ZMin-bounds.ZMax
            assert -1e-6<=lower<0.02 and -1e-6<=upper<0.02,(row['id'],kind,lower,upper)
            distances = [shape.distToShape(other)[0] for other in (seat,retainer)]
            overlaps = [shape.common(other).Volume for other in (seat,retainer)]
            assert max(abs(a-b) for a,b in zip(distances,(lower,upper)))<1e-5
            assert max(map(abs,overlaps))<1e-5,(row['id'],kind,overlaps)
            gaps[kind] = {'lower_mm':lower,'upper_mm':upper,'lift_mm':lift,
                          'brep_distances_mm':distances,'overlap_volumes_mm3':overlaps}
        rows.append({'id':row['id'],'diameters_mm':actual,'unground_end_gaps':gaps})
    journals = []
    for i,x in enumerate(layout(params,frame)['supports']):
        j = p['cam_diagram_indices_in_positive_x'][i]
        diameter = n['cam_journal_diameters_diagram_order_mm'][j]
        faces = [f for f in doc.Camshaft.Shape.Faces if isinstance(f.Surface,Part.Cylinder)
                 and abs(f.Surface.Radius-diameter/2)<1e-7 and f.BoundBox.XMin<x<f.BoundBox.XMax]
        assert len(faces)==1
        assert abs(faces[0].Surface.Center.z-p['cam_axis_z_mm'])<1e-7
        carrier = doc.getObject(f'CamCap{i+1}') or doc.CamCarrier
        housing = n['cam_housing_diameters_diagram_order_mm'][j]
        housing_faces = [f for f in carrier.Shape.Faces if isinstance(f.Surface,Part.Cylinder)
                         and abs(f.Surface.Radius-housing/2)<1e-7
                         and f.BoundBox.XMin<x<f.BoundBox.XMax
                         and abs(abs(f.Surface.Axis.x)-1)<1e-7]
        assert housing_faces
        assert all(abs(f.Surface.Center.y)<1e-7 and
                   abs(f.Surface.Center.z-p['cam_axis_z_mm'])<1e-7 for f in housing_faces)
        journals.append({'x_mm':x,'diameter_mm':2*faces[0].Surface.Radius,
                         'housing_diameter_mm':housing,'diametral_clearance_mm':housing-diameter})
    report = {'status':'PASS_DIMENSIONS_ONLY','document':doc.Name,'theta_deg':doc.Phase.ThetaDeg,
              'source_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
              'parameter_sha256':hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest(),
              'valves':rows,'journals':journals,'evidence_status':frame['status'],
              'spring_bounds_method':'optimalBoundingBox(False), corroborated by B-rep distance and intersection',
              'limits':['Journal end mapping remains provisional',
                        'Unground spring ends leave less than 0.02 mm axial gap in this pose']}
    (OUTPUT/f'reports/{doc.Name}_valve_dimensions.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def check_bottom_reuse(doc, original):
    assert doc.Phase.ThetaDeg==original.Phase.ThetaDeg==0
    differences = {}
    for obj in original.Objects:
        if not hasattr(obj,'Shape'):
            continue
        a,b = obj.Shape,doc.getObject(obj.Name).Shape
        delta = abs(a.cut(b).Volume)+abs(b.cut(a).Volume)
        assert delta<1e-5,(obj.Name,delta)
        differences[obj.Name] = delta
    assert len(differences)==68
    report = {'status':'PASS_BOTTOM_END_REUSE','source':original.FileName,
              'destination':doc.FileName,'theta_deg':0,'symmetric_difference_mm3':differences}
    (OUTPUT/f'reports/{doc.Name}_bottom_reuse.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
