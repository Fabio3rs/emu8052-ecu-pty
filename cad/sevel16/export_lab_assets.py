"""FreeCAD console entry point. Export and verify first, publish separately."""
import hashlib
import json
import shutil
from pathlib import Path

import FreeCAD as App

from config import OUTPUT, ROOT, load
import export_step
import export_meshes
import parts_manifest
import prepare_mesh_probe


def export(checkpoint, generator):
    source = Path(checkpoint).resolve(strict=True)
    params, frame = load()
    if frame['status'] not in ('PASS_PROVISIONAL_FOR_VISUAL_ONLY','PASS_CONFIRMED'):
        raise ValueError('Datum gate is closed')
    root = OUTPUT/'runtime_exports'/source.stem
    root.mkdir(exist_ok=True, parents=True)
    revision = 1
    while (root/f'v{revision:03d}').exists():
        revision += 1
    audit = root/f'v{revision:03d}'
    audit.mkdir()
    saved = audit/source.name
    shutil.copyfile(source, saved)
    shutil.copyfile(OUTPUT/'parameters.json',audit/'parameters.json')
    shutil.copyfile(OUTPUT/'datums/reference_frame.json',audit/'reference_frame.json')
    doc = App.openDocument(str(saved))
    try:
        if not abs(doc.Phase.ThetaDeg)<1e-9:
            raise ValueError('Save a zero-phase checkpoint before exporting')
        solids = [o for o in doc.Objects if hasattr(o,'Shape')]
        if len({o.PartId for o in solids}) != len(solids) or not all(
                len(o.Shape.Solids)==1 and o.Shape.isValid() for o in solids):
            raise ValueError('Invalid solid or duplicate PartId')
        folder = export_step.run(doc,audit/'geometry')
        parts_manifest.run(doc,generator,folder)
        meshes = export_meshes.run(doc,folder,params)
        prepare_mesh_probe.run(doc,meshes,params=params)
        scripts = ['parts_manifest','export_meshes','mesh_obj','material_regions','prepare_mesh_probe','export_step']
        hashes = {name: hashlib.sha256((ROOT/'cad/sevel16'/(name+'.py')).read_bytes()).hexdigest()
                  for name in scripts}
        (audit/'export.json').write_text(json.dumps(dict(meshes=str(meshes.relative_to(audit)),
            checkpoint_sha256=hashlib.sha256(saved.read_bytes()).hexdigest(),
            exporter_hashes=hashes, datum_status=frame['status']),indent=2)+'\n')
        return meshes
    finally:
        App.closeDocument(doc.Name)
