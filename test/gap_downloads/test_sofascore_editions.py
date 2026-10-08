"""The by-edition SofaScore adapter: name linking, completeness, and a whole run against a fake SofaScore
(offline; every answer is canned, and the raw, dump and evidence folders are temporary)."""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import sofascore_editions as E  # noqa: E402

API = E.API
D0 = pd.Timestamp("2026-03-30")   # Houston 2026 starts on a Monday
TS = lambda day, hour=12: int(pd.Timestamp(f"{day} {hour}:00", tz="UTC").timestamp())  # noqa: E731


def team(name, slug=None, doubles=False):
    t = {"name": name, "slug": slug or name.lower().replace(" ", "-"), "type": 2 if doubles else 1}
    if doubles:
        t["subTeams"] = [{"id": 1}, {"id": 2}]
    return t


def event(eid, home, away, day, *, utid=2409, sid=80801, tname="Houston, USA", rnd="Round of 32", sets=(1, 0),
          doubles=False, hour=12):
    return {"id": eid, "startTimestamp": TS(day, hour), "homeTeam": team(home, doubles=doubles),
            "awayTeam": team(away, doubles=doubles),
            "tournament": {"name": tname, "uniqueTournament": {"id": utid}, "category": {"id": 3, "name": "ATP"}},
            "season": {"id": sid, "name": "Houston 2026", "year": "2026"}, "roundInfo": {"name": rnd},
            "status": {"code": 100, "type": "finished", "description": "Ended"}, "winnerCode": 1, "firstToServe": 1,
            "homeScore": {"current": 1, "period1": sets[0]}, "awayScore": {"current": 0, "period1": sets[1]}}


PAUL = event(101, "Tommy Paul", "Reilly Opelka", "2026-04-01")
STRUFF = event(102, "Jan-Lennard Struff", "Aleksandar Kovačević", "2026-03-29", tname="Houston, USA, Qualifying",
               rnd="Qualification Final")
OTHER = event(201, "Carlos Alcaraz", "Jannik Sinner", "2026-04-01", utid=2391, sid=80000, tname="Marrakech")
DOUBLES = event(103, "Paul / Shelton", "Opelka / Fritz", "2026-04-01", doubles=True)
PBP = {"pointByPoint": [{"set": 1, "games": [{"game": 1, "score": {"serving": 1, "scoring": 1, "homeScore": 1,
                                                                    "awayScore": 0},
                                              "points": [{"homePoint": "15", "awayPoint": "0", "pointDescription": 1},
                                                         {"homePoint": "30", "awayPoint": "0"},
                                                         {"homePoint": "40", "awayPoint": "0"}]}]}]}
STATS = {"statistics": [{"period": "ALL", "groups": [{"groupName": "Service", "statisticsItems": [
    {"key": k, "name": k, "home": "1", "away": "0"} for k in sorted(E.FULL_BOX)]}]}]}

ANSWERS = {
    f"{API}/category/3/scheduled-events/2026-04-01": {"events": [PAUL, OTHER, DOUBLES]},
    f"{API}/unique-tournament/2409/season/80801/events/last/0": {"events": [PAUL, DOUBLES], "hasNextPage": True},
    f"{API}/unique-tournament/2409/season/80801/events/last/1": {"events": [STRUFF], "hasNextPage": False},
    f"{API}/event/101/point-by-point": PBP,
    f"{API}/event/101/statistics": STATS,
}


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self.content, self.url = status, body, "http://fake"
        self.headers = {"content-type": "application/json"}


class FakeClient:
    """Answers from ANSWERS (anything else is a 404); raises Blocked on URLs listed in ``block``."""

    impersonate = "fake"

    def __init__(self, block=()):
        self.requests, self.urls, self.block = 0, [], set(block)

    def get(self, url, headers=None):
        if url in self.block:
            raise P.Blocked(f"HTTP 403 (challenge) for {url}")
        self.requests += 1
        self.urls.append(url)
        if url in ANSWERS:
            return FakeResponse(200, json.dumps(ANSWERS[url]).encode())
        return FakeResponse(404, b'{"error": {"code": 404}}')

    def stats(self):
        return {"impersonate": self.impersonate, "requests": self.requests}


def targets_frame():
    rows = [("T250", "main", "Tommy Paul", "Reilly Opelka"),
            ("TQ", "qual", "Jan-Lennard Struff", "Aleksandar Kovacevic"),
            ("T250", "main", "Nobody Here", "Someone Else")]
    t = pd.DataFrame([{"gap": "atp_points_2025", "uid": i, "tour": "M", "level": lv, "draw": dr, "year": 2026,
                       "d": D0, "tname": "Houston", "name1": a, "name2": b, "creator": "tml", "best": "stats",
                       "sources": "tml"} for i, (lv, dr, a, b) in enumerate(rows)])
    t["edition"] = E.edition_key(t)
    return t[E.TARGET_COLUMNS]


@pytest.fixture
def folders(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(E, "STUDY", tmp_path / "studies")
    return tmp_path


# pure parts ---------------------------------------------------------------------------
def test_words_drop_accents_particles_and_short_words():
    assert E.words("Aleksandar Kovačević") == {"aleksandar", "kovacevic"}
    assert E.words("Alex de Minaur") == {"alex", "minaur"}
    assert E.words("Wu Yibing") == {"yibing"}
    assert E.words("Li Tu") == {"li", "tu"}   # no longer word: the two-letter ones, or he could never link
    assert E.team_words({"name": "Struff J.", "shortName": "J. Struff", "slug": "struff-jan-lennard"}) == {
        "struff", "jan", "lennard"}


def test_pair_score_needs_both_players_in_either_orientation():
    a, b = E.words("Tommy Paul"), E.words("Reilly Opelka")
    assert E.pair_score(a, b, E.words("Opelka Reilly"), E.words("Paul Tommy")) == 4
    assert E.pair_score(a, b, E.words("Tommy Paul"), E.words("Ben Shelton")) == 0


def test_best_event_respects_the_window_and_prefers_more_shared_words():
    events = E.singles([dict(e) for e in (PAUL, OTHER, DOUBLES)] + [event(104, "Paul", "Opelka", "2026-04-02")])
    assert [e["id"] for e in events] == [101, 201, 104]   # the doubles event is left out
    found, score = E.best_event(E.words("Tommy Paul"), E.words("Reilly Opelka"), D0, D0, events)
    assert found["id"] == 101 and score == 4
    late = D0 + pd.Timedelta(days=30)
    assert E.best_event(E.words("Tommy Paul"), E.words("Reilly Opelka"), late, late, events) == (None, 0)


def test_a_pair_met_twice_links_by_draw():
    qual = event(301, "Lucas Pouille", "Jurij Rodionov", "2026-03-28", tname="Houston, USA, Qualifying", rnd=None)
    qual["roundInfo"] = {}   # SofaScore gave a qualifying match no round name (Roland Garros 2023)
    main = event(302, "Lucas Pouille", "Jurij Rodionov", "2026-03-30")
    events = E.singles([qual, main])
    a, b = E.words("Lucas Pouille"), E.words("Jurij Rodionov")
    assert E.best_event(a, b, D0, D0, events, "qual")[0]["id"] == 301
    assert E.best_event(a, b, D0, D0, events, "main")[0]["id"] == 302
    assert E.best_event(a, b, D0, D0, events)[0]["id"] == 302   # no draw given: the one nearest the start


def test_level_groups():
    assert E.level_group(["T250", "TQ"]) == "tour" and E.level_group(["CHQ"]) == "CHQ"
    assert E.level_group(["CH", "CHQ"]) == "CH" and E.level_group(["GS"]) == "GS" and E.level_group(["ITFQ"]) == "ITF"


def test_pbp_verdicts():
    ev = {"homeScore": {"period1": 6, "period2": 7}, "awayScore": {"period1": 4, "period2": 5}, "status": {"code": 100}}
    full = [{"set": 1, "games": [{}] * 10}, {"set": 2, "games": [{}] * 12}]
    assert E.pbp_verdict(full, ev)["pbp_verdict"] == "complete"
    assert E.pbp_verdict([{"set": 1, "games": [{}] * 10}, {"set": 2, "games": [{}] * 11}], ev)["pbp_verdict"] == "short"
    retired = {**ev, "status": {"code": 92, "description": "Retired"}}
    assert E.pbp_verdict([{"set": 1, "games": [{}] * 10}, {"set": 2, "games": [{}] * 13}], retired)["pbp_verdict"] == \
        "complete to retirement"
    assert E.stats_check(STATS["statistics"]) == {"stats_keys": len(E.FULL_BOX), "stats_full_box": True}


def test_gap_selection_uses_the_below_grain():
    m = pd.DataFrame({"tour": ["M", "M", "M", "W"], "level": ["T250", "T250", "CH", "T250"], "year": [2025] * 4,
                      "best": ["stats", "point", "stats", "stats"]})
    select = {"tours": ["M"], "levels": ["T250"], "years": [2025], "below": "point"}
    assert E.in_select(m, select).tolist() == [True, False, False, False]
    assert E.edition_key(targets_frame()).iloc[0] == "M|Houston|2026|w14"


# a run against the fake site --------------------------------------------------------------
def test_list_link_fetch_and_stage(folders):
    receipts = P.receipts_for(E.SOURCE)
    client = FakeClient()
    lister = E.Lister(client, receipts, offline=False)
    t = targets_frame()
    t = t.assign(w1=t["name1"].map(E.words), w2=t["name2"].map(E.words))
    ed_rows, rows, linked = E.list_and_link(lister, t, t)
    (ed,) = ed_rows
    assert (ed["utid"], ed["sid"], ed["located_by"], ed["season_pages"]) == (2409, 80801, "3/2026-04-01", 2)
    assert (ed["season_events"], ed["season_singles"], ed["targets_linked"]) == (3, 2, 2)
    assert [(r["listed"], r.get("event_id")) for r in rows] == [(True, 101), (True, 102), (False, None)]
    outcomes = E.fetch_parts(lister, linked, E.PARTS)
    assert outcomes == {"point-by-point:200": 1, "point-by-point:404": 1, "statistics:200": 1, "statistics:404": 1}
    assert client.urls[-4:] == [f"{API}/event/101/point-by-point", f"{API}/event/102/point-by-point",
                                f"{API}/event/101/statistics", f"{API}/event/102/statistics"]   # newest first, points first
    E.fetch_results(lister, rows, linked)
    assert (rows[0]["pbp_verdict"], rows[0]["pbp_points"], rows[0]["stats_full_box"]) == ("complete", 3, True)
    assert (rows[1]["pbp_status"], rows[1]["stats_status"], rows[2]["pbp_status"]) == (404, 404, None)
    before = client.requests
    assert E.fetch_parts(lister, linked, E.PARTS)["point-by-point:200:cached"] == 1 and client.requests == before

    staged = E.stage(receipts)
    assert {k: v["rows"] for k, v in staged.items()} == {"events": 3, "points": 3, "statistics": len(E.FULL_BOX)}
    ev = pd.read_parquet(P.dump_path(E.SOURCE, "events.parquet")).set_index("event_id")
    assert ev.loc["101", "pbp_status"] == "200" and ev.loc["102", "pbp_status"] == "404"
    assert ev.loc["103", "doubles"] == "TRUE" and ev.loc["102", "listed_in_season"] == "2409_80801"
    pts = pd.read_parquet(P.dump_path(E.SOURCE, "points.parquet"))
    assert pts["point_description"].fillna("").tolist() == ["1", "", ""] and set(pts["event_id"]) == {"101"}


def test_limit_leaves_later_editions_untried(folders):
    client = FakeClient()
    t = targets_frame()
    t = t.assign(w1=t["name1"].map(E.words), w2=t["name2"].map(E.words))
    ed_rows, rows, linked = E.list_and_link(E.Lister(client, P.receipts_for(E.SOURCE), offline=False), t, t, limit=0)
    assert client.requests == 0 and linked == {} and not any(r["listed"] for r in rows) and len(rows) == 3
    assert ed_rows[0]["locate_tried"] == "not tried: beyond --limit"


def test_run_freezes_targets_and_reports_a_block(folders, monkeypatch):
    monkeypatch.setattr(E, "load_targets", lambda gap, refresh: (targets_frame(), "test targets"))
    monkeypatch.setattr(E, "known_matches", lambda targets: targets[["tour", "tname", "year", "d", "name1", "name2"]])
    client = FakeClient(block={f"{API}/event/101/statistics"})
    monkeypatch.setattr(E, "make_client", lambda args: client)
    parser = argparse.ArgumentParser()
    E.add_arguments(parser)
    summary = E.run(parser.parse_args([]))
    assert summary["stopped"].startswith("Blocked") and summary["matches_selected"] == 2
    assert summary["all"]["points_any"] == 1 and summary["all"]["points_absent"] == 1
    assert summary["all"]["stats_any"] == 0 and summary["editions_located"] == 1
    table = pd.read_csv(E.targets_path("atp_points_2025"))
    assert len(table) == 3 and table["event_id"].dropna().astype(int).tolist() == [101, 102]
    assert table.loc[table["event_id"].eq(101), "stats_status"].item() == "not fetched"
    assert (folders / "studies" / "runs.jsonl").exists()
    assert pd.read_csv(folders / "studies" / "sofascore_atp_points_2025_editions.csv")["utid"].tolist() == [2409]
