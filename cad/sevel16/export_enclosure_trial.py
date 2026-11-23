"""Exchange files for the validated block candidate, not the full assembly."""
import json
from pathlib import Path
import Part
import MeshPart
from proof_chain import read, sha
from mesh_obj import encode, decode


def run(folder):
    folder = Path(folder)
    validation = read(folder/'validation.json')
    assert validation['status']=='PASS_AUXILIARY_ENCLOSURE'
    assert sha(folder/'block.brep')==validation['block_sha256']
    assert not (folder/'block.step').exists() and not (folder/'block.obj').exists()
    shape = Part.read(str(folder/'block.brep'))
    assert shape.isValid() and len(shape.Solids)==1
    shape.exportStep(str(folder/'block.step'))
    reloaded = Part.read(str(folder/'block.step'))
    step_error = abs(reloaded.Volume-shape.Volume)/shape.Volume
    assert reloaded.isValid() and len(reloaded.Solids)==1 and step_error<1e-6
    mesh = MeshPart.meshFromShape(Shape=shape,LinearDeflection=.08,AngularDeflection=.2,Relative=False)
    assert mesh.isSolid()
    vertices,triangles = mesh.Topology
    data,digest,batches = encode(vertices,triangles)
    (folder/'block.obj').write_bytes(data)
    loaded,faces,gpu_sizes = decode(folder/'block.obj')
    assert len(loaded)==len(vertices) and len(faces)==len(triangles)
    volume = sum(sum(a[i]*((b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],
                           b[0]*c[1]-b[1]*c[0])[i]) for i in range(3))/6 for a,b,c in faces)
    mesh_error = abs(volume*1e9-shape.Volume)/shape.Volume
    assert volume>0 and mesh_error<.015
    report = {'status':'PASS_ENCLOSURE_EXPORT_ONLY','source_brep_sha256':sha(folder/'block.brep'),
              'step_sha256':sha(folder/'block.step'),'obj_sha256':digest,
              'step_relative_volume_error':step_error,'mesh_relative_volume_error':mesh_error,
              'vertices':len(vertices),'triangles':len(triangles),'closed_mesh':True,
              'step_unit':'mm','obj_unit':'m','obj_basis':'(x,z,-y); master origin retained',
              'scope':'One corrected block candidate; full assembly export and GUI review remain pending'}
    (folder/'export_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report
