"""Test the photographed sump outline at the existing CAD joint and end drives."""
import json
import math

import FreeCAD as App
import Part

from build_spi_skirt_review import DEST
from check_auxiliary import volume
from config import OUTPUT, load
from spi_deck_surfaces import profile

V = App.Vector
REPORTS = OUTPUT/"polish/exterior-02/reports"


def boundary(points, z):
    # Long straight segments need interior poles to retain the stamped corner
    # locations when the periodic quadratic rounds the digitized outline.
    samples = []
    for a,b in zip(points,points[1:]+points[:1]):
        count = math.ceil(math.dist(a,b)/6)
        samples.extend([(a[0]+(b[0]-a[0])*i/count,a[1]+(b[1]-a[1])*i/count)
                        for i in range(count)])
    return profile(samples,z)


def run():
    params,_ = load()
    data = json.loads((REPORTS/"SPI-07-sump-registration.json").read_text())["provisional_frame"]
    z = -params["block_visual_estimated"]["value"]["height"]
    thick = params["external_closures_estimated"]["value"]["pan_gasket_mm"]
    bottom = z-thick
    outer,inner = (boundary(data[k],bottom) for k in ("outer_mm","inner_mm"))
    face = outer.cut(inner)
    ring = face.extrude(V(0,0,thick))
    assert ring.isValid() and len(ring.Solids)==1
    doc = App.openDocument(str(DEST))
    try:
        old = doc.OilPanGasket.Shape
        result = {"provisional_gasket_bbox_mm":str(ring.BoundBox),"old_bbox_mm":str(old.BoundBox),
                  "fraction_of_provisional_gasket_covered":volume(ring.common(old))/volume(ring),
                  "part_overlap_mm3_at_rest":{}, "existing_joint_land":[], "old_section_mm":[]}
        plane = Part.makePlane(600,420,V(-170,-220,z-.5*thick))
        for edges in Part.sortEdges(old.section(plane).Edges):
            wire = Part.Wire(edges)
            result["old_section_mm"].append([[round(p.x,2),round(p.y,2)] for p in wire.discretize(Deflection=.12)])
        assert len(result["old_section_mm"])>=2
        for obj in doc.Objects:
            if not hasattr(obj,"Shape") or obj.Name in ("Block","OilPan","OilPanGasket"):
                continue
            if ring.BoundBox.intersect(obj.Shape.BoundBox):
                overlap = volume(ring.common(obj.Shape))
                if overlap>1e-5:
                    result["part_overlap_mm3_at_rest"][obj.Name]=round(overlap,3)
        for x,y in data["side_fixings_mm"]:
            row = {"centre_mm":[x,y]}
            for name,level in (("Block",z),("OilPanGasket",bottom),("OilPan",bottom-1)):
                probe = Part.makeCylinder(3.8,min(thick,1),V(x,y,level))
                row[name] = round(volume(probe.common(doc.getObject(name).Shape))/volume(probe),4)
            result["existing_joint_land"].append(row)
        for key,shape in (("outer",outer),("inner",inner)):
            result[key+"_section_mm"]=[[round(p.x,2),round(p.y,2)] for p in
                                       shape.OuterWire.discretize(Deflection=.12)]
        (REPORTS/"SPI-07-sump-envelope.json").write_text(json.dumps(result,indent=2)+"\n")
        return result
    finally:
        App.closeDocument(doc.Name)
