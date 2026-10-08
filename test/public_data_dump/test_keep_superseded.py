"""Offline tests for keeping the bytes a download replaces (common.keep_replaced, download(keep_superseded=True)) and
for the Tennis My Life adapter, which turns it on by default (no network)."""
import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import tennis_my_life  # noqa: E402


class FakeResponse:
    def __init__(self, status, content=b"", url="http://x"):
        self.status_code = status
        self.content = content
        self.url = url
        self.headers = {"Content-Type": "text/csv"}


class FakeSite:
    """Serves whatever ``pages`` holds for a URL at the time of the request."""

    def __init__(self, pages):
        self.pages = dict(pages)
        self.requested = []

    def get(self, url, timeout=None):
        self.requested.append(url)
        if url in self.pages:
            return FakeResponse(200, self.pages[url], url)
        return FakeResponse(404, b"", url)


def test_download_keeps_replaced_bytes_only_when_asked_and_changed(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    receipts = C.Receipts("demo")
    dest = tmp_path / "raw" / "demo" / "sub" / "a.csv"
    old, new, newer = b"tourney_id\r\n1\r\n", b"tourney_id\n1\n", b"tourney_id\n2\n"
    site = FakeSite({"http://x/a.csv": old})

    first = C.download("http://x/a.csv", dest, receipts, name="sub/a.csv", sess=site, keep_superseded=True)
    assert "superseded" not in first and dest.read_bytes() == old
    same = C.download("http://x/a.csv", dest, receipts, name="sub/a.csv", sess=site, refresh=True, keep_superseded=True)
    assert "superseded" not in same and not (tmp_path / "raw" / "demo" / "superseded").exists()

    site.pages["http://x/a.csv"] = new           # a line-ending change alone is a new version of the bytes
    changed = C.download("http://x/a.csv", dest, receipts, name="sub/a.csv", sess=site, refresh=True, keep_superseded=True)
    kept = tmp_path / changed["superseded"]
    assert kept.read_bytes() == old and dest.read_bytes() == new
    assert kept.parent == tmp_path / "raw" / "demo" / "superseded" / "sub"
    stamp = re.sub(r"\D", "", first["retrieved_at"])[:14]          # named by the first sighting of those bytes
    assert kept.name == f"a.{stamp}.{C.sha256_bytes(old)[:12]}.csv"
    meta = json.loads((kept.parent / (kept.name + ".meta.json")).read_text(encoding="utf-8"))
    assert meta["receipt"]["sha256"] == C.sha256_bytes(old) and meta["replaced_by_sha256"] == C.sha256_bytes(new)
    assert meta["first_seen"]["retrieved_at"] == first["retrieved_at"]
    assert meta["receipt"]["retrieved_at"] == same["retrieved_at"]                # the last sighting
    assert C.Receipts("demo").get("sub/a.csv")["superseded"] == changed["superseded"]
    assert not list((tmp_path / "raw" / "demo").rglob("*.part"))                  # written whole, then renamed

    site.pages["http://x/a.csv"] = newer         # the default overwrites, as before
    plain = C.download("http://x/a.csv", dest, receipts, name="sub/a.csv", sess=site, refresh=True)
    assert "superseded" not in plain and dest.read_bytes() == newer
    assert len(list((tmp_path / "raw" / "demo" / "superseded").rglob("*.csv"))) == 1


def test_keep_replaced_uses_the_file_time_when_no_receipt_describes_the_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    receipts = C.Receipts("demo")
    receipts.record({"name": "b.csv", "sha256": "something else", "retrieved_at": "2026-01-01T00:00:00+00:00"})
    dest = tmp_path / "raw" / "demo" / "b.csv"
    dest.write_bytes(b"hand-copied\n")
    kept = C.keep_replaced(dest, "b.csv", receipts, b"downloaded\n")
    name = Path(kept).name
    assert re.fullmatch(r"b\.\d{14}\.[0-9a-f]{12}\.csv", name) and not name.startswith("b.20260101")
    assert C.keep_replaced(dest, "b.csv", receipts, b"hand-copied\n") is None      # identical bytes: nothing kept
    assert C.keep_replaced(tmp_path / "raw" / "demo" / "absent.csv", "absent.csv", receipts, b"x") is None


def test_keep_replaced_repairs_a_kept_copy_an_interrupted_run_left_damaged(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    receipts = C.Receipts("demo")
    dest = tmp_path / "raw" / "demo" / "c.csv"
    dest.write_bytes(b"tourney_id\n1\n2\n")
    first = C.keep_replaced(dest, "c.csv", receipts, b"tourney_id\n1\n2\n3\n")
    kept = tmp_path / first
    kept.write_bytes(b"tourney_id\n1")                  # torn: the earlier run stopped half-way through the copy
    again = C.keep_replaced(dest, "c.csv", receipts, b"tourney_id\n1\n2\n3\n")
    assert again == first and kept.read_bytes() == b"tourney_id\n1\n2\n"


def tml_site(season: bytes) -> FakeSite:
    catalog = {"count": 1, "files": [{"name": "2026.csv", "url": "http://tml/2026.csv", "mtime": "m1", "size": len(season)}]}
    return FakeSite({tennis_my_life.CATALOG_URL: json.dumps(catalog).encode(), tennis_my_life.README_URL: b"# TML\n",
                     "http://tml/2026.csv": season})


def test_tennis_my_life_keeps_a_revised_season_file(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    head = b"tourney_id,tourney_date,round,winner_id,winner_name,loser_id,loser_name,score\n"
    old = head + b"2026-339,20260727,QF,S0S1,Ben Shelton,S0H2,Denis Shapovalov,7-6(5) 6-6 RET\n"
    new = head + b"2026-339,20260727,QF,S0S1,Ben Shelton,S0H2,Denis Shapovalov,7-6(5) 6-6 DEF\n"
    site = tml_site(old)
    monkeypatch.setattr(C, "session", lambda: site)
    args = argparse.Namespace(start_year=2026, end_year=2026, refresh=False, no_keep_superseded=False)
    tennis_my_life.run(args)
    revised = tml_site(new)
    revised.pages[tennis_my_life.CATALOG_URL] = revised.pages[tennis_my_life.CATALOG_URL].replace(b'"m1"', b'"m2"')
    monkeypatch.setattr(C, "session", lambda: revised)
    tennis_my_life.run(args)
    folder = tmp_path / "raw" / "tennis_my_life"
    assert (folder / "2026.csv").read_bytes() == new
    kept = sorted((folder / "superseded").glob("2026.*.csv"))
    assert len(kept) == 1 and kept[0].read_bytes() == old
    manifests = [p for p in (folder / "superseded").glob("_catalog.*.json") if not p.name.endswith(".meta.json")]
    assert len(manifests) == 1                                                  # the manifest's history is kept too


def test_tennis_my_life_can_still_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    args = argparse.Namespace(start_year=2026, end_year=2026, refresh=True, no_keep_superseded=True)
    head = b"tourney_id,tourney_date,round,winner_id,winner_name,loser_id,loser_name,score\n"
    first = head + b"2026-339,20260727,QF,S0S1,Ben Shelton,S0H2,Denis Shapovalov,7-6(5) 6-6 RET\n"
    second = head + b"2026-339,20260727,QF,S0S1,Ben Shelton,S0H2,Denis Shapovalov,7-6(5) 6-6 DEF\n"
    monkeypatch.setattr(C, "session", lambda: tml_site(first))
    tennis_my_life.run(args)
    monkeypatch.setattr(C, "session", lambda: tml_site(second))
    tennis_my_life.run(args)
    folder = tmp_path / "raw" / "tennis_my_life"
    assert (folder / "2026.csv").read_bytes() == second              # replaced: the correction passed the gate
    assert not (folder / "superseded").exists()                      # and nothing was kept
