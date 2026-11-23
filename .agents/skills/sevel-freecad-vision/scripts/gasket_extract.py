#!/usr/bin/env python3
"""Convert a transparent gasket collage PNG into a cautiously calibrated 2D CAD reference.

Dependencies: numpy, opencv-python[-headless], Pillow.
Assumptions: 4 recognizable large circular holes in the largest connected component.
The source raster is a photograph/product image, NOT a dimensioned manufacturing drawing.
This tool does NOT undo a possible projective distortion nor know actual gasket clearance.

Creates:
  head_gasket_analytic.svg -- independent outer contour, 4 analytic bore circles,
                              and individual hole paths (for editing in Inkscape/FreeCAD)
  head_gasket_geometry.json -- OpenCV-derived, millimeter-valued geometric inputs
  head_gasket_overlay.png -- raster reference + detected ellipse / output circle comparison
  head_gasket_report.json -- diagnostics, assumptions and provenance

Example:
  python gasket_extract.py source.png --output build/gasket --nominal-bore-mm 86.4
  python gasket_extract.py source.png --output build/gasket --actual-opening-mm 87.0
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


def foreground_mask(image_path: Path, alpha_threshold: int = 128) -> np.ndarray:
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Could not read: {image_path}")
    if image.ndim == 3 and image.shape[2] == 4:
        # The supplied PNG is RGBA with transparent background; RGB is nearly black.
        return np.uint8(image[:, :, 3] >= alpha_threshold) * 255
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, thresholded = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Assume the largest region of the border is background, not gasket material.
    borders = np.concatenate([thresholded[0, :], thresholded[-1, :],
                              thresholded[:, 0], thresholded[:, -1]])
    background_is_white = float(np.mean(borders >= 128)) >= 0.5
    return cv2.bitwise_not(thresholded) if background_is_white else thresholded


def segment_components(mask: np.ndarray, min_area: int = 1000) -> tuple[np.ndarray, list[dict[str, Any]]]:
    count, labels, stats, centers = cv2.connectedComponentsWithStats(mask, 8)
    comps = []
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x, y, w, h = [int(v) for v in stats[label, :4]]
        comps.append({"label": label, "area_px": area, "bbox_px": [x, y, w, h],
                      "centroid_px": [float(v) for v in centers[label]]})
    comps.sort(key=lambda x: x["area_px"], reverse=True)
    return labels, comps


def contour_metrics(contour: np.ndarray) -> dict[str, float | list[float]]:
    if len(contour) < 5:
        raise ValueError("Contour too short to fit an ellipse")
    (x, y), (a, b), angle = cv2.fitEllipse(contour)
    return {"center_px": [float(x), float(y)],
            "diameters_px": [float(min(a, b)), float(max(a, b))],
            "angle_deg": float(angle),
            "ovalization_fraction": float(max(a, b)/min(a, b) - 1.0),
            "contour_area_px2": float(cv2.contourArea(contour))}


def _polygon_valid(points: list[list[float]]) -> bool:
    # Optional Shapely diagnostic if present; otherwise deterministic segment intersection test.
    if len(points) < 3:
        return False
    try:
        from shapely.geometry import Polygon  # optional, not required
        p = Polygon(points)
        return bool(p.is_valid and p.area > 0)
    except ImportError:
        pass

    def orient(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    def on_segment(a, b, p):
        return (abs(orient(a,b,p)) < 1e-8
                and min(a[0],b[0])-1e-8 <= p[0] <= max(a[0],b[0])+1e-8
                and min(a[1],b[1])-1e-8 <= p[1] <= max(a[1],b[1])+1e-8)

    def crosses(a,b,c,d):
        o1,o2,o3,o4 = orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
        return ((o1*o2 < 0 and o3*o4 < 0)
                or on_segment(a,b,c) or on_segment(a,b,d)
                or on_segment(c,d,a) or on_segment(c,d,b))

    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i+1)%n]
        if a == b:
            return False
        for j in range(i+1,n):
            if abs(j-i) <= 1 or (i == 0 and j == n-1):
                continue
            c, d = points[j], points[(j+1)%n]
            if crosses(a,b,c,d):
                return False
    return True


def approx_points(contour: np.ndarray, epsilon_px: float) -> list[list[float]]:
    """Simplify while rejecting self-intersections; may increase epsilon to remove pixel spikes."""
    last = None
    for eps in [epsilon_px, epsilon_px*1.2, epsilon_px*1.5, epsilon_px*2, epsilon_px*3]:
        poly = cv2.approxPolyDP(contour, eps, True)
        result = [[float(x), float(y)] for x, y in poly[:, 0]]
        last = result
        if _polygon_valid(result):
            return result
    raise ValueError(f"Contour could not become a simple polygon ({len(last or [])} points). Review raster cleanup")


def svg_path(points_mm: list[list[float]]) -> str:
    return "M " + " L ".join(f"{x:.5f},{y:.5f}" for x, y in points_mm) + " Z"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="RGBA or high-contrast gasket image")
    parser.add_argument("--output", type=Path, default=Path("build/gasket"), help="Output directory")
    parser.add_argument("--nominal-bore-mm", type=float, default=86.4,
                        help="Known cylinder bore (manual); used as approximate image scale when gasket opening is unknown")
    parser.add_argument("--actual-opening-mm", type=float, default=None,
                        help="Measured diameter of the GASKET opening; overrides the nominal bore as calibration reference")
    parser.add_argument("--alpha-threshold", type=int, default=128)
    parser.add_argument("--epsilon-px", type=float, default=1.0,
                        help="Max distance for Douglas-Peucker simplification of non-circular contours")
    parser.add_argument("--component-index", type=int, default=0,
                        help="Component by decreasing filled area: 0 is the largest")
    parser.add_argument("--bore-count", type=int, default=4)
    parser.add_argument("--keep-image-skew", action="store_true", help="Keep bore centers at their raw image Y coordinates instead of aligning their model centers")
    return parser.parse_args()


def convert(args: argparse.Namespace) -> dict[str, Any]:
    if args.nominal_bore_mm <= 0 or (args.actual_opening_mm is not None and args.actual_opening_mm <= 0):
        raise ValueError("Bore/opening diameters must be positive")
    if args.epsilon_px <= 0:
        raise ValueError("epsilon-px must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    mask = foreground_mask(args.source, args.alpha_threshold)
    labels, components = segment_components(mask)
    if not components or args.component_index >= len(components) or args.component_index < 0:
        raise ValueError("No matching connected component; inspect source and thresholds")
    chosen = components[args.component_index]
    component_mask = np.uint8(labels == chosen["label"]) * 255
    contours, hierarchy = cv2.findContours(component_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        raise ValueError("No contours")
    h = hierarchy[0]
    root_candidates = [i for i in range(len(contours)) if h[i][3] == -1]
    if not root_candidates:
        raise ValueError("Could not find external contour")
    root = max(root_candidates, key=lambda i: cv2.contourArea(contours[i]))
    holes = [i for i in range(len(contours)) if h[i][3] == root and cv2.contourArea(contours[i]) >= 20]
    # Identify the four largest approximately circular holes, rather than relying
    # on arbitrary contour index order or fitting a single vectorization path.
    circular_candidates = []
    for i in holes:
        a = cv2.contourArea(contours[i])
        if a < 3500 or len(contours[i]) < 5:
            continue
        m = contour_metrics(contours[i])
        if m["ovalization_fraction"] < 0.25:
            circular_candidates.append((a, i, m))
    circular_candidates.sort(reverse=True)
    bores = circular_candidates[:args.bore_count]
    if len(bores) != args.bore_count:
        raise ValueError(f"Expected {args.bore_count} large round holes, found {len(bores)}. Inspect component index and image")
    bores.sort(key=lambda item: item[2]["center_px"][0])
    diameter_reference = args.actual_opening_mm or args.nominal_bore_mm
    observed_diams_px = [(m["diameters_px"][0] + m["diameters_px"][1]) / 2 for _, _, m in bores]
    scale_mm_per_px = diameter_reference / float(np.median(observed_diams_px))
    origin_x_px, origin_y_px = bores[0][2]["center_px"]
    # Four cylinder centers must be collinear mechanically. Fit a line and
    # remove the global product-photo skew from surrounding raster contours.
    # This does not recover a perspective projection or missing dimensions.
    fit_x = np.array([item[2]["center_px"][0] for item in bores], dtype=float)
    fit_y = np.array([item[2]["center_px"][1] for item in bores], dtype=float)
    slope, intercept = np.polyfit(fit_x, fit_y, 1)
    residuals = fit_y - (slope*fit_x + intercept)

    def transform(points_px: list[list[float]]) -> list[list[float]]:
        # SVG/JSON follow image Y down; FreeCAD helper flips Y at import.
        # Align the underlying gasket image to a straight bore centerline by
        # default; this only removes mild 2D skew, not true perspective.
        return [[round((x - origin_x_px) * scale_mm_per_px, 5),
                 round((y - (origin_y_px if args.keep_image_skew else slope*x + intercept)) * scale_mm_per_px, 5)]
                for x, y in points_px]

    bore_indices = {idx for _, idx, _ in bores}
    bore_geometries = []
    for number, (_, i, metrics) in enumerate(bores, 1):
        center_mm = transform([metrics["center_px"]])[0]
        if not args.keep_image_skew:
            # Even residual < 1 px shifts matter in a crankshaft assembly;
            # explicitly impose the known straight-line geometric invariant.
            center_mm[1] = 0.0
        bore_geometries.append({
            "id": f"cylinder_{number}_opening", "kind": "circle", "center_mm_image_y_down": center_mm,
            "diameter_mm": diameter_reference, "source_contour_index": int(i), "fit": metrics,
            "dimension_status": "measured_gasket_opening" if args.actual_opening_mm else "assumed_equal_to_nominal_cylinder_bore",
        })

    outline_pts_mm = transform(approx_points(contours[root], args.epsilon_px))
    other_holes = []
    for i in sorted(holes, key=lambda idx: (-cv2.contourArea(contours[idx]), idx)):
        if i in bore_indices:
            continue
        pts = transform(approx_points(contours[i], args.epsilon_px))
        other_holes.append({"id": f"raster_hole_{len(other_holes)+1:02d}", "kind": "polyline",
                            "source_contour_index": int(i), "contour_area_px2": round(cv2.contourArea(contours[i]), 2),
                            "points_mm_image_y_down": pts, "dimension_status": "raster_estimate_not_verified"})

    geometry = {
        "source": str(args.source.name),
        "units": "mm", "coordinate_system": "image Y down, X origin = first bore center; nominal Y=0 on bore centerline",
        "deskew_enabled": not args.keep_image_skew,
        "fitted_bore_centerline_y_px": {"slope": float(slope), "intercept": float(intercept)},
        "estimated_scale_mm_per_pixel": scale_mm_per_px,
        "nominal_cylinder_bore_mm": args.nominal_bore_mm,
        "assumed_or_measured_gasket_opening_mm": diameter_reference,
        "calibration_assumption": "measured gasket opening" if args.actual_opening_mm else "GASKET opening assumed equal to nominal cylinder bore; NOT verified",
        "geometry_provenance": {"outline": "raster estimate", "large_holes": "analytic circles with tentative scale", "other_holes": "raster estimates"},
        "contour_tolerance_px": args.epsilon_px,
        "outline_points_mm_image_y_down": outline_pts_mm,
        "bores": bore_geometries,
        "other_holes": other_holes,
    }
    # Independent geometric SVG shapes. Unlike Inkscape auto-trace's single path,
    # CAD users can select each hole and each analytic circle as separate geometry.
    allpoints = np.array(outline_pts_mm)
    minx, miny = np.min(allpoints, axis=0)
    maxx, maxy = np.max(allpoints, axis=0)
    margin = 6.0
    vb = [minx-margin, miny-margin, maxx-minx+2*margin, maxy-miny+2*margin]
    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb[2]:.5f}mm" height="{vb[3]:.5f}mm" viewBox="{vb[0]:.5f} {vb[1]:.5f} {vb[2]:.5f} {vb[3]:.5f}">',
        '<title>SEVEL 1.6 head gasket - provisional, not a fabrication drawing</title>',
        '<desc>Vector-derived outline; analytic cylinder circles; non-bore holes remain raster estimates. Units mm, image Y down.</desc>',
        '<g id="outline" fill="none" stroke="#242d3a" stroke-width="0.36">',
        f'<path id="gasket_outer_outline" d="{svg_path(outline_pts_mm)}"/>',
        '</g>',
        '<g id="cylinder_openings" fill="none" stroke="#b13a4b" stroke-width="0.44">',
    ]
    for bore in bore_geometries:
        x, y = bore["center_mm_image_y_down"]
        svg_lines.append(f'<circle id="{bore["id"]}" cx="{x:.5f}" cy="{y:.5f}" r="{diameter_reference/2:.5f}"/>')
    svg_lines.extend(['</g>', '<g id="other_gasket_holes" fill="none" stroke="#4c6f95" stroke-width="0.26">'])
    for hole in other_holes:
        svg_lines.append(f'<path id="{hole["id"]}" d="{svg_path(hole["points_mm_image_y_down"])}"/>')
    svg_lines.extend(['</g>', '</svg>'])
    (args.output / 'head_gasket_analytic.svg').write_text('\n'.join(svg_lines) + '\n', encoding='utf8')
    (args.output / 'head_gasket_geometry.json').write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

    # Diagnostic image: top gasket source (light grey) with original ellipse and
    # projected analytic circle at the same estimated scale. Image crop retains
    # the source source pixel coordinates for comparison with reference material.
    rgba = Image.open(args.source).convert('RGBA')
    backdrop = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
    backdrop.alpha_composite(rgba)
    canvas = backdrop.convert('RGB')
    draw = ImageDraw.Draw(canvas)
    for k, bore in enumerate(bore_geometries, 1):
        m = bore["fit"]
        x, y = m["center_px"]
        radius_px = diameter_reference / (2 * scale_mm_per_px)
        draw.ellipse((x-radius_px, y-radius_px, x+radius_px, y+radius_px), outline=(190, 50, 55), width=3)
        draw.line([(x-6, y), (x+6, y)], fill=(40, 130, 170), width=2)
        draw.line([(x, y-6), (x, y+6)], fill=(40, 130, 170), width=2)
        draw.text((x-7, y+radius_px+5), str(k), fill=(15, 65, 100))
    x, y, w, height = chosen["bbox_px"]
    crop = (max(0,x-16),max(0,y-18),min(canvas.width,x+w+16),min(canvas.height,y+height+30))
    canvas.crop(crop).save(args.output / 'head_gasket_overlay.png')

    centers_px = [b["fit"]["center_px"] for b in bore_geometries]
    center_spacing_px = [round(centers_px[i+1][0]-centers_px[i][0], 3) for i in range(len(centers_px)-1)]
    report = {
        "source_png_dimensions_px": [int(mask.shape[1]), int(mask.shape[0])],
        "all_components_over_1000px": components,
        "selected_component": chosen,
        "head_gasket_holes_total": len(holes),
        "analytic_bore_count": len(bore_geometries),
        "other_holes_count": len(other_holes),
        "bore_diameters_px": [[round(x,3) for x in b["fit"]["diameters_px"]] for b in bore_geometries],
        "bore_ovalization_pct": [round(100*b["fit"]["ovalization_fraction"], 3) for b in bore_geometries],
        "center_spacing_px": center_spacing_px,
        "estimated_center_spacing_mm": [round(d*scale_mm_per_px, 2) for d in center_spacing_px],
        "estimated_scale_mm_per_px": scale_mm_per_px,
        "bore_centerline_fit_residual_px": [round(float(r),3) for r in residuals],
        "aligned_nominal_bore_centers": not args.keep_image_skew,
        "warnings": [
            "The photo may be scaled, perspective distorted, anti-aliased or resampled.",
            "Cylinder-to-cylinder spacing is an image estimate, NOT a verified engine dimension.",
            "Nominal CAD bore centers are aligned to a straight line by default; photo perspective remains uncorrected.",
            "The reference circle is the nominal cylinder bore; gasket opening diameter might differ.",
            "Do NOT machine a gasket or engine component from this provisional tracing.",
            "Other gasket parts of the collage may have different image scales; calibrate separately.",
            "SVG outlines may require CAD cleanup (self-intersections, very short edges, tangent holes).",
        ],
    }
    (args.output / 'head_gasket_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return report


if __name__ == '__main__':
    args = parse_args()
    report = convert(args)
    print(json.dumps({
        "output": str(args.output),
        "analytic_bores": report["analytic_bore_count"],
        "other_holes": report["other_holes_count"],
        "mm_per_pixel_estimate": round(report["estimated_scale_mm_per_px"], 6),
        "estimated_center_spacing_mm": report["estimated_center_spacing_mm"],
    }, indent=2))
