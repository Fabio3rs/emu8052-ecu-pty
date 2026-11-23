"""Versioned mechanical STEP checkpoint with a nonzero-pivot calibration."""
import hashlib
import json
from pathlib import Path
import FreeCAD as App
import Part
import Import
from config import OUTPUT


def run(doc):
    assert doc.Name.startswith(('SEVEL_Moving_A2_','SEVEL_ValveTrain_A3_',
                               'SEVEL_Flywheel_A4_','SEVEL_Timing_A4_','SEVEL_Trigger_A4_',
                               'SEVEL_Auxiliary_A4_','SEVEL_Carrier_A3_','SEVEL_Head_A3_',
                               'SEVEL_Casting_A4_','SEVEL_Closures_A5_','SEVEL_Accessories_A5_'))
    assert hasattr(doc,'Phase')
    folder = OUTPUT/'exports'/doc.Name
    folder.mkdir(exist_ok=False)
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    path = folder/'assembly.step'
    Import.export(objects,str(path))
    shape = Part.read(str(path))
    source = Part.makeCompound([o.Shape for o in objects])
    error = abs(shape.Volume-source.Volume)/source.Volume
    assert shape.isValid() and len(shape.Solids)==len(objects)
    assert error < 1e-6
    # Two asymmetric instances, pivot offset, and two noncommuting rotations.
    pivot, offset = App.Vector(7,11,13),App.Vector(17,-23,41)
    rotation = App.Rotation(App.Vector(0,0,1),37).multiply(App.Rotation(App.Vector(1,0,0),23))
    placement = App.Placement(offset+pivot-rotation.multVec(pivot),rotation)
    probe = Part.makeBox(86.4,33.7,67.4)
    probe.Placement = placement
    second = probe.copy()
    second.translate(App.Vector(160,0,0))
    calibration = Part.makeCompound([probe,second])
    calibration.exportStep(str(folder/'calibration.step'))
    reloaded = Part.read(str(folder/'calibration.step'))
    vertex_error = max(min((v.Point-w.Point).Length for w in reloaded.Vertexes)
                       for v in calibration.Vertexes)
    assert vertex_error < 1e-6 and reloaded.isValid() and len(reloaded.Solids)==2
    assert (placement.multVec(pivot)-(pivot+offset)).Length<1e-8
    assert abs(reloaded.Volume-2*86.4*33.7*67.4)<1e-5
    report = {'status':'PASS','document':doc.Name,'unit':'mm','solids':len(shape.Solids),
              'theta_deg':doc.Phase.ThetaDeg,'relative_volume_error':error,
              'calibration_vertex_error_mm':vertex_error,
              'calibration_pivot_mm':list(pivot),'calibration_pivot_transformed_mm':list(pivot+offset),
              'step_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'source_fcstd_sha256':hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest(),
              'evidence_status':doc.Phase.EvidenceStatus,
              'limitations':'CAD geometry only. Runtime mesh, material and semantic pivot proof still pending.'}
    (folder/'export_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return folder
