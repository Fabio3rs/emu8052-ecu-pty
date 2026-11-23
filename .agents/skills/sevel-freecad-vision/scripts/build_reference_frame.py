#!/usr/bin/env python3
"""Generate the deterministic canonical SEVEL bore reference from sourced parameters.

No FreeCAD dependencies. Inputs are user-editable and explicit about variant scope.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

TARGET_EVIDENCE = {'MANUAL_TARGET', 'MEASURED_TARGET'}
ACCEPTABLE_EVIDENCE = TARGET_EVIDENCE | {'OTHER_VARIANT_REFERENCE', 'PHOTO_ESTIMATE', 'ASSUMPTION'}


def _positive(entry: dict, name: str) -> float:
    if not isinstance(entry, dict) or entry.get('evidence') not in ACCEPTABLE_EVIDENCE:
        raise ValueError(f'{name}: missing/unsupported evidence class')
    if not str(entry.get('source', '')).strip():
        raise ValueError(f'{name}: source missing')
    value = entry.get('value')
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name}: numeric value missing')
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f'{name}: expected positive finite mm value')
    return number


def calculate(data: dict) -> tuple[dict, dict]:
    if data.get('schema') != 'sevel.reference-parameters.v1':
        raise ValueError('unsupported parameter schema')
    target = str(data.get('target_variant', '')).strip()
    if not target:
        raise ValueError('target_variant missing')
    coords = data.get('coordinate_convention')
    if not isinstance(coords, dict) or coords.get('origin') != 'cylinder_1_axis_intersection_with_block_deck':
        raise ValueError('reference frame origin must be canonical')
    if coords.get('x') != 'cylinder_1_to_cylinder_4' or coords.get('z') != 'cylinder_axis_pointing_toward_cylinder_head':
        raise ValueError('reference frame axes do not match the skill contract')
    if coords.get('block_deck_z_mm') != 0:
        raise ValueError('deck z must equal zero; transform references separately')
    dims = data.get('dimensions')
    if not isinstance(dims, dict):
        raise ValueError('dimensions object missing')
    bore_entry = dims.get('cylinder_bore_diameter_mm')
    stroke_entry = dims.get('stroke_mm')
    bore = _positive(bore_entry, 'cylinder bore')
    stroke = _positive(stroke_entry, 'stroke')
    spacings_entries = dims.get('center_spacings_mm')
    if not isinstance(spacings_entries, list) or len(spacings_entries) != 3:
        raise ValueError('center_spacings_mm must be three sourced dimension objects')
    spacings = [_positive(entry, f'center spacing {i+1}') for i, entry in enumerate(spacings_entries)]
    edge_gaps = [round(s - bore, 7) for s in spacings]
    if any(gap <= 0 for gap in edge_gaps):
        raise ValueError('circular bores overlap or touch according to the supplied centers')
    xs = [0.0]
    for s in spacings:
        xs.append(round(xs[-1] + s, 7))
    if any(xs[i] >= xs[i+1] for i in range(3)):
        raise ValueError('centers must increase in X')
    radius = bore / 2
    source_entries = [bore_entry, stroke_entry, *spacings_entries]
    all_target = all(entry['evidence'] in TARGET_EVIDENCE for entry in source_entries)
    status = 'PASS_CONFIRMED' if all_target else 'PASS_PROVISIONAL_FOR_VISUAL_ONLY'
    report = {
        'schema': 'sevel.reference-gate.v1',
        'target_variant': target,
        'status': status,
        'unknown_or_unconfirmed': [
            {'dimension': label, 'evidence': entry['evidence'], 'source': entry['source']}
            for label, entry in [
                ('cylinder_bore_diameter_mm', bore_entry),
                ('stroke_mm', stroke_entry),
                *[(f'center_spacing_{i+1}{i+2}_mm', ent) for i, ent in enumerate(spacings_entries)],
            ] if entry['evidence'] not in TARGET_EVIDENCE
        ],
        'gasket_opening_mm': 'UNMEASURED_AND_SEPARATE_FROM_CYLINDER_BORE',
        'cad_fabrication_approved': False,
        'tested_invariants': ['coordinates_ordered', 'no_bore_overlap', 'source_and_unit_present', 'deck_z_zero'],
    }
    frame = {
        'schema': 'sevel.reference-frame.v1',
        'units': 'mm',
        'target_variant': target,
        'frame': coords,
        'status': status,
        'cylinder_bore_diameter_mm': bore,
        'stroke_mm': stroke,
        'crank_radius_mm_derived': stroke/2,
        'center_spacings_mm': spacings,
        'center_to_center_span_mm': xs[-1],
        'edge_gaps_nominal_mm': edge_gaps,
        'bore_bounds_x_mm': [round(-radius, 7), round(xs[-1]+radius, 7)],
        'bore_circle_centers_mm': [
            {'cylinder': i+1, 'x': x, 'y': 0, 'z': 0, 'radius_mm': radius, 'diameter_mm': bore}
            for i, x in enumerate(xs)
        ],
        'cylinder_bore_source': bore_entry,
        'stroke_source': stroke_entry,
        'center_spacing_sources': spacings_entries,
        'head_gasket_opening_diameter_mm': dims.get('head_gasket_opening_diameter_mm', {}).get('value'),
        'crank_axis_z_mm': dims.get('crank_axis_z_mm', {}).get('value'),
    }
    return frame, report


def make_svg(frame: dict) -> str:
    radius = frame['cylinder_bore_diameter_mm'] / 2
    xs = [p['x'] for p in frame['bore_circle_centers_mm']]
    pad = 16.0
    xmin, ymin = -radius-pad, -radius-pad
    width, height = (xs[-1] + radius + pad)-xmin, 2*(radius+pad)
    nodes = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg"',
        f' width="{width:.4f}mm" height="{height:.4f}mm" viewBox="{xmin:.4f} {ymin:.4f} {width:.4f} {height:.4f}">',
        f'<desc>{escape(frame["target_variant"])} | {escape(frame["status"])} | bores only, gasket holes NOT inferred</desc>',
        f'<line x1="{xmin:.4f}" y1="0" x2="{xs[-1]+radius+pad:.4f}" y2="0" stroke="#64748b" stroke-width="0.35" stroke-dasharray="4,2"/>',
    ]
    for index, x in enumerate(xs, 1):
        nodes.extend([
            f'<circle cx="{x:.4f}" cy="0" r="{radius:.4f}" fill="none" stroke="#2563eb" stroke-width="0.8"/>',
            f'<line x1="{x:.4f}" y1="{-radius-5:.4f}" x2="{x:.4f}" y2="{radius+5:.4f}" stroke="#64748b" stroke-width="0.25" stroke-dasharray="2,2"/>',
            f'<text x="{x:.4f}" y="4" text-anchor="middle" font-size="8" fill="#0f172a">C{index}</text>',
        ])
    nodes.extend(['</svg>', ''])
    return '\n'.join(nodes)


def main(argv: list[str] | None = None) -> int:
    default = Path(__file__).resolve().parents[1] / 'assets' / 'reference_parameters.example.json'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--params', type=Path, default=default, help='Source-tracked JSON of input dimensions')
    parser.add_argument('--output', type=Path, required=True, help='Output folder for reference geometry and gate status')
    parser.add_argument('--require-confirmed', action='store_true', help='Treat other-variant or approximate dimensions as blocking')
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.params.read_text(encoding='utf-8'))
        frame, gate = calculate(data)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'reference_frame.json').write_text(json.dumps(frame, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (args.output / 'reference_gate.json').write_text(json.dumps(gate, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (args.output / 'reference_frame.svg').write_text(make_svg(frame), encoding='utf-8')
        print(f'{gate["status"]}: {frame["target_variant"]}')
        print('X centers:', [item['x'] for item in frame['bore_circle_centers_mm']])
        print('Nominal edge gaps (not measured wall thickness):', frame['edge_gaps_nominal_mm'])
        print('Output:', args.output)
        if args.require_confirmed and gate['status'] != 'PASS_CONFIRMED':
            print('BLOCKED: unverified center spacings for target variant')
            return 2
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f'FAIL: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
