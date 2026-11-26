"""Derive numbered comparison sheets from selected originals."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from .store import OUTPUT, ROOT, connect


def sheet(db, members, directory=OUTPUT / "sheets", root=ROOT, edge=800):
    members = list(members)
    if not 2 <= len(members) <= 4 or len(set(members)) != len(members):
        raise ValueError("Choose two to four distinct image IDs")
    if not 128 <= edge <= 1800:
        raise ValueError("Tile edge must be 128–1800 pixels")
    tiles = []
    mapping = []
    for number, image in enumerate(members, 1):
        row = db.execute("SELECT s.path FROM sources s JOIN source_images a ON s.id=a.source "
                         "WHERE a.image=? AND a.active ORDER BY s.path LIMIT 1", (image,)).fetchone()
        if not row:
            raise ValueError(f"Unknown active image {image}")
        path = root / row[0]
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != image:
                raise ValueError(f"Source changed since scan: {row[0]}")
            stream.seek(0)
            with Image.open(stream) as original:
                tile = ImageOps.exif_transpose(original).convert("RGBA")
        tile.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        tiles.append(tile)
        mapping.append(dict(label=f"IMG-{number:03}", image_id=image, original=row[0]))
    key = hashlib.sha256(json.dumps(["sheet-v1", members, edge]).encode()).hexdigest()
    width = max(tile.width for tile in tiles)
    height = max(tile.height for tile in tiles)
    canvas = Image.new("RGB", (2 * width, ((len(tiles)+1)//2) * (height+32)), "white")
    draw = ImageDraw.Draw(canvas)
    for index, tile in enumerate(tiles):
        x, y = index % 2 * width, index // 2 * (height+32)
        draw.text((x+4, y+7), mapping[index]["label"], fill="black")
        canvas.paste(tile, (x+(width-tile.width)//2, y+32+(height-tile.height)//2), tile)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (key + ".png")
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temp:
        try:
            canvas.save(temp, format="PNG")
            temp.flush()
            os.replace(temp.name, target)
        finally:
            Path(temp.name).unlink(missing_ok=True)
    with db:
        db.execute("INSERT INTO artifacts VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                   "path=excluded.path,members=excluded.members",
                   (key, os.path.relpath(target, root), json.dumps(mapping), "comparison_sheet"))
    return target


def grouped_sheets(db):
    count = 0
    for row in db.execute("SELECT id FROM groups WHERE kind='listing_candidate' ORDER BY id"):
        members = [r[0] for r in db.execute(
            "SELECT image FROM group_members JOIN images ON images.id=image "
            "WHERE group_id=? AND format IN ('JPEG','WEBP','PNG') ORDER BY image", (row[0],))]
        while len(members) >= 2:
            size = 3 if len(members) == 5 else min(4, len(members))
            sheet(db, members[:size])
            members = members[size:]
            count += 1
    return count


if __name__ == "__main__":
    with connect() as db:
        print(grouped_sheets(db), "comparison sheets")
