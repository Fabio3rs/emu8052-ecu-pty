"""Pair five v014 CAD close-ups with the corresponding original photographs."""
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from config import OUTPUT, ROOT

FOLDER = OUTPUT/"polish/exterior-02"
ROWS = [
    ("selos", "Bloco · parede dos três selos", "*_710159-*", None),
    ("nichos", "Cabeçote · colunas entre as velas", "*_870987-*", None),
    ("bocal", "Tampa · base do bocal arredondado", "suporte_bobina_bocal_oleo/*114830230*", None),
    ("carter", "Cárter · vincos na parede longa", "*_679775-*", (.12,.36,.92,.79)),
    ("respiro", "Respiro · ombro e saída da mangueira", "*_949850-*", None),
]


def tile(path, crop=None, rotation=0):
    with Image.open(path) as source:
        rgba = ImageOps.exif_transpose(source).convert("RGBA")
    image = Image.new("RGB",rgba.size,"white")
    image.paste(rgba,mask=rgba.getchannel("A"))
    if crop:
        w,h = image.size
        image = image.crop((crop[0]*w,crop[1]*h,crop[2]*w,crop[3]*h))
    else:
        field = Image.new("RGB",image.size,image.getpixel((0,0)))
        bounds = ImageChops.difference(image,field).convert("L").point(lambda x: 255 if x>15 else 0).getbbox()
        if bounds:
            image = image.crop(bounds)
    if rotation:
        image = image.rotate(rotation,expand=True)
    return ImageOps.contain(image,(410,205),Image.Resampling.LANCZOS)


def run():
    sheet = Image.new("RGB",(1290,1275),"white")
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype("DejaVuSans.ttf",22)
    label = ImageFont.truetype("DejaVuSans.ttf",17)
    for j, name in enumerate(("Foto de referência","FreeCAD v012","FreeCAD v014")):
        draw.text((18+j*430,10),name,font=title,fill="#243a30")
    for i,(key,name,pattern,crop) in enumerate(ROWS):
        y = 45+i*245
        draw.line((12,y,1278,y),fill="#c4ccc7",width=1)
        draw.text((18,y+5),name,font=label,fill="#243a30")
        reference, = (ROOT/"PhotosMotor").glob(pattern)
        sources = [(reference,crop),(FOLDER/f"v012-foto-{key}.png",None),(FOLDER/f"v014-{key}.png",None)]
        for j,(source,area) in enumerate(sources):
            image = tile(source,area)
            sheet.paste(image,(j*430+(430-image.width)//2,y+29+(205-image.height)//2))
    sheet.save(FOLDER/"comparacao-SPI-v014.jpg",quality=90)


if __name__ == "__main__":
    run()
