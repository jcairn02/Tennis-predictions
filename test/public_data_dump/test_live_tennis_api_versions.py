"""Offline tests for the Live Tennis API adapter's Zenodo versions (no network): each record's files are kept side by
side, the staged tables follow the record asked for and say which version they hold, a file whose MD5 is not the
record's is never staged, and staged_time_zone() reads Israel local time for v1.0.0 only."""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import live_tennis_api_zenodo as Z  # noqa: E402

V0, V2 = Z.FIRST_RECORD, Z.RECORD_ID
ISRAEL = b"match_id,scheduled_time_utc\nm1,2026-06-20 13:00:00\n"   # v1.0.0: Israel local time, labelled UTC
UTC = b"match_id,scheduled_time_utc\nm1,2026-06-20 10:00:00\n"      # v1.0.2: the same row in UTC


class FakeResponse:
    def __init__(self, status, content=b"", url="http://x"):
        self.status_code = status
        self.content = content
        self.url = url
        self.headers = {"Content-Type": "application/octet-stream"}


class FakeZenodo:
    def __init__(self):
        self.pages, self.requested = {}, []

    def publish(self, record: int, version: str, files: dict, wrong_md5: tuple = ()) -> None:
        listed = []
        for key, body in files.items():
            url = f"https://zenodo.org/api/records/{record}/files/{key}/content"
            md5 = "0" * 32 if key in wrong_md5 else hashlib.md5(body).hexdigest()
            listed.append({"key": key, "size": len(body), "checksum": f"md5:{md5}", "links": {"self": url}})
            self.pages[url] = body
        self.pages[Z.RECORD_URL.format(record=record)] = json.dumps(
            {"id": record, "metadata": {"version": version}, "files": listed}).encode()

    def get(self, url, timeout=None):
        self.requested.append(url)
        return FakeResponse(200, self.pages[url], url) if url in self.pages else FakeResponse(404, b"", url)


def setup(tmp_path, monkeypatch) -> FakeZenodo:
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    site = FakeZenodo()
    site.publish(V0, "1.0.0", {"matches.csv.gz": gzip.compress(ISRAEL), "README.md": b"# v1.0.0\n"})
    site.publish(V2, "1.0.2", {"matches.csv.gz": gzip.compress(UTC), "README.md": b"# v1.0.2\n"})
    monkeypatch.setattr(C, "session", lambda: site)
    return site


def run(record: int, refresh: bool = False) -> dict:
    return Z.run(argparse.Namespace(record=record, refresh=refresh))


def staged(tmp_path) -> Path:
    return tmp_path / "dump" / "matches" / Z.SOURCE / "matches.parquet"


def test_records_are_kept_side_by_side_and_staging_follows_the_record_asked_for(tmp_path, monkeypatch):
    site = setup(tmp_path, monkeypatch)
    folder = tmp_path / "raw" / Z.SOURCE
    first = run(V0)
    assert first["zenodo_version"] == "1.0.0" and (folder / "matches.csv.gz").exists()
    assert Z.staged_version(staged(tmp_path)) == "1.0.0" and Z.staged_time_zone(staged(tmp_path)) == "Asia/Jerusalem"
    second = run(V2)
    assert gzip.decompress((folder / "matches.csv.gz").read_bytes()) == ISRAEL               # v1.0.0 kept as it was
    assert gzip.decompress((folder / f"record_{V2}" / "matches.csv.gz").read_bytes()) == UTC
    assert (folder / f"record_{V2}" / "_record.json").exists() and (folder / "_record.json").exists()
    assert second["staged_files"] == 1 and Z.staged_time_zone(staged(tmp_path)) == "UTC"
    table = pq.read_table(staged(tmp_path))
    assert table.column("scheduled_time_utc").to_pylist() == ["2026-06-20 10:00:00"]
    assert table.column("_zenodo_record").to_pylist() == [str(V2)]
    assert table.column("_source_file").to_pylist() == [f"raw/{Z.SOURCE}/record_{V2}/matches.csv.gz"]
    receipts = C.Receipts(Z.SOURCE)
    assert receipts.get("matches.csv.gz")["zenodo_record"] == V0
    assert receipts.get(f"record_{V2}/matches.csv.gz")["zenodo_record"] == V2
    site.requested.clear()
    back = run(V0)                                   # held files, another record staged: re-staged, nothing downloaded
    assert back["staged_files"] == 1 and Z.staged_version(staged(tmp_path)) == "1.0.0"
    assert site.requested == [Z.RECORD_URL.format(record=V0)]
    assert run(V0)["staged_files"] == 0              # the record staged already: nothing to do


def test_a_file_whose_md5_is_not_the_records_is_never_staged(tmp_path, monkeypatch):
    site = setup(tmp_path, monkeypatch)
    run(V0)
    site.publish(V2, "1.0.2", {"matches.csv.gz": gzip.compress(UTC)}, wrong_md5=("matches.csv.gz",))
    summary = run(V2)
    assert summary["md5_mismatches"] == [f"record_{V2}/matches.csv.gz"] and summary["staged_files"] == 0
    assert Z.staged_version(staged(tmp_path)) == "1.0.0"                               # the v1.0.0 tables stay


def test_a_table_staged_before_the_versions_were_recorded_reads_as_israel_time(tmp_path):
    path = tmp_path / "matches.parquet"
    pq.write_table(pa.table({"scheduled_time_utc": ["2026-06-20 13:00:00"]}), path)
    assert Z.staged_version(path) == "1.0.0" and Z.staged_time_zone(path) == "Asia/Jerusalem"
    pq.write_table(pa.table({"scheduled_time_utc": ["x"], "_zenodo_version": ["1.0.1"]}), path)
    assert Z.staged_time_zone(path) == "Asia/Jerusalem"
    assert Z.record_name(V0, "matches.csv.gz") == "matches.csv.gz"
    assert Z.record_name(V2, "matches.csv.gz") == f"record_{V2}/matches.csv.gz"
