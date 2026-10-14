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


def test_a_played_event_beats_a_cancelled_one_of_the_same_pair():
    ghost = event(401, "Marat Sharipov", "Ivan Ivanov", "2026-03-30")   # nearer the start, but never played
    ghost["status"] = {"code": 70, "type": "canceled", "description": "Canceled"}
    played = event(402, "Ivan Ivanov", "Marat Sharipov", "2026-03-31")
    events = E.singles([ghost, played])
    assert E.best_event(E.words("Marat Sharipov"), E.words("Ivan Ivanov"), D0, D0, events, "main")[0]["id"] == 402


def test_the_winner_decides_between_two_meetings_of_a_pair():
    # ATP Finals 2021: Medvedev beat Zverev in the round robin, Zverev beat him in the final
    group = event(701, "Daniil Medvedev", "Alexander Zverev", "2026-03-30")
    final = event(702, "Alexander Zverev", "Daniil Medvedev", "2026-04-04")
    events = E.singles([group, final])
    a, b = E.words("Alexander Zverev"), E.words("Daniil Medvedev")
    assert E.best_event(a, b, D0, D0, events, "main", winner=a)[0]["id"] == 702
    assert E.best_event(a, b, D0, D0, events, "main")[0]["id"] == 701   # no winner known: the one nearest the start


class CannedLister:
    """Every day listing and season page answers with the same events (offline)."""

    client = None

    def __init__(self, events):
        self.events = events

    def day_events(self, category, day):
        return [dict(e) for e in self.events]

    def season_events(self, utid, sid):
        return [dict(e) for e in self.events], 1


def test_an_event_another_known_match_names_better_is_not_linked():
    # Costa do Sauipe 2025: Gima v Hernandez Serrano is not listed, and Gima v Varillas shares 'juan' with it
    varillas = event(501, "Sebastian Gima", "Juan Pablo Varillas", "2026-03-30")
    t = targets_frame().iloc[:1].assign(name1="Sebastian Gima", name2="Juan Alejandro Hernandez Serrano")
    t = t.assign(w1=t["name1"].map(E.words), w2=t["name2"].map(E.words))
    known = pd.concat([t, t.assign(name2="Juan Pablo Varillas")])
    known = known.assign(w1=known["name1"].map(E.words), w2=known["name2"].map(E.words))
    _, rows, linked = E.list_and_link(CannedLister([varillas]), t, known)
    assert not rows[0]["listed"] and linked == {}
    assert rows[0]["link_note"] == "event 501 names another known match better"
    _, rows, _ = E.list_and_link(CannedLister([varillas]), t, t)   # with no better claimant, the shared word links
    assert rows[0]["listed"] and rows[0]["event_id"] == 501 and rows[0]["link_note"] is None


class DayLister(CannedLister):
    """Only one day's listing names the events; records the days asked for."""

    def __init__(self, events, day):
        super().__init__(events)
        self.day, self.asked = day, []

    def day_events(self, category, day):
        self.asked.append(f"{category}/{day}")
        return [dict(e) for e in self.events] if day == self.day else []


def test_an_edition_dated_a_week_late_is_found_in_the_week_before():
    played = [event(601, "Franco Agamenone", "Max Alcala Gurri", "2026-03-25", tname="Targu Mures, Romania")]
    known = pd.DataFrame({"w1": [E.words("Franco Agamenone")], "w2": [E.words("Max Alcala Gurri")]})
    lister = DayLister(played, "2026-03-25")
    loc = E.locate(lister, "M", ["CH"], D0, D0, known)
    assert (loc["utid"], loc["located_by"]) == (2409, "72/2026-03-25")
    assert lister.asked == [f"72/{d}" for d in ("2026-04-01", "2026-04-03", "2026-03-31", "2026-04-04", "2026-03-29",
                                                "2026-03-27", "2026-03-25")]


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
    # streamed one table at a time: the events still carry each record's shape and the box score's periods
    assert (ev.loc["101", "pbp_points"], ev.loc["101", "stats_periods"]) == ("3", "ALL")
    assert ev.loc[["102", "103"], ["pbp_points", "stats_periods"]].isna().all().all()
    assert list(staged) == ["events", "points", "statistics"]


def test_the_itf_gaps_keep_their_tables_gzipped(folders):
    assert E.targets_path("itf_detail").name == "sofascore_itf_detail_matches.csv.gz"
    assert E.table_path("itf_points_2025_2026", "link_check").name == "sofascore_itf_points_2025_2026_link_check.csv.gz"
    assert E.targets_path("atp_points_2025").name == "sofascore_atp_points_2025_matches.csv"
    path = E.targets_path("itf_detail")
    path.parent.mkdir(parents=True)
    targets_frame().assign(gap="itf_detail").to_csv(path, index=False)
    assert path.read_bytes()[:2] == b"\x1f\x8b"   # gzip
    t, origin = E.load_targets("itf_detail", refresh=False)   # a frozen list is read back from the gzipped file
    assert len(t) == 3 and origin.startswith("frozen in") and t["d"].dtype.kind == "M"


def test_only_the_editions_named_are_tried(folders, monkeypatch):
    client = FakeClient()
    t = pd.concat([targets_frame(), targets_frame().assign(d=D0 + pd.Timedelta(days=7))], ignore_index=True)
    t["edition"] = E.edition_key(t)   # Houston's week 14 and a week 15 that would be tried first (newest first)
    t = t.assign(w1=t["name1"].map(E.words), w2=t["name2"].map(E.words))
    lister = E.Lister(client, P.receipts_for(E.SOURCE), offline=False)
    ed_rows, rows, linked = E.list_and_link(lister, t, t, limit=1, only={"M|Houston|2026|w14"})
    assert {e["edition"]: e["locate_tried"] for e in ed_rows}["M|Houston|2026|w15"] == "not tried: not in --editions"
    assert set(linked) == {101, 102} and sum(r["listed"] for r in rows) == 2
    monkeypatch.setattr(E, "load_targets", lambda gap, refresh: (targets_frame(), "test targets"))
    parser = argparse.ArgumentParser()
    E.add_arguments(parser)
    with pytest.raises(SystemExit, match="not editions of gap"):   # a mistyped key would make a trial of nothing
        E.run(parser.parse_args(["--editions", "M|Nowhere|2026|w14"]))


def test_defer_uncovered_leaves_flagged_events_for_later(folders, monkeypatch):
    # SofaScore lists most ITF events of 2025 to February 2026 with coverage -1 and holds no record for them
    monkeypatch.setattr(E, "load_targets", lambda gap, refresh: (targets_frame(), "test targets"))
    monkeypatch.setattr(E, "known_matches", lambda targets: targets[["tour", "tname", "year", "d", "name1", "name2"]])
    monkeypatch.setitem(ANSWERS, f"{API}/unique-tournament/2409/season/80801/events/last/1",
                        {"events": [dict(STRUFF, coverage=-1)], "hasNextPage": False})
    client = FakeClient()
    monkeypatch.setattr(E, "make_client", lambda args: client)
    parser = argparse.ArgumentParser()
    E.add_arguments(parser)
    summary = E.run(parser.parse_args(["--defer-uncovered", "--no-stage"]))
    assert not any("/event/102/" in u for u in client.urls)   # the flagged event is not asked for
    assert f"{API}/event/101/point-by-point" in client.urls and f"{API}/event/101/statistics" in client.urls
    table = pd.read_csv(E.targets_path("atp_points_2025"))
    flagged = table[table["event_id"].eq(102)].iloc[0]
    assert (flagged["pbp_status"], flagged["stats_status"]) == (E.DEFERRED, E.DEFERRED)
    assert summary["all"]["points_deferred"] == 1 and summary["all"]["points_not_fetched"] == 0
    E.run(parser.parse_args(["--no-stage"]))   # a later run without the option asks for it
    assert f"{API}/event/102/point-by-point" in client.urls


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
