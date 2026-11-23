"""Record actual CAD poses for an independent C++ renderer/loader smoke test."""
import json
from pathlib import Path
import FreeCAD as App
import MeshPart
import Part
from assembly import apply_pose
from config import load, OUTPUT
from mesh_obj import encode


def record(folder, part_id, mesh_path, batches, placement, bounds, color, visible):
    basis = App.Rotation(App.Vector(1,0,0),-90)
    rotation = basis.multiply(placement.Rotation).multiply(basis.inverted())
    converted = App.Placement(basis.multVec(placement.Base)*0.001,rotation)
    matrix = list(converted.toMatrix().A)
    expected = [bounds.XMin, bounds.ZMin, -bounds.YMax,
                bounds.XMax, bounds.ZMax, -bounds.YMin]
    numbers = [*color[:3], *matrix, *(v*0.001 for v in expected), int(visible)]
    return [part_id+' '+json.dumps(str(mesh_path))+' '+batch+' '+
            ' '.join(f'{v:.12g}' for v in numbers)+'\n' for batch in batches]


def export_shape(shape, folder, prefix):
    local = shape.copy()
    local.Placement = App.Placement()
    mesh = MeshPart.meshFromShape(Shape=local,LinearDeflection=0.08,
                                 AngularDeflection=0.2,Relative=False)
    assert mesh.isSolid()
    data, digest, batches = encode(*mesh.Topology)
    path = folder/(prefix+digest[:20]+'.obj')
    if not path.exists():
        path.write_bytes(data)
    return path, batches


def run(doc, folder, angles=(0,90,359,720), params=None):
    folder = Path(folder)
    manifest = json.loads((folder/'parts_manifest.json').read_text())
    _,frame = load()
    if params is None:
        params = json.loads((OUTPUT/f'reports/{doc.Name}.parameters.json').read_text())
    initial = doc.Phase.ThetaDeg
    paths = []
    fixed_bounds = {}
    try:
        for theta in angles:
            apply_pose(doc,theta,params,frame)
            lines = []
            for row in manifest['parts']:
                obj = doc.getObject(row['source_object'])
                path, batches = folder/row['mesh_file'], row['mesh_batches']
                if obj.MotionType=='spring':
                    path, batches = export_shape(obj.Shape,folder,'spring_pose_')
                visible = obj.ViewObject.Visibility if App.GuiUp else True
                bounds = fixed_bounds.get(obj.Name)
                if bounds is None:
                    bounds = obj.Shape.optimalBoundingBox(False)
                    if obj.MotionType=='fixed':
                        fixed_bounds[obj.Name] = bounds
                for batch in batches:
                    material = row.get('material_bindings',{}).get(batch)
                    color = manifest['materials'][material]['rgb'] if material else row['visual_material']['rgb']
                    lines.extend(record(folder,obj.PartId,path,[batch],obj.Placement,bounds,color,visible))
            path = folder/f'pose_{theta:03d}.txt'
            path.write_text(''.join(lines))
            paths.append(str(path))
    finally:
        apply_pose(doc,initial,params,frame)
    # Offset pivot, noncommuting rotations, two instances, two material colors.
    box = Part.makeBox(86.4,33.7,67.4,App.Vector(-7,-11,-13))
    local = Part.makeCompound([box])
    mesh_path,batches = export_shape(local,folder,'calibration_')
    rotation = App.Rotation(App.Vector(0,0,1),37).multiply(
        App.Rotation(App.Vector(1,0,0),23))
    lines = []
    for i,color in enumerate([(0.8,0.3,0.1),(0.1,0.5,0.8)]):
        shape = local.copy()
        shape.Placement = App.Placement(App.Vector(24+i*160,-12,54),rotation)
        lines.extend(record(folder,'calibration_'+str(i),mesh_path,batches,
                            shape.Placement,shape.optimalBoundingBox(False),color,True))
    path = folder/'calibration_pose.txt'
    path.write_text(''.join(lines))
    paths.append(str(path))
    print(json.dumps({'pose_inputs':paths,'restored_theta':initial}))
    return paths
