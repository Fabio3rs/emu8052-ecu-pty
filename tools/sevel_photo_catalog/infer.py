"""Cache and persist validated inference separately from human observations."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import tomllib

import requests

from .store import ROOT, connect
from .pool import CallLimitReached, batch
from .vision import payload, request_vision, validate


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def infer(db, path, labels, config, budget, session, dry_run=False, provenance=None):
    body = payload(path, labels, config, provenance)
    prompt_hash = digest(json.dumps([item["text"] for item in body["messages"][0]["content"]
                                     if item["type"] == "text"], ensure_ascii=False))
    key = digest(json.dumps([body, labels, config["base_url"]], sort_keys=True))
    if dry_run:
        return "dry-run"
    database = Path(db.execute("PRAGMA database_list").fetchone()[2])
    locks = database.parent / (database.name + ".locks")
    locks.mkdir(exist_ok=True)
    # A process crash releases flock. No SQLite write transaction spans an HTTP request.
    with (locks / key[:2]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return run_cached(db, key, prompt_hash, body, labels, config, budget, session)


def run_cached(db, key, prompt_hash, body, labels, config, budget, session):
    cached = db.execute("SELECT status FROM inference_runs WHERE cache_key=? AND "
                        "status IN ('validated','uncertain') ORDER BY id DESC LIMIT 1", (key,)).fetchone()
    if cached:
        return cached[0]

    def save(status, raw, error):
        return db.execute("INSERT INTO inference_runs(cache_key,model,prompt_hash,status,raw,error) "
                          "VALUES(?,?,?,?,?,?)", (key, config["model"], prompt_hash, status, raw, error)).lastrowid

    def record(status, raw, error):
        with db:
            save(status, raw, error)

    previous = db.execute("SELECT raw FROM inference_runs WHERE cache_key=? AND status='invalid' "
                          "ORDER BY id DESC LIMIT 1", (key,)).fetchone()
    if previous:
        raw = previous[0]
    else:
        response = request_vision(session, body, config, budget, record)
        if response is None:
            return db.execute("SELECT status FROM inference_runs WHERE cache_key=? ORDER BY id DESC LIMIT 1",
                              (key,)).fetchone()[0]
        raw = response.text
    try:
        content = json.loads(raw)["choices"][0]["message"]["content"]
        data = validate(content, list(labels))
    except (ValueError, TypeError, IndexError, KeyError) as exc:
        if not previous:
            record("invalid", raw, type(exc).__name__)
        return "invalid"
    with db:
        run = save("validated", raw, None)
        for item in data["observations"]:
            seen = [labels[label] for label in item["seen_in"]]
            for image in seen:
                obs = db.execute("INSERT INTO observations(image,detail,seen_in,origin,run) VALUES(?,?,?,?,?)",
                                 (image, item["detail"], json.dumps(seen), "model", run)).lastrowid
                if "roi" in item:
                    db.execute("INSERT INTO regions(image,box,observation) VALUES(?,?,?)",
                               (image,json.dumps(item["roi"]),obs))
        for item in data["classifications"]:
            db.execute("INSERT INTO classifications(image,part,view,confidence,variant,origin,run) "
                       "VALUES(?,?,?,?,?,?,?)", (labels[item["label"]],item["part"],item["view"],
                       item["confidence"],"unknown","model",run))
    return "validated"


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--config", type=Path, default=Path(__file__).with_name("config.toml"))
    cli.add_argument("--limit", type=int, default=1)
    cli.add_argument("--model")
    cli.add_argument("--prompt-language", choices=("en","pt"))
    cli.add_argument("--base-url")
    cli.add_argument("--workers", type=int)
    cli.add_argument("--dry-run", action="store_true")
    cli.add_argument("--sheet")
    args = cli.parse_args()
    config = tomllib.loads(args.config.read_text())["vision"]
    if args.workers is not None:
        config["concurrency"] = args.workers
    if config["concurrency"] < 1 or config["max_calls"] < 0:
        cli.error("workers must be positive and max_calls must be nonnegative")
    for k in ("model","base_url","prompt_language"):
        if getattr(args,k):
            config[k] = getattr(args,k)
    budget = [config["max_calls"]]
    with connect() as db, requests.Session() as session:
        if args.sheet:
            row = db.execute("SELECT path,members FROM artifacts WHERE id=?", (args.sheet,)).fetchone()
            if not row:
                cli.error("Unknown sheet")
            members = json.loads(row["members"])
            labels = {v["label"]:v["image_id"] for v in members}
            provenance = [dict(label=v["label"], filename=Path(v["original"]).name,
                               sha256=v["image_id"]) for v in members]
            if len(labels) > config["max_images"]:
                cli.error("Sheet exceeds configured image limit")
            try:
                print(infer(db, ROOT/row["path"], labels, config, budget, session, args.dry_run, provenance))
            except CallLimitReached:
                print("batch-limit")
            return
        rows = db.execute("WITH candidates AS (SELECT i.id,min(s.path) path,coalesce(min(c.part),'unknown') part "
                          "FROM images i JOIN source_images a ON i.id=a.image JOIN sources s ON s.id=a.source "
                          "LEFT JOIN classifications c ON c.image=i.id AND c.origin LIKE 'prior/%' "
                          "WHERE a.active AND i.format IN ('JPEG','PNG','WEBP') GROUP BY i.id) "
                          "SELECT id,path FROM candidates ORDER BY row_number() OVER(PARTITION BY part ORDER BY id),"
                          "part,id LIMIT ?", (max(0,args.limit),)).fetchall()
    for image,status in batch(rows, config, args.dry_run):
        print(image[:12], status, flush=True)


if __name__ == "__main__":
    main()
