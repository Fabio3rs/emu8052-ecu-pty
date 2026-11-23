"""Save a useful initial camera without changing validated B-rep geometry."""
import hashlib
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import FreeCAD as App
import Part
from config import OUTPUT
from capture_checkpoint import prepare_view
from parts_manifest import run as write_manifest


def shape_members(path):
    with zipfile.ZipFile(path) as archive:
        return {name:hashlib.sha256(archive.read(name)).hexdigest()
                for name in archive.namelist() if name.endswith('.brp')}


def run(doc, save_camera=True):
    path = Path(doc.FileName)
    checks_path = OUTPUT/'exports'/doc.Name/'export_checks.json'
    checks = json.loads(checks_path.read_text())
    previous_hash = checks['source_fcstd_sha256']
    reference = next((p for p in [path,Path(str(path)+'1')] if p.exists()
                      and hashlib.sha256(p.read_bytes()).hexdigest()==previous_hash),None)
    if reference is None:
        raise ValueError('Cannot locate the exact FCStd used for STEP export')
    with zipfile.ZipFile(reference) as archive:
        before = {n:archive.read(n) for n in archive.namelist() if n.endswith('.brp')}
        previous_tree = ET.fromstring(archive.read('Document.xml'))
    App.setActiveDocument(doc.Name)
    prepare_view('Isometric')
    if save_camera:
        doc.save()
    after = shape_members(path)
    assert set(before)==set(after)
    differences = {}
    with zipfile.ZipFile(path) as archive:
        current_tree = ET.fromstring(archive.read('Document.xml'))
        for name,data in before.items():
            current = archive.read(name)
            if current==data:
                differences[name] = 0
                continue
            # OCCT normalizes directions/topology when resaving; bytes can differ.
            a,b = Part.Shape(),Part.Shape()
            a.importBrepFromString(data.decode())
            b.importBrepFromString(current.decode())
            assert a.isValid() and b.isValid() and len(a.Solids)==len(b.Solids)
            delta = a.cut(b).Volume+b.cut(a).Volume
            assert abs(delta)<1e-5,(name,delta)
            differences[name] = delta
    for previous in previous_tree.findall('./ObjectData/Object'):
        query = "./Properties/Property[@name='Placement']/PropertyPlacement"
        a = previous.find(query)
        if a is None:
            continue
        b = current_tree.find(f"./ObjectData/Object[@name='{previous.get('name')}']").find(query)
        assert max(abs(float(a.get(k))-float(b.get(k))) for k in ['Px','Py','Pz','Q0','Q1','Q2','Q3'])<1e-10
    checks['source_fcstd_sha256_before_camera_save'] = previous_hash
    checks['source_fcstd_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    checks['geometry_members_sha256'] = after
    checks['camera_save_preserved_geometry'] = True
    checks['camera_save_symmetric_difference_mm3'] = differences
    checks_path.write_text(json.dumps(checks,indent=2)+'\n')
    write_manifest(doc)
    print('Saved camera; geometric equivalence checked:',len(after),'B-reps')
