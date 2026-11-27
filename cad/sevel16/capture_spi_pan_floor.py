"""Match the long straight side, underside and open pan in the workshop photos."""
import FreeCAD as App
import FreeCADGui as Gui

from build_manifold_review import camera
from build_spi_pan_floor import DEST, SOURCE
from config import OUTPUT
from sheet_spi_cast_details import run as sheet

FOLDER = OUTPUT/"polish/exterior-02"
VIEWS = [
    ("cuba",(141,0,-275),(-.035,1,-.61),(0,0,-1),330),
    ("fundo",(141,0,-280),(-.24,.13,-1),(0,-1,0),345),
    ("interior",(141,0,-266),(-.08,-.32,1),(0,1,0),345),
]


def run():
    for tag,source in (("antes-v019",SOURCE),("v019",DEST)):
        doc = App.newDocument("SPI_Sump_Comparison")
        try:
            doc.mergeProject(str(source))
            for obj in doc.Objects:
                if hasattr(obj,"Shape"):
                    obj.ViewObject.Visibility = obj.Name in ("OilPan","OilDrainPlug")
            doc.OilPan.ViewObject.DisplayMode = "Shaded"
            doc.OilPan.ViewObject.ShapeColor = (.48,.49,.48)
            doc.recompute()
            for key,center,back,up,height in VIEWS:
                camera(center,back,height,App.Vector(*up))
                Gui.activeDocument().activeView().saveImage(str(FOLDER/f"{tag}-{key}.png"),
                                                           960,680,"White")
        finally:
            App.closeDocument(doc.Name)
    sheet([("cuba","*_679775-*","Cuba funda · patamar e término do primeiro vinco",(.11,.40,.92,.76),0),
           ("fundo","*_845764-*","Fundo · vinco curto na parte rasa e ressalto do bujão",(.19,.30,.80,.92),90),
           ("interior","*_790487-*","Interior · verso da estampagem e espaço da divisória",(.12,.41,.86,.72),0)],
          "v018","v019")
