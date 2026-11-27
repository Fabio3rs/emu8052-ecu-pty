"""Compare the open carrier in two photos using its six cover fixing ears."""
import hashlib
import json
import math

import cv2
import numpy as np

from config import OUTPUT, ROOT, layout, load
from register_spi_spark_face import camera


def run():
    params,frame = load()
    v = params["valvetrain_layout_estimated"]["value"]
    c = params["cam_carrier_outline_estimated"]["value"]
    angle = math.radians(params["carrier_section_estimated"]["value"]["top_slope_y_deg"])
    half = v["carrier_half_width_mm"]/math.cos(angle)
    stations = layout(params,frame)["supports"]
    w = v["cam_journal_width_mm"]
    lo,hi = stations[0]-w/2,stations[-1]+w/2
    fix = np.float64([(lo+t*(hi-lo),y) for y in (half,-half) for t in c["cover_boss_fractions"]])
    world = np.float64([(x,y*math.cos(angle),v["carrier_cap_top_z_mm"]+y*math.sin(angle)) for x,y in fix])
    photos = [
        ("cima",ROOT/"PhotosMotor/cabeçote_cima.png",[640,480],
         [(98,84),(318,78),(542,79),(81,193),(320,189),(561,184)],
         [[(31,129),(158,131),(106,89),(98,178)],[(182,132),(307,132),(244,87),(243,177)],
          [(329,131),(456,130),(396,84),(394,174)],[(481,128),(612,130),(540,82),(541,172)]],
         [[(169,125),(169,133),(168,145)],[(317,120),(318,133),(319,146)],[(466,119),(468,132),(470,144)]]),
        ("726745",next((ROOT/"PhotosMotor").glob("*_726745-*")),[760,585],
         [(133,44),(318,83),(552,129),(93,173),(269,223),(493,293)],
         [[(77,105),(162,117),(132,65),(104,157)],[(183,130),(284,150),(251,85),(214,187)],
          [(303,156),(425,180),(378,108),(350,229)],[(450,196),(602,217),(540,145),(503,273)]],
         [[(177,111),(174,123),(169,138)],[(301,140),(297,153),(291,168)],[(441,174),(436,190),(431,206)]])]
    report = {"status":"PHOTO_ESTIMATE","plane":"Valve cover seat; local XY in mm",
              "note":"Points on the seating plane, including stud roots. Both photos show an open 8V carrier. Cima is unlabelled and 726745 is advertised Palio/Uno.",
              "nominal_bridge_width_mm":w,"nominal_window_y_mm":[-(half-c["side_rail_width_mm"]/math.cos(angle)),half-c["side_rail_width_mm"]/math.cos(angle)],"views":{}}
    for key,path,imgsize,anchors,windows,holes in photos:
        transform,_ = cv2.findHomography(np.float64(anchors),fix,0)
        def project(pts):
            return cv2.perspectiveTransform(np.float64([pts]),transform)[0]
        residual = np.linalg.norm(project(anchors)-fix,axis=1)
        bounds = [[at[0,0],at[1,0],at[3,1],at[2,1]] for at in (project(s) for s in windows)]
        widths = [bounds[i+1][0]-bounds[i][1] for i in range(3)]
        intrinsic,rotation,translation,errors = camera(world,np.float64(anchors),imgsize)
        report["views"][key] = {"path":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "intrinsic":intrinsic.tolist(),"rotation":rotation.tolist(),"eye_mm":(-rotation.T@translation).tolist(),
            "camera_anchor_errors_px":errors.round(2).tolist(),
            "control_image_size_px":imgsize,"fixings_px":anchors,"fixing_error_mm":residual.round(2).tolist(),
            "window_marks_px":windows,"window_limits_xmin_xmax_ymin_ymax_mm":np.round(bounds,2).tolist(),
            "bridge_widths_mm":np.round(widths,2).tolist(),"three_central_marks_px":holes,
            "three_central_marks_xy_mm":[project(s).round(2).tolist() for s in holes]}
    path = OUTPUT/"polish/exterior-02/reports/SPI-04-carrier-registration.json"
    path.write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    run()
