"""Matched comparison cameras for the v014 and v015 SPI casting checkpoints."""
import FreeCAD as App
import FreeCADGui as Gui

from build_manifold_review import camera
from build_spi_cast_details import DEST, EXTERIOR_BASE
from config import OUTPUT

ROOT = OUTPUT / "polish/exterior-02"
FITTINGS = ("IntakeManifoldHoseTail", "IntakeManifoldPlugBase", "IntakeManifoldSocket")
VIEWS = (
    ("selos-luz", ("Block", "CorePlug1", "CorePlug2", "CorePlug3"), (142,67,-105), (.04,1,.28), 340),
    ("respiro-perfil", ("PCVBreatherOutlet",), (112,-100,-54), (.94,-.05,.28), 95),
    ("respiro-inferior", ("PCVBreatherOutlet",), (112,-100,-54), (.50,-.08,-.86), 95),
    ("admissao", ("IntakeManifold", *FITTINGS), (141,161,75), (0,.72,1), 246),
    ("escape-frente", ("ExhaustManifold",), (141,141,8), (.05,.53,1), 278),
)


def capture(checkpoint, tag, views=VIEWS):
    # Merge into a scratch document so visibility and display settings in the
    # user's working assembly and the saved checkpoint are never modified.
    doc = App.newDocument("SPI_Camera_Comparison")
    try:
        doc.mergeProject(str(checkpoint))
        parts = [o for o in doc.Objects if hasattr(o, "Shape")]
        for obj in parts:
            obj.ViewObject.Visibility = True
        doc.recompute()
        camera((135,10,-47), (-.72,-1,.44), 690)
        view = Gui.activeDocument().activeView()
        view.saveImage(str(ROOT/(tag+"-inteiro.png")), 1050, 740, "White")
        for key, names, center, back, height in views:
            for obj in parts:
                visible = obj.Name in names
                obj.ViewObject.Visibility = visible
                if visible:
                    obj.ViewObject.DisplayMode = "Shaded"
                    obj.ViewObject.Deviation = .06
                    if key in ("selos-luz", "parede", "pe") and obj.Name == "Block":
                        obj.ViewObject.ShapeColor = (.62,.63,.59)
                    elif key == "escape-frente":
                        obj.ViewObject.ShapeColor = (.53,.47,.43)
                    elif key.startswith("respiro"):
                        obj.ViewObject.ShapeColor = (.43,.44,.42)
            camera(center, back, height)
            view.saveImage(str(ROOT/(tag+"-"+key+".png")), 960, 680, "White")
    finally:
        App.closeDocument(doc.Name)


def run():
    capture(EXTERIOR_BASE, "antes-v015")
    capture(DEST, "v015")
