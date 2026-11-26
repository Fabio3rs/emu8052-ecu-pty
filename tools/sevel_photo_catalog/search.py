"""Offline search over provenance, observations, and human review history."""
import re
import unicodedata


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower())
                   if not unicodedata.combining(c))


def rebuild(db):
    with db:
        db.execute("DELETE FROM search")
        for image, in db.execute("SELECT DISTINCT image FROM source_images WHERE active"):
            fields = []
            for sql in (
                "SELECT path FROM sources JOIN source_images ON source=sources.id WHERE image=? AND active",
                "SELECT part,view,utility FROM classifications WHERE image=?",
                "SELECT detail FROM observations WHERE image=?",
                "SELECT status,part,view,note FROM review_decisions WHERE image=?",
                "SELECT part_id FROM cad_links WHERE image=?",
            ):
                for row in db.execute(sql, (image,)):
                    fields.extend(str(value) for value in row if value)
            document = normalize(" ".join(fields))
            if "spark-plug side" in document:
                document += " lado velas"
            if re.search(r"\bhead\b", document):
                document += " cabecote"
            db.execute("INSERT INTO search(image,description) VALUES(?,?)", (image, document))


def lookup(db, query):
    words = [w for w in re.findall(r"\w+", normalize(query))
             if w not in {"vista","do","das","dos","de","da","sevel"}]
    sql = db.execute("SELECT sql FROM sqlite_master WHERE name='search'").fetchone()[0]
    if words and "fts5" in sql.lower():
        return db.execute("SELECT image FROM search WHERE search MATCH ? ORDER BY rank,image",
                          (" AND ".join('"' + word + '"' for word in words),)).fetchall()
    predicate = " AND ".join("description LIKE ?" for _ in words) or "1"
    return db.execute(f"SELECT image FROM search WHERE {predicate} ORDER BY image",
                      tuple("%" + word + "%" for word in words)).fetchall()
