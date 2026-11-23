"""Run inside FreeCAD Python via execute_code with include_screenshot=False.

Print numerical checks for solids. Optionally set VALIDATE_OBJECTS = ['name', ...].
This does not prove dimensional accuracy against a manual or image.
"""
import json
import FreeCAD as App

doc = App.ActiveDocument
if doc is None:
    raise RuntimeError('No active document')
names = set(globals().get('VALIDATE_OBJECTS', []))
reports = []
for obj in doc.Objects:
    if names and obj.Name not in names:
        continue
    if not hasattr(obj, 'Shape'):
        continue
    shape = obj.Shape
    bb = shape.BoundBox
    reports.append({
        'name': obj.Name,
        'label': obj.Label,
        'null': bool(shape.isNull()),
        'valid': bool(shape.isValid()) if not shape.isNull() else False,
        'solids': len(shape.Solids),
        'faces': len(shape.Faces),
        'volume_mm3': float(shape.Volume),
        'bbox_mm': {'x': bb.XLength, 'y': bb.YLength, 'z': bb.ZLength},
    })
print(json.dumps({'document': doc.Name, 'object_reports': reports}, indent=2))
