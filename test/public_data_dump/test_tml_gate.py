"""Offline tests for the Tennis My Life gate (a damaged file never becomes current), its held outcome in
common.download, the change log, --accept-held and the run lock (no network)."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import tennis_my_life as T  # noqa: E402

HEADER = "tourney_id,tourney_date,round,winner_id,winner_name,loser_id,loser_name,score,w_ace\n"
ROWS = ["2026-339,20260727,R32,A1,Ann,B1,Bea,6-1 6-1,3\n", "2026-339,20260727,R32,A2,Cat,B2,Dee,6-2 6-2,4\n",
        "2026-339,20260727,R16,A1,Ann,A2,Cat,6-3 6-3,5\n"]


def csv_bytes(rows, header=HEADER, eol="\n"):
    return (header + "".join(rows)).replace("\n", eol).encode()


def test_read_rows_flags_a_half_written_file():
    _, rows, ragged = T.read_rows(csv_bytes(ROWS))
    assert len(rows) == 3 and not ragged
    _, _, ragged = T.read_rows(csv_bytes(ROWS)[:-12])
    assert ragged


def test_row_changes_pairs_corrections_and_ignores_line_endings():
    h, old, _ = T.read_rows(csv_bytes(ROWS, eol="\r\n"))
    same = T.row_changes(h, old, *T.read_rows(csv_bytes(ROWS))[:2])
    assert (same["added"], same["removed"], same["corrected"]) == (0, 0, 0)
    fixed = [ROWS[0].replace("6-1 6-1", "6-1 6-1 DEF")] + ROWS[1:] + ["2026-339,20260727,QF,A1,Ann,C1,Eve,6-0 6-0,1\n"]
    d = T.row_changes(h, old, *T.read_rows(csv_bytes(fixed))[:2])
    assert (d["added"], d["removed"], d["corrected"]) == (1, 0, 1) and d["cells"] == {"score": 1}


def test_row_changes_pairs_a_row_whose_blank_ids_were_filled_in():
    blank = [ROWS[0].replace("A1,Ann,B1", ",Ann,")] + ROWS[1:]
    h, old, _ = T.read_rows(csv_bytes(blank))
    d = T.row_changes(h, old, *T.read_rows(csv_bytes(ROWS))[:2])
    assert (d["removed"], d["corrected"]) == (0, 1) and d["cells"] == {"winner_id": 1, "loser_id": 1}


def gate_for(tmp_path, name, current, item_size=None):
    dest = tmp_path / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if current is not None:
        dest.write_bytes(current)
    changes = {}
    return T.make_gate(name, dest, {"size": item_size}, set(), changes), changes


def test_gate_accepts_growth_and_holds_damage(tmp_path):
    current = csv_bytes(ROWS)
    grown = csv_bytes(ROWS + ["2026-339,20260727,QF,A1,Ann,C1,Eve,6-0 6-0,1\n"])
    gate, changes = gate_for(tmp_path, "2026.csv", current, len(grown))
    assert gate(grown) is None and changes["2026.csv"]["added"] == 1
    assert "half-written" in gate(grown[:-10])
    assert "manifest lists" in gate_for(tmp_path, "2026.csv", current, len(grown) + 7)[0](grown)
    header_only = csv_bytes([])
    gate, _ = gate_for(tmp_path, "2026.csv", current, len(header_only))
    assert "3 of the current copy's 3 rows are gone (more than half)" in gate(header_only)   # a small file emptied
    big = csv_bytes([f"2026-339,20260727,R64,P{i},X{i},Q{i},Y{i},6-0 6-0,1\n" for i in range(10)])
    gate, _ = gate_for(tmp_path, "2026.csv", big, len(header_only))
    assert "10 rows of the current copy are gone (more than 5)" in gate(header_only)
    one_less = csv_bytes([f"2026-339,20260727,R64,P{i},X{i},Q{i},Y{i},6-0 6-0,1\n" for i in range(9)])
    gate, changes = gate_for(tmp_path, "2026.csv", big, len(one_less))
    assert gate(one_less) is None and changes["2026.csv"]["removed"] == 1                    # a duplicate dropped
    narrower = csv_bytes([r.rsplit(",", 1)[0] + "\n" for r in ROWS], header=HEADER.replace(",w_ace", ""))
    gate, _ = gate_for(tmp_path, "2026.csv", current, len(narrower))
    assert "columns lost: w_ace" in gate(narrower)


def test_gate_lets_ongoing_files_turn_over_but_not_tear(tmp_path):
    gate, _ = gate_for(tmp_path, "ongoing_tourneys.csv", csv_bytes(ROWS[:2]))
    assert gate(csv_bytes(["2026-500,20261005,R32,Z1,Zed,Z2,Zoe,6-4 6-4,2\n"])) is None
    assert "half-written" in gate(csv_bytes(ROWS)[:-12])


class Site:
    def __init__(self, pages):
        self.pages = dict(pages)

    def get(self, url, timeout=None):
        class R:
            pass
        r = R()
        r.status_code = 200 if url in self.pages else 404
        r.content, r.url, r.headers = self.pages.get(url, b""), url, {"Content-Type": "text/csv"}
        return r


def site_with(season: bytes, mtime: str) -> Site:
    catalog = {"count": 1, "files": [{"name": "2026.csv", "url": "http://tml/2026.csv", "mtime": mtime, "size": len(season)}]}
    return Site({T.CATALOG_URL: json.dumps(catalog).encode(), T.README_URL: b"# TML\n", "http://tml/2026.csv": season})


@pytest.fixture
def raw(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    return tmp_path


def args(**kw):
    base = dict(start_year=2026, end_year=2027, refresh=False, no_keep_superseded=False, accept_held=[])
    base.update(kw)
    return argparse.Namespace(**base)


def test_a_held_version_stays_aside_until_accepted(raw, monkeypatch):
    good = csv_bytes([f"2026-339,20260727,R64,P{i},X{i},Q{i},Y{i},6-0 6-0,1\n" for i in range(10)])
    monkeypatch.setattr(C, "session", lambda: site_with(good, "m1"))
    assert T.run(args())["held"] == []
    bad = csv_bytes([])
    monkeypatch.setattr(C, "session", lambda: site_with(bad, "m2"))
    summary = T.run(args())
    folder = raw / "raw" / "tennis_my_life"
    assert len(summary["held"]) == 1 and (folder / "2026.csv").read_bytes() == good
    assert C.Receipts("tennis_my_life").get("2026.csv")["sha256"] == C.sha256_bytes(good)    # still describes dest
    assert C.Receipts("tennis_my_life").get("held/2026.csv")["held"]
    assert len(list((folder / "held").glob("2026.*.csv"))) == 1
    staged = raw / "dump" / "matches" / "tennis_my_life" / "atp_main" / "2026.parquet"
    import pyarrow.parquet as pq
    assert pq.read_metadata(staged).num_rows == 10                                          # staging kept the good copy
    accept = summary["held"][0]["accept_with"].split(" ", 1)[1]
    summary = T.run(args(accept_held=[accept]))
    assert summary["held"] == [] and (folder / "2026.csv").read_bytes() == bad
    log = [json.loads(x) for x in (folder / "_changes.jsonl").read_text(encoding="utf-8").splitlines()]
    assert log[-1]["accepted_after_review"] is True and log[-1]["previous_sha256"] == C.sha256_bytes(good)


def test_an_accepted_correction_is_logged(raw, monkeypatch):
    monkeypatch.setattr(C, "session", lambda: site_with(csv_bytes(ROWS), "m1"))
    T.run(args())
    fixed = csv_bytes([ROWS[0].replace("6-1 6-1", "6-1 6-1 DEF")] + ROWS[1:])
    monkeypatch.setattr(C, "session", lambda: site_with(fixed, "m2"))
    assert T.run(args())["held"] == []
    folder = raw / "raw" / "tennis_my_life"
    entry = json.loads((folder / "_changes.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert (entry["corrected"], entry["added"], entry["cells"]) == (1, 0, {"score": 1}) and entry["superseded"]


def test_the_lock_stops_a_second_run_and_clears_a_dead_ones(raw, monkeypatch):
    lock = raw / "raw" / "tennis_my_life" / ".lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("{}")
    with pytest.raises(RuntimeError, match="another Tennis My Life run"):
        T.run(args())
    old = time.time() - 2 * T.LOCK_MAX_AGE
    os.utime(lock, (old, old))
    monkeypatch.setattr(C, "session", lambda: site_with(csv_bytes(ROWS), "m1"))
    T.run(args())
    assert not lock.exists()


def test_the_default_end_year_looks_one_season_ahead():
    import datetime as dt
    assert T.default_end_year() == dt.datetime.now(dt.timezone.utc).year + 1
