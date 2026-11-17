"""Restore one losslessly packaged donor shader during the GUI build."""

import base64
import hashlib
from pathlib import Path
import sys
import zlib


if len(sys.argv) != 4:
    raise SystemExit("usage: decode_lab_shader.py source destination sha256")

source, destination, expected_hash = sys.argv[1:]
encoded = "".join(Path(source).read_text().split())
data = zlib.decompress(base64.b64decode(encoded, validate=True))
if hashlib.sha256(data).hexdigest() != expected_hash:
    raise SystemExit(f"shader hash mismatch: {source}")
Path(destination).parent.mkdir(parents=True, exist_ok=True)
Path(destination).write_bytes(data)
