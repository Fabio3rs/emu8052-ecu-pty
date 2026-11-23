"""Verify a relocated package with its own sources, inputs and native loader."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root):
    root = Path(root).resolve()
    index = json.loads((root/'delivery.json').read_text())
    def inside(relative):
        path = (root/relative).resolve()
        assert path.is_relative_to(root),relative
        return path
    for relative,digest in index['files'].items():
        assert sha(inside(relative))==digest,relative
    folder = inside(index['mesh_folder'])
    manifest = json.loads((folder/'parts_manifest.json').read_text())
    original = json.loads((folder/'original_parts_manifest.json').read_text())
    expected = dict(original,source_fcstd=manifest['source_fcstd'],
                    portable_delivery=manifest['portable_delivery'])
    assert manifest==expected, 'Relocation must not change geometry, materials or transforms'
    assert sha(inside(manifest['source_fcstd']))==index['source_sha256']==manifest['source_sha256']
    assert sha(inside('build/sevel-cad/parameters.json'))==index['parameter_sha256']
    for row in manifest['meshes'].values():
        assert sha(folder/row['file'])==row['sha256']
    historical = json.loads((folder/'renderer_checks.json').read_text())
    assert sha(folder/'original_parts_manifest.json')==historical['manifest_sha256']
    paths = []
    for filename,digest in historical['pose_inputs_sha256'].items():
        original_path = folder/'original_pose_inputs'/filename
        assert sha(original_path)==digest
        before = [shlex.split(s) for s in original_path.read_text().splitlines()]
        after = [shlex.split(s) for s in (folder/filename).read_text().splitlines()]
        assert len(before)==len(after)
        for a,b in zip(before,after):
            assert len(a)==len(b)==29 and a[0]==b[0] and a[2:]==b[2:]
            assert inside(b[1]).parent==folder and inside(b[1]).is_file()
            assert Path(a[1]).name==Path(b[1]).name
        paths.append(str((folder/filename).relative_to(root)))
    verification = root/'verification'
    verification.mkdir(exist_ok=True)
    env = dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    def execute(args):
        result = subprocess.run(args,cwd=root,env=env,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+result.stderr
        return result
    tests = execute([sys.executable,'-m','unittest','discover','-s','cad/sevel16','-p','test_*.py','-v'])
    (verification/'analytic_tests.txt').write_text(tests.stdout+tests.stderr)
    binary = verification/'check_mesh_renderer'
    execute(['c++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Iinclude',
             '-Ithird_party/open-engine-sim/include','cad/sevel16/check_mesh_renderer.cpp',
             'third_party/open-engine-sim/src/authored_mesh_library.cpp','-o',str(binary)])
    result = execute([str(binary),*paths])
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows)==len(paths)==len(historical['poses'])
    old = {Path(r['pose']).name:r for r in historical['poses']}
    for row in rows:
        prior = old[Path(row['pose']).name]
        assert row['status']=='PASS_RENDERER_POSE_ONLY' and row['parts']==prior['parts']
        assert abs(row['max_bbox_error_m']-prior['max_bbox_error_m'])<1e-12
    for relative,digest in index['files'].items():
        assert sha(inside(relative))==digest,relative
    report = {'status':'PASS_RELOCATED_SOURCES_AND_RENDERER','root_tested':str(root),
        'delivery_index_sha256':sha(root/'delivery.json'),'files_verified':len(index['files']),
        'source_sha256':index['source_sha256'],'parameter_sha256':index['parameter_sha256'],
        'renderer_recompiled':True,'poses':rows,'transforms_and_materials_preserved':True,
        'unit_test_output_sha256':sha(verification/'analytic_tests.txt'),
        'limits':'Does not re-run full FreeCAD B-rep collision scans or certify remaining visual work'}
    (verification/'relocation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='poses'}))
    return report


if __name__=='__main__':
    run(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[2])
