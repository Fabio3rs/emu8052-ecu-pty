"""Recover the plug-side lower rim from two views using both drilled fixing rows."""
import hashlib
import json

import cv2
import numpy as np
from scipy.optimize import minimize_scalar

from config import OUTPUT, ROOT, layout, load
from head_fixing_alignment import LANDMARKS, lower_centers, register

# Nine visible hole centres, followed by the lower edge of the casting.
VIEWS = {
    "870987": ([(96,145),(301,154),(533,173),(789,195),(1058,224),
                (210,294),(371,309),(674,343),(876,369)],
               [(127,331),(180,336),(212,356),(240,364),(290,371),(329,374),(363,370),
                (387,368),(425,370),(464,370),(484,369),(510,375),(538,386),(566,390),
                (601,390),(643,396),(676,409),(704,422),(751,430),(802,438),(842,441),
                (867,435),(894,432),(919,433),(949,437),(990,439),(1030,437)]),
    "726745": ([(100,421),(257,463),(439,528),(650,603),(868,709),
                (212,570),(335,618),(571,718),(737,789)],
               [(160,569),(191,584),(210,595),(221,622),(248,644),(279,659),(307,672),
                (326,672),(350,669),(378,675),(404,680),(424,683),(453,696),(472,724),
                (506,736),(547,754),(565,765),(579,790),(615,805),(654,822),(692,846),
                (707,848),(735,845),(769,849),(800,855),(840,869),(877,876),(910,877)]),
}

# Lower machined edge on the chamber face. Ignore the plug tips behind that edge.
DECK_EDGE = [(1134,438),(1129,455),(1108,472),(1092,485),(1075,490),(1047,492),
             (1021,498),(1004,509),(991,523),(976,531),(947,535),(910,540),(878,542),
             (866,541),(853,533),(843,527),(826,523),(796,523),(768,522),(749,517),
             (733,517),(709,520),(696,526),(683,536),(674,541),(662,542),(643,537),
             (620,537),(595,540),(580,545),(567,556),(556,556),(543,563),(529,577),
             (515,585),(498,589),(465,594),(431,598),(397,602),(377,602),(363,597),
             (349,589),(335,583),(323,580),(301,579),(274,579),(248,581),(217,578),
             (187,573),(159,568),(145,561),(135,550)]


def camera(points, pixels, size):
    w,h = size
    def solve(focal):
        K = np.array([[focal,0,w/2],[0,focal,h/2],[0,0,1]],float)
        ok,r,t = cv2.solvePnP(points,pixels,K,None)
        if not ok:
            raise ValueError("Could not locate head photograph")
        predicted = cv2.projectPoints(points,r,t,K,None)[0].reshape(-1,2)
        return K,cv2.Rodrigues(r)[0],t.ravel(),np.linalg.norm(predicted-pixels,axis=1)
    best = minimize_scalar(lambda f: np.mean(solve(f)[3]**2),
                           bounds=(.55*w,3*w),method="bounded")
    return solve(best.x)


def run():
    params,frame = load()
    xs = layout(params,frame)["centers"]
    deck = params["head_lower_casting_estimated"]["value"]
    tops = np.round(np.mean([register(row,xs)["plug_side"] for row in LANDMARKS.values()],axis=0))
    points = np.float64([[x,y,deck["head_bolt_boss_top_z_mm"]] for x,y in tops]+
                        [[x,y,10] for x,y in lower_centers(xs)])
    faces = {}
    for number,(controls,edge) in VIEWS.items():
        path, = (ROOT/"PhotosMotor").glob(f"*_{number}-*.png")
        h,w = cv2.imread(str(path),cv2.IMREAD_GRAYSCALE).shape
        K,R,t,err = camera(points,np.float64(controls),(w,h))
        eye = -R.T@t
        rays = (np.column_stack((edge,np.ones(len(edge))))@np.linalg.inv(K).T)@R
        depth = (deck["head_gasket_thickness_mm"]-eye[2])/rays[:,2]
        xy = (eye+depth[:,None]*rays)[:,:2]
        assert np.all(depth>0) and np.all(np.diff(xy[:,0])>0)
        faces[number] = {"source":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                         "image_size_px":[w,h],"fixings_px":controls,"fixings_error_px":err.round(2).tolist(),
                         "intrinsic":K.tolist(),"rotation":R.tolist(),"translation":t.tolist(),
                         "eye_mm":eye.tolist(),"lower_rim_px":edge,"lower_rim_xy_mm":xy.round(2).tolist()}
    deck_source = json.loads((OUTPUT/"gasket/spi_deck_surfaces.json").read_text())["HeadLower"]
    matrix,_ = cv2.findHomography(np.float64(deck_source["control_px"]),np.float64(deck_source["control_mm"]))
    deck_rim = cv2.perspectiveTransform(np.float64([DECK_EDGE]),matrix)[0]
    assert np.all(np.diff(deck_rim[:,0])>0)
    common = []
    for x in np.arange(0,283,6):
        ys = [np.interp(x,*np.array(view["lower_rim_xy_mm"]).T) for view in faces.values()]
        common.append([int(x),*np.round(ys,2),round(float(np.interp(x,*deck_rim.T)),2)])
    return {"status":"PHOTO_ESTIMATE","fixings_xyz_mm":points.tolist(),"views":faces,
            "deck_view":{"source":deck_source["source"],"sha256":deck_source["sha256"],
                         "lower_rim_px":DECK_EDGE,"lower_rim_xy_mm":deck_rim.round(2).tolist()},
            "rim_comparison_x_y870987_y726745_y704878_mm":common}


if __name__ == "__main__":
    path = OUTPUT/"polish/exterior-02/reports/SPI-04-spark-face-registration.json"
    path.write_text(json.dumps(run(),indent=2)+"\n")
