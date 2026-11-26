"""Fixed FreeCAD cameras and photo pairs for the exterior head review."""
import subprocess

from config import OUTPUT, ROOT

FOLDER = OUTPUT/'reviews/head-v008'
PHOTOS = ROOT/'PhotosMotor'
CASTINGS = ('HeadLower', 'CarrierGasket', 'CamCarrier', 'ValveCoverGasket', 'ValveCover', 'OilFillerCap')
VIEWS = {
    'plugs': (('HeadLower',), (141,-20,39), (-.22,-1,.55), 262, ('723789','726745')),
    'ports': (('HeadLower','CamCarrier'), (141,5,87), (.10,1,.24), 267, ('621331','610418')),
    'end': (CASTINGS+('Camshaft',), (325,0,119), (1,0,.04), 280, ('649747','728942')),
    'timing': (CASTINGS, (-48,0,109), (-1,-.06,.05), 255, ('833777','726745')),
    'cover': (('ValveCover','OilFillerCap'), (149,0,181), (.12,1,.51), 285,
              ('201617543000572','219683186606960')),
    'throat': (('ValveCover',), (300,0,199), (.68,-1,.45), 138, ('728942','114608513')),
    'filter': (('Block','AuxSprocket','CrankSprocket','OilFilterSpigot','OilFilterCartridge','PCVBreatherOutlet'),
               (136,-68,-124), (-.69,-1,.30), 330, ('F9Lhc','KpWw4')),
    'filter-side': (('Block','AuxSprocket','CrankSprocket','OilFilterSpigot','OilFilterCartridge','PCVBreatherOutlet'),
                    (140,-60,-123), (.52,-1,.10), 330, ('KpWw4','F9Lhc')),
    'carrier': (('CamCarrier','Camshaft'), (141,0,125), (.02,-.46,1), 257,
                ('cabeçote_cima','troca_junta_tampa_valvulas_2_')),
    'installed': (CASTINGS+('IgnitionCoilMount','IgnitionCoil','ThermostatHousing',
                  'ThermostatGasket','ThermostatMainHose','ThermostatBranchHose'),
                  (340,-3,105), (.50,-.68,.91), 340, ('114205137','10-55-36')),
    'installed-end': (CASTINGS+('IgnitionCoilMount','IgnitionCoil','ThermostatHousing',
                      'ThermostatGasket','ThermostatMainHose','ThermostatBranchHose'),
                      (345,-4,105), (1,-.16,.15), 288, ('114205137','10-55-36')),
}


def reference(key):
    candidates = [f for f in sorted(PHOTOS.rglob('*'+key+'*'))
                  if f.suffix.lower() in ('.jpg','.png','.jpeg') and 'guias' not in f.name]
    if not candidates:
        raise ValueError(key)
    return candidates[0]


def capture(doc, stage, names):
    import FreeCAD as App
    import FreeCADGui as Gui
    from pivy import coin  # Register Coin nodes before getCameraNode().
    from build_manifold_review import camera
    FOLDER.mkdir(parents=True, exist_ok=True)
    App.setActiveDocument(doc.Name)
    gd = Gui.activeDocument()
    saved_camera = gd.activeView().getCameraOrientation()
    saved_state = gd.activeView().getCamera()
    objects = [o for o in doc.Objects if hasattr(o,'Shape')]
    visible = {o.Name:o.Visibility for o in objects}
    mode = doc.HeadLower.ViewObject.DisplayMode
    cartridge = doc.getObject('OilFilterCartridge')
    cartridge_mode = cartridge.ViewObject.DisplayMode if cartridge else None
    try:
        doc.HeadLower.ViewObject.DisplayMode = 'Flat Lines'
        if cartridge:
            cartridge.ViewObject.DisplayMode = 'Shaded'
        for key in names:
            selection, center, direction, height, _ = VIEWS[key]
            for obj in objects:
                obj.Visibility = obj.Name in selection
            camera(center,direction,height)
            gd.activeView().saveImage(str(FOLDER/f'{key}-{stage}.png'),1024,640,'White')
    finally:
        doc.HeadLower.ViewObject.DisplayMode = mode
        if cartridge:
            cartridge.ViewObject.DisplayMode = cartridge_mode
        for obj in objects:
            obj.Visibility = visible[obj.Name]
        gd.activeView().setCameraOrientation(saved_camera)
        gd.activeView().setCamera(saved_state)


def compare(stage, names):
    for key in names:
        refs = [reference(k) for k in VIEWS[key][-1]]
        pics = [*refs, FOLDER/f'{key}-v007.png', FOLDER/f'{key}-{stage}.png']
        command = ['montage','-font','DejaVu-Sans','-pointsize','14']
        for picture, label in zip(pics,['Foto '+refs[0].stem[:28], 'Foto '+refs[1].stem[:28],
                                        'FreeCAD v007', 'FreeCAD '+stage]):
            command.extend(['-label',label,str(picture)])
        subprocess.run(command+['-auto-orient','-thumbnail','420x260','-geometry','420x260+4+4',
                                '-background','white','-tile','2x2',str(FOLDER/f'{key}-{stage}.jpg')],check=True)
