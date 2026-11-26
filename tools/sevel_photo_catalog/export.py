"""Render portable Markdown from a consistent catalog snapshot."""
import hashlib
import json
import os
import re
from collections import defaultdict
from urllib.parse import quote

from .store import OUTPUT, ROOT, connect


def selected(db, filters):
    predicates = ["a.active=1"]
    values = []
    fields = {"component":"part", "view":"view", "utility":"utility"}
    criteria = []
    for key,column in fields.items():
        if filters.get(key):
            expression = f"c.{column}"
            if key != "utility":
                expression = (f"coalesce((SELECT nullif(d.{column},'') FROM review_decisions d "
                              f"WHERE d.id=(SELECT max(id) FROM review_decisions WHERE image=a.image) "
                              f"AND d.status='confirmed'),c.{column})")
            criteria.append(f"instr(lower(coalesce({expression},'')),lower(?))>0")
            values.append(filters[key])
    if criteria:
        predicates.append("EXISTS (SELECT 1 FROM images i LEFT JOIN classifications c ON c.image=i.id "
                          "WHERE i.id=a.image AND "
                          + " AND ".join(criteria) + ")")
    if filters.get("group"):
        predicates.append("EXISTS (SELECT 1 FROM group_members m JOIN groups g ON g.id=m.group_id "
                          "WHERE m.image=a.image AND (g.id=? OR g.evidence=?))")
        values.extend([filters["group"]]*2)
    status = """coalesce((SELECT status FROM review_decisions r WHERE r.image=a.image
                           ORDER BY id DESC LIMIT 1), CASE
               WHEN EXISTS(SELECT 1 FROM classifications c WHERE c.image=a.image AND c.origin LIKE 'prior/%')
               THEN 'prior-review' WHEN EXISTS(SELECT 1 FROM observations o WHERE o.image=a.image AND o.run IS NOT NULL)
               THEN 'provisional' ELSE 'unreviewed' END)"""
    if filters.get("status"):
        predicates.append(status + "=?")
        values.append(filters["status"])
    return db.execute(f"SELECT a.image,s.path,{status} FROM source_images a JOIN sources s "
                      "ON s.id=a.source WHERE " + " AND ".join(predicates) + " ORDER BY a.image,s.path",values)


def export(db, directory=OUTPUT / "exports", root=ROOT, filters=None):
    filters = filters or {}
    if filters:
        suffix = hashlib.sha256(json.dumps(filters,sort_keys=True).encode()).hexdigest()[:16]
        directory = directory / "filtered" / suffix
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "SEVEL_PHOTO_CATALOG.md"
    previous = set()
    if target.is_file():
        previous.update(re.findall(r"\]\((SEVEL_[A-Za-z0-9_]+_REFERENCES(?:_\d+)?\.md)\)",
                                   target.read_text(encoding="utf-8")))

    def link(path):
        return quote(os.path.relpath(root / path, directory))

    sections = defaultdict(list)
    sheets = defaultdict(list)
    sheet_links = {}
    index = ["# Catálogo de referências SEVEL SOHC 1.6 8V", "",
             "Abra os originais e confira cada detalhe antes de revisar o CAD.", ""]
    with db:
        db.execute("BEGIN")
        for key, path, members, title in db.execute(
                "SELECT a.id,a.path,a.members,g.evidence FROM artifacts a "
                "LEFT JOIN groups g ON g.id=a.id AND g.kind='Prancha' "
                "WHERE a.kind IN ('comparison_sheet','user_annotated_sheet') ORDER BY a.id"):
            sheet_links[key] = link(path)
            for item in json.loads(members):
                label = f"{title} · {item['label']}" if title else f"Prancha {item['label']}"
                sheets[item["image_id"]].append(f"[{label}]({sheet_links[key]})")
        assets = defaultdict(list)
        statuses = {}
        for image, path, status in selected(db, filters):
            assets[image].append(path)
            statuses[image] = status
        if filters:
            index += ["Filtros · " + ", ".join(f"{k}={v}" for k,v in sorted(filters.items())), ""]
        index += [f"{sum(map(len, assets.values()))} caminhos ativos · {len(assets)} conteúdos.", ""]
        for status in sorted(set(statuses.values())):
            index.append(f"- {status} · {sum(s == status for s in statuses.values())}")
        if not filters:
            covered = {r[0] for r in db.execute("SELECT DISTINCT image FROM observations WHERE run IS NOT NULL")}
            index += [f"- Conteúdos sem observação automática validada · {len(assets.keys() - covered)}",
                      f"- Caminhos duplicados por SHA-256 · {sum(map(len, assets.values())) - len(assets)}"]
            for status,count in db.execute("SELECT status,count(*) FROM inference_runs GROUP BY status ORDER BY status"):
                index.append(f"- Registros de inferência · {status} · {count}")
            for status in ("confirmed","rejected","uncertain"):
                count = db.execute("SELECT count(*) FROM review_decisions WHERE status=?",(status,)).fetchone()[0]
                index.append(f"- Decisões humanas registradas · {status} · {count}")
        index.append("")
        for image, paths in assets.items():
            entry = [f"### {image}", ""]
            entry.extend(f"- [{os.path.basename(path)}]({link(path)})" for path in paths)
            entry.extend("- " + item for item in sheets[image])
            entry.append(f"- Estado da revisão · {statuses[image]}")
            pdf = db.execute("SELECT pages,image_entries,image_pages,error FROM document_inventory "
                             "WHERE image=?",(image,)).fetchone()
            if pdf:
                if pdf["error"]:
                    entry.append(f"- Inspeção interna do PDF pendente · {pdf['error']}")
                else:
                    entry.append(f"- PDF · {pdf['pages']} páginas · {pdf['image_entries']} ocorrências "
                                 f"de imagens em {len(json.loads(pdf['image_pages']))} páginas")
            parts = set()
            prior_parts = set()
            suggestions = set()
            for part, view, utility, variant, confidence, origin, model in db.execute(
                    "SELECT c.part,c.view,c.utility,c.variant,c.confidence,c.origin,r.model "
                    "FROM classifications c LEFT JOIN inference_runs r ON r.id=c.run "
                    "WHERE c.image=? ORDER BY c.origin,c.part,c.view,c.id", (image,)):
                parts.add(part or "unknown")
                if origin.startswith("prior/"):
                    prior_parts.add(part)
                elif model:
                    suggestions.add(part)
                entry.append(f"- {part} · {view} · {utility or 'unknown'} · variante {variant or 'unknown'} "
                             f"· confiança {confidence if confidence is not None else 'unknown'} · {model or origin}")
            if prior_parts and suggestions - prior_parts:
                entry.append("- Conciliação pendente de rótulos · revisão anterior: " +
                             ", ".join(sorted(prior_parts)) + " · sugestões automáticas: " +
                             ", ".join(sorted(suggestions - prior_parts)))
            if prior_parts:
                parts = prior_parts.copy()
            if not parts:
                entry.append("- Sem classificação visual registrada. Variante desconhecida.")
            for detail, support, origin in db.execute("SELECT o.detail,o.seen_in,coalesce(r.model,o.origin) "
                    "FROM observations o LEFT JOIN inference_runs r ON r.id=o.run "
                    "WHERE o.image=? ORDER BY o.id", (image,)):
                support_links = [f"[{item}]({link(assets[item][0])})" if item in assets else item
                                 for item in json.loads(support)]
                entry.append(f"- {detail} · suporte {', '.join(support_links)} · {origin}")
            for status, part, view, note in db.execute("SELECT status,part,view,note FROM review_decisions "
                                                       "WHERE image=? ORDER BY id", (image,)):
                entry.append(f"- Revisão humana {status} · {part} · {view} · {note or ''}")
                if part and status == "confirmed":
                    parts = {part}
            for part_id, in db.execute("SELECT DISTINCT part_id FROM cad_links WHERE image=? "
                                        "ORDER BY part_id", (image,)):
                entry.append(f"- CAD `{part_id}`")
            for part in parts or {"unknown"}:
                sections[part].append("\n".join(entry))
        index += ["## Grupos", ""]
        for key, kind, evidence, members in db.execute("SELECT g.id,kind,evidence,group_concat(m.image) FROM groups g "
                "JOIN group_members m ON g.id=m.group_id GROUP BY g.id ORDER BY kind,evidence"):
            visible = sorted(set(members.split(",")) & assets.keys())
            if visible:
                refs = ", ".join(f"[{image[:12]}]({link(assets[image][0])})" for image in visible)
                if key in sheet_links:
                    evidence = f"[{evidence}]({sheet_links[key]})"
                index.append(f"- {kind} · {evidence} · {refs}")
    index += ["", "## Referências por componente", ""]
    used = set()
    for part, entries in sorted(sections.items()):
        slug = re.sub(r"[^A-Z0-9_]+", "_", part.upper()).strip("_") or "COMPONENT"
        if len(slug) > 72:
            slug = slug[:60] + "_" + hashlib.sha256(part.encode()).hexdigest()[:10]
        if slug in used:
            slug += "_" + hashlib.sha256(part.encode()).hexdigest()[:12]
        used.add(slug)
        for offset in range(0, len(entries), 16):
            suffix = "" if offset == 0 else f"_{offset//16+1}"
            name = f"SEVEL_{slug}_REFERENCES{suffix}.md"
            previous.discard(name)
            index.append(f"- [{part} · página {offset//16+1}]({name})")
            header = f"# {part}\n\n[Índice geral](SEVEL_PHOTO_CATALOG.md)\n\n"
            (directory / name).write_text(header + "\n\n".join(entries[offset:offset+16]) + "\n")
    target.write_text("\n".join(index) + "\n")
    for obsolete in previous:
        (directory / obsolete).unlink(missing_ok=True)
    return target


if __name__ == "__main__":
    with connect() as db:
        print(export(db))
