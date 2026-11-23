"""Stage the active runtime package, or atomically reactivate a verified revision."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cad/sevel16'))
from runtime_registry import registry_lock


def switch(source, destination, checker, revision=None):
    with registry_lock(destination):
        return _switch(source,destination,checker,revision)


def _switch(source, destination, checker, revision):
    source = source.resolve(strict=True)
    if revision is None:
        pointer = json.loads((source/'current.json').read_bytes())
        if pointer.get('schema_version') != 1:
            raise ValueError('Unsupported revision pointer')
        revision = pointer['asset_revision']
    if not re.fullmatch('[0-9a-f]{64}', revision):
        raise ValueError('Invalid revision digest')
    package = source/revision
    manifest = package/'parts_manifest.json'
    if package.resolve().parent != source or manifest.resolve().parent != package:
        raise ValueError('Manifest outside package')
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != revision:
        raise ValueError('Manifest digest mismatch')
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as tmp:
        stage = Path(tmp)/revision
        target = destination/revision
        if not target.exists():
            stage.mkdir()
            shutil.copyfile(manifest, stage/manifest.name)
            for mesh in json.loads(manifest.read_bytes())['meshes'].values():
                name = mesh['file']
                path = package/name
                if Path(name).name != name or path.suffix != '.obj' or path.resolve().parent != package:
                    raise ValueError('Invalid mesh path')
                shutil.copyfile(path, stage/name)
        candidate = target if target.exists() else stage
        if candidate.resolve().parent not in (destination.resolve(),Path(tmp).resolve()):
            raise ValueError('Revision outside destination')
        if hashlib.sha256((candidate/'parts_manifest.json').read_bytes()).hexdigest() != revision:
            raise ValueError('Damaged destination manifest')
        subprocess.run([checker,candidate],check=True)
        if (destination/'current.json').exists():
            subprocess.run([checker,destination,'--compare',candidate],check=True)
        if candidate == stage:
            stage.rename(target)
        pointer = Path(tmp)/'current.json'
        pointer.write_text(json.dumps(dict(schema_version=1,asset_revision=revision))+'\n')
        os.replace(pointer,destination/'current.json')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('registry',type=Path)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--revision',help='Rollback or select an existing revision by its full SHA-256')
    parser.add_argument('--checker',required=True,type=Path)
    args = parser.parse_args()
    print(switch(args.registry,args.destination or args.registry,args.checker,args.revision))
