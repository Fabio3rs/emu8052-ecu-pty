"""Persistent image identities and the history of evidence attached to them."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/sevel-photo-catalog"
DATABASE = OUTPUT / "catalog.sqlite3"

SCHEMA = """
CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE images(id TEXT PRIMARY KEY, size INTEGER NOT NULL, format TEXT, width INTEGER,
 height INTEGER, orientation INTEGER, alpha INTEGER, dhash TEXT, error TEXT);
CREATE TABLE sources(id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE);
CREATE TABLE source_images(source INTEGER REFERENCES sources, image TEXT REFERENCES images,
 active INTEGER NOT NULL, PRIMARY KEY(source,image));
CREATE INDEX source_image_lookup ON source_images(image,active);
CREATE TABLE groups(id TEXT PRIMARY KEY, kind TEXT NOT NULL, evidence TEXT NOT NULL);
CREATE TABLE group_members(group_id TEXT REFERENCES groups ON DELETE CASCADE,
 image TEXT REFERENCES images, PRIMARY KEY(group_id,image));
CREATE TABLE inference_runs(id INTEGER PRIMARY KEY, cache_key TEXT NOT NULL, model TEXT,
 prompt_hash TEXT, status TEXT NOT NULL, raw TEXT, error TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX inference_cache ON inference_runs(cache_key,status);
CREATE TABLE observations(id INTEGER PRIMARY KEY, image TEXT REFERENCES images, detail TEXT NOT NULL,
 seen_in TEXT NOT NULL, origin TEXT NOT NULL, run INTEGER REFERENCES inference_runs);
CREATE TABLE regions(id INTEGER PRIMARY KEY, image TEXT REFERENCES images, box TEXT NOT NULL,
 observation INTEGER REFERENCES observations, decision INTEGER REFERENCES review_decisions);
CREATE TABLE classifications(id INTEGER PRIMARY KEY, image TEXT REFERENCES images, part TEXT,
 view TEXT, utility TEXT, variant TEXT, confidence REAL, origin TEXT, run INTEGER REFERENCES inference_runs);
CREATE INDEX classification_image ON classifications(image,part);
CREATE TABLE review_decisions(id INTEGER PRIMARY KEY, image TEXT REFERENCES images, status TEXT
 CHECK(status IN ('confirmed','rejected','uncertain')), part TEXT, view TEXT, note TEXT,
 created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE artifacts(id TEXT PRIMARY KEY, path TEXT NOT NULL, members TEXT NOT NULL, kind TEXT);
CREATE TABLE cad_links(image TEXT REFERENCES images, part_id TEXT, origin TEXT,
 PRIMARY KEY(image,part_id,origin));
INSERT INTO schema_migrations(version) VALUES(1);
PRAGMA user_version=1;
"""


def private_database(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    return path


def connect(path=DATABASE):
    path = private_database(path)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    if db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
        db.close()
        raise RuntimeError("Catalog requires SQLite WAL on a local filesystem")
    try:
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    db.execute(statement)
            try:
                db.execute("CREATE VIRTUAL TABLE search USING fts5(image UNINDEXED, description)")
            except sqlite3.OperationalError as exc:
                if "no such module" not in str(exc):
                    raise
                db.execute("CREATE TABLE search(image TEXT PRIMARY KEY, description TEXT)")
        if version < 2:
            db.execute("CREATE TABLE document_inventory(image TEXT PRIMARY KEY REFERENCES images, "
                       "pages INTEGER, image_entries INTEGER, image_pages TEXT, error TEXT)")
            db.execute("INSERT INTO schema_migrations(version) VALUES(2)")
            db.execute("PRAGMA user_version=2")
        elif version != 2:
            raise ValueError(f"Unsupported catalog version {version}")
        db.commit()
    except Exception:
        db.close()
        raise
    return db
