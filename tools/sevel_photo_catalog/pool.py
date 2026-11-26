"""Spawn workers with independent SQLite/HTTP connections and a batch call budget."""
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing

import requests

from .store import DATABASE, ROOT, connect


class CallLimitReached(Exception):
    pass


def reserve(remaining):
    if hasattr(remaining, "get_lock"):
        with remaining.get_lock():
            if not remaining.value:
                raise CallLimitReached()
            remaining.value -= 1
    else:
        if not remaining[0]:
            raise CallLimitReached()
        remaining[0] -= 1


def initialize(counter):
    global batch_budget
    batch_budget = counter


def process_image(task):
    from .infer import infer
    image, path, config, dry_run, database = task
    with closing(connect(database)) as db, requests.Session() as session:
        try:
            status = infer(db, path, {"IMG-001":image}, config, batch_budget, session, dry_run)
        except CallLimitReached:
            status = "batch-limit"
        return image, status


def batch(rows, config, dry_run=False, database=DATABASE, root=ROOT):
    ctx = multiprocessing.get_context("spawn")
    counter = ctx.Value("q", config["max_calls"])
    tasks = [(image,root/path,config,dry_run,database) for image,path in rows]
    if not tasks:
        return
    with ProcessPoolExecutor(max_workers=min(len(tasks),config["concurrency"]), mp_context=ctx,
                             initializer=initialize, initargs=(counter,)) as workers:
        yield from workers.map(process_image,tasks)
