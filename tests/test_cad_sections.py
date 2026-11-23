"""Exercise the real SDL_GPU pipeline on closed, hollow, concave and touching solids."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from PIL import Image
from cad_fixture import package, moving_cube


def run(binary,rom,out):
    package(out/'fixture')
    camera = dict(version=1,inspect=True,ortho=True,phase_deg=0,cut=True,fill=True,
                  invert=True,normal=[0,0,1],distance_mm=550,target_mm=[0,0,0],yaw_rad=0,pitch_rad=0)
    env = dict(os.environ,SDL_VIDEODRIVER='offscreen',SDL_AUDIODRIVER='dummy')
    def capture(name, **values):
        preset = out/(name+'.json')
        preset.write_text(json.dumps(dict(camera,**values)))
        result = subprocess.run([binary,rom,'--live','--no-audio','--cad-assets',out/'fixture',
            '--cad-preset',preset,'--window-frames','4','--capture-tick','50000','--screenshot',out/(name+'.png')],
            env=env,capture_output=True,text=True,timeout=40)
        (out/(name+'.log')).write_text(result.stdout+result.stderr)
        assert result.returncode == 0 and '[LAB-CAD] capture tick=50000' in result.stdout, name
        return Image.open(out/(name+'-gpu.png')).convert('RGB')
    def sample(im,x,y):
        scale = im.height*2.4/(2*.55)
        return im.getpixel((round(im.width/2+x*scale),round(im.height/2-y*scale)))
    def cap(rgb):
        r,g,b = rgb
        return r > 55 and r > 1.55*g and g > 1.4*b
    def count(im):
        return sum(cap(pixel) for pixel in im.getdata())
    front = capture('section-basic')
    for pos in [(-.14,.075),(0,.075),(.177,.075),(-.176,-.045),(-.112,-.11),(0,-.075),(.1,-.075)]:
        assert cap(sample(front,*pos)), (pos,sample(front,*pos))
    for pos in [(.14,.075),(-.112,-.045),(.219,.075),(0,.2)]:
        assert sample(front,*pos) == front.getpixel((0,0)), pos
    solid = capture('section-disabled',cut=False)
    assert count(solid) == 0
    # The +Z face receives the key light. A reversed winding shows the darker back face.
    assert 145 <= sample(solid,-.14,.075)[2] <= 167
    assert count(capture('section-open',fill=False)) == 0
    full = capture('section-outside',offset_mm=100)
    assert count(full) == 0 and sample(full,0,.075) != full.getpixel((0,0))
    empty = capture('section-removed',offset_mm=-100)
    assert len(empty.getcolors(empty.width*empty.height)) == 1
    assert count(capture('section-reverse',invert=False,yaw_rad=3.1415926)) > 5000
    assert count(capture('section-x',normal=[1,0,0],yaw_rad=1.57)) > 500
    assert count(capture('section-y',normal=[0,1,0],pitch_rad=1.57,offset_mm=75)) > 500
    assert count(capture('section-oblique',normal=[.6,0,.8],yaw_rad=.3,ortho=False)) > 500
    quarter = capture('section-quarter',second_cut=True,second_plane_mm=[1,0,0,0])
    assert sample(quarter,-.14,.075) == quarter.getpixel((0,0))
    assert cap(sample(quarter,.177,.075)) and not cap(sample(quarter,.14,.075))
    tangent = capture('section-tangent',offset_mm=45)
    assert sample(tangent,.14,.075) == tangent.getpixel((0,0))
    moving_cube(out/'fixture')
    moving = dict(selected='cube',isolate=True,normal=[0,1,0],pitch_rad=1.57,cut_moving=True)
    assert count(capture('moving-tdc',**moving,offset_mm=75)) > 1000
    assert count(capture('moving-bdc',**moving,offset_mm=75,phase_deg=180)) == 0
    assert count(capture('moving-bdc-lower',**moving,offset_mm=-25,phase_deg=180)) > 1000
    assert count(capture('moving-tdc-lower',**moving,offset_mm=-25)) == 0
    print('PASS real GPU section masks, three axes, oblique perspective, tangent and opposite half-spaces')


if __name__ == '__main__':
    if len(sys.argv)>3:
        out = Path(sys.argv[3]); out.mkdir(parents=True,exist_ok=True)
        run(sys.argv[1],sys.argv[2],out)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            run(sys.argv[1],sys.argv[2],Path(tmp))
