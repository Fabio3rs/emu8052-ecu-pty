"""Check the gasket lands, independently registered openings and blind floors."""
import FreeCAD as App
import Part

from build_head_main_row import centers
from config import layout
from head_fixing_alignment import lower_centers
from spi_deck_surfaces import casting_openings, circle, gasket_windows, registration

V = App.Vector


def interface(shape, z):
    face = max((f for f in shape.Faces if f.BoundBox.ZLength<1e-5 and
                abs(f.BoundBox.ZMin-z)<1e-5),key=lambda f:f.Area).copy()
    face.translate(V(0,0,-z))
    return face


def run(doc, params, frame):
    data = registration(params,frame)
    h = params["head_lower_casting_estimated"]["value"]
    spec = params["spi_deck_faces_estimated"]["value"]
    b = params["casting_visual_estimated"]["value"]
    g = layout(params,frame)
    joints = {name:interface(doc.getObject(name).Shape,z) for name,z in
              [("Block",0),("HeadGasket",0),("HeadLower",h["head_gasket_thickness_mm"])]}
    report = {"face_loops":{name:len(f.Wires) for name,f in joints.items()},
              "lands_missing_mm2":{}, "window_area_mm2":[], "floor_missing_mm2":{}}
    fixes = centers(g["centers"]) + [(x,b["deck_hole_y"]) for x in g["supports"]]
    for name,face in joints.items():
        lands = [(x,0,h["head_gasket_opening_radius_mm"]+.02,1) for x in g["centers"]]
        lands += [(x,y,b["deck_hole_radius"]+.02,1) for x,y in fixes]
        r = {"Block":3.4,"HeadGasket":4.9,"HeadLower":4.3}[name]
        lands += [(x,y,r+.02,7.5-r-.02) for x,y in lower_centers(g["centers"])]
        missing = []
        for x,y,inner,width in lands:
            land = circle(x,y,inner+width,0).cut(circle(x,y,inner,0))
            missing.append(round(land.cut(face).Area,6))
        report["lands_missing_mm2"][name] = missing
    for row,window in zip(data["gasket"]["windows"],gasket_windows(data,spec)):
        connected = window.cut(joints["HeadGasket"]).cut(joints["Block"]).cut(joints["HeadLower"])
        report["window_area_mm2"].append({"center":row["center_mm"],"window":round(window.Area,2),
                                          "through_all_faces":round(connected.Area,2),
                                          "common_openings":len(connected.Faces)})
    for name,sign in (("Block",-1),("HeadLower",1)):
        z = (-h["deck_coolant_recess_depth_mm"] if sign<0 else
             h["head_gasket_thickness_mm"]+spec["head_floor_above_deck_mm"])
        shape = doc.getObject(name).Shape
        floors = [f for f in shape.Faces if f.BoundBox.ZLength<1e-5 and abs(f.BoundBox.ZMin-z)<1e-5]
        openings = casting_openings(name,data,spec,z)
        report["floor_missing_mm2"][name] = [round(f.cut(floors).Area,5) for f in openings]
        backing = Part.makeCompound([f.extrude(V(0,0,sign*.25)) for f in openings])
        report.setdefault("floor_backing_missing_mm3",{})[name] = abs(backing.cut(shape).Volume)
    return report


def accept(report):
    for key in ("lands_missing_mm2","floor_missing_mm2"):
        for name,values in report[key].items():
            assert max(values)<1e-4,(name,key,values)
    for name,value in report["floor_backing_missing_mm3"].items():
        assert value<1e-4,(name,"pocket broke through backing",value)
    for w in report["window_area_mm2"]:
        assert w["through_all_faces"]>1,w
        if w["window"]>500:
            assert w["common_openings"]==2,w
