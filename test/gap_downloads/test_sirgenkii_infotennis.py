"""The SirGenkii/infotennis adapter's MySQL dump reader (offline, on a small dump written here)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import sirgenkii_infotennis as G  # noqa: E402

DUMP = r"""-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
DROP TABLE IF EXISTS `atp_results`;
CREATE TABLE `atp_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tournament` varchar(255) DEFAULT NULL,
  `match_id` varchar(255) DEFAULT NULL,
  `score` varchar(255) DEFAULT NULL,
  `court_vision` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
LOCK TABLES `atp_results` WRITE;
INSERT INTO `atp_results` VALUES (1,'Queen\'s Club, (London)','ms001','76(5) 62',0),(2,'a\\b\nc',NULL,'',-1);
INSERT INTO `atp_results` VALUES (3,'NULL','qs015','W/O',2.5e1);
UNLOCK TABLES;
"""


def test_columns_and_rows_keep_the_dumped_text():
    assert G.table_columns(DUMP, "atp_results") == ["id", "tournament", "match_id", "score", "court_vision"]
    assert list(G.dump_rows(DUMP, "atp_results")) == [
        ["1", "Queen's Club, (London)", "ms001", "76(5) 62", "0"],
        ["2", "a\\b\nc", None, "", "-1"],
        ["3", "NULL", "qs015", "W/O", "2.5e1"],   # a quoted 'NULL' is text; numbers are not converted
    ]


def test_unescape_and_blob_hash():
    assert G.unescape(r"it\'s a \"test\"\t\\") == "it's a \"test\"\t\\"
    assert G.git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"   # git hash-object
    assert G.WANTED.match("backup_sql/infotennis4_atp_results.sql") and not G.WANTED.match("infotennis/x.py")


def test_stage_writes_one_table_per_dump(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    receipts = C.Receipts(G.SOURCE)
    path = C.raw_path(G.SOURCE, "backup_sql", "infotennis4_atp_results.sql")
    path.parent.mkdir(parents=True)
    path.write_text(DUMP, encoding="utf-8")
    receipts.record({"name": "backup_sql/infotennis4_atp_results.sql", "sha256": "x", "retrieved_at": "2026-09-29"})
    (meta,) = G.stage(receipts)
    assert meta["table"] == "atp_results" and meta["rows"] == 3
    frame = pd.read_parquet(C.dump_path("points", G.SOURCE, "atp_results.parquet"))
    assert frame["tournament"].tolist() == ["Queen's Club, (London)", "a\\b\nc", "NULL"]
    assert frame["match_id"].isna().tolist() == [False, True, False] and set(frame["_commit"]) == {G.PINNED_COMMIT}
