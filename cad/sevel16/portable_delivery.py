"""Package an identified checkpoint without rewriting its historical evidence."""
import json
from pathlib import Path
import shlex
import shutil
import sys
from config import ROOT, OUTPUT
from proof_chain import sha


def run(name, mesh_version='meshes_v001'):
    assert Path(name).name==name and Path(mesh_version).name==mesh_version
    source = OUTPUT/'exports'/name/mesh_version
    manifest = json.loads((source/'parts_manifest.json').read_text())
    model = OUTPUT/'models'/f'{name}.FCStd'
    snapshot = OUTPUT/'reports'/f'{name}.parameters.json'
    assert manifest['source_sha256']==sha(model)
    consolidated = json.loads((OUTPUT/'reports/kinematics_validation.json').read_text())
    stage = next(r for r in consolidated['collision_proof_chain'] if r['document']==name)
    assert stage['parameter_snapshot_sha256']==sha(snapshot)
    stage_path = OUTPUT/stage['report']
    assert stage['report_sha256']==sha(stage_path)
    stage_report = json.loads(stage_path.read_text())
    assert stage_report['source_sha256']==sha(model)
    assert manifest['generator']['parameter_sha256']==stage_report['parameter_sha256']
    parameter_source = OUTPUT/'parameters.json'
    if sha(parameter_source)!=stage_report['parameter_sha256']:
        parameter_source = snapshot
    assert json.loads(parameter_source.read_text())==json.loads(snapshot.read_text())
    entrypoint = ROOT/manifest['generator']['entrypoint']
    assert manifest['generator']['entrypoint_sha256']==sha(entrypoint)
    renderer = json.loads((source/'renderer_checks.json').read_text())
    assert renderer['manifest_sha256']==sha(source/'parts_manifest.json')
    parent = OUTPUT/'deliveries'
    version = 1
    while (parent/f'{name}_v{version:03d}').exists():
        version += 1
    target = parent/f'{name}_v{version:03d}'
    target.mkdir(parents=True)
    def copy(path, relative=None):
        relative = Path(relative) if relative else path.relative_to(ROOT)
        assert not relative.is_absolute() and '..' not in relative.parts
        out = target/relative
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,out)
        return out
    for folder,patterns in [(ROOT/'cad/sevel16',('*.py','*.cpp','*.md')),
                            (OUTPUT/'generator',('*.py',)),
                            (OUTPUT/'datums',('*.json','*.svg')),
                            (OUTPUT/'models',('*.FCStd',)),
                            (OUTPUT/'reports',('*.json','*.md','*.txt'))]:
        for pattern in patterns:
            for path in sorted(folder.glob(pattern)):
                copy(path)
    for filename in ('GOAL_SEVEL_CONJUNTO_MOVEL_CINEMATICA.md','SEVEL_16_FREECAD_CODEX_SPEC.md'):
        copy(ROOT/filename)
    copy(ROOT/'.agents/skills/sevel-freecad-vision/scripts/build_reference_frame.py')
    for path in sorted((OUTPUT/'exports').rglob('*.json')):
        copy(path)
    for path in sorted((OUTPUT/'trials').rglob('*')):
        if path.is_file() and path.suffix in ('.json','.brep','.step'):
            copy(path)
    for path in sorted((OUTPUT/'evidence').glob(name+'*')):
        if path.suffix in ('.png','.json'):
            copy(path)
    for filename in ('assembly.step','calibration.step','export_checks.json'):
        copy(source.parent/filename)
    for path in sorted(source.iterdir()):
        if path.suffix in ('.obj','.json','.txt','.png'):
            copy(path)
    for filename in ('check_mesh_renderer',):
        copy(OUTPUT/filename)
    for filename in ('authored_mesh_library.h','render_math.h','renderer.h','shaders.h','ui_math.h'):
        copy(ROOT/'third_party/open-engine-sim/include'/filename)
    copy(ROOT/'third_party/open-engine-sim/src/authored_mesh_library.cpp')
    for filename in ('include/lab/RecordingRenderer.hpp','include/Lifetime.hpp'):
        copy(ROOT/filename)
    copy(parameter_source,'build/sevel-cad/parameters.json')
    mesh_relative = source.relative_to(ROOT)
    copied_meshes = target/mesh_relative
    shutil.copy2(copied_meshes/'parts_manifest.json',copied_meshes/'original_parts_manifest.json')
    manifest['source_fcstd'] = model.relative_to(ROOT).as_posix()
    manifest['portable_delivery'] = {'path_base':'package root',
        'original_manifest_sha256':sha(source/'parts_manifest.json'),
        'parameters':'build/sevel-cad/parameters.json',
        'parameter_snapshot_sha256':sha(snapshot),
        'parameter_note':'Original validated bytes when available; otherwise the validated parsed snapshot',
        'datum':'build/sevel-cad/datums/reference_frame.json',
        'reference_index':'build/sevel-cad/reports/moving_sources.json',
        'historical_reports':'Preserved verbatim; absolute source paths describe the original workspace'}
    (copied_meshes/'parts_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for path in sorted(copied_meshes.glob('*pose*.txt')):
        original_inputs = copied_meshes/'original_pose_inputs'
        original_inputs.mkdir(exist_ok=True)
        shutil.copy2(path,original_inputs/path.name)
        lines = []
        for line in path.read_text().splitlines():
            fields = shlex.split(line)
            assert len(fields)==29
            original = Path(fields[1]).resolve()
            assert original.parent==source.resolve() and original.is_file()
            relative = mesh_relative/original.name
            assert sha(target/relative)==sha(original)
            fields[1] = json.dumps(relative.as_posix())
            lines.append(' '.join(fields))
        path.write_text('\n'.join(lines)+'\n')
    files = {str(p.relative_to(target)):sha(p) for p in sorted(target.rglob('*')) if p.is_file()}
    index = {'schema':'sevel.portable-delivery.v1','status':'PACKAGED_AWAITING_RELOCATION_CHECK',
        'document':name,'goal_complete':False,'files':files,
        'mesh_folder':mesh_relative.as_posix(),'source_sha256':sha(model),
        'parameter_sha256':sha(parameter_source),'original_renderer_proof_sha256':sha(source/'renderer_checks.json'),
        'code_scope':'Current generator sources; historical report code hashes remain unchanged',
        'reference_files_included':False,
        'limits':['Reference photos/PDFs remain external and are identified in moving_sources.json',
                  'Bundled renderer binary requires a compatible Linux runtime; C++ sources are included',
                  'This package does not certify completion of outstanding casting/visual work']}
    (target/'delivery.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps({'folder':str(target),'files':len(files),'document':name}))
    return target


if __name__=='__main__':
    run(*sys.argv[1:])
