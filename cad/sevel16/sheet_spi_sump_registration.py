"""Show the matched long-side fixings and the current CAD seal in photo space."""
import json

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from config import OUTPUT, ROOT
from register_spi_sump_faces import project


def run():
    reports = OUTPUT/"polish/exterior-02/reports"
    data = json.loads((reports/"SPI-07-sump-registration.json").read_text())
    check = json.loads((reports/"SPI-07-sump-envelope.json").read_text())
    frame = data["provisional_frame"]
    inverse = np.linalg.inv(frame["gasket_pixel_to_xy_mm"])
    origin = frame["gasket_origin_px"]
    fig,axes = plt.subplots(2,2,figsize=(13,8),layout="constrained")
    for ax,(name,photo) in zip(axes.flat,[("Junta avulsa · 980809",data["gasket"]),
                ("Cárter · 790487",data["pan"]),("Bloco · 654874",data["blocks"]["654874"]),
                ("Bloco · 721011",data["blocks"]["721011"])]):
        ax.imshow(Image.open(ROOT/photo["path"]))
        xy = np.asarray(photo["control_px"])
        ax.scatter(*xy.T,s=56,facecolors="none",edgecolors="#09c4cd",linewidths=1.35)
        if "to_gasket_px" not in photo:
            for curve in check["old_section_mm"]:
                points = np.asarray(curve)@inverse.T+origin
                ax.plot(*points.T,color="#f6730d",lw=1.6)
        else:
            expected = project(np.linalg.inv(photo["to_gasket_px"]),data["gasket"]["control_px"])
            ax.scatter(*expected.T,s=9,marker="+",color="#fcfd81",linewidths=.8)
        if "cap_bolts_px" in photo:
            for pair in photo["cap_bolts_px"]:
                ax.plot(*np.asarray(pair).T,color="#f9d71c",lw=.7,alpha=.8)
        margin = .11*np.ptp(xy[:,0])
        w,h = Image.open(ROOT/photo["path"]).size
        ax.set_xlim(max(0,min(xy[:,0])-margin),min(w,max(xy[:,0])+margin))
        ax.set_ylim(min(h,max(xy[:,1])+margin),max(0,min(xy[:,1])-margin))
        ax.set_title(name,loc="left",fontsize=13)
        ax.set_axis_off()
    fig.suptitle("Catorze fixações do cárter nas quatro referências",fontsize=18)
    fig.supxlabel("Ciano · furo identificado     Laranja · junta v018     Amarelo · registro e pares de parafusos dos mancais",fontsize=11)
    fig.savefig(reports/"SPI-07-sump-registration.jpg",dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    run()
