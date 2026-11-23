"""Render a fixed ROM replay and compare a single exterior CAD revision in the Lab."""
import argparse
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess

from PIL import Image, ImageChops, ImageDraw, ImageFont


def run(binary, rom, baseline, trial, out, overview=None):
    out.mkdir(exist_ok=True,parents=True)
    inputs = Path(__file__).resolve().parent
    long_cut = json.loads((inputs/'cad_longitudinal.json').read_text())
    env = dict(os.environ,SDL_VIDEODRIVER='offscreen',SDL_AUDIODRIVER='dummy')
    state = None
    def capture(name, package, settings, panel=False):
        nonlocal state
        preset = out/(name+'.json')
        preset.write_text(json.dumps(dict(version=1,**settings)))
        cmd = [binary,rom,'--live','--no-audio','--cad-assets',package,
               '--cad-preset',preset,'--stop-ticks','1200000','--capture-tick','1200000',
               '--window-frames','180','--replay-controls',inputs/'data/lab_control_replay.txt',
               '--idle-contact-p46','--idle-bridge-p15-p16','--adc7-mv','1232',
               '--screenshot',out/(name+'.png')]
        if panel:
            cmd.append('--cad-panel')
        proc = subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=120)
        log = proc.stdout+proc.stderr
        (out/(name+'.log')).write_text(log)
        assert proc.returncode == 0, log[-1200:]
        line = re.search(r'^\[LAB-STATE\] (.+)$',log,re.M).group(1)
        assert 'tick=1200000 ' in line and (state is None or line == state), line
        state = line
        match = re.search(r'\[LAB-CAD\] (?:capture|panel) tick=1200000 phase_deg=(\S+) revision=(\w+) pose=(\w+)',log)
        assert match and match[2] == package.name, name
        digest = hashlib.sha256((out/(name+'-gpu.json')).read_bytes()).hexdigest()
        assert 'preset_sha256='+digest in log
        image = Image.open(out/(name+'-gpu.png')).convert('RGB')
        assert len(image.getcolors(image.width*image.height)) > 40, name
        return match[1],match[3],image

    long_cut.pop('version')
    for angle in (0,90,180,360,720):
        phase,_,_ = capture('cut-'+str(angle),baseline,dict(long_cut,phase_deg=angle))
        assert float(phase) == angle
    capture('panel',baseline,long_cut,True)
    capture('perspective',baseline,{})
    capture('top-ghost',baseline,dict(pitch_rad=1.28,ghost=['head','cover','block'],
                                      hidden=['intake','exhaust','accessories']))
    capture('moving-oblique',baseline,dict(long_cut,normal=[.6,0,.8],cut_moving=True,offset_mm=87))
    capture('transverse',baseline,dict(long_cut,normal=[1,0,0],offset_mm=94,yaw_rad=1.25,
                                      target_mm=[94,-60,0],cut_moving=True))
    capture('horizontal',baseline,dict(long_cut,normal=[0,1,0],offset_mm=-25,pitch_rad=1.22,cut_moving=True))
    capture('exploded',baseline,dict(explode_mm=75))
    manifests = [json.loads((p/'parts_manifest.json').read_bytes()) for p in (baseline,trial)]
    parts = [{row['id']:row['mesh_id'] for row in m['parts']} for m in manifests]
    assert parts[0].keys() == parts[1].keys()
    assert [pid for pid in parts[0] if parts[0][pid] != parts[1][pid]] == ['sevel.block']
    checker = binary.with_name('sevel-cad-check')
    for angle in (0,90,180,270,359,360,540,719,720,-90):
        def poses(package):
            return subprocess.check_output([checker,package,'--pose',str(angle)],stderr=subprocess.DEVNULL)
        assert poses(baseline) == poses(trial), ('pose changed after reexport',angle)
    _,cut_hash,_ = capture('reexport-section',trial,dict(long_cut,phase_deg=90))
    assert 'pose='+cut_hash in (out/'cut-90.log').read_text()
    assert (out/'cut-90-gpu.json').read_bytes() == (out/'reexport-section-gpu.json').read_bytes()
    groups = {p['scene_group'] for p in manifests[0]['parts']}
    camera = dict(yaw_rad=2.82,pitch_rad=.14,distance_mm=560,target_mm=[140,-125,-65],
                  hidden=sorted(groups-{'block'}))
    before = capture('rib-original',baseline,camera)
    after = capture('rib-reexport',trial,camera)
    assert before[:2] == after[:2]
    assert (out/'rib-original-gpu.json').read_bytes() == (out/'rib-reexport-gpu.json').read_bytes()
    a,b = before[2],after[2]
    difference = ImageChops.difference(a,b)
    changed = sum(max(p)>3 for p in difference.getdata())
    assert 100 < changed < a.width*a.height//5, changed
    comparison = Image.new('RGB',(2*a.width,a.height))
    comparison.paste(a); comparison.paste(b,(a.width,0))
    comparison.save(out/'rib-comparison.png')
    box = difference.getbbox()
    crop = (max(0,box[0]-35),max(0,box[1]-35),min(a.width,box[2]+35),min(a.height,box[3]+35))
    close = [im.crop(crop) for im in (a,b)]
    w,h = close[0].size
    detail = Image.new('RGB',(2*w,h))
    for i,im in enumerate(close): detail.paste(im,(w*i,0))
    detail.resize((4*w,2*h)).save(out/'rib-detail.png')
    if overview:
        sheet = Image.new('RGB',(1100,796),'#161b21')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype('DejaVuSans.ttf',18)
        views = [('perspective-gpu.png','Montagem v005',0,0),
                 ('cut-90-gpu.png','Corte longitudinal em 90°',550,0),
                 ('panel.png','Mechanics e osciloscópio',0,392),
                 ('rib-detail.png','Nervura original e revisão de ensaio',550,392)]
        for file,label,x,y in views:
            frame = Image.open(out/file).convert('RGB')
            frame.thumbnail((530,350))
            sheet.paste(frame,(x+(550-frame.width)//2,y+34+(350-frame.height)//2))
            draw.text((x+14,y+6),label,font=font,fill='#e8edf0')
        overview.parent.mkdir(parents=True,exist_ok=True)
        sheet.save(overview)
    print(f'PASS {changed} changed rib pixels, stable replay and poses. {state}',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary','rom','baseline','trial','out'):
        parser.add_argument(name,type=lambda arg: Path(arg).resolve())
    parser.add_argument('--overview',type=Path,help='Write a contact sheet of the actual captures')
    run(**vars(parser.parse_args()))
