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


FULL = ("tourney_id,tourney_name,tourney_date,round,winner_id,winner_name,loser_id,loser_name,score,w_ace\n")


def full(rows):
    return csv_bytes(rows, header=FULL)


def test_row_changes_pairs_the_same_event_and_players_in_any_order_round_or_score():
    """Decision 1 (28 Oct 2026): a winner reversed (with its score) and a round relabelled are corrections."""
    old = ["2026-718,Dubai,20260215,R16,A1,Ann,B1,Bea,6-1 6-4,3\n", "2026-718,Dubai,20260215,R16,A2,Cat,B2,Dee,6-2 6-2,4\n",
           "2026-W-FC,BJK Cup Finals,20260915,QF,A3,Eve,B3,Fay,6-3 6-3,5\n"]
    new = ["2026-718,Dubai,20260215,R16,B1,Bea,A1,Ann,7-5 6-4,3\n", "2026-718,Dubai,20260215,R16,A2,Cat,B2,Dee,6-2 6-2,4\n",
           "2026-W-FC,BJK Cup Finals,20260915,RR,A3,Eve,B3,Fay,6-3 6-3,5\n"]
    d = T.row_changes(*T.read_rows(full(old))[:2], *T.read_rows(full(new))[:2])
    assert (d["removed"], d["added"], d["corrected"]) == (0, 0, 2)
    assert d["paired"] == {"same event and players": 2}
    assert d["paired_kinds"] == {"winner reversed + score": 1, "round": 1}
    assert d["paired_rows"][0]["before"]["winner"] == "Ann (A1)" and d["paired_rows"][0]["after"]["winner"] == "Bea (B1)"


def test_row_changes_pairs_an_event_tml_renumbered_by_its_name_and_date():
    old = [f"2026-2971,San Diego 2,20260921,R32,P{i},X{i},Q{i},Y{i},6-3 6-3,1\n" for i in range(8)]
    new = [r.replace("2026-2971", "2026-3175") for r in old]
    d = T.row_changes(*T.read_rows(full(old))[:2], *T.read_rows(full(new))[:2])
    assert (d["removed"], d["corrected"], d["paired"]) == (0, 8, {"event renumbered": 8})


def test_a_row_whose_player_id_changed_still_counts_as_gone():
    """Not decision 1's "same two players": a player re-identified (Xiyu Wang 216016 as Xin Yu Wang 216133) is held
    for review as before."""
    old = [f"2025-1017,Cincinnati,20250807,R128,P{i},X{i},Q{i},Y{i},6-3 6-3,1\n" for i in range(6)]
    new = [r.replace(f"Q{i},Y{i}", f"Z{i},W{i}") for i, r in enumerate(old)]       # another id and name
    d = T.row_changes(*T.read_rows(full(old))[:2], *T.read_rows(full(new))[:2])
    assert (d["removed"], d["added"], d.get("paired")) == (6, 6, None) and len(d["removed_rows"]) == 6
    gate, _ = gate_for_full(old, new)
    assert "6 rows of the current copy are gone (more than 5)" in gate(full(new))


def gate_for_full(old, new, tmp=None):
    import tempfile
    folder = Path(tmp or tempfile.mkdtemp())
    dest = folder / "2026_wta.csv"
    dest.write_bytes(full(old))
    changes = {}
    return T.make_gate("2026_wta.csv", dest, {"size": len(full(new))}, set(), changes), changes


def test_the_gate_accepts_the_corrections_that_held_whole_files_until_28_october(tmp_path):
    """19 Oct 2026's 2026_wta.csv: 28 corrections of the same event and players and one other row held the file (and
    with it a finished week) for nine days. Now it goes in, the corrections listed in the change entry."""
    old = [f"2026-2066,Rouen,20260413,R32,P{i},X{i},Q{i},Y{i},6-3 6-3,1\n" for i in range(12)]
    new = [f"2026-2066,Rouen,20260413,R32,Q{i},Y{i},P{i},X{i},3-6 6-3 6-4,1\n" for i in range(12)]
    gate, changes = gate_for_full(old, new, tmp_path)
    assert gate(full(new)) is None
    assert changes["2026_wta.csv"]["paired_kinds"] == {"winner reversed + score": 12}
    many = [f"2026-2066,Rouen,20260413,R32,P{i},X{i},Z{i},W{i},6-3 6-3,1\n" for i in range(6)] + new[6:]
    gate, _ = gate_for_full(old, many, tmp_path)
    assert gate(full(many)) == "6 rows of the current copy are gone (more than 5); 6 more are corrections of the same " \
                               "event and players"


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


def site_files(files: dict) -> Site:
    """A fake site: {name: (bytes, mtime, the size the manifest lists or None for the true size)}."""
    catalog = {"count": len(files), "files": [{"name": n, "url": f"http://tml/{n}", "mtime": m,
                                                "size": len(b) if s is None else s} for n, (b, m, s) in files.items()]}
    return Site({T.CATALOG_URL: json.dumps(catalog).encode(), T.README_URL: b"# TML\n",
                 **{f"http://tml/{n}": b for n, (b, _, _) in files.items()}})


BRISBANE = ["2026-800,Brisbane,20260104,R64,A1,Ann,B1,Bea,6-1 6-3,1\n"]
WUHAN = [f"2026-1075,Wuhan,20261012,R64,W{i},Wa{i},V{i},Va{i},6-4 6-4,1\n" for i in range(3)]
GUANGZHOU = [f"2026-1023,Guangzhou,20261026,R32,G{i},Ga{i},H{i},Ha{i},6-2 6-2,1\n" for i in range(2)]


def staged_ongoing(raw):
    import pyarrow.parquet as pq
    p = raw / "dump" / "matches" / "tennis_my_life" / "ongoing" / "wta_ongoing_tourneys.parquet"
    return pq.read_table(p).to_pandas(), json.loads(p.with_name(p.name + ".meta.json").read_text(encoding="utf-8"))


def test_a_finished_event_that_lands_in_a_held_season_file_is_carried_until_the_file_is_accepted(raw, monkeypatch):
    """The 19 Oct 2026 hole: Wuhan left the file of events under way for a season file the download held."""
    def day(ongoing, season, mtime, listed=None):
        monkeypatch.setattr(C, "session", lambda: site_files({
            "wta_ongoing_tourneys.csv": (full(ongoing), mtime, None), "2026_wta.csv": (full(season), mtime, listed)}))
        return T.run(args())
    assert day(WUHAN, BRISBANE, "m1")["carried"] == {"new": [], "kept": [], "back": []}
    moved = BRISBANE + [WUHAN[0].replace("6-4 6-4", "6-4 7-5")] + WUHAN[1:]       # TML's later version of the event
    s = day(GUANGZHOU, moved, "m2", listed=len(full(moved)) + 4)                     # held: the manifest lags
    assert len(s["held"]) == 1
    assert [(e["event"], e["rows"]) for e in s["carried"]["new"]] == [("2026-1075", 3)]
    assert s["carried"]["new"][0]["from"].startswith("raw/tennis_my_life/held/2026_wta.")
    t, meta = staged_ongoing(raw)
    assert list(t["tourney_name"]) == ["Guangzhou", "Guangzhou", "Wuhan", "Wuhan", "Wuhan"]
    assert t["score"].iloc[2] == "6-4 7-5" and t["_source_file"].iloc[2] == s["carried"]["new"][0]["from"]
    assert meta["carried_rows"] == 3 and meta["rows"] == 5
    s = day(GUANGZHOU, moved, "m3", listed=len(full(moved)) + 4)                     # still held: still carried
    assert [e["event"] for e in s["carried"]["kept"]] == ["2026-1075"] and len(staged_ongoing(raw)[0]) == 5
    s = day(GUANGZHOU, moved, "m4")                                                  # accepted: back, no longer carried
    assert s["held"] == [] and [e["event"] for e in s["carried"]["back"]] == ["2026-1075"]
    t, meta = staged_ongoing(raw)
    assert list(t["tourney_name"]) == ["Guangzhou", "Guangzhou"] and "carried_rows" not in meta
    state = json.loads((raw / "raw" / "tennis_my_life" / "carried" / "wta_ongoing_tourneys.json").read_text("utf-8"))
    assert state["events"] == []


def test_an_event_whose_season_file_is_not_updated_yet_is_carried_from_the_previous_copy(raw, monkeypatch):
    def day(ongoing, season, mtime):
        monkeypatch.setattr(C, "session", lambda: site_files({
            "wta_ongoing_tourneys.csv": (full(ongoing), mtime, None), "2026_wta.csv": (full(season), "s1", None)}))
        return T.run(args())
    day(WUHAN, BRISBANE, "m1")
    s = day(GUANGZHOU, BRISBANE, "m2")
    assert [(e["event"], e["rows"]) for e in s["carried"]["new"]] == [("2026-1075", 3)]
    assert s["carried"]["new"][0]["from"].startswith("raw/tennis_my_life/superseded/wta_ongoing_tourneys.")
    assert list(staged_ongoing(raw)[0]["_row"]) == [1, 2, 1, 2, 3]                  # each row's number in its own file


def test_the_archived_copies_of_19_october_give_back_the_241_missing_rows():
    """The plan's check, on the real archived copies (skipped where they are not on disk): the download of 19 Oct 2026,
    14:30 UTC, would have carried Wuhan (55 rows) and the week's six Challengers (186), each from its held season copy."""
    d = PROJECT_ROOT / "data" / "raw" / "public_dump" / "tennis_my_life"
    files = {"wta": ("wta_ongoing_tourneys.20261018143008.30354942c372.csv",
                     "wta_ongoing_tourneys.20261019143010.1cc013670c62.csv",
                     "2026_wta.20261015143002.47e4432d01c1.csv", "2026_wta.8f6fb09ef0b0.csv"),
             "challenger": ("challenger_ongoing_tourneys.20261018205752.c068f8d52303.csv",
                            "challenger_ongoing_tourneys.20261019143010.96b90ea4262c.csv",
                            "2026_challenger.20261012143004.a85557b94fa6.csv", "2026_challenger.290817794982.csv")}
    paths = {k: (d / "superseded" / a, d / "superseded" / b, d / "superseded" / c, d / "held" / h)
             for k, (a, b, c, h) in files.items()}
    if not all(p.exists() for ps in paths.values() for p in ps):
        pytest.skip("the archived Tennis My Life copies are not on disk")
    out = {}
    for k, (prev, cur, accepted, held) in paths.items():
        rows = lambda p: T.read_rows(p.read_bytes())[:2]   # noqa: E731
        hl = [{"path": C.rel(held), "sha256": "", "retrieved_at": "2026-10-19T14:30", "events": T.events_of(*rows(held))}]
        carried, _ = T.carry_forward(T.events_of(*rows(prev)), T.events_of(*rows(cur)),
                                     T.event_keys(T.events_of(*rows(accepted))), hl, [], {"path": C.rel(prev)}, "now")
        out[k] = {e["tourney_name"]: (len(e["rows"]), e["from"] == C.rel(held)) for e in carried}
    assert out["wta"] == {"Wuhan": (55, True)}
    assert sorted(out["challenger"]) == ["Catania", "Jinan Open", "Maia Open", "Olbia Challenger",
                                         "Santa Cruz de la Sierra 2", "l'Open Auvergne-Rhone-Alpes de Roanne"]
    assert all(v == (31, True) for v in out["challenger"].values())
    assert sum(n for v in out.values() for n, _ in v.values()) == 241


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
