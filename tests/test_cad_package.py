"""Exercise CAD package validation and revision compatibility without a GPU or ROM."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from cad_fixture import package


def check(binary, root):
    baseline, candidate = root/'baseline',root/'candidate'
    original = package(baseline)
    package(candidate)
    manifest = candidate/'parts_manifest.json'
    def expect(valid, *args):
        proc = subprocess.run([binary,*args],text=True,capture_output=True)
        assert (proc.returncode == 0) == valid, (args,proc.stderr)
    def modify(path,value,compare=False):
        obj = deepcopy(original)
        node = obj
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        manifest.write_text(json.dumps(obj))
        expect(False,*([baseline,'--compare',candidate] if compare else [candidate]))
    expect(True,baseline,'--compare',candidate)
    for path,value in [
        (['schema'],'v900'),(['units','length'],'mm'),(['cad_to_runtime'],'changed basis'),
        (['parts',1,'id'],'cube'),(['parts',0,'motion_axis_local'],[0,0,1]),
        (['parts',0,'rest_rotation_xyzw'],[0,0,0,5]),(['parts',0,'rest_scale'],[1,2,1]),
        (['materials','fixture','opacity'],2),(['parts',0,'mesh_id'],'missing'),
        (['parts',0,'parent_id'],'missing'),(['parts',0,'mesh_batches'],[]),
        (['parts',0,'rest_translation_m'],[0,12,0])]:
        modify(path,value)
    modify(['generator','datum_sha256'],'b'*64,True)
    modify(['parts',0,'rest_translation_m'],[0,0,0],True)
    modify(['parts',0,'scene_group'],'another',True)
    mesh_id = original['parts'][0]['mesh_id']
    mesh = original['meshes'][mesh_id]
    name = mesh['file']
    modify(['meshes',mesh_id,'file'],'../baseline/'+name)
    modify(['meshes',mesh_id,'sha256'],'e'*64)
    modify(['parts',0,'material_bindings',mesh['batches'][0]],'missing')
    manifest.write_text(json.dumps(original).replace('"theta_deg": 0','"theta_deg": 0,"theta_deg": 0'))
    expect(False,candidate)
    manifest.write_text(json.dumps(original))
    obj_path = candidate/name
    obj_path.unlink()
    obj_path.symlink_to(baseline/name)
    expect(False,candidate)
    obj_path.unlink()
    text = (baseline/name).read_text()
    damaged = text.replace('f ','f 65536//1 ',1)
    lines = text.splitlines()
    del lines[next(i for i,line in enumerate(lines) if line.startswith('f '))]
    for bad in (damaged,text.replace('vn ','vn nan ',1),'\n'.join(lines)+'\n'):
        obj = deepcopy(original)
        sha = hashlib.sha256(bad.encode()).hexdigest()
        key = 'mesh_'+sha[:20]
        obj['meshes'][key] = dict(obj['meshes'].pop(mesh_id),sha256=sha)
        for part in obj['parts']:
            if part['mesh_id']==mesh_id: part['mesh_id'] = key
        manifest.write_text(json.dumps(obj))
        obj_path.write_text(bad)
        expect(False,candidate)
    obj_path.write_text(text)
    modified = deepcopy(original)
    modified['parts'].pop()
    modified['parts'].append(dict(modified['parts'][0],id='added-component'))
    manifest.write_text(json.dumps(modified))
    expect(True,baseline,'--compare',candidate)
    manifest.unlink()
    manifest.symlink_to(baseline/'parts_manifest.json')
    expect(False,candidate)
    print('PASS relocation, additions/removals, incompatible rig, datum, units, topology, paths and hashes')


if __name__ == '__main__':
    with TemporaryDirectory() as tmp:
        check(Path(sys.argv[1]).resolve(),Path(tmp))
