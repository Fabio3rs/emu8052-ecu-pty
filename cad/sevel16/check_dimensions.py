"""Measure generated B-reps and the actual sealing face, not construction operands."""
import json
import hashlib
from pathlib import Path
import FreeCAD as App
import Part
from config import OUTPUT, load, layout
from kinematics import pose
from stationary import _sump


def cylinders(shape, radius, axis):
    return [f.Surface for f in shape.Faces if isinstance(f.Surface,Part.Cylinder)
            and abs(f.Surface.Radius-radius)<1e-7
            and abs(abs(f.Surface.Axis.dot(axis))-1)<1e-7]


def run(doc):
    params,frame = load()
    g = layout(params,frame)
    n = params['piston_rod_nominal']['value']
    state = pose(doc.Phase.ThetaDeg,params,frame)
    rows = []
    for c in state['cylinders']:
        i = c['cylinder']
        piston = doc.getObject(f'C{i}_Piston').Shape
        pin = doc.getObject(f'C{i}_Pin').Shape
        rod = doc.getObject(f'C{i}_Rod').Shape
        assert cylinders(piston,n['piston_diameter_mm']/2,App.Vector(0,0,1))
        assert cylinders(pin,n['pin_diameter_mm']/2,App.Vector(1,0,0))
        centers = []
        for key,expected in [('big_bearing_seat_mm',c['crankpin_mm']),
                             ('small_bushing_seat_mm',c['piston_pin_mm'])]:
            faces = cylinders(rod,n[key]/2,App.Vector(1,0,0))
            assert faces
            measured = faces[0].Center
            error = ((measured.y-expected[1])**2+(measured.z-expected[2])**2)**0.5
            assert error<1e-7
            centers.append([measured.y,measured.z])
        length = ((centers[1][0]-centers[0][0])**2+(centers[1][1]-centers[0][1])**2)**0.5
        assert abs(length-params['moving_geometry_estimated']['value']['rod_length_mm'])<1e-7
        rows.append({'cylinder':i,'rod_centers_yz_mm':centers,'rod_length_mm':length,
                     'piston_diameter_mm':n['piston_diameter_mm'],'pin_diameter_mm':n['pin_diameter_mm']})
    z = -params['block_visual_estimated']['value']['height']
    wire = _sump.outline(params,frame,z)
    footprint = Part.Face(wire)
    faces = [f for f in doc.Block.Shape.Faces if isinstance(f.Surface,Part.Plane)
             and abs(f.BoundBox.ZMin-z)<1e-7 and f.BoundBox.ZLength<1e-7]
    assert faces
    outside_area = sum(f.cut(footprint).Area for f in faces)
    assert outside_area<1e-6
    distances = [doc.Block.Shape.distToShape(Part.Vertex(e.valueAt((e.FirstParameter+e.LastParameter)/2)))[0]
                 for e in wire.Edges]
    assert max(distances)<1e-6
    report = {'status':'PASS','document':doc.Name,'theta_deg':doc.Phase.ThetaDeg,
              'source_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
              'parameter_sha256':hashlib.sha256((OUTPUT/'parameters.json').read_bytes()).hexdigest(),
              'parts':[{'id':o.PartId,'valid':o.Shape.isValid(),'solids':len(o.Shape.Solids),
                        'volume_mm3':o.Shape.Volume} for o in doc.Objects if hasattr(o,'Shape')],
              'measurements':rows,'sealing_face_outside_area_mm2':outside_area,
              'seal_maximum_boundary_distance_mm':max(distances),
              'seal_test_note':'Actual planar face tested. Old 0.1-mm slice test is not applicable to a wall widening immediately above the sealing plane.',
              'evidence_status':frame['status']}
    assert all(r['valid'] and r['solids']==1 and r['volume_mm3']>0 for r in report['parts'])
    path = OUTPUT/f'reports/{doc.Name}_dimensions.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(str(path))
    return report
