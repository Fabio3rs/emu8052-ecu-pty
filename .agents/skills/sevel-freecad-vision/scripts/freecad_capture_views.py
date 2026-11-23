"""Run through MCP execute_code in FreeCAD's GUI thread; save evidence images.

Set CAPTURE_OUTPUT_DIR, CAPTURE_PREFIX, CAPTURE_VIEWS variables before exec.
Examples: CAPTURE_VIEWS = ['Isometric', 'Top', 'Front', 'Right']
No command lines, shell screenshot programs, or screen sharing required.
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
import FreeCADGui as Gui

views = {
    'Isometric': 'viewAxonometric',
    'Top': 'viewTop',
    'Front': 'viewFront',
    'Right': 'viewRight',
    'Left': 'viewLeft',
    'Back': 'viewRear',
    'Bottom': 'viewBottom',
}
requested = globals().get('CAPTURE_VIEWS', ['Isometric', 'Top', 'Front', 'Right'])
prefix = str(globals().get('CAPTURE_PREFIX', 'SEVEL_milestone')).replace('/', '_')
out_dir = Path(globals().get('CAPTURE_OUTPUT_DIR', os.getenv('SEVEL_CAPTURE_DIR', 'build/cad_evidence'))).expanduser().resolve()
out_dir.mkdir(parents=True, exist_ok=True)
if Gui.activeDocument() is None:
    raise RuntimeError('No active FreeCAD GUI document')
view = Gui.activeDocument().activeView()
original_camera = view.getCamera()
stamp = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')
created = []
try:
    for title in requested:
        if title not in views:
            raise ValueError(f'Unsupported capture view: {title}')
        getattr(view, views[title])()
        view.fitAll()
        dest = out_dir / f'{prefix}-{title}-{stamp}.png'
        # FreeCAD saveImage captures the actual 3D viewport; unlike a screen grab,
        # it need not include unrelated windows.
        view.saveImage(str(dest), 1440, 960, 'White')
        if not dest.exists() or dest.stat().st_size < 200:
            raise RuntimeError(f'Capture missing/empty: {dest}')
        created.append(str(dest))
finally:
    view.setCamera(original_camera)
print('\n'.join(created))
