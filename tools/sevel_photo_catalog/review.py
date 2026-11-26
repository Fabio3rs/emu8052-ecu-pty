"""Local review views and transactional, append-only decisions."""
import json
from html import escape
from pathlib import Path

from .search import lookup
from .export import selected
from .vision import roi_valid


def decide(db, image, form):
    status = form.get("status")
    if status not in ("confirmed", "rejected", "uncertain"):
        raise ValueError("Status inválido")
    box = json.loads(form["roi"]) if form.get("roi") else None
    if box is not None and not roi_valid(box):
        raise ValueError("ROI inválida")
    if not db.execute("SELECT 1 FROM images WHERE id=?", (image,)).fetchone():
        raise ValueError("Imagem desconhecida")
    with db:
        decision = db.execute("INSERT INTO review_decisions(image,status,part,view,note) "
                              "VALUES(?,?,?,?,?)", (image,status,form.get("part"),form.get("view"),
                              form.get("note"))).lastrowid
        if box is not None:
            db.execute("INSERT INTO regions(image,box,decision) VALUES(?,?,?)",
                       (image,json.dumps(box),decision))
        if form.get("cad"):
            db.execute("INSERT OR IGNORE INTO cad_links VALUES(?,?,?)",
                       (image,form["cad"],f"decision/{decision}"))


def cards(db, ids):
    result = []
    for image, in ids:
        row = db.execute("SELECT min(path),format FROM images JOIN source_images ON image=images.id "
                         "JOIN sources ON source=sources.id WHERE images.id=? AND active GROUP BY image",
                         (image,)).fetchone()
        if not row:
            continue
        preview = (f'<img loading="lazy" width="160" height="120" style="object-fit:contain" '
                   f'src="/thumb/{image}" alt="">'
                   if row[1] in ("PNG","JPEG","WEBP") else escape(row[1]))
        result.append(f'<a class="card" href="/image/{image}">{preview}'
                      f'<small>{escape(Path(row[0]).name)}</small></a>')
    return '<section>' + ''.join(result) + '</section>'


def home(db, query, filters=None):
    filters = filters or {}
    results = lookup(db,query)
    if filters:
        allowed = {row[0] for row in selected(db,filters)}
        results = [row for row in results if row[0] in allowed]
    controls = "".join(f'<label>{title} <input name="{field}" value="{escape(filters.get(field,""))}"></label> '
                       for field,title in (("component","Componente"),("view","Vista"),("utility","Utilidade")))
    options = []
    for value,title in (("","Todos"),("prior-review","Revisão anterior"),("unreviewed","A revisar"),
                        ("provisional","Provisório"),("confirmed","Confirmado"),("rejected","Rejeitado"),
                        ("uncertain","Incerto")):
        chosen = " selected" if filters.get("status","") == value else ""
        options.append(f'<option value="{value}"{chosen}>{title}</option>')
    groups = db.execute("SELECT id,kind,evidence FROM groups ORDER BY kind,evidence")
    links = "".join(f'<li><a href="/group/{g}">{escape(k)} · {escape(e)}</a></li>' for g,k,e in groups)
    return (f'<h1>Referências SEVEL 1.6</h1><form><label>Buscar peça, vista ou revisão '
            f'<input name="q" value="{escape(query)}"></label> {controls}<label>Revisão '
            f'<select name="status" aria-label="Revisão">{"".join(options)}</select></label> <button>Buscar</button></form>'
            f'<details><summary>Grupos</summary><ul>{links}</ul></details>' + cards(db,results))


def detail(db, image, token):
    path = db.execute("SELECT min(path) FROM sources JOIN source_images ON source=sources.id "
                      "WHERE image=? AND active", (image,)).fetchone()[0]
    if not path:
        raise KeyError(image)
    lines = [f'<h1>{escape(Path(path).name)}</h1><a href="/original/{image}">Abrir original</a>']
    fmt = db.execute("SELECT format FROM images WHERE id=?", (image,)).fetchone()[0]
    if fmt in ("JPEG","WEBP","PNG"):
        lines.append(f'<p><a href="/original/{image}"><img width="480" src="/original/{image}"></a></p>')
    for sql in ("SELECT part,view,variant,origin FROM classifications WHERE image=? ORDER BY id",
                "SELECT detail,origin FROM observations WHERE image=? ORDER BY id",
                "SELECT status,part,view,note,created FROM review_decisions WHERE image=? ORDER BY id",
                "SELECT box FROM regions WHERE image=?", "SELECT part_id FROM cad_links WHERE image=?"):
        for row in db.execute(sql,(image,)):
            lines.append("<p>" + escape(" · ".join(str(v) for v in row if v is not None)) + "</p>")
    for artifact,members in db.execute("SELECT id,members FROM artifacts ORDER BY id"):
        for item in json.loads(members):
            if item["image_id"] == image:
                lines.append(f'<p><a href="/sheet/{artifact}">Prancha · {escape(item["label"])}</a></p>')
    lines.append(f'<form method="post"><input type="hidden" name="token" value="{token}">'
                 '<label>Decisão <select name="status"><option>uncertain</option><option>confirmed</option>'
                 '<option>rejected</option></select></label>')
    for field,label in (("part","Componente"),("view","Vista"),("note","Observação"),
                        ("roi","ROI normalizada [x0,y0,x1,y1]"),("cad","Objeto CAD / PartId")):
        lines.append(f'<p><label>{label} <input name="{field}"></label></p>')
    return "".join(lines) + "<button>Registrar revisão</button></form>"
