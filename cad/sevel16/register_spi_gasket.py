"""Register corresponding coolant windows in the two 8V gasket photographs."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import ROOT, layout, load


def contours(path, alpha_mask):
    image = Image.open(path).convert("RGBA")
    if alpha_mask:
        solid = np.asarray(image)[:,:,3] > 127
    else:
        white = Image.new("RGB", image.size, "white")
        white.paste(image, mask=image.getchannel("A"))
        solid = np.max(np.asarray(white), axis=2) < 180
    curves, hierarchy = cv2.findContours(solid.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    outer = max(range(len(curves)), key=lambda i: cv2.contourArea(curves[i]))
    holes = [c for i,c in enumerate(curves) if hierarchy[0,i,3] == outer and cv2.contourArea(c)>35]
    return curves[outer], holes


def center(contour):
    moments = cv2.moments(contour)
    return np.array([moments["m10"], moments["m01"]])/moments["m00"]


def registered(holes, reverse, axes):
    bores = sorted(sorted(holes, key=cv2.contourArea, reverse=True)[:4],
                   key=lambda c: center(c)[0], reverse=reverse)
    start, end = center(bores[0]), center(bores[-1])
    direction = end-start
    gain = (axes[-1]-axes[0])/np.dot(direction,direction)

    def project(points):
        p = np.asarray(points).reshape(-1,2) - start
        # The pair of large windows is on the plug side (-Y) on both references.
        return np.column_stack((axes[0]+gain*(p@direction),
                                gain*(p[:,0]*direction[1]-p[:,1]*direction[0])))
    residual = [round(float(project(center(c))[0,0]-x), 3) for c,x in zip(bores,axes)]
    return project, residual


def trace():
    source = ROOT/"PhotosMotor"
    first, = source.glob("*_666447-*_bk.png")
    second, = source.glob("*_926507-*.png")
    outer, holes = contours(first, True)
    second_outer, check = contours(second, False)
    axes = layout(*load())["centers"]
    project, errors = registered(holes, True, axes)
    confirm, second_errors = registered(check, False, axes)
    positions = np.array([confirm(center(c))[0] for c in check])
    pairs, rounds = [], []
    for curve in sorted(holes, key=cv2.contourArea, reverse=True)[4:]:
        points = project(cv2.approxPolyDP(curve, 1.15, True))
        xy = project(center(curve))[0]
        spans = np.ptp(points, axis=0)
        nearest = int(np.argmin(np.linalg.norm(positions-xy,axis=1)))
        other = confirm(cv2.approxPolyDP(check[nearest], 1.8, True))
        if max(spans) < 13 or max(spans)/max(1,min(spans)) < 1.55:
            # A circular opening should be compact on both photographs. The colour
            # photo includes thin dark fragments along the edge of the printed seal.
            a, b = np.ptp(project(curve),axis=0), np.ptp(confirm(check[nearest]),axis=0)
            if max(a)/min(a) < 1.4 and max(b)/min(b) < 1.4 and np.linalg.norm(positions[nearest]-xy) < 7:
                rounds.append({"center_mm":((xy+positions[nearest])/2).round(1).tolist(),
                               "radius_mm":round(float((a.mean()+b.mean())/4),1)})
            continue
        pairs.append(dict(center_mm=xy.round(3).tolist(), points_mm=points.round(3).tolist(),
                          check_center_mm=positions[nearest].round(3).tolist(),
                          check_points_mm=other.round(3).tolist(),
                          center_delta_mm=round(float(np.linalg.norm(positions[nearest]-xy)),3),
                          spans_mm=spans.round(3).tolist(), check_spans_mm=np.ptp(other,axis=0).round(3).tolist()))
    return {"status":"PHOTO_ESTIMATE", "axes_mm":axes, "bore_center_residuals_mm":[errors,second_errors],
              "sources":[{"path":str(f.relative_to(ROOT)), "sha256":hashlib.sha256(f.read_bytes()).hexdigest()}
                         for f in (first,second)], "windows":pairs,
              "outline_mm":project(cv2.approxPolyDP(outer,1.2,True)).round(3).tolist(),
              "check_outline_mm":confirm(cv2.approxPolyDP(second_outer,2.5,True)).round(3).tolist(),
              "round_apertures":rounds}


def run(output):
    with output.open("x") as handle:
        json.dump(trace(),handle,indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    run(parser.parse_args().output)
