"""Publish the OBJ manifest and its exact CAD rig into a relocatable Lab package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import subprocess

from config import OUTPUT
from timing_layout import path as belt_path
from runtime_mesh_cache import resolve_payloads
from runtime_registry import registry_lock


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scene_group(row):
    name = row['source_object']
    for prefix, group in (
        ('Spark', 'spark_plugs'), ('IntakeManifold', 'intake'), ('ExhaustManifold', 'exhaust'),
        ('OilPan', 'oil_pan'), ('OilDrain', 'oil_pan'), ('ValveCover', 'cover'),
        ('OilFiller', 'cover'), ('CamCarrier', 'head'), ('Head', 'head'), ('Carrier', 'head'),
        ('Block', 'block'), ('MainCap', 'block'), ('CorePlug', 'block'), ('Timing', 'timing'),
        ('Tensioner', 'timing'), ('Auxiliary', 'accessories')):
        if prefix in name:
            return group
    return {'fixed':'accessories','piston':'pistons','rod':'rods','spring':'springs',
            'valve':'valves'}.get(row['motion_type'],row['motion_type'])


def publish(folder, destination, parameters, datum, checker):
    with registry_lock(destination):
        return _publish(folder,destination,parameters,datum,checker)


def _publish(folder, destination, parameters, datum, checker):
    source = folder/'parts_manifest.json'
    manifest = json.loads(source.read_bytes())
    params, frame = (json.loads(p.read_bytes()) for p in (parameters, datum))
    generator = manifest['generator']
    if (sha(parameters), sha(datum)) != (generator['parameter_sha256'], generator['datum_sha256']):
        raise ValueError('Parameters or datum differ from the checkpoint')
    if manifest['theta_deg'] != 0 or manifest['reference_status'] != frame['status']:
        raise ValueError('Checkpoint phase or datum status')
    layout = params['valvetrain_layout_estimated']['value']
    timing = params['timing_visual_estimated']['value']
    rig = dict(compression_tdc_deg=manifest['compression_tdc_deg'],
               radius_m=params['dimensions']['stroke_mm']['value']/2000,
               rod_m=params['moving_geometry_estimated']['value']['rod_length_mm']/1000,
               cam_phase_deg=params['cam_profile_estimated']['value']['global_phase_deg'],
               valves=params['valve_timing_nominal']['value'], springs=layout,
               belt_segments=belt_path(params,frame), pitch_mm=timing['pitch_mm'],
               crank_teeth=timing['crank_teeth'])
    for row in manifest['parts']:
        row['scene_group'] = scene_group(row)
    checkpoint = Path(manifest['source_fcstd'])
    if sha(checkpoint) != manifest['source_sha256']:
        raise ValueError('Checkpoint hash mismatch')
    proof = json.loads((folder/'renderer_checks.json').read_bytes())
    if proof['manifest_sha256'] != sha(source) or proof['status'] != 'PASS_EXISTING_RECORDING_RENDERER_ONLY':
        raise ValueError('Run check_mesh_package.py for this export')
    step = json.loads((folder.parent/'export_checks.json').read_bytes())
    if (step['status'] != 'PASS' or step['theta_deg'] != 0 or step['solids'] != len(manifest['parts'])
            or step['source_fcstd_sha256'] != sha(checkpoint) or step['step_sha256'] != sha(folder.parent/'assembly.step')):
        raise ValueError('STEP roundtrip evidence mismatch')
    checks = json.loads((folder/'mesh_checks.json').read_bytes())
    if (checks['status'] != 'PASS_MESH_EXPORT_ONLY' or checks['source_sha256'] != sha(checkpoint)
            or checks['parts'] != len(manifest['parts']) or checks['unique_meshes'] != len(manifest['meshes'])):
        raise ValueError('Mesh verification evidence mismatch')
    manifest['source_fcstd'] = checkpoint.name
    manifest['runtime'] = dict(schema_version=1, rig=rig, export_manifest_sha256=sha(source),
                               step_sha256=step['step_sha256'],
                               packager_sha256=hashlib.sha256(''.join(sha(Path(__file__).with_name(n+'.py'))
                                   for n in ('runtime_package','runtime_mesh_cache','timing_layout')).encode()).hexdigest(),
                               mesh_exporter_sha256=hashlib.sha256(''.join(sha(Path(__file__).with_name(n+'.py'))
                                   for n in ('export_meshes','material_regions','mesh_obj')).encode()).hexdigest())
    if not manifest['meshes'] or not manifest['parts']:
        raise ValueError('Empty package')
    destination.mkdir(parents=True, exist_ok=True)
    for mesh in manifest['meshes'].values():
        path = (folder/mesh['file']).resolve(strict=True)
        if path.parent != folder.resolve() or sha(path) != mesh['sha256']:
            raise ValueError('Damaged export: '+mesh['file'])
    paths = resolve_payloads(manifest,folder,destination,checkpoint)
    with tempfile.TemporaryDirectory(dir=destination) as tmp:
        stage = Path(tmp)/'package'
        stage.mkdir()
        for key,mesh in manifest['meshes'].items():
            filename = mesh['file']
            path = paths[key].resolve(strict=True)
            if Path(filename).name != filename or sha(path) != mesh['sha256']:
                raise ValueError('Invalid mesh '+filename)
            if path.is_relative_to(destination.resolve()):
                os.link(path,stage/filename)
            else:
                shutil.copyfile(path, stage/filename)
        (stage/'parts_manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        revision = sha(stage/'parts_manifest.json')
        subprocess.run([checker,stage],check=True)
        if (destination/'current.json').exists():
            subprocess.run([checker,destination,'--compare',stage],check=True)
        target = destination/revision
        if target.exists():
            for file in stage.iterdir():
                if sha(file) != sha(target/file.name):
                    raise ValueError('Existing revision damaged: '+str(target/file.name))
        else:
            stage.rename(target)
        pointer = Path(tmp)/'current.json'
        pointer.write_text(json.dumps({'schema_version':1,'asset_revision':revision})+'\n')
        os.replace(pointer,destination/'current.json')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('meshes', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--parameters', type=Path)
    parser.add_argument('--datum', type=Path, default=OUTPUT/'datums/reference_frame.json')
    parser.add_argument('--checker',type=Path,required=True)
    args = parser.parse_args()
    parameters = args.parameters or OUTPUT/'reports'/(args.meshes.parent.name+'.parameters.json')
    print(publish(args.meshes,args.destination,parameters,args.datum,args.checker))
