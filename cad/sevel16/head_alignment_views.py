"""Capture four v010 FreeCAD views and pair each with the corresponding photograph."""
from config import OUTPUT
from head_review_views import CASTINGS, reference

FOLDER = OUTPUT/'reviews/head-v010'
VIEWS = (
    ('lateral-cabecote', 'Face das velas', CASTINGS[:-1], (141,0,99), (.10,-1,.64), (0,0,1), 322,
     '2X_885508', None),
    ('bloco-face', 'Face superior do bloco', ('Block',), (141,0,-70), (0,.28,1), (0,-1,0), 345,
     '666661', None),
    ('junta-planta', 'Junta do cabeçote em planta', ('HeadGasket',), (141,0,0), (0,0,1), (0,-1,0), 310,
     '666447*sevel_bk', (42,32,672,277)),
    ('flange-extremidade', 'Extremidade da termostática e bocal de óleo', CASTINGS[:-1]+('Camshaft',),
     (330,0,109), (1,0,.075), (0,0,1), 294, '649747', None),
)


def capture(doc):
    import FreeCAD as App
    import FreeCADGui as Gui
    from pivy import coin  # Register the camera node type.
    from build_manifold_review import camera

    previous = App.ActiveDocument
    App.setActiveDocument(doc.Name)
    view = Gui.activeDocument().activeView()
    saved_camera = view.getCamera()
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    visibility = {o.Name:o.Visibility for o in objects}
    FOLDER.mkdir(parents=True, exist_ok=True)
    try:
        for key,_,names,center,direction,up,height,_,_ in VIEWS:
            for obj in objects:
                obj.Visibility = obj.Name in names
            camera(center,direction,height,App.Vector(*up))
            view.saveImage(str(FOLDER/(key+'-freecad.png')),1100,680,'White')
    finally:
        for obj in objects:
            obj.Visibility = visibility[obj.Name]
        view.setCamera(saved_camera)
        if previous:
            App.setActiveDocument(previous.Name)


def compare():
    from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

    title = ImageFont.truetype('DejaVuSans.ttf',27)
    label = ImageFont.truetype('DejaVuSans.ttf',17)
    for key,heading,_,_,_,_,_,photo_key,crop in VIEWS:
        photo = reference(photo_key)
        board = Image.new('RGB',(1540,590),'white')
        draw = ImageDraw.Draw(board)
        draw.text((25,12),heading,font=title,fill='#18232a')
        for column,path in enumerate((photo,FOLDER/(key+'-freecad.png'))):
            with Image.open(path) as opened:
                img = ImageOps.exif_transpose(opened).convert('RGBA')
            if column==0 and crop:
                img = img.crop(crop)
            paper = Image.new('RGB',img.size,'white')
            paper.paste(img,mask=img.getchannel('A'))
            diff = ImageChops.difference(paper,Image.new('RGB',paper.size,'white'))
            box = diff.convert('L').point(lambda v: 255 if v>35 else 0).getbbox()
            if box:
                paper = paper.crop(box)
            paper = ImageOps.contain(paper,(734,470),Image.Resampling.LANCZOS)
            left = 770*column
            board.paste(paper,(left+(770-paper.width)//2,76+(470-paper.height)//2))
            caption = 'Foto · '+photo.name.split('-MLB')[0].split('2X_')[-1] if column==0 else 'FreeCAD · v010'
            draw.text((left+25,552),caption,font=label,fill='#303c41')
        draw.line((770,65,770,540),fill='#cccccc')
        board.save(FOLDER/(key+'-lado-a-lado.jpg'),quality=94)


if __name__=='__main__':
    compare()
