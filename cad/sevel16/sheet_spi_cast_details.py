"""Pair the v014 and v015 camera captures with the corresponding original photos."""
from PIL import Image, ImageChops, ImageDraw, ImageFont

from config import ROOT
from sheet_spi_exterior import FOLDER, tile

ROWS = [
    ("selos-luz", "*_710159-*", "Bloco · painéis entre os selos e descida até o pé"),
    ("respiro-perfil", "*_949850-*", "Respiro · pescoço inclinado, ressalto perfurado e reforço"),
    ("respiro-inferior", "*_925239-*", "Respiro · espiga e abertura inferior"),
    ("admissao", "*_713001-*", "Admissão · união dos ramos e conexões da face externa"),
    ("escape-frente", "*_755038-*", "Escape · pés laterais e reunião dos dois ramos centrais"),
]


def shared_crop(paths):
    masks = []
    for path in paths:
        with Image.open(path) as source:
            pixels = source.convert("RGB")
        field = Image.new("RGB",pixels.size,pixels.getpixel((0,0)))
        masks.append(ImageChops.difference(pixels,field).convert("L"))
    if masks[0].size!=masks[1].size:
        raise ValueError("Matched views must have the same capture dimensions")
    box = ImageChops.lighter(*masks).point(lambda v: 255 if v>15 else 0).getbbox()
    if box is None:
        raise ValueError("Empty CAD comparison")
    w,h = masks[0].size
    return box[0]/w,box[1]/h,box[2]/w,box[3]/h


def run(rows=ROWS, before="v014", after="v015", *, matched_scale=False):
    sheet = Image.new("RGB", (1290, 50+245*len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    heading = ImageFont.truetype("DejaVuSans.ttf", 22)
    caption = ImageFont.truetype("DejaVuSans.ttf", 17)
    for j, title in enumerate(("Foto da peça", "FreeCAD "+before, "FreeCAD "+after)):
        draw.text((18 + 430*j, 10), title, font=heading, fill="#243a30")
    for i, (key, pattern, label, *photo_crop_and_rotation) in enumerate(rows):
        y = 45 + 245*i
        draw.line((12,y,1278,y), fill="#c4ccc7")
        draw.text((18, y+5), label, font=caption, fill="#243a30")
        photo, = (ROOT/"PhotosMotor").glob(pattern)
        cad = [FOLDER/f"antes-{after}-{key}.png", FOLDER/f"{after}-{key}.png"]
        bounds = shared_crop(cad) if matched_scale else None
        for j, path in enumerate([photo,*cad]):
            panel = tile(path,*photo_crop_and_rotation) if j==0 else tile(path,bounds)
            sheet.paste(panel, (430*j + (430-panel.width)//2, y+29+(205-panel.height)//2))
    sheet.save(FOLDER/f"comparacao-SPI-{after}.jpg", quality=91)


if __name__ == "__main__":
    run()
