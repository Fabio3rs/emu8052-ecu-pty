"""Matched views of the loose head and the owner's installed ignition coil."""
import json

import FreeCAD as App
import FreeCADGui as Gui

from build_manifold_review import camera
from build_spi_ignition_side import DEST
from build_spi_pan_floor import DEST as BASE
from capture_spi_upper_castings import FOLDER, capture_head, visible
from sheet_spi_cast_details import run as sheet


def run():
    head = json.loads((FOLDER/"reports/SPI-04-spark-face-registration.json").read_bytes())
    for tag,path in (("antes-v021",BASE),("v021",DEST)):
        doc = App.newDocument("SPI_Ignition_Side_Comparison")
        try:
            doc.mergeProject(str(path))
            capture_head(doc,tag,head,dressed=True)
            names = {"ValveCover","OilFillerCap","IgnitionCoil","IgnitionCoilMount","CamCarrier","HeadLower"}
            names.update(o.Name for o in doc.Objects if o.Name.startswith(("IgnitionBoot","IgnitionLead")))
            visible(doc,names)
            view = Gui.activeDocument().activeView()
            view.setCameraType("Orthographic")
            for key,center,back,up,height in (
                    ("torres",(413,0,134),(.04,-.06,1),(1,0,0),122),
                    ("bobina",(377,-3,139),(.38,-.36,1),(0,1,0),200)):
                camera(center,back,height,App.Vector(*up))
                view.saveImage(str(FOLDER/f"{tag}-{key}.png"),900,610,"White")
        finally:
            App.closeDocument(doc.Name)
    sheet([("870987","*_870987-*","Face das velas · fundos dos nichos, colunas e recuo da borda"),
           ("726745","*_726745-*","Cabeçote · transição para os apoios na vista oblíqua"),
           ("torres","suporte_bobina_bocal_oleo/*114255366*","Bobina instalada · cachimbos superiores e saída lateral",(.13,0,.95,.72),0),
           ("bobina","suporte_bobina_bocal_oleo/*114205137*","Bobina junto ao bocal de óleo · terceiro cotovelo visível",(.13,.18,.96,.94),0)],
          "v019","v021",matched_scale=True)
