"""Compile the CAD shader offline. Emit the files consumed by sevel_restore_shader."""
import argparse
import base64
import hashlib
from pathlib import Path
import subprocess
import tempfile
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--glslang', default='glslangValidator')
    parser.add_argument('--spirv-cross', default='spirv-cross')
    parser.add_argument('--dxc', default='dxc')
    args = parser.parse_args()
    shader = Path(__file__).resolve().parents[1]/'third_party/open-engine-sim/assets/shaders/sevel_cad.hlsl'
    args.output.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        for stage, entry, name, profile in [('vert','VSMain','vertex','vs_6_0'),
                                             ('frag','PSMain','fragment','ps_6_0')]:
            spv = Path(tmp)/f'sevel_cad.{name}.spv'
            dxil = spv.with_suffix('.dxil')
            subprocess.run([args.glslang,'-D','-V','-S',stage,'-e',entry,'--hlsl-iomap',
                            '-o',spv,shader],check=True)
            msl = subprocess.check_output([args.spirv_cross,spv,'--msl','--msl-version','20100'])
            (args.output/spv.with_suffix('.msl').name).write_bytes(msl.rstrip()+b'\n')
            subprocess.run([args.dxc,'-T',profile,'-E',entry,'-Fo',dxil,shader],check=True)
            for path in (spv,dxil):
                data = path.read_bytes()
                (args.output/(path.name+'.zlib.b64')).write_bytes(base64.b64encode(zlib.compress(data,9))+b'\n')
                print(path.name,hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
