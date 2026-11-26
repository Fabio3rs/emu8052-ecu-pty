"""Generate reproducible candidate groups, keeping each evidence level separate."""
import hashlib
import itertools
import re
from collections import defaultdict

from .evidence import import_reviews
from .store import connect


def propose_specimen(db, members, evidence):
    members = sorted(set(members))
    if len(members) < 2 or not evidence.strip():
        raise ValueError("Provide two distinct image IDs and the visual evidence for association")
    identity = hashlib.sha256(("specimen_candidate/" + "/".join(members) + "/" + evidence).encode()).hexdigest()
    with db:
        for image in members:
            if not db.execute("SELECT 1 FROM source_images WHERE active AND image=?", (image,)).fetchone():
                raise ValueError("Unknown active image " + image)
        db.execute("INSERT OR IGNORE INTO groups VALUES(?,?,?)", (identity,"specimen_candidate",evidence))
        db.executemany("INSERT OR IGNORE INTO group_members VALUES(?,?)",
                       ((identity,image) for image in members))
    return identity


def group(db):
    buckets = defaultdict(set)
    rows = db.execute("SELECT s.path,i.id,i.dhash FROM sources s JOIN source_images a "
                      "ON s.id=a.source JOIN images i ON i.id=a.image WHERE a.active=1 "
                      "ORDER BY s.path").fetchall()
    hashes = {}
    aliases = defaultdict(list)
    for path, image, dhash in rows:
        aliases[image].append(path)
        if dhash:
            hashes[image] = int(dhash, 16)
        # The marketplace media ID identifies a photograph. The seller title
        # can suggest a common source across angles, with no specimen guarantee.
        listing = re.search(r'ML[AB]\d+_\d+-[FO]-(.+?)(?: \(\d+\))?\.\w+$', path)
        if listing:
            buckets["listing_candidate", listing[1]].add(image)
    for image, paths in aliases.items():
        if len(paths) > 1:
            buckets["identical_bytes", image].add(image)
    for left, right in itertools.combinations(sorted(hashes), 2):
        distance = (hashes[left] ^ hashes[right]).bit_count()
        if distance <= 4:
            buckets["near_image", f"dHash64 distance {distance}: {left}/{right}"].update([left,right])
    for image, part in db.execute("""
        WITH latest AS (
            SELECT image,part,status,row_number() OVER(PARTITION BY image ORDER BY id DESC) AS position
            FROM review_decisions
        ), preferred AS (
            SELECT image,part FROM latest WHERE position=1 AND status='confirmed' AND nullif(part,'') IS NOT NULL
        )
        SELECT image,part FROM preferred
        UNION SELECT c.image,c.part FROM classifications c
        WHERE c.part IS NOT NULL AND NOT EXISTS(SELECT 1 FROM preferred p WHERE p.image=c.image)
        AND (c.origin LIKE 'prior/%' OR NOT EXISTS(
            SELECT 1 FROM classifications h WHERE h.image=c.image AND h.origin LIKE 'prior/%'))
        """):
        if image in aliases:
            buckets["component", part].add(image)
    with db:
        db.execute("DELETE FROM groups WHERE kind IN "
                   "('identical_bytes','near_image','listing_candidate','component')")
        for (kind, evidence), members in sorted(buckets.items()):
            key = hashlib.sha256((kind + '/' + evidence).encode()).hexdigest()
            db.execute("INSERT INTO groups VALUES(?,?,?)", (key, kind, evidence))
            db.executemany("INSERT INTO group_members VALUES(?,?)",
                           ((key, image) for image in sorted(members)))


if __name__ == "__main__":
    with connect() as db:
        import_reviews(db)
        group(db)
        print([tuple(r) for r in db.execute("SELECT kind,count(*) FROM groups GROUP BY kind")])
