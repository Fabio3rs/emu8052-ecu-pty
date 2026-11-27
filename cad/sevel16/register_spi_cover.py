"""Register the upper shoulders and the underside ribs to the same six fixing ears."""
import hashlib
import json
import math

import cv2
import numpy as np
from PIL import Image

from config import OUTPUT, ROOT, layout, load


def run():
    params,frame = load()
    v = params["valvetrain_layout_estimated"]["value"]
    half = v["carrier_half_width_mm"]/math.cos(math.radians(params["carrier_section_estimated"]["value"]["top_slope_y_deg"]))
    stations = layout(params,frame)["supports"]
    lo,hi = stations[0]-v["cam_journal_width_mm"]/2,stations[-1]+v["cam_journal_width_mm"]/2
    fs = params["cam_carrier_outline_estimated"]["value"]["cover_boss_fractions"]
    xs = [lo+u*(hi-lo) for u in reversed(fs)]
    photos = [
        ("top","215616663404314",(470,65,812,1216),True,
         [(228,77),(535,74),(871,70),(199,250),(532,249),(898,256)],[(356,150),(843,150)]),
        ("underside","223649425194962",(65,444,1216,836),False,
         [(131,38),(492,52),(879,62),(129,238),(482,255),(861,276)],
         [(105,135),(149,140),(291,145),(462,151),(511,155),(823,172),(894,176)])]
    result = {"status":"PHOTO_ESTIMATE","units":"cover-local millimetres","base_x_limits":[lo,hi]}
    for side,number,crop,turn,fixings,features in photos:
        path = ROOT/f"PhotosMotor/TAMPA_VALVULAS/{number}.png"
        with Image.open(path) as im:
            original = im.size
        w,h = crop[2]-crop[0],crop[3]-crop[1]
        w,h = (h,w) if turn else (w,h)
        ys = [half,-half] if turn else [-half,half]
        target = np.float64([[x,y] for y in ys for x in xs])
        matrix,_ = cv2.findHomography(np.float64(fixings),target)
        def project(points):
            return cv2.perspectiveTransform(np.float64([points]),matrix)[0]
        residuals = np.linalg.norm(project(fixings)-target,axis=1)
        assert max(residuals)<2
        result[side] = {"source":str(path.relative_to(ROOT)), "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                        "original_size_px":original,"crop_box_px":crop,"rotate_ccw_deg":90 if turn else 0,
                        "resized_control_image_px":[1000,round(h*1000/w)],"fixings_px":fixings,
                        "fixings_error_mm":residuals.round(2).tolist(),"feature_px":features,
                        "feature_local_mm":project(features).round(2).tolist()}
    return result


if __name__ == "__main__":
    path = OUTPUT/"polish/exterior-02/reports/SPI-06-cover-registration.json"
    path.write_text(json.dumps(run(),indent=2)+"\n")
