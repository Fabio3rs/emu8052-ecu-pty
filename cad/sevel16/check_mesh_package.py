"""Run the existing-renderer probe and persist integrity/periodicity evidence."""
import hashlib
import json
import math
import shlex
from pathlib import Path
import subprocess
import sys
from config import ROOT, OUTPUT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder/'parts_manifest.json').read_text())
    for mesh in manifest['meshes'].values():
        assert sha(folder/mesh['file'])==mesh['sha256']
    assert sha(Path(manifest['source_fcstd']))==manifest['source_sha256']
    assert all(len(p['visual_material']['rgb'])==3 for p in manifest['parts'])
    by_id = {p['id']:p for p in manifest['parts']}
    region_parts = [p for p in manifest['parts'] if 'material_bindings' in p]
    if 'default_material_bindings' in manifest:
        assert len(region_parts)==len(manifest['parts'])
        assert manifest['material_bindings']=={p['id']:p['material_bindings'] for p in region_parts}
    for part in region_parts:
        assert set(part['material_bindings'])==set(part['mesh_batches'])
        assert all(m in manifest['materials'] for m in part['material_bindings'].values())
    for theta in (0,90,359,720):
        for line in (folder/f'pose_{theta:03d}.txt').read_text().splitlines():
            fields = shlex.split(line)
            part = by_id[fields[0]]
            if 'material_bindings' not in part:
                continue
            binding = part['material_bindings'].get(fields[2])
            assert binding or part['motion_type']=='spring'
            expected = manifest['materials'][binding]['rgb'] if binding else part['visual_material']['rgb']
            assert max(abs(float(v)-c) for v,c in zip(fields[3:6],expected))<1e-9
    inputs = [folder/'calibration_pose.txt']
    inputs += [folder/f'pose_{theta:03d}.txt' for theta in (0,90,359,720)]
    separate = {p['id']:p for p in manifest['parts'] if p.get('transform_period_crank_deg')
                and abs(720/p['transform_period_crank_deg']-round(720/p['transform_period_crank_deg']))>1e-9}
    periodic = [folder/'pose_000.txt',folder/'pose_720.txt']
    own_period_checks = {}
    if separate:
        periodic = []
        for theta in (0,720):
            source = (folder/f'pose_{theta:03d}.txt').read_text().splitlines(keepends=True)
            path = folder/f'pose_{theta:03d}_periodic.txt'
            path.write_text(''.join(line for line in source if line.split()[0] not in separate))
            periodic.append(path)
        inputs += periodic
        def matrices(path):
            result = {}
            for line in path.read_text().splitlines():
                fields = shlex.split(line)
                assert len(fields)==29
                matrix = list(map(float,fields[6:22]))
                if fields[0] in result:
                    assert matrix==result[fields[0]]
                result[fields[0]] = matrix
            return result
        first,last = matrices(folder/'pose_000.txt'),matrices(folder/'pose_720.txt')
        for part_id,part in separate.items():
            delta = math.radians(720*part['angular_ratio_to_crank'])
            c,s = math.cos(delta),math.sin(delta)
            before,after = first[part_id],last[part_id]
            expected = before.copy()
            for j in range(3):
                expected[4+j] = c*before[4+j]-s*before[8+j]
                expected[8+j] = s*before[4+j]+c*before[8+j]
            error = max(abs(a-b) for a,b in zip(expected,after))
            assert error<1e-9,(part_id,error)
            own_period_checks[part_id] = {'period_crank_deg':part['transform_period_crank_deg'],
                                           'matrix_error':error}
    binary = OUTPUT/'check_mesh_renderer'
    result = subprocess.run([str(binary),*(str(p) for p in inputs)],
                            check=True,capture_output=True,text=True)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows)==len(inputs) and rows[0]['parts']==2
    assert all(r['parts']==len(manifest['parts']) for r in rows[1:5])
    assert all(r['parts']==len(manifest['parts'])-len(separate) for r in rows[5:])
    assert periodic[0].read_bytes()==periodic[1].read_bytes()
    assert Path(str(periodic[0])+'.svg').read_bytes()==Path(str(periodic[1])+'.svg').read_bytes()
    assert (folder/'pose_000.txt').read_bytes()!=(folder/'pose_090.txt').read_bytes()
    report = {'status':'PASS_EXISTING_RECORDING_RENDERER_ONLY',
              'scope':'OBJ loader + existing RecordingRenderer; not the interactive Lab UI',
              'source_fcstd_sha256':manifest['source_sha256'],
              'manifest_sha256':sha(folder/'parts_manifest.json'),
              'parts_with_primitive_materials':len(region_parts),
              'executable_sha256':sha(binary),
              'loader_source_sha256':sha(ROOT/'third_party/open-engine-sim/src/authored_mesh_library.cpp'),
              'pose_inputs_sha256':{p.name:sha(p) for p in inputs},
              'poses':rows, 'periodicity_0_720':'identical inputs/SVG for parts with compatible periods',
              'independent_period_checks':own_period_checks,
              'movement_0_90':'different absolute poses',
              'limits':'Four poses; no depth occlusion in SVG; continuous playback uses FreeCAD.'}
    (folder/'renderer_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'parts':len(manifest['parts']),
                      'max_bbox_error_m':max(r['max_bbox_error_m'] for r in rows)}))


if __name__=='__main__':
    run(sys.argv[1])
