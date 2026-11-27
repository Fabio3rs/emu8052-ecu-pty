"""Orthographic photoside views of the three deck faces, each with its own handedness."""
import FreeCAD as App
import FreeCADGui as Gui

from build_manifold_review import camera
from config import OUTPUT

ROOT = OUTPUT/"polish/exterior-02"
V = App.Vector
VIEWS = [
    ("junta","HeadGasket", (0,0,1), (0,1,0)),
    ("deck","Block", (0,-.10,1), (0,-1,0)),
    ("camaras","HeadLower", (0,.07,-1), (0,1,0)),
]


def capture(checkpoint, tag):
    doc = App.newDocument("SPI_Deck_Comparison")
    try:
        doc.mergeProject(str(checkpoint))
        parts = [o for o in doc.Objects if hasattr(o,"Shape")]
        for o in parts:
            o.ViewObject.Visibility=True
        camera((135,10,-47),(-.72,-1,.44),690)
        view=Gui.activeDocument().activeView()
        view.saveImage(str(ROOT/(tag+"-inteiro.png")),1050,740,"White")
        for key,name,back,up in VIEWS:
            for o in parts:
                o.ViewObject.Visibility=o.Name==name
            obj=doc.getObject(name)
            obj.ViewObject.DisplayMode="Flat Lines"
            obj.ViewObject.ShapeColor=(.49,.48,.45) if key=="junta" else (.71,.72,.69)
            obj.ViewObject.LineColor=(.16,.16,.15)
            obj.ViewObject.LineWidth=1
            obj.ViewObject.Deviation=.05
            camera((141,0,0),back,286,V(*up))
            view.saveImage(str(ROOT/(tag+"-"+key+".png")),1100,740,"White")
    finally:
        App.closeDocument(doc.Name)


def sheet():
    from sheet_spi_cast_details import run
    run([("junta","*_926507-*","Junta · contorno assimétrico e duas janelas grandes"),
         ("deck","*_666661-*","Bloco · divisórias nas janelas e recortes triangulares entre os cilindros"),
         ("camaras","*_704878-*","Cabeçote · três pares afilados de um lado e quatro bocas ovais do outro")],
        "v016","v017")
