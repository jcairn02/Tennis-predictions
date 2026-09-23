"""Offline tests for the public dump staging helpers (no network)."""
import datetime as dt
import gzip
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402


def test_dedupe_header_handles_blanks_duplicates_and_underscores():
    assert C.dedupe_header(["a", "", "a", "_row", None]) == ["a", "col_2", "a__2", "src_row", "col_5"]


def test_slugify_is_safe_and_never_empty():
    assert C.slugify("Masters 1000") == "masters_1000"
    assert C.slugify("ATP250") == "atp250"
    assert C.slugify(None) == "unknown"
    assert C.slugify("  ") == "unknown"


def test_stage_rows_keeps_short_and_long_rows(tmp_path):
    dest = tmp_path / "out.parquet"
    prov = C.Provenance("src", "file.csv", "abc", "2026-09-22T00:00:00+00:00", {"_route": "live"})
    rows = [(1, ["x", "1"]), (2, ["y"]), (3, ["z", "3", "extra1", "extra2"])]
    stats = C.stage_rows(["name", "value"], rows, dest, prov)
    assert stats["rows"] == 3 and stats["short_rows"] == 1 and stats["long_rows"] == 1
    table = pq.read_table(dest)
    assert table.column_names == ["name", "value", "_source", "_source_file", "_row", "_width_ok", "_extra",
                                  "_sha256", "_retrieved_at", "_route"]
    assert table.column("value").to_pylist() == ["1", None, "3"]
    assert table.column("_width_ok").to_pylist() == ["ok", "short", "long"]
    assert table.column("_extra").to_pylist() == [None, None, "extra1\x1fextra2"]
    assert table.column("_route").to_pylist() == ["live"] * 3
    assert table.column("_row").to_pylist() == [1, 2, 3]
    assert all(t == pa.string() for t in table.schema.types[:2])


def test_stage_delimited_reads_gzip_and_skips_empty_lines(tmp_path):
    src = tmp_path / "data.csv.gz"
    with gzip.open(src, "wt", encoding="utf-8") as handle:
        handle.write("id,score\n1,6-4 6-4\n\n2,\"7-6(5) 3-6, 6-3\"\n")
    stats = C.stage_delimited(src, tmp_path / "data.parquet", C.Provenance("s", "data.csv.gz", None, None))
    assert stats["rows"] == 2 and stats["encoding"] == "utf-8-sig"
    table = pq.read_table(tmp_path / "data.parquet")
    assert table.column("score").to_pylist() == ["6-4 6-4", "7-6(5) 3-6, 6-3"]


def test_stage_delimited_falls_back_for_non_utf8(tmp_path):
    src = tmp_path / "latin.csv"
    src.write_bytes("name,ioc\nJos\xe9,ESP\n".encode("latin-1"))
    stats = C.stage_delimited(src, tmp_path / "latin.parquet", C.Provenance("s", "latin.csv", None, None))
    assert stats["encoding"] == "cp1252"
    assert pq.read_table(tmp_path / "latin.parquet").column("name").to_pylist() == ["Jos\xe9"]


def test_cell_to_str_conversions():
    assert C.cell_to_str(None) is None
    assert C.cell_to_str(dt.datetime(2026, 6, 7)) == "2026-06-07"
    assert C.cell_to_str(dt.datetime(2026, 6, 7, 13, 30)) == "2026-06-07 13:30:00"
    assert C.cell_to_str(6.0) == "6"
    assert C.cell_to_str(1.36) == "1.36"
    assert C.cell_to_str(True) == "TRUE"
    assert C.cell_to_str("ATP250") == "ATP250"


def test_read_workbook_detects_header_and_trims(tmp_path):
    import openpyxl

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "2026"
    sheet.append([None, None])
    sheet.append(["ATP", "Date", "Series", None])
    sheet.append([1, dt.datetime(2026, 1, 5), "ATP250"])
    sheet.append([2, dt.datetime(2026, 1, 6), "Grand Slam", "note"])
    sheet.append([None, None, None])
    path = tmp_path / "book.xlsx"
    book.save(path)
    name, header, rows, meta = C.read_workbook(path)
    assert name == "2026" and header == ["ATP", "Date", "Series"]
    assert rows == [["1", "2026-01-05", "ATP250"], ["2", "2026-01-06", "Grand Slam", "note"]]
    assert meta["header_row_index"] == 1 and meta["blank_rows"] == 1


def test_stage_parquet_as_strings_renders_lists_dates_and_bools(tmp_path):
    src = tmp_path / "src.parquet"
    pq.write_table(pa.table({"ids": pa.array([["a", "b"], None], pa.list_(pa.string())),
                             "day": pa.array([dt.date(2026, 8, 29), None], pa.date32()),
                             "flag": pa.array([True, None], pa.bool_()),
                             "n": pa.array([3, None], pa.int64())}), src)
    stats = C.stage_parquet_as_strings(src, tmp_path / "out.parquet", C.Provenance("s", "src.parquet", None, None))
    assert stats["rows"] == 2
    table = pq.read_table(tmp_path / "out.parquet")
    assert table.column("ids").to_pylist() == ['["a", "b"]', None]
    assert table.column("day").to_pylist() == ["2026-08-29", None]
    assert table.column("flag").to_pylist() == ["TRUE", None]
    assert table.column("n").to_pylist() == ["3", None]


class FakeResponse:
    def __init__(self, status, content=b"", url="http://x"):
        self.status_code = status
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.url = url
        self.headers = {"Content-Type": "text/csv", "Last-Modified": "Mon, 01 Sep 2026 00:00:00 GMT"}


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, timeout=None):
        self.calls += 1
        return self.responses.pop(0)


def test_download_records_receipt_skips_repeat_and_reports_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("demo")
    dest = tmp_path / "demo" / "a.csv"
    sess = FakeSession([FakeResponse(200, b"tourney_id,x\n1,2\n")])
    receipt = C.download("http://x/a.csv", dest, receipts, name="a.csv", validator=C.csv_header_contains("tourney_id"), sess=sess)
    assert not receipt.get("error") and receipt["bytes"] == 17 and dest.read_bytes().startswith(b"tourney_id")
    again = C.download("http://x/a.csv", dest, receipts, name="a.csv", sess=sess)
    assert again["skipped"] is True and sess.calls == 1
    bad = C.download("http://x/b.csv", tmp_path / "demo" / "b.csv", receipts, name="b.csv", sess=FakeSession([FakeResponse(404, b"nope")]))
    assert bad["error"] == "HTTP 404" and not (tmp_path / "demo" / "b.csv").exists()
    html = C.download("http://x/c.csv", tmp_path / "demo" / "c.csv", receipts, name="c.csv",
                      validator=C.csv_header_contains("tourney_id"), sess=FakeSession([FakeResponse(200, b"<!DOCTYPE html><html>")]))
    assert "HTML page" in html["error"]
    lines = (tmp_path / "demo" / "_receipts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 and json.loads(lines[1])["name"] == "b.csv"
    assert C.Receipts("demo").get("c.csv")["error"] == html["error"]


def test_workbook_magic_and_not_html_validators():
    assert C.workbook_magic(b"PK\x03\x04" + b"0" * 20000) is None
    assert "not an Excel workbook" in C.workbook_magic(b"<!DOCTYPE html>")
    assert "small" in C.workbook_magic(b"PK\x03\x04abc")
    assert C.not_html(b"  <html><body>parked") is not None
    assert C.not_html(b"tourney_id,tourney_name") is None
