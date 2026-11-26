"""Scan originals read-only. A content hash identifies the asset across renames."""
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageOps

from .store import ROOT, connect


def inspect_document(db, path, identity):
    cached = db.execute("SELECT 1 FROM document_inventory WHERE image=? AND error IS NULL",
                        (identity,)).fetchone()
    if cached:
        return
    pages = entries = listed = error = None
    try:
        info = subprocess.run(["pdfinfo",path], capture_output=True, check=True, timeout=60,
                              text=True, env={**os.environ,"LC_ALL":"C"}).stdout
        pages = int(next(line.split(":")[1] for line in info.splitlines() if line.startswith("Pages:")))
        listing = subprocess.run(["pdfimages","-list",path], capture_output=True, check=True,
                                 timeout=60,text=True).stdout
        rows = [line.split() for line in listing.splitlines() if line.split() and line.split()[0].isdigit()]
        page_numbers = [int(row[0]) for row in rows if row[2] == "image"]
        entries = len(page_numbers)
        listed = json.dumps(sorted(set(page_numbers)))
    except (OSError, subprocess.SubprocessError, ValueError, StopIteration) as exc:
        error = type(exc).__name__
    with db:
        db.execute("INSERT OR REPLACE INTO document_inventory VALUES(?,?,?,?,?)",
                   (identity,pages,entries,listed,error))


def inspect(path):
    fmt, width, height, orientation, alpha, dhash, error = ("unknown",) + (None,) * 6
    try:
        with path.open("rb") as stream:
            prefix = stream.read(4096)
        if prefix.startswith(b"%PDF-"):
            fmt = "PDF"
        elif prefix.startswith(b"gimp xcf ") and len(prefix) >= 26 and prefix[13] == 0:
            fmt = "XCF"
            width = int.from_bytes(prefix[14:18], "big")
            height = int.from_bytes(prefix[18:22], "big")
            if not width or not height:
                raise ValueError("invalid XCF canvas dimensions")
        elif b"<svg" in prefix:
            root = ET.parse(path).getroot()
            if root.tag.split("}")[-1] != "svg":
                raise ValueError("invalid SVG element")
            fmt = "SVG"
            bounds = root.get("viewBox", "").split()
            if len(bounds) == 4:
                width, height = map(float, bounds[2:])
        else:
            with Image.open(path) as im:
                fmt = im.format
                width, height = im.size
                im.load()
                orientation = im.getexif().get(274)
                alpha = int("A" in im.getbands() or "transparency" in im.info)
                grey = ImageOps.exif_transpose(im).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
                bits = [grey.getpixel((x,y)) > grey.getpixel((x+1,y))
                        for y in range(8) for x in range(8)]
                dhash = f"{int(''.join(str(int(b)) for b in bits), 2):016x}"
    except (OSError, ValueError, SyntaxError, TypeError) as exc:
        error = str(exc)
    return fmt, width, height, orientation, alpha, dhash, error


def scan(db, folder=ROOT / "PhotosMotor"):
    paths = set()
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        relative = str(Path(folder.name) / path.relative_to(folder))
        paths.add(relative)
        with path.open("rb") as stream:
            identity = hashlib.file_digest(stream, "sha256").hexdigest()
        exists = db.execute("SELECT format FROM images WHERE id=?", (identity,)).fetchone()
        info = None if exists else inspect(path)
        with db:
            if info:
                db.execute("INSERT OR IGNORE INTO images VALUES(?,?,?,?,?,?,?,?,?)",
                           (identity, path.stat().st_size, *info))
            db.execute("INSERT OR IGNORE INTO sources(path) VALUES(?)", (relative,))
            source = db.execute("SELECT id FROM sources WHERE path=?", (relative,)).fetchone()[0]
            db.execute("UPDATE source_images SET active=0 WHERE source=? AND image<>?",
                       (source, identity))
            db.execute("INSERT INTO source_images VALUES(?,?,1) ON CONFLICT(source,image) "
                       "DO UPDATE SET active=1", (source, identity))
        if (exists[0] if exists else info[0]) == "PDF":
            inspect_document(db,path,identity)
    with db:
        for source, path in db.execute("SELECT id,path FROM sources"):
            if path.startswith(folder.name + "/") and path not in paths:
                db.execute("UPDATE source_images SET active=0 WHERE source=?", (source,))
    return len(paths)


if __name__ == "__main__":
    with connect() as db:
        print(f"{scan(db)} original files inventoried")
