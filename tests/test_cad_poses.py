"""Compare the C++ runtime to CAD placements and the independent mechanical model."""
import argparse
import json
import math
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad/sevel16'))
from kinematics import pose


def check(binary, package, meshes, parameters, datum):
    if (package/'current.json').exists():
        revision = json.loads((package/'current.json').read_bytes())['asset_revision']
        package = package/revision
    m = json.loads((package/'parts_manifest.json').read_bytes())
    rows = {p['id']:p for p in m['parts']}
    params = json.loads(parameters.read_bytes())
    frame = json.loads(datum.read_bytes())
    results = {}
    for angle in (0,90,180,270,359,360,540,719,720,-90):
        output = subprocess.check_output([binary,package,'--pose',str(angle)],text=True)
        lines = output.splitlines()
        digest = lines[0].split()[1]
        actual = {r[0]:list(map(float,r[1:])) for r in map(str.split,lines[1:])}
        assert set(actual) == set(rows)
        fixture = meshes/f'pose_{angle:03d}.txt'
        if fixture.exists():
            for line in fixture.read_text().splitlines():
                r = shlex.split(line)
                assert max(abs(a-float(b)) for a,b in zip(actual[r[0]],r[6:22])) < 4e-6, (r[0],angle)
        state = pose(angle,params,frame)
        rest = pose(0,params,frame)
        for part_id,p in rows.items():
            a = actual[part_id]
            if p['motion_type'] in ('rod','piston'):
                c = state['cylinders'][p['cylinder_id']-1]
                expected = c['crankpin_mm' if p['motion_type']=='rod' else 'piston_pin_mm']
                assert max(abs(a[i]-v/1000) for i,v in zip((3,7,11),(expected[0],expected[2],-expected[1]))) < 1e-7
                if p['motion_type'] == 'rod':
                    length = p['connection_points_local_m']['small_end'][1]
                    assert abs(a[11]+a[9]*length) < 1e-7
                    assert abs(a[7]+a[5]*length-c['piston_pin_mm'][2]/1000) < 1e-7
            if p['motion_type'] in ('valve','spring'):
                idx,kind = p['cylinder_id']-1,p['valve_kind']
                delta = (rest['cylinders'][idx]['valve_lifts_mm'][kind]-
                         state['cylinders'][idx]['valve_lifts_mm'][kind])/1000
                measured = a[16] if p['motion_type']=='spring' else a[7]-p['rest_translation_m'][1]
                assert abs(delta-measured) < 1e-7, (part_id,angle)
        results[angle] = actual,digest
    for pid,p in rows.items():
        if p['motion_type'] in ('rod','piston','crank'):
            assert max(abs(x-y) for x,y in zip(results[0][0][pid],results[360][0][pid])) < 1e-6
        if p['motion_type'] == 'piston':
            assert abs(abs(results[0][0][pid][7]-results[180][0][pid][7])-.0674) < 1e-7
        if p['motion_type'] != 'tensioner':
            assert max(abs(x-y) for x,y in zip(results[0][0][pid],results[720][0][pid])) < 1e-6
        if p['motion_type'] == 'cam':
            assert abs(results[0][0][pid][5]+results[360][0][pid][5]) < 1e-6
    assert results[0][1] != results[90][1]
    print(f'PASS {len(rows)} parts, {len(results)} phases, CAD fixture tolerance 4e-6, joint tolerance 1e-7 m')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary','package','meshes','parameters','datum'):
        parser.add_argument(name,type=Path)
    check(**vars(parser.parse_args()))
