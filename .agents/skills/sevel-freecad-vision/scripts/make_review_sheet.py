#!/usr/bin/env python3
"""Generate a contact sheet of reference photos versus FreeCAD screenshots.

This organizes visual review; it does NOT measure shape similarity or correct
camera perspective. The user/agent selects matching camera angles manually.
Pillow is the only dependency.

Examples:
  python make_review_sheet.py --photos PhotosMotor --captures build/sevel-cad/evidence \
       --part bloco --output build/sevel-cad/reports/block_review_sheet.png
  python make_review_sheet.py --photos PhotosMotor --captures build/sevel-cad/evidence \
       --part cabecote --output build/sevel-cad/reports/head_review_sheet.png
"""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps


def font(size:int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()

EXTS={'.png','.jpg','.jpeg','.webp','.tif','.tiff'}

def getfiles(root:Path, filterterm:str, maxcount:int):
    if not root.exists():
        return []
    matches=[]
    for f in sorted(root.rglob('*')):
        if f.is_file() and f.suffix.lower() in EXTS and (not filterterm or filterterm.lower() in f.stem.lower()):
            matches.append(f)
    return matches[:maxcount]

def thumbnail_cell(path:Path|None,heading:str,w:int,h:int):
    canvas=Image.new('RGB',(w,h),(248,249,251))
    draw=ImageDraw.Draw(canvas)
    draw.rectangle((0,0,w-1,h-1),outline=(198,204,213),width=1)
    draw.text((15,12),heading,fill=(45,55,69),font=font(17))
    if path is None:
        draw.text((15,60),'Nenhuma imagem selecionada',fill=(120,125,132),font=font(14))
        return canvas
    try:
        with Image.open(path) as src:
            src=src.convert('RGBA')
            # Composite transparency onto neutral white instead of black.
            base=Image.new('RGBA',src.size,(255,255,255,255))
            base.alpha_composite(src)
            picture=ImageOps.contain(base.convert('RGB'),(w-30,h-105))
            left=(w-picture.width)//2
            top=47+(h-105-picture.height)//2
            canvas.paste(picture,(left,top))
    except Exception as e:
        draw.text((16,70),f'ERRO AO ABRIR: {e}',fill=(150,30,40),font=font(13))
    stem=path.name
    maxchars=max(16,(w-30)//8)
    if len(stem)>maxchars:
        stem=stem[:maxchars-1]+'…'
    draw.text((15,h-42),stem,fill=(62,68,79),font=font(13))
    return canvas

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--photos',type=Path,required=True)
    p.add_argument('--captures',type=Path,required=True)
    p.add_argument('--part',default='',help='case-insensitive substring used to filter photos, not screenshots')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-photos',type=int,default=6)
    p.add_argument('--max-captures',type=int,default=6)
    args=p.parse_args()
    photos=getfiles(args.photos,args.part,max(0,args.max_photos))
    caps=getfiles(args.captures,'',max(0,args.max_captures))
    if not photos and not caps:
        raise SystemExit('No matching reference photos or captures')
    width=1500
    cell_w=728
    cell_h=380
    margin=15
    head=80
    tail=45
    rows=max(len(photos),len(caps))
    canvas=Image.new('RGB',(width,head+rows*(cell_h+margin)+tail),(242,245,249))
    dr=ImageDraw.Draw(canvas)
    dr.text((24,12),'SEVEL • revisão visual lado a lado',fill=(32,45,58),font=font(22))
    dr.text((24,45),'Ajuste a orientação da câmera; isto é revisão visual, não metrologia de pixels.',fill=(97,106,114),font=font(13))
    for idx in range(rows):
        y=head+idx*(cell_h+margin)
        a=thumbnail_cell(photos[idx] if idx<len(photos) else None,f'REFERÊNCIA {idx+1:02d}',cell_w,cell_h)
        b=thumbnail_cell(caps[idx] if idx<len(caps) else None,f'FREECAD {idx+1:02d}',cell_w,cell_h)
        canvas.paste(a,(margin,y))
        canvas.paste(b,(margin*2+cell_w,y))
    dr.text((24,canvas.height-29),f'{len(photos)} referências | {len(caps)} capturas | seleção por nome, sem pareamento automático de vistas',fill=(65,75,85),font=font(12))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(args.output)
    print(args.output,'size',canvas.size,'photos',len(photos),'captures',len(caps))
if __name__=='__main__':
    main()
