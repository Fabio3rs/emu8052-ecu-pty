"""Offline contracts for original identity, review persistence and vision transport."""
import json
import sqlite3
import tempfile
import tomllib
import unittest
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from PIL import Image

from tools.sevel_photo_catalog import export, grouping, review, scan, search, sheets, store, vision
from tools.sevel_photo_catalog import pool


def simulated_worker(task):
    response = Mock(status_code=200, text=json.dumps({"choices":[{"message":{"content":json.dumps({
        "observations":[{"detail":"synthetic edge","seen_in":["IMG-001"]}],
        "classifications":[],"limitations":"synthetic"})}}]}))
    with patch.object(requests.Session,"post",return_value=response):
        return pool.process_image(task)


class PhotoCatalogTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.photos = self.root / "PhotosMotor"
        self.photos.mkdir()
        self.db = store.connect(self.root / "catalog.sqlite3")
        self.addCleanup(self.db.close)
        self.config = tomllib.loads(Path(vision.__file__).with_name("config.toml").read_text())["vision"]

    def test_identity_history_sheet_export_and_backup(self):
        for name,color in (("first angle","red"),("copy","red"),("side","blue")):
            Image.new("RGB",(100,80),color).save(self.photos / (name+".png"))
        scan.scan(self.db,self.photos)
        (self.photos/"copy.png").rename(self.photos/"alias.png")
        scan.scan(self.db,self.photos)
        grouping.group(self.db)
        ids = [r[0] for r in self.db.execute("SELECT id FROM images ORDER BY id")]
        self.assertEqual(len(ids),2)
        self.assertEqual(self.db.execute("SELECT sum(active),count(*) FROM source_images").fetchone()[:],(3,4))
        self.assertEqual(self.db.execute("SELECT count(*) FROM groups WHERE kind='identical_bytes'").fetchone()[0],1)
        path = sheets.sheet(self.db,ids,self.root/"sheets",self.root)
        with Image.open(path) as im:
            self.assertEqual(im.size,(200,112))
            self.assertLess(im.crop((0,0,100,32)).convert("L").getextrema()[0],64)
        mapping = json.loads(self.db.execute("SELECT members FROM artifacts").fetchone()[0])
        self.assertEqual([(m["label"],m["image_id"]) for m in mapping],list(zip(["IMG-001","IMG-002"],ids)))
        review.decide(self.db,ids[0],dict(status="confirmed",part="pistão",roi="[0,0,1,1]"))
        with self.db:
            self.db.execute("INSERT INTO classifications(image,part,origin) VALUES(?,?,'model')",(ids[0],"biela"))
        self.assertEqual(self.db.execute("SELECT part FROM review_decisions").fetchone()[0],"pistão")
        rows = export.selected(self.db,{"component":"pistão","status":"confirmed"}).fetchall()
        self.assertEqual({r[0] for r in rows},{ids[0]})
        self.assertFalse(export.selected(self.db,{"component":"biela","status":"confirmed"}).fetchall())
        with self.assertRaises(ValueError):
            review.decide(self.db,ids[0],dict(status="confirmed",roi="[1,1,0,0]"))
        target = export.export(self.db,self.root/"exports",self.root)
        self.assertTrue(target.exists())
        content = "".join(p.read_text() for p in target.parent.glob("*.md"))
        self.assertIn("../PhotosMotor/first%20angle.png",content)
        self.assertIn("../sheets/",content)
        self.assertEqual(self.db.execute("PRAGMA journal_mode").fetchone()[0],"wal")
        with sqlite3.connect(":memory:") as copy:
            self.db.backup(copy)
            self.assertEqual(copy.execute("SELECT count(*) FROM regions").fetchone()[0],1)
            self.assertEqual(copy.execute("SELECT max(version) FROM schema_migrations").fetchone()[0],
                             copy.execute("PRAGMA user_version").fetchone()[0])

    def test_exif_failure_and_fallback_search(self):
        path = self.photos/"head.png"
        Image.new("RGB",(12,12)).save(path)
        with patch.object(Image.Image,"getexif",side_effect=ValueError("invalid EXIF")):
            scan.scan(self.db,self.photos)
        self.assertIn("EXIF",self.db.execute("SELECT error FROM images").fetchone()[0])
        search.rebuild(self.db)
        result = search.lookup(self.db,"head")
        self.assertEqual(len(result),1)
        with self.db:
            self.db.execute("DROP TABLE search")
            self.db.execute("CREATE TABLE search(image TEXT PRIMARY KEY,description TEXT)")
        search.rebuild(self.db)
        self.assertEqual(search.lookup(self.db,"head"),result)

    def test_retry_budget_and_timeout(self):
        session,record,sleep = Mock(),Mock(),Mock()
        busy = Mock(status_code=429,headers={"Retry-After":"2"})
        ok = Mock(status_code=200)
        session.post.side_effect = [busy,ok]
        budget = [2]
        self.assertIs(vision.request_vision(session,{},self.config,budget,record,sleep),ok)
        self.assertEqual(budget,[0])
        sleep.assert_called_once_with(2)
        session.post.side_effect = requests.Timeout()
        self.assertIsNone(vision.request_vision(session,{},self.config,[2],record,sleep))
        record.assert_called_with("uncertain",None,"timeout")

    def test_schema_and_roi(self):
        data = dict(observations=[dict(detail="contorno",seen_in=["IMG-001"],roi=[0,0,1,1])],
                    classifications=[],limitations="oclusão")
        self.assertEqual(vision.validate(json.dumps(data),["IMG-001"]),data)
        data["observations"][0]["seen_in"] = ["IMG-002"]
        with self.assertRaises(ValueError):
            vision.validate(json.dumps(data),["IMG-001"])

    def test_process_pool_cache_and_global_budget(self):
        for name in ("red","blue","green"):
            Image.new("RGB",(12,12),name).save(self.photos/(name+".png"))
        scan.scan(self.db,self.photos)
        tasks = [(image,self.root/path,self.config,False,self.root/"catalog.sqlite3")
                 for image,path in self.db.execute("SELECT image,path FROM source_images "
                                                   "JOIN sources ON sources.id=source")]
        ctx = multiprocessing.get_context("spawn")
        counter = ctx.Value("q",2)
        with ProcessPoolExecutor(max_workers=3,mp_context=ctx,initializer=pool.initialize,
                                 initargs=(counter,)) as workers:
            repeated = list(workers.map(simulated_worker,[tasks[0]]*3))
            remaining = list(workers.map(simulated_worker,tasks[1:]))
        self.assertEqual([status for _,status in repeated],["validated"]*3)
        self.assertCountEqual([status for _,status in remaining],["validated","batch-limit"])
        self.assertEqual(counter.value,0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM inference_runs").fetchone()[0],2)
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0],"ok")


if __name__ == "__main__":
    unittest.main()
