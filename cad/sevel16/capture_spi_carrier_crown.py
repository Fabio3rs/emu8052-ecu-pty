"""Frame both ends of the four windows and the detailed central cast bridge."""
import json
import math

import FreeCAD as App
import FreeCADGui as Gui

from build_manifold_review import camera
from build_spi_carrier_crown import DEST, SOURCE
from capture_spi_upper_castings import FOLDER, visible
from sheet_spi_cast_details import run as sheet

V = App.Vector


def run():
    registration = json.loads((FOLDER/"reports/SPI-04-carrier-registration.json").read_bytes())
    for tag,path in (("antes-v022",SOURCE),("v022",DEST)):
        doc = App.newDocument("SPI_Carrier_Window_Comparison")
        try:
            doc.mergeProject(str(path))
            view = Gui.activeDocument().activeView()
            for key,row in registration["views"].items():
                visible(doc,("CamCarrier","Camshaft","HeadLower"))
                view.setCameraType("Perspective")
                node = view.getCameraNode()
                rot = row["rotation"]
                node.orientation.setValue(App.Rotation(V(),-V(*rot[1]),-V(*rot[2]),"ZYX").Q)
                node.position.setValue(*row["eye_mm"])
                w,h = row["control_image_size_px"]
                node.heightAngle.setValue(2*math.atan(h/(2*row["intrinsic"][0][0])))
                node.nearDistance.setValue(1)
                node.farDistance.setValue(3000)
                Gui.updateGui()
                view.saveImage(str(FOLDER/f"{tag}-gaiola-{key}.png"),w*2,h*2,"White")
            visible(doc,("CamCarrier","Camshaft"))
            view.setCameraType("Orthographic")
            at = doc.ValveCover.Placement
            camera(tuple(at.multVec(V(141,0,0))),tuple(at.Rotation.multVec(V(0,-.10,1))),
                   88,at.Rotation.multVec(V(0,1,0)))
            view.saveImage(str(FOLDER/f"{tag}-travessa.png"),760,750,"White")
        finally:
            App.closeDocument(doc.Name)
    sheet([("gaiola-cima","cabeçote_cima.png","Gaiola aberta · largura das travessas e da janela na ponta"),
           ("gaiola-726745","*_726745-*","Cabeçote e comando · margem da janela junto ao mancal da ponta"),
           ("travessa","cabeçote_cima.png","Travessa central · duas depressões redondas em torno da marca central",(.404,.115,.604,.442),0)],
          "v021","v022",matched_scale=True)
