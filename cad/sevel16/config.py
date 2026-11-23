"""Load one parameter authority; never move or silently regenerate the datums."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'build/sevel-cad'


def load():
    params = json.loads((OUTPUT / 'parameters.json').read_text())
    frame = json.loads((OUTPUT / 'datums/reference_frame.json').read_text())
    path = ROOT / '.agents/skills/sevel-freecad-vision/scripts/build_reference_frame.py'
    spec = importlib.util.spec_from_file_location('sevel_reference', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calculated, gate = module.calculate(params)
    if calculated != frame or gate['status'] != frame['status']:
        raise ValueError('Stale master datum: reconcile parameters before building')
    return params, frame


def layout(params, frame):
    xs = [b['x'] for b in frame['bore_circle_centers_mm']]
    supports = [(3*xs[0]-xs[1])/2]
    supports += [(a+b)/2 for a, b in zip(xs, xs[1:])]
    supports += [(3*xs[-1]-xs[-2])/2]
    p = params['moving_geometry_estimated']['value']
    radius = params['dimensions']['stroke_mm']['value']/2
    height = params['block_visual_estimated']['value']['crank_depth']
    compression = height-p['rod_length_mm']-radius-p['deck_clearance_mm']
    if compression <= 0 or p['rod_length_mm'] <= radius or p['pin_offset_mm'] != 0:
        raise ValueError('Invalid centered-pin baseline or height closure')
    return {'centers': xs, 'supports': supports, 'radius': radius,
            'height': height, 'compression_height': compression}
