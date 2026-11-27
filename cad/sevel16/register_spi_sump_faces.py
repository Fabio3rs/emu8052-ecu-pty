"""Compare the fourteen long-side sump holes across the gasket, pan and bare block."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from config import OUTPUT, ROOT, layout, load
from register_spi_gasket import contours

# Straight rail first, then the stepped rail, starting at the deep end.
# The bright spots flanking a hole in the pan are visible in photo 790487.
# Only the central hole in each group has a counterpart in the bare block.
GASKET = [(133,68),(256,59),(392,56),(524,52),(655,51),(789,48),(920,57),
          (170,513),(284,503),(407,447),(533,436),(657,423),(789,424),(920,410)]
PAN = [(197,555),(274,547),(357,544),(436,538),(513,532),(594,526),(671,527),
       (199,835),(282,823),(371,779),(461,764),(544,750),(635,744),(720,729)]
BLOCK = {
    "654874": ([(213,463),(316,466),(427,466),(530,466),(632,468),(733,470),(833,463),
                (281,150),(364,158),(451,194),(544,202),(628,211),(720,212),(810,221)],
               [[(248,270),(229,381)],[(394,273),(382,382)],[(537,279),(531,384)],
                [(678,281),(680,387)],[(817,283),(825,390)]]),
    "721011": ([(71,670),(222,670),(391,664),(553,660),(710,656),(869,650),(1023,633),
                (159,167),(282,171),(414,220),(555,230),(680,234),(821,230),(960,240)],
               [[(111,356),(92,535)],[(332,353),(319,530)],[(550,346),(549,523)],
                [(761,343),(771,518)],[(982,338),(1001,511)]]),
}


def project(matrix, points):
    return cv2.perspectiveTransform(np.float64([points]),matrix)[0]


def source(number):
    path, = (ROOT/"PhotosMotor").glob(f"*_{number}-*.png")
    return {"path":str(path.relative_to(ROOT)), "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def register(points):
    image, gasket = np.float64(points), np.float64(GASKET)
    matrix, _ = cv2.findHomography(image,gasket)
    holdout = []
    for index in range(len(points)):
        keep = np.arange(len(points)) != index
        other, _ = cv2.findHomography(image[keep],gasket[keep])
        inferred = project(other,[image[index]])[0]
        holdout.append(round(float(np.linalg.norm(inferred-gasket[index])),2))
    return matrix, {"control_px":points, "to_gasket_px":matrix.tolist(),
                    "residual_px":np.linalg.norm(project(matrix,points)-gasket,axis=1).round(2).tolist(),
                    "leave_one_out_px":holdout}


def run():
    result = {"gasket":{**source("980809"),"control_px":GASKET}, "pan":{}, "blocks":{},
              "units":"pixels in original images", "status":"PHOTO_ESTIMATE"}
    _, quality = register(PAN)
    result["pan"] = {**source("790487"),**quality}
    for number,(points,cap_pairs) in BLOCK.items():
        matrix, quality = register(points)
        # Bearing-cap bolts sit above the sealing plane. Compare their apparent
        # midpoint in two independent views, without treating it as a datum.
        midpoints = [project(matrix,pair).mean(axis=0) for pair in cap_pairs]
        result["blocks"][number] = {**source(number),**quality,"cap_bolts_px":cap_pairs,
                                    "apparent_centres_on_gasket_px":np.round(midpoints,2).tolist()}
    # This similarity assumes the photographed loose gasket has the same scale
    # along and across its rails. The independently traced block views test the
    # indexing and perspective. Neither establishes an OEM transverse dimension.
    centres = [r["apparent_centres_on_gasket_px"] for r in result["blocks"].values()]
    supports = np.asarray(layout(*load())["supports"])
    origin, direction = np.linalg.lstsq(np.column_stack((np.ones(5),supports)),
                                         np.mean(centres,axis=0),rcond=None)[0]
    f = direction/(direction@direction)
    axes = np.array([f,[f[1],-f[0]]])
    def metric(points):
        return ((np.float64(points).reshape(-1,2)-origin)@axes.T).round(2)
    outer, holes = contours(ROOT/result["gasket"]["path"],False)
    inner = max(holes,key=cv2.contourArea)
    result["provisional_frame"] = {
        "support_x_mm":supports.tolist(), "gasket_origin_px":origin.tolist(),
        "gasket_pixel_to_xy_mm":axes.tolist(),
        "apparent_bearing_centres_mm":[metric(pts).tolist() for pts in centres],
        "side_fixings_mm":metric(GASKET).tolist(),
        "outer_mm":metric(cv2.approxPolyDP(outer,3.2,True)).tolist(),
        "inner_mm":metric(cv2.approxPolyDP(inner,3.2,True)).tolist(),
        "provenance":"Projected cap-bolt centres from two views above the seal plane. Transverse scale assumed isotropic."}
    assert all(max(row["leave_one_out_px"])<8 for row in [result["pan"],*result["blocks"].values()])
    assert np.max(np.linalg.norm(metric(centres[0])-metric(centres[1]),axis=1))<3
    return result


if __name__ == "__main__":
    out = OUTPUT/"polish/exterior-02/reports/SPI-07-sump-registration.json"
    data = run()
    out.write_text(json.dumps(data,indent=2)+"\n")
    for row in [data["pan"],*data["blocks"].values()]:
        print(Path(row["path"]).name, max(row["leave_one_out_px"]),row.get("apparent_centres_on_gasket_px"))
