"""Run inside FreeCAD (through MCP execute_code), not standard Python.

Set FRAME_MANIFEST_PATH and optionally FRAME_OUTPUT in the MCP shared namespace.
Expected input is reference_frame.json from build_reference_frame.py.
This creates reference wire circles and visual centerlines, not a physical block.
"""
from pathlib import Path
import json
import math
import FreeCAD as App
import Part

frame_path = Path(globals()['FRAME_MANIFEST_PATH']).expanduser().resolve()
frame = json.loads(frame_path.read_text(encoding='utf-8'))
if frame.get('schema') != 'sevel.reference-frame.v1' or frame.get('units') != 'mm':
    raise ValueError('Missing or unexpected SEVEL reference frame manifest')
if frame.get('status') not in ('PASS_CONFIRMED', 'PASS_PROVISIONAL_FOR_VISUAL_ONLY'):
    raise ValueError('Reference gate has not passed')

name = 'SEVEL_MasterDatum'
doc = App.newDocument(name)
group = doc.addObject('App::DocumentObjectGroup', 'MasterDatum')
group.Label = 'MASTER DATUM - NOT THE ENGINE BLOCK'
color = (0.13, 0.42, 0.84) if frame['status'] == 'PASS_CONFIRMED' else (0.88, 0.40, 0.13)

for item in frame['bore_circle_centers_mm']:
    index = int(item['cylinder'])
    x = float(item['x'])
    radius = float(item['radius_mm'])
    ring = doc.addObject('Part::Feature', f'Cylinder{index}_DeckBoreDatum')
    ring.Shape = Part.Wire([Part.makeCircle(radius, App.Vector(x, 0, 0), App.Vector(0, 0, 1))])
    ring.Label = f'C{index}: deck bore datum (Ø{radius*2:.3f} mm)'
    ring.addProperty('App::PropertyString', 'Provenance', 'Reference')
    ring.Provenance = frame['cylinder_bore_source']['source']
    ring.addProperty('App::PropertyString', 'Confidence', 'Reference')
    ring.Confidence = frame['cylinder_bore_source']['evidence']
    ring.ViewObject.LineColor = color
    ring.ViewObject.LineWidth = 3.0
    group.addObject(ring)

    # Finite line for visual guidance only, not a real cylinder or crank position.
    line = doc.addObject('Part::Feature', f'Cylinder{index}_AxisDatum')
    line.Shape = Part.makeLine(App.Vector(x, 0, -30), App.Vector(x, 0, 30))
    line.Label = f'C{index}: visual +Z axis (unbounded in actual model)'
    line.ViewObject.LineColor = (0.5, 0.5, 0.5)
    group.addObject(line)

for idx, (a, b) in enumerate(zip(frame['bore_circle_centers_mm'], frame['bore_circle_centers_mm'][1:]), 1):
    dist = doc.addObject('Part::Feature', f'CenterSpacing{idx}{idx+1}_Datum')
    dist.Shape = Part.makeLine(App.Vector(a['x'], 0, 0), App.Vector(b['x'], 0, 0))
    dist.Label = f'C{idx}-C{idx+1}: {b["x"]-a["x"]:.3f} mm (from source manifest)'
    dist.ViewObject.LineColor = color
    dist.addProperty('App::PropertyString', 'Confidence', 'Reference')
    dist.Confidence = frame['center_spacing_sources'][idx-1]['evidence']
    group.addObject(dist)

doc.recompute()
bores = [doc.getObject(f'Cylinder{i}_DeckBoreDatum') for i in range(1, 5)]
for i, datum in enumerate(bores):
    length = datum.Shape.Length
    expected = 2 * math.pi * frame['cylinder_bore_diameter_mm'] / 2
    if abs(length-expected) > 0.01 or not datum.Shape.isValid():
        raise AssertionError(f'Cylinder {i+1} invalid bore datum: {length} mm')
try:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewTop()
    Gui.activeDocument().activeView().fitAll()
except Exception as exc:
    print('GUI view not available:', exc)
output = globals().get('FRAME_OUTPUT')
if output:
    filename = Path(output).expanduser().resolve()
    filename.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(str(filename))
    print('Saved reference FCStd:', filename)
print('Master datum status:', frame['status'])
print('Cylinder X:', [v['x'] for v in frame['bore_circle_centers_mm']])
print('Crank Z is UNKNOWN until separately sourced or explicitly estimated')
