"""Photo-registered outlines on three separate faces of the SPI deck joint."""
import hashlib
import json
import math
from collections import Counter

import FreeCAD as App
import Part

from build_head_main_row import centers
from config import OUTPUT, layout
from head_fixing_alignment import lower_centers
from precise_volume import volumes

V = App.Vector


def registration(params, frame):
    spec = params["spi_deck_faces_estimated"]["value"]
    raw = (OUTPUT/spec["registration"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
        raise ValueError("Deck registration differs from its parameter snapshot")
    data = json.loads(raw)
    assert data["gasket"]["axes_mm"] == layout(params,frame)["centers"]
    return data


def profile(points, z):
    # A periodic quadratic follows the digitized bends without reproducing
    # individual raster pixels as corners or introducing interpolation overshoot.
    poles = [V(x,y,z) for x,y in points]
    curve = Part.BSplineCurve()
    knots = list(range(len(poles)+1))
    curve.buildFromPolesMultsKnots(poles,[1]*len(knots),knots,True,2)
    return Part.Face(Part.Wire([curve.toShape()]))


def circle(x, y, radius, z):
    return Part.Face(Part.Wire([Part.makeCircle(radius,V(x,y,z))]))


def gasket_windows(data, spec):
    apertures = []
    for window in data["gasket"]["windows"]:
        aperture = profile(window["points_mm"],0)
        if math.dist(window["center_mm"],(93,-54))<1:
            aperture.translate(V(*spec["gasket_slot_land_adjustment_mm"],0))
        apertures.append(aperture)
    return apertures


def gasket(params, frame, data):
    g = layout(params,frame)
    b = params["casting_visual_estimated"]["value"]
    h = params["head_lower_casting_estimated"]["value"]
    spec = params["spi_deck_faces_estimated"]["value"]
    outer = profile(spec["gasket_outline_mm"],0)
    fixes = centers(g["centers"]) + [(x,b["deck_hole_y"]) for x in g["supports"]]
    secondary = lower_centers(g["centers"])
    holes = [circle(x,0,h["head_gasket_opening_radius_mm"],0) for x in g["centers"]]
    holes += [circle(x,y,b["deck_hole_radius"],0) for x,y in fixes]
    holes += [circle(x,y,4.9,0) for x,y in secondary]
    trace = data["gasket"]
    for row in trace["round_apertures"]:
        xy = row["center_mm"]
        if min(math.dist(xy,p) for p in fixes + secondary) > 9:
            holes.append(circle(*xy,row["radius_mm"],0))
    holes += gasket_windows(data,spec)
    surface = outer.cut(holes).removeSplitter()
    assert len(surface.Faces)==1 and len(surface.Wires)==len(holes)+1, "Gasket web or perimeter opened"
    return surface.extrude(V(0,0,h["head_gasket_thickness_mm"]))


def shoulders(name, spec, z):
    pads = []
    depth = spec["shoulder_blend_depth_mm"] * (-1 if name=="Block" else 1)
    for edge in spec[name+"_shoulders_mm"]:
        sections = []
        for x,y in edge:
            points = [V(x,-62,z),V(x,y,z),V(x,spec["shoulder_root_y_mm"],z+depth),V(x,-62,z+depth)]
            sections.append(Part.makePolygon(points+[points[0]]))
        pads.append(Part.makeLoft(sections,True,True))
    return pads


def casting_openings(name, data, spec, z):
    traces = data[name]
    openings = [profile(pts,z) for pts in traces["profiles_mm"]]
    if name=="Block":
        # Keep the secondary fixing land at x=199 within the registration error.
        openings[2].translate(V(*spec["block_divided_window_land_adjustment_mm"],0))
    return openings + [circle(x,y,r,z) for x,y,r in traces["rounds"]]


def continuous_head_face(solid, z):
    # The full-solid refiner can retain old pocket perimeters as coplanar
    # seams. Unite just the machined face while keeping its actual boundary edges.
    coplanar, others = [], []
    for f in solid.Faces:
        if f.BoundBox.ZLength<1e-6 and abs(f.CenterOfMass.z-z)<1e-6:
            coplanar.append(f)
        else:
            others.append(f)
    if len(coplanar)==1:
        return solid
    uses = Counter(e.hashCode() for f in coplanar for e in f.Edges)
    boundary = [e for f in coplanar for e in f.Edges if uses[e.hashCode()]==1]
    wires = [Part.Wire(sequence) for sequence in Part.sortEdges(boundary)]
    assert all(w.isClosed() for w in wires)
    cap, = Part.makeFace(wires,"Part::FaceMakerBullseye").Faces
    if cap.normalAt(0,0).dot(coplanar[0].normalAt(0,0)) < 0:
        cap.reverse()
    shell = Part.makeShell(others+[cap])
    if not shell.isClosed():
        shell.sewShape()
    assert len(solid.Shells)==len(shell.Shells)==1 and shell.isClosed()
    result = Part.makeSolid(shell.Shells[0])
    before,after = volumes(solid,result)
    assert result.isValid() and abs(before-after)/before<1e-6
    return result


def casting(shape, name, params, data):
    h = params["head_lower_casting_estimated"]["value"]
    b = params["casting_visual_estimated"]["value"]
    z = 0 if name=="Block" else h["head_gasket_thickness_mm"]
    face = max((f for f in shape.Faces if f.BoundBox.ZLength < 1e-5 and
                abs(f.BoundBox.ZMin-z)<1e-5), key=lambda f:f.Area)
    # Locate the old rectangles at this interface. Some rims are trimmed by
    # tapered fixing bosses and therefore narrower than the original cutters.
    rims = [w for w in face.Wires if b["water_slot_length"]*.7 < w.BoundBox.XLength < b["water_slot_length"]+.01
            and abs(w.BoundBox.YLength-b["water_slot_width"])<.01 and abs(abs(w.BoundBox.Center.y)-55)<.01]
    assert len(rims)==8,(name,"legacy pocket count",len(rims))
    signed_depth = -17 if name=="Block" else h["deck_coolant_recess_depth_mm"]-z
    low = min(z,z+signed_depth)
    stock = [Part.makeBox(b["water_slot_length"], b["water_slot_width"], abs(signed_depth),
                          V(x-b["water_slot_length"]/2, side*55-b["water_slot_width"]/2,low))
             for x in data["gasket"]["axes_mm"] for side in (-1,1)]
    spec = params["spi_deck_faces_estimated"]["value"]
    filled = shape.Solids[0].fuse(stock).removeSplitter()
    for pad in shoulders(name,spec,z):
        filled = filled.fuse(pad).removeSplitter()
    # Restore the shallow drills where the rectangular tools crossed them.
    r,lo,hi = (3.4,-5,0) if name=="Block" else (4.3,z,10)
    drills = [Part.makeCylinder(r,hi-lo,V(x,y,lo)) for x,y in lower_centers(data["gasket"]["axes_mm"])]
    filled = filled.cut(drills).removeSplitter()
    openings = casting_openings(name,data,spec,z)
    # The two cast faces show different mouths. Their depth below the face
    # is unresolved. Keep recesses shallow enough to inspect in an open view.
    depth = -h["deck_coolant_recess_depth_mm"] if name=="Block" else spec["head_floor_above_deck_mm"]
    cutters = [f.extrude(V(0,0,depth)) for f in openings]
    candidate = filled.cut(cutters).removeSplitter()
    if name=="HeadLower":
        candidate = continuous_head_face(candidate,z)
    assert len(candidate.Solids)==1 and candidate.isValid() and candidate.Solids[0].isClosed(),name
    assert len(shape.Shells)==len(candidate.Shells) and .99<abs(candidate.Volume/shape.Volume)<1.01,name
    return candidate
