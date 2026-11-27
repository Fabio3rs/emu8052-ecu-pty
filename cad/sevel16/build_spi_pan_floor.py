"""Build and gauge the two photographed sump-floor pressings from the v018 assembly."""
import copy
import math
from pathlib import Path

import FreeCAD as App
import Part

from build_pan_side_press import press
from build_spi_skirt_review import DEST as SOURCE
from check_auxiliary import difference
from config import OUTPUT, load
from oil_pan import build

DEST = OUTPUT/"models/SEVEL_Accessories_A5_v019_SPISumpPressings.FCStd"
V = App.Vector


def gauge(pan, params):
    close = params["external_closures_estimated"]["value"]
    spec = params["spi_pan_floor_estimated"]["value"]
    wall = close["pan_wall_mm"]
    top = -params["block_visual_estimated"]["value"]["height"]-close["pan_gasket_mm"]
    deep,shallow = (top-close[key] for key in ("pan_deep_depth_mm","pan_shallow_depth_mm"))
    x,y = spec["shelf_corner_xy"]
    h,w = spec["shelf_lift"],spec["shelf_runout"]
    r = (w*w+h*h)/(4*h)
    outer_center = V(x+spec["shelf_corner_radius"],y+12,deep+h-r)
    inner_center = V(outer_center.x+w,outer_center.y,deep+r)
    angle = math.atan2(w,2*r-h)
    samples = []
    for fraction in (.02,.35,.75,.98):
        normal = V(math.sin(angle*fraction),0,math.cos(angle*fraction))
        samples.extend([(outer_center+normal*r,normal),(inner_center-normal*r,normal)])
    r = spec["shallow_channel_radius"]
    center = V(sum(spec["shallow_channel_ends_x"])/2,spec["shallow_channel_y"],
               shallow+spec["shallow_channel_depth"]-r)
    for angle in (-.60,0,.60):
        normal = V(0,math.sin(angle),math.cos(angle))
        samples.append((center+normal*r,normal))
    samples.append((V(x-15,y+12,deep+h),V(0,0,1)))
    readings = []
    for point,normal in samples:
        line = Part.makeLine(point-normal,point+(wall+1)*normal)
        hits = sorted((v.Point-point).dot(normal) for v in pan.section(line).Vertexes)
        if len(hits)!=2 or abs(hits[0])>1e-4 or abs(hits[1]-wall)>1e-4:
            raise ValueError(f"Sump gauge at {point} along {normal}: {hits}")
        readings.append({"outer_point_mm":list(point),"normal":list(normal),"gauge_mm":hits[1]-hits[0]})
    return readings


def sump(params, frame):
    local = copy.deepcopy(params)
    # The first side groove now ends at the raised shelf.
    local["pan_side_press_estimated"]["value"]["stations"][0][1] = (
        local["spi_pan_floor_estimated"]["value"]["adjacent_side_press_bottom_z"])
    raw = build(local,frame,offset_drain=True,floor_press=True)
    return press(raw["OilPan"],local)


def run(source=SOURCE, destination=DEST):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if not App.GuiUp:
        raise RuntimeError("Build the coloured assembly in the FreeCAD GUI")
    params, frame = load()
    doc = App.newDocument(destination.stem)
    try:
        doc.mergeProject(str(source))
        before = build(params,frame,offset_drain=True)
        assert difference(press(before["OilPan"],params),doc.OilPan.Shape)<1e-5
        assert difference(before["OilDrainPlug"],doc.OilDrainPlug.Shape)<1e-5
        assert difference(before["OilPanGasket"],doc.OilPanGasket.Shape)<1e-5
        pan = sump(params,frame)
        readings = gauge(pan,params)
        doc.OilPan.Shape = pan
        doc.recompute()
        doc.Label = destination.stem
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return destination, readings
