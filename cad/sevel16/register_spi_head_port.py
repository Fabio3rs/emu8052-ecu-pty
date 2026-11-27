"""Fit the visible upper port lip to the bare head in three camera orientations."""
import hashlib
import json

import cv2
import numpy as np
from scipy.optimize import least_squares

from config import OUTPUT, ROOT
from register_spi_spark_face import camera

PHOTOS = {
    "723789": ([(313,501),(576,355),(799,248),(969,167),(1108,115),
                (540,591),(718,485),(944,347),(1052,284)],
               [(698,303),(700,294),(709,287),(716,287),(728,295),(734,306),
                (735,313),(730,324),(721,329),(710,324),(703,315)]),
    "885508": ([(118,430),(309,438),(526,457),(760,481),(1005,519),
                (246,561),(396,580),(670,616),(854,640)],
               [(455,464),(458,452),(467,445),(475,444),(486,447),(493,455),
                (495,466),(491,478),(482,485),(472,487),(461,481),(456,473)]),
    # The nearby head-bolt boss conceals the lower right of the lip in this view.
    "726745": ([(100,421),(257,463),(439,528),(650,603),(868,709),
                (212,570),(335,618),(571,718),(737,789)],
               [(392,512),(396,502),(403,496),(407,495),(416,498),(423,506),
                (405,539),(398,533),(393,524)]),
}


def circle_points(values):
    center = np.array(values[:3])
    normal = np.array([values[3],-1,values[4]])
    normal /= np.linalg.norm(normal)
    u = np.cross(normal,[0.,0.,1.])
    u /= np.linalg.norm(u)
    v = np.cross(normal,u)
    angle = np.linspace(0,2*np.pi,60,endpoint=False)
    return center+values[5]*(np.outer(np.cos(angle),u)+np.outer(np.sin(angle),v)),normal


def run():
    root = OUTPUT/"polish/exterior-02/reports"
    datum = json.loads((root/"SPI-04-spark-face-registration.json").read_text())
    pcs,refs = {},{}
    for key,(fixings,lip) in PHOTOS.items():
        path, = (ROOT/"PhotosMotor").glob(f"D_NQ_NP_2X_{key}-*.png")
        h,w = cv2.imread(str(path),cv2.IMREAD_GRAYSCALE).shape
        K,R,t,err = camera(np.float64(datum["fixings_xyz_mm"]),np.float64(fixings),(w,h))
        pcs[key] = (K,R,t,np.float64(lip))
        refs[key] = {"source":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                     "fixings_px":fixings,"lip_px":lip,"fixing_residuals_px":err.round(2).tolist(),
                     "intrinsic":K.tolist(),"rotation":R.tolist(),"translation":t.tolist()}
    def distances(values,key):
        xy,_ = circle_points(values)
        K,R,t,seen = pcs[key]
        points = (xy@R.T+t)@K.T
        uv = points[:,:2]/points[:,2,None]
        center,diameters,angle = cv2.fitEllipse(uv.astype(np.float32))
        a = np.deg2rad(angle)
        axes = np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])
        delta = (seen-center)@axes
        squared = (np.asarray(diameters)/2)**2
        return ((delta**2/squared).sum(axis=1)-1)/(2*np.linalg.norm(delta/squared,axis=1))
    def errors(values):
        return np.concatenate([distances(values,key) for key in pcs])
    solution = least_squares(errors,[100,-39,47,0,.25,8],diff_step=1e-4,
                             jac="3-point",x_scale=[10,10,10,1,1,5],loss="soft_l1")
    values = solution.x
    _,normal = circle_points(values)
    for key in pcs:
        refs[key]["lip_residuals_px"] = distances(values,key).round(2).tolist()
    result = {"status":"PHOTO_ESTIMATE","centre_mm":values[:3].round(2).tolist(),
              "outer_normal":normal.round(5).tolist(),"visible_bore_radius_mm":round(values[5],2),
              "photos":refs, "limits":"Visible lip only; thread, internal destination and depth unmeasured."}
    # The fitted bare port belongs to the comparison heads. In the separate
    # Tipo photo the installed fitting occludes the hole. Compare its visible
    # base before considering the donor position for the target casting.
    target = datum["views"]["870987"]
    K,R,t = (np.asarray(target[k]) for k in ("intrinsic","rotation","translation"))
    camera_point = K@(R@values[:3]+t)
    predicted = camera_point[:2]/camera_point[2]
    base = [405,180]
    result["tipo_check"] = {"photo":target["source"],"visible_base_px":base,
                            "donor_centre_projected_px":predicted.round(2).tolist(),
                            "separation_px":round(float(np.linalg.norm(predicted-base)),2),
                            "decision":"Donor location withheld; the target hole axis is covered by the installed fitting."}
    if not solution.success or max(abs(errors(values)))>10:
        raise ValueError(result)
    (root/"SPI-04-head-port.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__ == "__main__":
    fitted = run()
    print(fitted["centre_mm"],fitted["outer_normal"],fitted["visible_bore_radius_mm"])
