"""Recheck a suspect FreeCAD volume with span-aware OCCT integration."""
import subprocess
import tempfile
from pathlib import Path

from config import OUTPUT


def volumes(*shapes):
    tool = OUTPUT/'check_brep_volume'
    with tempfile.TemporaryDirectory() as scratch:
        inputs = []
        for i, shape in enumerate(shapes):
            path = Path(scratch)/f'{i}.brep'
            shape.exportBrep(str(path))
            inputs.append(str(path))
        result = subprocess.run([str(tool),*inputs],capture_output=True,text=True,check=True)
        values = [float(line) for line in result.stdout.splitlines()]
        if len(values)!=len(shapes) or not all(value>0 for value in values):
            raise ValueError('Invalid adaptive volume result')
        return values
