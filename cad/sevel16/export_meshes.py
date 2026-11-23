"""Export a saved zero-phase CAD checkpoint without changing its document."""
import hashlib
import json
from pathlib import Path
import FreeCAD as App
import MeshPart
from config import OUTPUT, load
from mesh_obj import encode, decode, runtime_point
import material_regions


def run(doc):
    assert abs(doc.Phase.ThetaDeg)<1e-9
    parent = OUTPUT/'exports'/doc.Name
    manifest = json.loads((parent/'parts_manifest.json').read_text())
    assert manifest['source_sha256']==hashlib.sha256(Path(doc.FileName).read_bytes()).hexdigest()
    _,frame = load()
    params = json.loads((OUTPUT/f'reports/{doc.Name}.parameters.json').read_text())
    version = 1
    while (parent/f'meshes_v{version:03d}').exists():
        version += 1
    folder = parent/f'meshes_v{version:03d}'
    folder.mkdir()
    basis = App.Rotation(App.Vector(1,0,0),-90)
    geometry, checks = {}, []
    for row in manifest['parts']:
        color = row['visual_material']['rgb']
        row['visual_material'].update(rgb=color[:3], opacity=color[3] if len(color)==4 else 1)
        obj = doc.getObject(row['source_object'])
        assert obj.PartId==row['id'] and obj.Shape.isValid()
        shape = obj.Shape.copy()
        shape.Placement = App.Placement()
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.08,
                                     AngularDeflection=0.2, Relative=False)
        assert mesh.isSolid(), obj.Name
        vertices, triangles = mesh.Topology
        regions = material_regions.classify(obj.Name,vertices,triangles,params,frame)
        data, digest, batches = encode(vertices, triangles, regions)
        mesh_id = 'mesh_'+digest[:20]
        path = folder/(mesh_id+'.obj')
        if mesh_id not in geometry:
            path.write_bytes(data)
            geometry[mesh_id] = {'file':path.name, 'sha256':digest, 'batches':batches,
                                 'vertices':len(vertices), 'triangles':len(triangles)}
        loaded, loaded_triangles, gpu_sizes = decode(path)
        assert len(loaded)==len(vertices) and len(loaded_triangles)==len(triangles)
        rotation = App.Rotation(*row['rest_rotation_xyzw'])
        translation = App.Vector(*row['rest_translation_m'])
        error = max((rotation.multVec(App.Vector(*q))+translation-
                     basis.multVec(obj.Placement.multVec(p))*0.001).Length
                    for p,q in zip(vertices,loaded))
        assert error<1e-8, (obj.Name, error)
        volume = sum(sum(a[i]*((b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2],
                              b[0]*c[1]-b[1]*c[0])[i]) for i in range(3))/6
                     for a,b,c in loaded_triangles)
        volume_error = abs(volume*1e9-shape.Volume)/shape.Volume
        assert volume>0 and volume_error<0.015, (obj.Name,volume_error)
        cad_bounds = shape.optimalBoundingBox(False)
        bounds_error = max(abs(getattr(mesh.BoundBox,k)-getattr(cad_bounds,k))
                           for k in ('XMin','XMax','YMin','YMax','ZMin','ZMax'))
        assert bounds_error<0.25, (obj.Name,bounds_error)
        row.update(mesh_id=mesh_id, mesh_status='EXPORTED_LOCAL_METERS',
                   mesh_batches=batches, mesh_file=path.name)
        material_regions.bind(row,batches,manifest)
        checks.append({'id':row['id'], 'world_vertex_roundtrip_error_m':error,
                       'relative_volume_error':volume_error, 'bbox_error_mm':bounds_error,
                       'max_gpu_batch_vertices':max(gpu_sizes.values()),
                       'closed_mesh':True, 'outward_winding_and_normals':True,
                       'material_triangles':{r:regions.count(r) for r in sorted(set(regions))},
                       'material_batches_complete':set(row['material_bindings'])==set(batches)})
    manifest['default_material_bindings'] = manifest['material_bindings']
    manifest['material_bindings'] = {row['id']:row['material_bindings'] for row in manifest['parts']}
    manifest.update(status='MESH_EXPORTED_VIEWER_VALIDATION_PENDING',
                    conversion_owner='cad/sevel16/export_meshes.py',
                    meshes=geometry, mesh_quality={'linear_deflection_mm':0.08,
                                                   'angular_deflection_rad':0.2,
                                                   'normal_crease_angle_deg':30})
    (folder/'parts_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    report = {'status':'PASS_MESH_EXPORT_ONLY', 'source_sha256':manifest['source_sha256'],
              'parts':len(checks), 'unique_meshes':len(geometry), 'checks':checks,
              'limits':'CAD checkpoint pose only; renderer load and animated poses still pending.'}
    (folder/'mesh_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'folder':str(folder),'parts':len(checks),'unique_meshes':len(geometry)}))
    return folder
