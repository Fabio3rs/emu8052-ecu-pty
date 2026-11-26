"""Loopback-only offline review server."""
import io
import mimetypes
import secrets
from contextlib import closing
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from PIL import Image, ImageOps

from .review import cards, decide, detail, home
from .search import rebuild
from .store import DATABASE, ROOT, connect


def serve(port, database=DATABASE):
    token = secrets.token_urlsafe(32)
    with closing(connect(database)) as db:
        rebuild(db)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, data, mime):
            self.send_response(200)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'none'; img-src 'self'; "
                             "style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; sandbox allow-forms allow-same-origin")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlsplit(self.path)
            route, _, key = url.path.strip("/").partition("/")
            with closing(connect(database)) as db:
                if route in ("original","thumb","sheet"):
                    if route == "sheet":
                        row = db.execute("SELECT path FROM artifacts WHERE id=?", (key,)).fetchone()
                        base = ROOT / "build/sevel-photo-catalog/sheets"
                    else:
                        row = db.execute("SELECT path FROM sources JOIN source_images ON sources.id=source "
                                         "WHERE image=? AND active ORDER BY path LIMIT 1", (key,)).fetchone()
                        base = ROOT / "PhotosMotor"
                    if not row:
                        return self.send_error(404)
                    path = (ROOT/row[0]).resolve()
                    if not path.is_relative_to(base.resolve()) or not path.is_file():
                        return self.send_error(404)
                    if route == "thumb":
                        with Image.open(path) as im:
                            thumb = ImageOps.exif_transpose(im).convert("RGB")
                            thumb.thumbnail((240,180))
                            data = io.BytesIO()
                            thumb.save(data,"JPEG")
                        return self.reply(data.getvalue(),"image/jpeg")
                    return self.reply(path.read_bytes(),mimetypes.guess_type(path)[0] or "application/octet-stream")
                if not route:
                    params = parse_qs(url.query)
                    body = home(db,params.get("q",[""])[0],
                                {k:params[k][0] for k in ("component","view","utility","status") if k in params})
                elif route == "image":
                    try:
                        body = detail(db,key,token)
                    except KeyError:
                        return self.send_error(404)
                elif route == "group":
                    row = db.execute("SELECT evidence FROM groups WHERE id=?", (key,)).fetchone()
                    if not row:
                        return self.send_error(404)
                    body = "<h1>"+escape(row[0])+"</h1>"+cards(db,db.execute(
                        "SELECT image FROM group_members WHERE group_id=? ORDER BY image",(key,)))
                else:
                    return self.send_error(404)
                page = ('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Referências SEVEL</title>'
                        '<style>body{font:16px system-ui;max-width:1100px;margin:2em auto;padding:1em}'
                        'section{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:1em}'
                        'small{display:block;overflow-wrap:anywhere}img{max-width:100%}</style>'
                        '<a href="/">Catálogo</a>'+body+'</html>')
                self.reply(page.encode(),"text/html; charset=utf-8")

        def do_POST(self):
            route, _, key = self.path.strip("/").partition("/")
            if route != "image":
                return self.send_error(404)
            try:
                size = int(self.headers.get("Content-Length",0))
                if not 0 < size <= 16384:
                    return self.send_error(413)
                form = {k:v[0] for k,v in parse_qs(self.rfile.read(size).decode()).items()}
                if form.get("token") != token:
                    return self.send_error(403)
                with closing(connect(database)) as db:
                    decide(db,key,form)
                    rebuild(db)
            except ValueError:
                return self.send_error(400)
            self.send_response(303)
            self.send_header("Location","/image/"+key)
            self.end_headers()

    with ThreadingHTTPServer(("127.0.0.1",port),Handler) as server:
        print(f"http://127.0.0.1:{server.server_port}",flush=True)
        server.serve_forever()
