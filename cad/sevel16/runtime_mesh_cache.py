"""Reuse validated OBJ payloads when a FreeCAD resave only perturbs ASCII coefficients."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

# OCCT serializes normalized rotation coefficients one ULP differently after
# reopen. Keep topology, element order and integer fields byte-exact. Round
# floating values at 1e-9 (CAD mm or dimensionless), below the mesh tolerance.
DECIMAL = re.compile(rb'(?<!\S)[-+]?(?:\d+\.\d*|\d*\.\d+|\d+[eE][-+]?\d+)(?:[eE][-+]?\d+)?(?=\s|$)')


def geometry_hashes(checkpoint, rows):
    with zipfile.ZipFile(checkpoint) as archive:
        tree = ET.fromstring(archive.read('Document.xml'))
        objects = {o.attrib['name']:o for o in tree.findall('ObjectData/Object')}
        result = {}
        for row in rows:
            p = objects[row['source_object']].find("Properties/Property[@name='Shape']/Part")
            data = archive.read(p.attrib['file'])
            data = DECIMAL.sub(lambda m: format(round(float(m[0]),9)+0.,'.15g').encode(),data)
            result[row['id']] = hashlib.sha256(data).hexdigest()
        return result


def resolve_payloads(manifest, folder, destination, checkpoint):
    signatures = geometry_hashes(checkpoint,manifest['parts'])
    previous, old_rows, old_folder = {}, {}, None
    pointer = destination/'current.json'
    if pointer.exists():
        revision = json.loads(pointer.read_bytes())['asset_revision']
        if not re.fullmatch('[a-f0-9]{64}',revision):
            raise ValueError('Invalid current revision')
        old_folder = destination/revision
        data = (old_folder/'parts_manifest.json').read_bytes()
        if hashlib.sha256(data).hexdigest() != revision:
            raise ValueError('Current manifest hash mismatch')
        previous = json.loads(data)
        if previous['generator']['datum_sha256'] == manifest['generator']['datum_sha256'] and (
                previous.get('runtime',{}).get('mesh_exporter_sha256') == manifest['runtime']['mesh_exporter_sha256']):
            old_rows = {p['id']:p for p in previous['parts']}
    meshes, paths = {}, {}
    for row in manifest['parts']:
        row['geometry_source_sha256'] = signatures[row['id']]
        old = old_rows.get(row['id'])
        reuse = old and old.get('geometry_source_sha256') == signatures[row['id']] and old['mesh_batches'] == row['mesh_batches']
        if reuse and previous['generator']['parameter_sha256'] != manifest['generator']['parameter_sha256']:
            # A uniform body batch has no parameter-dependent surface assignments.
            # Mixed or classified surfaces still require fresh classification.
            reuse = all(batch.startswith('body_surface_batch_') for batch in row['mesh_batches'])
        if reuse:
            row['mesh_id'],row['mesh_file'] = old['mesh_id'],old['mesh_file']
        key = row['mesh_id']
        meshes[key] = (previous if reuse else manifest)['meshes'][key]
        paths[key] = (old_folder if reuse else folder)/meshes[key]['file']
    manifest['meshes'] = meshes
    return paths
