"""Measure the actual auxiliary journal and exercise its absolute GUI placements."""
import math
import FreeCAD as App
import Part
from assembly import apply_pose


def run(doc, params, frame):
    p = params['auxiliary_internal_estimated']['value']
    n = params['auxiliary_nominal']['value']
    pivot = doc.AuxiliaryFrontShaft.Placement.Base
    radii = []
    for face in doc.AuxiliaryFrontShaft.Shape.Faces:
        s = face.Surface
        if isinstance(s,Part.Cylinder) and abs(s.Axis.x)>.999999:
            q = face.optimalBoundingBox(False)
            if abs(q.XMin-p['rear_journal_x_mm'])<1e-7 and abs(q.XLength-p['rear_journal_width_mm'])<1e-7:
                radii.append(s.Radius)
                assert abs(s.Center.y-pivot.y)<1e-7 and abs(s.Center.z-pivot.z)<1e-7
    assert len(radii)==1 and abs(2*radii[0]-n['journal_diameters_mm'][1])<1e-7
    fixed = {name:doc.getObject(name).Placement.copy() for name in ('Block','AuxiliaryRearBush','AuxiliaryFrontBush')}
    ratio = params['timing_visual_estimated']['value']['crank_teeth']/params['timing_visual_estimated']['value']['aux_teeth']
    phase = params['timing_visual_estimated']['value']['aux_phase_deg']
    worst = 0.0
    try:
        for theta in range(0,721,5):
            apply_pose(doc,theta,params,frame,update_springs=False)
            a = doc.AuxiliaryFrontShaft.Placement
            angle = math.radians(theta*ratio+phase)
            wanted = App.Vector(0,math.cos(angle),math.sin(angle))
            worst = max(worst,(a.Rotation.multVec(App.Vector(0,1,0))-wanted).Length,(a.Base-pivot).Length)
            assert a==doc.AuxSprocket.Placement
            assert all(doc.getObject(name).Placement==placement for name,placement in fixed.items())
        assert worst<1e-10
    finally:
        apply_pose(doc,0,params,frame,update_springs=False)
    return {'phase_count':145,'max_rotation_vector_or_pivot_error':worst,
            'rear_journal_diameter_mm':2*radii[0],
            'same_placement_as_aux_sprocket':True,'both_bushes_and_block_fixed':True}
