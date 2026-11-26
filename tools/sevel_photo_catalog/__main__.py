"""Command line entry point for the SEVEL photo catalog."""
import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path

from .evidence import import_reviews
from .export import export
from .grouping import group, propose_specimen
from .scan import scan
from .sheets import grouped_sheets, sheet
from .store import DATABASE, OUTPUT, ROOT, connect, private_database


def main():
    if sys.argv[1:2] == ["infer"]:
        from .infer import main as infer
        del sys.argv[1]
        return infer()
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "stats", "validate", "infer"):
        commands.add_parser(name)
    sheet_command = commands.add_parser("sheets")
    sheet_command.add_argument("--images", nargs="+", metavar="IMAGE_ID")
    groups = commands.add_parser("group")
    groups.add_argument("--specimen", nargs="+", metavar="IMAGE_ID")
    groups.add_argument("--evidence")
    markdown = commands.add_parser("export-md")
    for field in ("component","view","group","utility"):
        markdown.add_argument("--"+field)
    markdown.add_argument("--status", choices=("prior-review","confirmed","rejected","uncertain",
                                              "provisional","unreviewed"))
    backup = commands.add_parser("backup")
    review = commands.add_parser("review")
    review.add_argument("--port", type=int, default=8765)
    backup.add_argument("destination", nargs="?", type=Path, default=OUTPUT / "backup.sqlite3")
    args = parser.parse_args()
    if args.command == "review":
        from .server import serve
        return serve(args.port)
    with connect() as db:
        if args.command == "scan":
            print(scan(db), "original paths")
            import_reviews(db)
        elif args.command == "group":
            if args.specimen or args.evidence:
                if not args.specimen or not args.evidence:
                    parser.error("--specimen and --evidence must be supplied together")
                print(propose_specimen(db,args.specimen,args.evidence))
            else:
                group(db)
        elif args.command == "sheets":
            if args.images:
                print(sheet(db,args.images))
            else:
                print(grouped_sheets(db), "sheets")
        elif args.command == "export-md":
            print(export(db,filters={k:v for k,v in vars(args).items() if k != "command" and v}))
        elif args.command == "backup":
            if args.destination.resolve() == DATABASE.resolve():
                parser.error("Backup destination must differ from the active database")
            with sqlite3.connect(private_database(args.destination)) as dest:
                db.backup(dest)
        elif args.command == "validate":
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute(
                    "PRAGMA foreign_key_check").fetchone():
                raise ValueError("Database integrity check failed")
            for path, image in db.execute("SELECT path,image FROM sources JOIN source_images "
                                          "ON sources.id=source WHERE active"):
                with (ROOT/path).open("rb") as f:
                    if hashlib.file_digest(f, "sha256").hexdigest() != image:
                        raise ValueError(f"Changed original: {path}")
            print("Database and active source hashes verified")
        else:
            for table in ("images","groups","classifications","review_decisions","inference_runs","artifacts"):
                print(table, db.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


if __name__ == "__main__":
    main()
