"""TennisLive's pages for the map's gap matches (work package P5): the reference rows, the link rules, the record and
box-score checks, the pauses on a silent site, the page order, the frozen targets, the map's placement, and a whole
run against a fake TennisLive (offline; every answer is canned, and the raw, dump and evidence folders are
temporary)."""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M  # noqa: E402
from src.eda.gap_downloads import verify_links as V  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import sofascore_editions as SE  # noqa: E402
from src.ingest.point_sources import tennislive as TL  # noqa: E402
from src.ingest.point_sources import tennislive_gaps as G  # noqa: E402

SITE = TL.SITE
FIXTURES = PROJECT_ROOT / "test" / "point_shot_sources" / "fixtures"
HOLT_URL = "/atp/match/brandon-holt-VS-inaki-montes-de-la-torre/champaign-challenger-2023/"
# the fixture page's statistics block as Sackmann's box score, Holt (the winner) first
HOLT_BOX = {"w_ace": 3, "w_df": 1, "w_svpt": 70, "w_1stIn": 49, "w_1stWon": 39, "w_2ndWon": 9, "w_bpSaved": 3,
            "w_bpFaced": 6, "l_ace": 2, "l_df": 5, "l_svpt": 58, "l_1stIn": 36, "l_1stWon": 18, "l_2ndWon": 10,
            "l_bpSaved": 3, "l_bpFaced": 10}


# ----------------------------------------------------------------------------------------- helpers
def listed_row(event, p1, p2, day, *, score="6-3 6-4", winner="1", draw="main", rnd="R32", url=True, tour="atp",
               played="TRUE", match_id=None, name="ATP X Challenger"):
    slug = f"{p1.lower().replace(' ', '-')}-VS-{p2.lower().replace(' ', '-')}"
    return {"event_key": event, "event_name": name, "event_kind": "challenger", "tour": tour,
            "discipline": "singles", "junior": "FALSE", "played": played, "match_id": match_id or f"{event}:{slug}",
            "url": f"/{tour}/match/{slug}/{event.split(':')[1]}/" if url else None,
            "draw": "qualifying" if draw == "qual" else "main", "round": rnd, "state": "finished",
            "end_reason": None, "winner_side": winner, "score": score, "player1_name": p1, "player2_name": p2,
            "start_utc": f"{day} 10:00"}


def listing(rows, events):
    li = pd.DataFrame(rows)
    ev = pd.DataFrame(events)
    return G.Listing(li, ev)


def target(name1, name2, d, *, draw="main", score="6-3 6-4", rnd="R32", tname="X CH", year=None, tour="M",
           winner=None, edition="e"):
    return pd.Series({"name1": name1, "name2": name2, "d": pd.Timestamp(d), "draw": draw, "official_score": score,
                      "official_round": rnd, "tname": tname, "year": year or pd.Timestamp(d).year, "tour": tour,
                      "official_winner": winner or name1, "edition": edition, "creator": "tml"})


def link_one(t, lst, event):
    pair = M.pair_key(pd.Series([M.surname_key(t["name1"])]), pd.Series([M.surname_key(t["name2"])])).iat[0]
    return G.link_target(t, pair, lst, event)


EVENTS = [{"key": "atp:1", "first_week": "2021-02-08", "url": "/atp-men/x/", "name": "X", "kind": "challenger",
           "section_status": "200"},
          {"key": "atp:2", "first_week": "2021-02-15", "url": "/atp-men/y/", "name": "Y", "kind": "challenger",
           "section_status": "200"},
          {"key": "atp:3", "first_week": "2021-05-31", "url": "/atp-men/z/", "name": "Z", "kind": "challenger",
           "section_status": "200"}]


# ----------------------------------------------------------------------------------------- scores and references
def test_scores_and_api_tennis_sets():
    assert G.games_of("7-6(6) 1-6 6-3") == [13, 7, 9] and G.games_of(None) == [] and G.games_of(" ") == []
    assert G.set_scores("6-7(3) 7-5 6-3") == frozenset({(6, 7), (5, 7), (3, 6)})
    assert G.set_scores("4-6 7-5 [10-5]") == frozenset({(4, 6), (5, 7), (5, 10)})      # a match tiebreak is a set
    assert G.set_scores("3-6 6-4", listed=True) == frozenset({(3, 6), (4, 6)})
    assert G.ended_early("5-4 RET") and G.ended_early("7-6(4) 0-0 Def.") and not G.ended_early("6-4 6-4")
    sets = '[{"score_first": "6.4", "score_second": "7.7", "score_set": "1"}, {"score_first": "6", "score_second": "4",' \
           ' "score_set": "2"}]'
    assert G.api_tennis_sets(sets) == [(6, 7), (6, 4)] and G.api_tennis_sets("nonsense") == []
    box = G.box_json({**{k: str(v) for k, v in HOLT_BOX.items()}, "w_SvGms": "9"})
    assert json.loads(box) == HOLT_BOX
    assert G.box_json({"w_svpt": "0", "w_ace": "1"}) is None and G.box_json({}) is None


# ----------------------------------------------------------------------------------------- linking
def test_the_editions_event_by_its_games_or_by_pair_round_and_a_set():
    lst = listing([listed_row("atp:1", "Aa Alpha", "Bb Beta", "2021-02-10", score="6-3 6-4"),
                   listed_row("atp:1", "Cc Gamma", "Dd Delta", "2021-02-11", score="7-6(5) 7-6(3)", rnd="R16")], EVENTS)
    found, how, ok = link_one(target("Aa Alpha", "Bb Beta", "2021-02-08"), lst, "atp:1")
    assert ok and how == "edition's event" and found[0]["player1"] == "Aa Alpha" and found[2]["games_agree"]
    # the score differs, the pair, the round and one set agree (a retirement recorded otherwise, a typo): confirmed
    found, how, ok = link_one(target("Cc Gamma", "Dd Delta", "2021-02-08", score="7-6(5) 5-7 6-3", rnd="R16"), lst,
                              "atp:1")
    assert ok and how == "edition's event" and found[2]["set_agrees"] and not found[2]["games_agree"]
    # no set agrees and the match was played out: the pair met elsewhere (Prague I and II of 2020); unconfirmed
    found, how, ok = link_one(target("Cc Gamma", "Dd Delta", "2021-02-08", score="5-7 6-4 6-3", rnd="R16"), lst,
                              "atp:1")
    assert not ok and how == "edition's event" and found[0]["player1"] == "Cc Gamma"
    # ... unless the reference's match ended early
    found, how, ok = link_one(target("Cc Gamma", "Dd Delta", "2021-02-08", score="5-4 RET", rnd="R16"), lst, "atp:1")
    assert ok


def test_games_found_in_a_neighbouring_event_come_before_a_pair_and_round():
    lst = listing([listed_row("atp:1", "Cc Gamma", "Dd Delta", "2021-02-10", score="7-6(3) 6-3"),
                   listed_row("atp:2", "Cc Gamma", "Dd Delta", "2021-02-17", score="5-7 6-4 6-3")], EVENTS)
    found, how, ok = link_one(target("Cc Gamma", "Dd Delta", "2021-02-08", score="5-7 6-4 6-3"), lst, "atp:1")
    assert ok and how == "another event" and found[0]["event_key"] == "atp:2"


def test_another_week_needs_pair_games_draw_and_round():
    # Tennis My Life files Biella 2-7 of 2021 under Biella 1's date: the match is months away
    lst = listing([listed_row("atp:3", "Holger Rune", "Daniel Altmaier", "2021-06-01", score="6-2 6-7(4) 7-6(5)")],
                  EVENTS)
    t = target("Holger Rune", "Daniel Altmaier", "2021-02-14", score="6-2 6-7(4) 7-6(5)")
    found, how, ok = link_one(t, lst, "atp:1")
    assert ok and how == "another week"
    assert not link_one(target("Holger Rune", "Daniel Altmaier", "2021-02-14", score="6-2 6-4"), lst, "atp:1")[2]
    assert not link_one(target("Holger Rune", "Daniel Altmaier", "2021-02-14", score="6-2 6-7(4) 7-6(5)", rnd="QF"),
                        lst, "atp:1")[2]
    assert not link_one(target("Holger Rune", "Daniel Altmaier", "2021-02-14", score="6-2 6-7(4) 7-6(5)",
                               draw="qual", rnd=None), lst, "atp:1")[2]


def test_name_words_alone_need_three_words_outside_the_event():
    # 'Juan ... v Facundo ...' shares a first name each with another pair: never enough elsewhere
    lst = listing([listed_row("atp:2", "Juan Ignacio Londero", "Facundo Mena", "2021-02-16", score="6-3 6-4")], EVENTS)
    found, how, ok = link_one(target("Juan Pablo Ficovich", "Facundo Bagnis", "2021-02-08"), lst, "atp:1")
    assert not ok and found is None and how == "not linked"
    # an initial-and-surname form (API-Tennis) shares the surnames: three words with the games, confirmed
    lst = listing([listed_row("atp:2", "Oscar Jose Gutierrez", "Kai Wehnelt", "2021-02-16", score="6-3 6-4")], EVENTS)
    found, how, ok = link_one(target("J. Gutierrez Oscar", "K. Wehnelt", "2021-02-08"), lst, "atp:1")
    assert ok and how == "another event" and not found[2]["pair_agrees"]


def test_without_a_reference_the_surname_pair_in_the_event_or_its_week():
    lst = listing([listed_row("atp:1", "Aa Alpha", "Bb Beta", "2021-02-10"),
                   listed_row("atp:2", "Ee Eps", "Ff Phi", "2021-02-17")], EVENTS)
    assert link_one(target("Aa Alpha", "Bb Beta", "2021-02-08", score=None, rnd=None), lst, "atp:1")[2]
    assert link_one(target("Ee Eps", "Ff Phi", "2021-02-15", score=None, rnd=None), lst, "atp:1")[1:] == (
        "another event", True)                                        # 2 days after the map's date: its week
    assert not link_one(target("Ee Eps", "Ff Phi", "2021-02-08", score=None, rnd=None), lst, "atp:1")[2]


def test_link_targets_selects_confirmed_links_with_a_page_in_their_draw():
    rows = [listed_row("atp:1", "Aa Alpha", "Bb Beta", "2021-02-10", draw="qual", rnd="Q1"),
            listed_row("atp:1", "Cc Gamma", "Dd Delta", "2021-02-10", url=False),
            listed_row("atp:1", "Ee Eps", "Ff Phi", "2021-02-10", draw="qual", rnd="Q2", score="6-1 6-1")]
    lst = listing(rows, EVENTS)
    t = pd.DataFrame([target("Aa Alpha", "Bb Beta", "2021-02-08", rnd="SF", edition="e1"),     # API-Tennis's 'SF'
                      target("Cc Gamma", "Dd Delta", "2021-02-08", edition="e1"),
                      target("Ee Eps", "Ff Phi", "2021-02-08", score="6-3 6-3", rnd="SF", edition="e1")])
    out = G.link_targets(t, lst, {"e1": "atp:1"})
    assert out["link_confirmed"].tolist() == [True, True, False]
    assert out["tl_selected"].tolist() == [True, False, False]        # the other draw with its games; no page URL
    assert out["link_verdict"].tolist()[:2] == ["agrees", "agrees"] and pd.isna(out["tl_url"].iloc[1])


def test_link_verdicts():
    assert G.link_verdict("Aa Alpha", "Bb Beta", "6-3 6-4", "Aa Alpha", "Bb Beta", "1", "6-3 6-4", None) == "agrees"
    assert G.link_verdict("Aa Alpha", "Bb Beta", "6-3 6-4", "Bb Beta", "Aa Alpha", "2", "3-6 4-6", None) == "agrees"
    assert G.link_verdict("Aa Alpha", "Bb Beta", "6-3 6-4", "Bb Beta", "Aa Alpha", "1", "6-3 6-4", None) == \
        "winner differs"
    assert G.link_verdict("Aa Alpha", "Bb Beta", "6-3 6-4", "Aa Alpha", "Bb Beta", "1", "3-6 4-6", None) == \
        "winner agrees, official score written loser first"
    assert G.link_verdict("Aa Alpha", "Bb Beta", "6-3 2-1 RET", "Aa Alpha", "Bb Beta", "1", "6-3 2-1", "retired") == \
        "agrees"
    assert G.link_verdict("Aa Alpha", "Bb Beta", "6-3 6-4", "Aa Alpha", "Bb Beta", "1", "6-3 7-5", None) == \
        "winner agrees, score differs"
    assert G.link_verdict("Aa Alpha", "Bb Beta", None, "Aa Alpha", "Bb Beta", "1", "6-3", None) == "no official row"
    assert G.link_verdict("Aa Alpha", "Bb Beta", "6-3", "Aa Alpha", "Bb Beta", None, "6-3", None) == "no listed winner"


# ----------------------------------------------------------------------------------------- records
def test_record_verdicts_and_shapes():
    assert G.record_verdict(80, [10, 9], [10, 9], [10, 9]) == "complete"
    assert G.record_verdict(80, [9, 8], [9, 8], [10, 9]) == "only set-closing games missing"
    assert G.record_verdict(80, [7, 9], [7, 9], [10, 9]) == "other shortfall"
    assert G.record_verdict(80, [11, 9], [11, 9], [10, 9]) == "other shortfall (more games than the score)"
    assert G.record_verdict(0, [], [], [10, 9]) == "no points"
    assert G.record_verdict(80, [10], [10], []) == "no score to compare"
    games = pd.DataFrame({"url": ["u"] * 4 + ["v"], "set": ["1", "1", "3", "3", "1"], "game": ["1", "2", "1", "2", "1"],
                          "after": ["1-0", "1-1", "0-1", "1-1", "0-1"]})
    shape = G.shapes(games)
    assert shape["u"] == ([2, 0, 2], [2, None, 2]) and shape["v"] == ([1], [1])
    assert G.winner_index("Brandon Holt", "Inaki Montes-De La Torre", "Brandon Holt", "Inaki Montes De La Torre") == 0
    assert G.winner_index("Inaki Montes-De La Torre", "Brandon Holt", "Brandon Holt", "Inaki Montes De La Torre") == 1
    assert G.winner_index("Xx Yy", "Zz Ww", "Brandon Holt", "Inaki Montes") is None


# ----------------------------------------------------------------------------------------- fetching
def test_pauses_on_a_silent_site_then_slows_and_stops():
    class C:
        requests, min_interval, jitter = 10, 2.0, 1.0

    slept = []
    pauses = G.Pauses(C(), limit=2, minutes=30, max_pauses=2, sleep=slept.append)
    timeout = {"status": None, "error": "RuntimeError: Timeout: curl: (28) Operation timed out after 30010 ms"}
    pauses.note(timeout)
    pauses.note({"status": 200})                        # an answer in between resets the count
    pauses.note(timeout)
    assert slept == []
    pauses.note(timeout)                                # two in a row: one pause, then a slower pace
    assert slept == [1800] and (pauses.client.min_interval, pauses.client.jitter) == (3.0, 2.0)
    pauses.note({"status": None, "error": "response is not an HTML document"})    # answered: no stall
    pauses.note(timeout)
    pauses.note(timeout)
    assert slept == [1800, 1800] and pauses.in_row == 2
    pauses.note(timeout)
    with pytest.raises(P.Blocked):                      # a third pause in a row is not taken
        pauses.note(timeout)
    pauses.note({"status": 404})
    assert pauses.in_row == 0 and len(pauses.log) == 2


def test_pages_once_newest_first_with_their_gaps():
    f = pd.DataFrame({"gap": ["a", "b", "a", "a", "b"], "edition": ["e1", "e1", "e2", "e3", "e4"],
                      "d": pd.to_datetime(["2018-05-07", "2018-05-07", "2019-01-07", "2017-03-06", "2018-01-01"]),
                      "tl_url": ["/u1/", "/u1/", "/u2/", "/u3/", None], "tl_selected": [True, True, True, True, False],
                      "tl_start_utc": ["2018-05-09 10:00", "2018-05-09 10:00", None, None, None]})
    pages = G.select_pages(f)
    assert pages["url"].tolist() == ["/u2/", "/u1/", "/u3/"] and pages["gaps"].tolist() == ["a", "a;b", "a"]
    assert G.select_pages(f, limit=1)["url"].tolist() == ["/u2/", "/u1/"]        # each gap's newest edition


def test_the_map_places_a_pairs_two_meetings_by_their_draw(tmp_path):
    # Opelka and van de Zandschulp met in Basel's qualifying and again in its main draw: one key, two draws
    m = pd.DataFrame({"uid": [5, 6, 7], "tour": "M", "tname": "Basel", "d": pd.to_datetime(["2025-10-20"] * 3),
                      "name1": ["Reilly Opelka", "Reilly Opelka", "Aa Alpha"],
                      "name2": ["Botic van de Zandschulp"] * 2 + ["Bb Beta"], "draw": ["qual", "main", "main"],
                      "year": 2025})
    m = pd.concat([m, m.iloc[[2]].assign(uid=8)])                           # a row the map holds twice: placed nowhere
    links = m.drop(columns=["uid", "year"]).assign(d="2025-10-20", tl_selected="True",
                                                   tl_url=["/atp/match/q/", "/atp/match/m/", "/atp/match/a/",
                                                           "/atp/match/a/"])
    path = tmp_path / "tennislive_x_matches.csv.gz"
    links.to_csv(path, index=False)
    rows = pd.DataFrame({"url": ["/atp/match/q/", "/atp/match/m/", "/atp/match/a/"], "tour": "M",
                         "d": pd.to_datetime(["2025-10-19", "2025-10-22", "2025-10-21"]), "name1": "x", "name2": "y"})
    placed = M.tennislive_gap_uids(rows, m, [path]).set_index("url")
    assert placed.loc["/atp/match/q/", "preset_uid"] == 5 and placed.loc["/atp/match/m/", "preset_uid"] == 6
    assert pd.isna(placed.loc["/atp/match/a/", "preset_uid"]) and placed.loc["/atp/match/a/", "name1"] == "x"
    assert placed.loc["/atp/match/q/", "name1"] == "Reilly Opelka"                 # a placed page takes the map's keys


# ----------------------------------------------------------------------------------------- a whole run
class FakeResponse:
    def __init__(self, status, body, url="http://fake"):
        self.status_code, self.content, self.url = status, body, url
        self.headers = {"content-type": "text/html"}


class FakeClient:
    impersonate = "fake"

    def __init__(self, answers):
        self.answers, self.requests, self.urls = answers, 0, []
        self.min_interval, self.jitter = 2.0, 1.0

    def get(self, url, headers=None):
        self.requests += 1
        self.urls.append(url)
        body = self.answers.get(url)
        if body is None:
            return FakeResponse(404, b"not found", url)
        return FakeResponse(200, body.encode("utf-8"), url)

    def stats(self):
        return {"impersonate": self.impersonate, "requests": self.requests}


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A map with five gap matches, P4's listings of their event, the result file and the page of one of them."""
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump" / "points")
    for mod in (G,):
        monkeypatch.setattr(mod, "STUDY", tmp_path / "studies")
    monkeypatch.setattr(TL, "GAP_TABLES", tmp_path / "studies")
    monkeypatch.setattr(TL, "SAMPLES_CSV", tmp_path / "studies" / "tennislive_samples.csv")
    monkeypatch.setattr(G, "MATCHES", tmp_path / "map" / "matches.parquet")
    monkeypatch.setattr(G, "API_TENNIS", tmp_path / "none")
    monkeypatch.setattr(V, "RESULTS", tmp_path / "results")
    catalog = tmp_path / "data_map.yaml"
    catalog.write_text("gaps:\n  - id: challenger_points_2022_2024\n    select: {tours: [M], levels: [CH, CHQ], "
                       "years: [2023], below: point}\n", encoding="utf-8")
    monkeypatch.setattr(SE, "CATALOG", catalog)
    base = {"tour": "M", "level": "CH", "draw": "main", "year": 2023, "d": pd.Timestamp("2023-11-13"),
            "tname": "Champaign CH", "best": "stats", "best_status": "on_disk", "best_on_disk": "stats",
            "sources": "tml"}
    games = [("Brandon Holt", "Inaki Montes De La Torre", "tml"), ("Brandon Holt", "Inaki Montes De La Torre", "sackmann"),
             ("Aa Alpha", "Bb Beta", "tml"), ("Cc Gamma", "Dd Delta", "tml"), ("Ee Eps", "Ff Phi", "tml")]
    m = pd.DataFrame([{**base, "uid": i, "name1": a, "name2": b, "creator": c,
                       "tname": "Champaign CH" if c == "tml" else "Champaign 2 CH",
                       "d": pd.Timestamp("2023-11-13") if c == "tml" else pd.Timestamp("2023-08-07")}
                      for i, (a, b, c) in enumerate(games)])
    m.loc[m["name1"].eq("Ee Eps"), "best"] = "point"                                    # not in the gap
    (tmp_path / "map").mkdir()
    m.to_parquet(tmp_path / "map" / "matches.parquet")
    dump = tmp_path / "dump" / "points" / "tennislive"
    dump.mkdir(parents=True)
    rows = [listed_row("atp:9", "Brandon Holt", "Inaki Montes-De La Torre", "2023-11-14", score="5-7 6-0 6-1",
                       name="ATP Champaign Challenger"),
            listed_row("atp:9", "Aa Alpha", "Bb Beta", "2023-11-15", score="6-3 6-4", name="ATP Champaign Challenger"),
            listed_row("atp:9", "Cc Gamma", "Dd Delta", "2023-11-15", score="6-1 6-1", rnd="R16",
                       name="ATP Champaign Challenger")]
    rows[0]["url"] = HOLT_URL
    pd.DataFrame(rows).to_parquet(dump / "listed.parquet")
    pd.DataFrame([{"key": "atp:9", "first_week": "2023-11-13", "url": "/atp-men/champaign-challenger-2023/",
                   "name": "Champaign Challenger", "kind": "challenger", "section_status": "200"}]).to_parquet(
        dump / "events.parquet")
    res = tmp_path / "results" / "tennis_my_life" / "atp_challenger"
    res.mkdir(parents=True)
    official = [{"tourney_name": "Champaign CH", "tourney_date": "20231113", "round": "R32",
                 "winner_name": "Brandon Holt", "loser_name": "Inaki Montes De La Torre", "score": "5-7 6-0 6-1",
                 **{k: str(v) for k, v in HOLT_BOX.items()}},
                {"tourney_name": "Champaign CH", "tourney_date": "20231113", "round": "R32", "winner_name": "Aa Alpha",
                 "loser_name": "Bb Beta", "score": "6-3 6-4"},
                {"tourney_name": "Champaign CH", "tourney_date": "20231113", "round": "QF", "winner_name": "Cc Gamma",
                 "loser_name": "Dd Delta", "score": "6-4 6-4"}]
    pd.DataFrame(official).to_parquet(res / "2023_challenger.parquet")
    sack = tmp_path / "results" / "sackmann_archive" / "atp"
    sack.mkdir(parents=True)
    swapped = {f"{'l' if k[0] == 'w' else 'w'}{k[1:]}": str(v) for k, v in HOLT_BOX.items()}
    pd.DataFrame([{"tourney_name": "Champaign 2 CH", "tourney_date": "20230807", "round": "R32",
                   "winner_name": "Brandon Holt", "loser_name": "Inaki Montes De La Torre", "score": "5-7 6-0 6-1",
                   **swapped}]).to_parquet(sack / "atp_matches_qual_chall_2023.parquet")
    html = (FIXTURES / "tennislive_match.html").read_text(encoding="utf-8")
    client = FakeClient({SITE + HOLT_URL: html})
    monkeypatch.setattr(G, "make_client", lambda args: client)
    return tmp_path, client


def test_a_run_freezes_links_fetches_checks_and_feeds_the_map(world, monkeypatch):
    tmp_path, client = world
    parser = argparse.ArgumentParser()
    G.add_arguments(parser)
    summary = G.run(parser.parse_args(["--gaps", "challenger_points_2022_2024", "--max-requests", "50"]))
    assert not summary.get("stopped")
    frozen = tmp_path / "studies" / "tennislive_challenger_points_2022_2024_matches.csv.gz"
    t = pd.read_csv(frozen).set_index("uid")
    assert sorted(t.index) == [0, 1, 2, 3]                                   # the match with points is no target
    # Holt is in the map twice (a misdated copy, under another name and date): both link to the one page
    assert t.loc[0, "link_how"] == "edition's event" and t.loc[1, "link_how"] == "another week"
    assert t.loc[[0, 1], "tl_url"].tolist() == [HOLT_URL, HOLT_URL] and t.loc[[0, 1], "tl_selected"].all()
    assert t.loc[2, "tl_selected"] and str(t.loc[2, "page_status"]) == "404"
    assert not t.loc[3, "link_confirmed"] and not t.loc[3, "tl_selected"]   # no set agrees: unconfirmed
    assert client.urls.count(SITE + HOLT_URL) == 1 and summary["fetch_outcomes"]["page:200"] == 1
    assert summary["fetch_outcomes"]["page:404"] == 1                       # Alpha v Beta has no page: absent
    holt, copy = t.loc[0], t.loc[1]
    assert str(holt["page_status"]) == "200" and holt["record_verdict"] == "other shortfall"
    assert holt["box_compared"] and holt["box_all_equal"] and not holt["box_swapped"]
    assert copy["box_swapped"] and not copy["box_all_equal"]                 # the copy's box has the players swapped
    staged = pd.read_parquet(P.dump_path(G.SOURCE, "matches.parquet")).set_index("url")
    assert staged.loc[HOLT_URL, "gaps_in"] == "challenger_points_2022_2024"
    assert (tmp_path / "studies" / "tennislive_gaps_summary.json").exists()
    assert (tmp_path / "studies" / "tennislive_challenger_points_2022_2024_editions.csv").exists()
    again = G.run(parser.parse_args(["--gaps", "challenger_points_2022_2024", "--max-requests", "50"]))
    assert again["fetch_outcomes"] == {"page:200:cached": 1, "page:404:cached": 1} and client.requests == 2
    # rebuilding the evidence with no HTTP keeps the last fetching run's counts
    rebuilt = G.run(parser.parse_args(["--gaps", "challenger_points_2022_2024", "--link-only"]))
    assert rebuilt["client"] is None and rebuilt["last_fetch"]["fetch_outcomes"] == again["fetch_outcomes"]
    assert rebuilt["last_fetch"]["finished_at"] == again["finished_at"] and rebuilt["all"]["pages"] == 2

    # an unconfirmed link whose URL is another target's page gets no record
    frame = pd.read_csv(frozen)
    frame = pd.concat([frame, frame[frame["uid"].eq(0)].assign(uid=9, tl_selected=False, link_confirmed=False)])
    frame["tl_selected"] = frame["tl_selected"].astype(bool)
    frame["official_box"] = None
    page = G.records(frame.reset_index(drop=True), P.receipts_for(G.SOURCE)).iloc[-1]
    assert page["page_status"] == 200 and pd.isna(page["record_verdict"]) and pd.isna(page["box_compared"])
    assert G.cell(frame.assign(page_status=frame["page_status"].astype(str)))["pages"] == 2

    # the map reads the pages and puts them on the linked matches, both copies of Holt's
    monkeypatch.setattr(M, "DUMP", tmp_path / "dump")
    rows = M.load_tennislive(gaps=True)
    assert rows["url"].tolist() == [HOLT_URL] and rows["grain"].tolist() == ["point"]
    m = pd.read_parquet(tmp_path / "map" / "matches.parquet")
    placed = M.tennislive_gap_uids(rows, m, [frozen])
    assert sorted(placed["preset_uid"].astype(int)) == [0, 1]
    # each placed row takes its match's date (the copy's is August's), so that it stays in the map's window
    days = placed.set_index(placed["preset_uid"].astype(int))["d"].dt.strftime("%Y-%m-%d").to_dict()
    assert days == {0: "2023-11-13", 1: "2023-08-07"}
    assert M.load_tennislive().empty and M.load_tennislive(sampled=True).empty
