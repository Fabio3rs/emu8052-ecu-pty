"""Run IN FreeCAD Python (GUI, via MCP execute_code) to create provisional gasket reference.

Inputs:
  MANIFEST_PATH = '/absolute/path/to/head_gasket_geometry.json'  # optional script global
  GASKET_OUTPUT = '/absolute/path/to/output.fcstd'                 # optional
  GASKET_THICKNESS_MM = 1.2                                     # illustrative only

Example MCP execute_code payload:
  script = '/abs/.agents/skills/sevel-freecad-vision/scripts/freecad_gasket_from_json.py'
  manifest = '/abs/build/gasket/head_gasket_geometry.json'
  code = (
      "MANIFEST_PATH = " + repr(manifest) + "\n" +
      "exec(compile(open(" + repr(script) + ").read(), " + repr(script) + ", 'exec'))"
  )

This script was authored against the public FreeCAD API but has NOT been run
in a FreeCAD runtime in the artifact-generation environment. Verify at runtime.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import FreeCAD as App
import Part

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / 'assets/demo/head_gasket_geometry.json' if '__file__' in globals() else Path('build/gasket/head_gasket_geometry.json')
manifest_path = Path(globals().get('MANIFEST_PATH', os.getenv('SEVEL_GASKET_MANIFEST', DEFAULT_MANIFEST))).expanduser().resolve()
if not manifest_path.exists():
    raise FileNotFoundError(f'Gasket JSON not found: {manifest_path}')
data = json.loads(manifest_path.read_text(encoding='utf-8'))
assert data['units'] == 'mm'
thickness = float(globals().get('GASKET_THICKNESS_MM', 1.2))
if not 0.05 <= thickness <= 20:
    raise ValueError('Thickness out of reasonable preview range; specify GASKET_THICKNESS_MM explicitly')


def vector(xy):
    # Convert image Y down to a right-handed CAD XY reference.
    return App.Vector(float(xy[0]), -float(xy[1]), 0)


def polygon_wire(points):
    vertices = [vector(xy) for xy in points]
    if len(vertices) < 3:
        raise ValueError('Contour has fewer than 3 points')
    return Part.Wire(Part.makePolygon(vertices + [vertices[0]]).Edges)


def wire_signed_area(points):
    return 0.5 * sum(points[i][0] * points[(i + 1) % len(points)][1]
                     - points[(i + 1) % len(points)][0] * points[i][1]
                     for i in range(len(points)))


outer_points = data['outline_points_mm_image_y_down']
outer = polygon_wire(outer_points)
# Orient outer wire consistently in CAD coordinates; holes oppositely.
# Wires from imported contours can be clockwise or counterclockwise.
if wire_signed_area([[p[0], -p[1]] for p in outer_points]) < 0:
    outer.reverse()

hole_wires = []
for item in data['other_holes']:
    pts = item['points_mm_image_y_down']
    w = polygon_wire(pts)
    if wire_signed_area([[p[0], -p[1]] for p in pts]) > 0:
        w.reverse()
    hole_wires.append(w)
for bore in data['bores']:
    xy = bore['center_mm_image_y_down']
    c = Part.makeCircle(float(bore['diameter_mm'])/2, vector(xy), App.Vector(0,0,1))
    w = Part.Wire([c])
    w.reverse()  # inner wire orientation
    hole_wires.append(w)

# First attempt: one planar Face with all holes, to avoid repeated boolean cuts.
try:
    face = Part.Face([outer, *hole_wires])
    if not face.isValid() or len(face.Faces) != 1:
        raise ValueError('Composite face invalid; trying individual hole cuts')
except Exception as err:
    print('Part.Face([...]) warning:', err)
    face = Part.Face(outer)
    for k, hole in enumerate(hole_wires, 1):
        try:
            face = face.cut(Part.Face(hole))
        except Exception as e:
            raise RuntimeError(f'Cannot subtract hole {k}/{len(hole_wires)}: {e}') from e

solid = face.extrude(App.Vector(0, 0, thickness))
if not solid.isValid() or len(solid.Solids) != 1 or solid.Volume <= 0:
    raise RuntimeError(f'Invalid gasket solid: valid={solid.isValid()}, solids={len(solid.Solids)}, volume={solid.Volume}')

name = 'SEVEL_16_GasketReference'
doc = App.newDocument(name)
feature = doc.addObject('Part::Feature', 'HeadGasketReference')
feature.Shape = solid
feature.Label = 'Head gasket (PROVISIONAL - raster estimate)'
feature.addProperty('App::PropertyLength', 'NominalBore', 'Reference')
feature.NominalBore = float(data['nominal_cylinder_bore_mm'])
feature.addProperty('App::PropertyLength', 'PreviewThickness', 'Reference')
feature.PreviewThickness = thickness
feature.addProperty('App::PropertyString', 'ReferenceManifest', 'Provenance')
feature.ReferenceManifest = str(manifest_path)
feature.addProperty('App::PropertyString', 'Accuracy', 'Provenance')
feature.Accuracy = 'Not production CAD: source is raster/product illustration'
feature.ViewObject.ShapeColor = (0.30, 0.32, 0.36)
feature.ViewObject.LineColor = (0.05, 0.06, 0.09)
feature.ViewObject.DisplayMode = 'Flat Lines'
doc.recompute()
try:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
except Exception as exc:
    print('Viewer update unavailable:', exc)
output_path = globals().get('GASKET_OUTPUT') or os.getenv('SEVEL_GASKET_OUTPUT')
if output_path:
    p = Path(output_path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(str(p))
    print('Saved:', p)
print('Created:', feature.Name, 'valid:', solid.isValid(),
      'solids:', len(solid.Solids), 'volume_mm3:', round(solid.Volume, 3),
      'holes:', len(hole_wires), 'manifest:', manifest_path)
