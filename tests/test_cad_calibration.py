"""Verify asymmetric FreeCAD fiducials against orthographic world-space landmarks."""
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image
from cad_fixture import package


def check(binary,rom,export,out):
    out.mkdir(exist_ok=True,parents=True)
    with TemporaryDirectory() as work:
        folder = Path(work)
        scene = package(folder)
        template = scene['parts'][0]
        scene.update(parts=[],meshes={},materials={})
        bounds = []
        for line in (export/'calibration_pose.txt').read_text().splitlines():
            pid,path,batch,r,g,b,*numbers = shlex.split(line)
            obj = export/Path(path).name
            sha = hashlib.sha256(obj.read_bytes()).hexdigest()
            mesh = 'mesh_'+sha[:20]
            name = mesh+'.obj'
            shutil.copyfile(obj,folder/name)
            scene['meshes'][mesh] = dict(file=name,sha256=sha,batches=[batch],vertices=8,triangles=12)
            scene['materials'][pid] = dict(rgb=list(map(float,(r,g,b))),opacity=1)
            m = list(map(float,numbers))
            w = math.sqrt(1+m[0]+m[5]+m[10])/2
            quat = [(m[9]-m[6])/(4*w),(m[2]-m[8])/(4*w),(m[4]-m[1])/(4*w),w]
            scene['parts'].append(dict(template,id=pid,mesh_id=mesh,mesh_file=name,mesh_batches=[batch],
                rest_translation_m=[m[3],m[7],m[11]],rest_rotation_xyzw=quat,material_bindings={batch:pid}))
            bounds.append(m[16:22])
        (folder/'parts_manifest.json').write_text(json.dumps(scene))
        for name,yaw in [('front',0),('back',math.pi),('panel',0)]:
            preset = out/(name+'.json')
            preset.write_text(json.dumps(dict(version=1,yaw_rad=yaw,pitch_rad=0,ortho=True,
                                               target_mm=[135,75,0],distance_mm=450)))
            panel_args = ['--cad-panel'] if name == 'panel' else []
            subprocess.run([binary,rom,'--live','--no-audio','--cad-assets',folder,*panel_args,'--cad-preset',preset,
                            '--window-frames','10','--capture-tick','50000','--screenshot',out/(name+'.png')],
                           env=dict(os.environ,SDL_VIDEODRIVER='offscreen',SDL_AUDIODRIVER='dummy'),
                           check=True,stdout=subprocess.DEVNULL,timeout=30)
            image = Image.open(out/(name+'-gpu.png')).convert('RGB')
            red,_,blue = image.split()
            from PIL import ImageChops
            for i,channel in enumerate([ImageChops.subtract(red,blue),ImageChops.subtract(blue,red)]):
                box = channel.point(lambda v: 255 if v>30 else 0).getbbox()
                xmin,ymin,_,xmax,ymax,_ = bounds[i]
                scale = image.height*2.4/.9
                xs = [image.width/2+math.cos(yaw)*(x-.135)*scale for x in (xmin,xmax)]
                expected = [min(xs),image.height/2-(ymax-.075)*scale,
                            max(xs),image.height/2-(ymin-.075)*scale]
                assert box and max(abs(a-b) for a,b in zip(box,expected)) < 2,(box,expected)
            if name == 'panel':
                # Locate a scanline crossing the blue fiducial, then verify
                # that the UI sampled the complete CAD texture at native resolution.
                row = (box[1] + box[3]) // 2
                scanline = image.crop((0,row,image.width,row+1)).tobytes()
                frame = Image.open(out/'panel.png').convert('RGB')
                offset = frame.tobytes().find(scanline)
                assert offset >= 0 and offset % 3 == 0
                y,x = divmod(offset // 3,frame.width)
                top = y-row
                assert frame.crop((x,top,x+image.width,top+image.height)).tobytes() == image.tobytes()
        print('PASS opposite views of both asymmetric landmarks, under 2 pixels from FreeCAD bounds')


if __name__ == '__main__':
    check(*(Path(arg).resolve() for arg in sys.argv[1:]))
