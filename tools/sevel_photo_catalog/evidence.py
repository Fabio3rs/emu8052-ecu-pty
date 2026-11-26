"""Import prior visual reviews only when their source bytes match the catalog."""
import json

from .store import ROOT


def link_review_targets(db, manifest):
    """Map reviewed component categories to existing comparison objects."""
    targets = {
        "head": ("HeadLower",), "cabecote": ("HeadLower",),
        "head_and_cam": ("HeadLower", "CamCarrier"), "cam_carrier": ("CamCarrier",),
        "cabecote-montado": ("HeadLower",), "bloco": ("Block",),
        "bloco-montado": ("Block",), "crank": ("Crankshaft",),
        "oil_pan": ("OilPan",), "carter": ("OilPan",),
    }
    if not manifest.is_file():
        return
    parts = {p["source_object"]: p["id"] for p in json.loads(manifest.read_text())["parts"]}
    with db:
        for image, part in db.execute("SELECT DISTINCT image,part FROM classifications "
                                      "WHERE origin LIKE 'prior/%'"):
            for obj in targets.get(part, ()):
                if obj in parts:
                    db.execute("INSERT OR IGNORE INTO cad_links VALUES(?,?,?)",
                               (image, parts[obj], f"comparison/{manifest.parent.name}/{obj}"))


def import_reviews(db, directory=ROOT / "build/sevel-cad/reports"):
    for name in ("photo_manifest", "moving_sources"):
        path = directory / (name + ".json")
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data["photos"]
        with db:
            for row in rows:
                if row.get("reviewed") is False:
                    continue
                image = row["sha256"]
                if not db.execute("SELECT 1 FROM images WHERE id=?", (image,)).fetchone():
                    continue
                origin = f"prior/{name}/{row['path']}"
                if db.execute("SELECT 1 FROM classifications WHERE origin=? AND image=?",
                              (origin, image)).fetchone():
                    continue
                db.execute("INSERT INTO classifications(image,part,view,utility,variant,origin) "
                           "VALUES(?,?,?,?,?,?)", (image, row["part"],
                           row.get("view", row.get("orientation")), row.get("type", "foto"),
                           row.get("variant", row.get("variant_claim")), origin))
                detail = row.get("observation") or row.get("review")
                if detail:
                    db.execute("INSERT INTO observations(image,detail,seen_in,origin) "
                               "VALUES(?,?,?,?)", (image, detail, json.dumps([image]), origin))
    link_review_targets(db, directory.parent / "exports" /
                        "SEVEL_Accessories_A5_v005_ManifoldReview/parts_manifest.json")
