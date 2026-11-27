"""Compare both sides of the SPI cover and the two registered plug-side views."""
import json
import math

import FreeCAD as App
import FreeCADGui as Gui

from build_manifold_review import camera
from build_spi_upper_castings import DEST, SOURCE
from config import OUTPUT, load
from sheet_spi_cast_details import run as sheet

FOLDER = OUTPUT/"polish/exterior-02"
V = App.Vector


def visible(doc,names):
    for obj in doc.Objects:
        if hasattr(obj,"Shape"):
            obj.ViewObject.Visibility = obj.Name in names
            if obj.Name in names:
                obj.ViewObject.DisplayMode = "Shaded"
                obj.ViewObject.Deviation = .06
    doc.recompute()


def capture(doc,tag,head,params):
    view = Gui.activeDocument().activeView()
    view.setCameraType("Orthographic")
    placement = doc.ValveCover.Placement
    close = params["external_closures_estimated"]["value"]
    center = placement.multVec(V(141,0,close["cover_height_mm"]/2))
    for key,back,up in (("tampa-cima",(.15,-.21,1),(0,-1,0)),
                        ("tampa-dentro",(.03,.18,-1),(0,1,0))):
        visible(doc,("ValveCover","OilFillerCap") if key=="tampa-cima" else ("ValveCover",))
        camera(tuple(center),tuple(placement.Rotation.multVec(V(*back))),265,
               placement.Rotation.multVec(V(*up)))
        view.saveImage(str(FOLDER/f"{tag}-{key}.png"),960,550,"White")
    capture_head(doc,tag,head)


def capture_head(doc,tag,head,dressed=False):
    view = Gui.activeDocument().activeView()
    for key,row in head["views"].items():
        names = {"HeadLower"}
        if key=="870987":
            names.update(o.Name for o in doc.Objects if "_Spark" in o.Name)
            if dressed:
                names.update(o.Name for o in doc.Objects if o.Name.endswith(
                    ("_Valve","_Retainer","_Keeper1","_Keeper2","SpringSeat","InnerSpring","OuterSpring")))
        else:
            names.add("CamCarrier")
            if dressed:
                names.add("Camshaft")
        visible(doc,names)
        view.setCameraType("Perspective")
        node = view.getCameraNode()
        rotation = row["rotation"]
        node.orientation.setValue(App.Rotation(V(),-V(*rotation[1]),-V(*rotation[2]),"ZYX").Q)
        node.position.setValue(*row["eye_mm"])
        w,h = row["image_size_px"]
        node.heightAngle.setValue(2*math.atan(h/(2*row["intrinsic"][0][0])))
        node.nearDistance.setValue(1)
        node.farDistance.setValue(2200)
        Gui.updateGui()
        view.saveImage(str(FOLDER/f"{tag}-{key}.png"),w,h,"White")


def run():
    params,_ = load()
    head = json.loads((FOLDER/"reports/SPI-04-spark-face-registration.json").read_bytes())
    for tag,path in (("antes-v020",SOURCE),("v020",DEST)):
        doc = App.newDocument("SPI_Upper_Casting_Comparison")
        try:
            doc.mergeProject(str(path))
            capture(doc,tag,head,params)
        finally:
            App.closeDocument(doc.Name)
    sheet([("tampa-cima","TAMPA_VALVULAS/215616663404314.png","Tampa SPI · extensão dos ombros e bocal arredondado",(.367,.051,.635,.95),90),
           ("tampa-dentro","TAMPA_VALVULAS/223649425194962.png","Tampa aberta · sete travessas e término da nervura junto ao bocal",(.05,.347,.95,.653),0),
           ("870987","*_870987-*","Cabeçote · projeções da borda e recuo entre os cilindros centrais"),
           ("726745","*_726745-*","Cabeçote e gaiola · transição sob as colunas laterais")],"v019","v020")
