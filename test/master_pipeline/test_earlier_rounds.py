"""The earlier qualifying rounds from TennisLive (24 Oct 2026; prediction_run/earlier_rounds.py; master pipeline
process log, Part 14). Offline: no request, no build.

    * TennisLive's games as Tennis My Life's score, and a match page's statistics as its box columns;
    * a player's earlier wins at the event (src/pipeline/qualifying.earlier_wins);
    * Stage 0's live rows: a "played" row stays, and goes when its source's row stands (stage0_build.drop_replaced);
    * the data check (A3): a round 2 whose round 1 is in the matchups CSV's sidecar is not blocked;
    * since 25 Oct 2026, a main-draw match's qualifiers and lucky losers: every qualifying round at the event
      (qualifying.earlier_matches, live._qualifiers), and the data check's qualifier rule reading the sidecar;
    * since 27 Oct 2026, the main draw's first day on TennisLive (qualifying.main_draw_first_day), in the venue's zone.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import earlier_rounds as ER  # noqa: E402
from src.pipeline import qualifying as Q  # noqa: E402


def test_the_score_as_tennis_my_life_writes_it():
    assert ER.tl_score("6 3 6", "4 6 3", 1) == "6-4 3-6 6-3"
    assert ER.tl_score("4 6 3", "6 3 6", 2) == "6-4 3-6 6-3"                  # the winner listed second
    # each side's own tiebreak points in brackets; the score keeps the tiebreak's loser's
    assert ER.tl_score("7(7) 6", "6(5) 3", 1) == "7-6(5) 6-3"
    assert ER.tl_score("6(5) 3", "7(7) 6", 2) == "7-6(5) 6-3"
    assert ER.tl_score("6 2", "3 0", 1, "retired") == "6-3 2-0 RET"


def stats(p1: dict, p2: dict) -> list[dict]:
    """A match page's statistics (tennislive.parse_statistics' rows, the match period)."""
    out = []
    for name, (key, kind) in {"First serve": ("fs", "detail"), "First serve points won": ("fw", "detail"),
                              "Second serve points won": ("sw", "detail"), "Break points converted": ("bp", "detail"),
                              "Total points won": ("tp", "detail"), "Aces": ("ace", "value"),
                              "Double faults": ("df", "value")}.items():
        out.append({"period": "match", "name": name, f"player1_{kind}": p1[key], f"player2_{kind}": p2[key],
                    **({"player1_value": None, "player2_value": None} if kind == "detail" else
                       {"player1_detail": None, "player2_detail": None})})
    return out


P1 = {"fs": "40/62", "fw": "30/40", "sw": "12/22", "bp": "3/7", "tp": "70/120", "ace": "5", "df": "2"}
P2 = {"fs": "35/58", "fw": "22/35", "sw": "9/23", "bp": "2/6", "tp": "50/120", "ace": "1", "df": "4"}


def test_a_match_page_as_box_columns():
    box, note = ER.tl_box(stats(P1, P2), 1)
    assert note == "TennisLive match page (service games unknown: no first server)"
    assert (box["w_svpt"], box["w_1stIn"], box["w_1stWon"], box["w_2ndWon"]) == ("62", "40", "30", "12")
    assert (box["w_ace"], box["w_df"], box["w_SvGms"]) == ("5", "2", "")      # service games: not given
    # break points faced are the opponent's chances; saved, those less his conversions
    assert (box["w_bpFaced"], box["w_bpSaved"], box["l_bpFaced"], box["l_bpSaved"]) == ("6", "4", "7", "4")
    box2, _ = ER.tl_box(stats(P2, P1), 2)                                     # the winner listed second
    assert box2 == box
    # a winner under 45% of the points: the sides look swapped, the page is not used
    assert ER.tl_box(stats(P1, P2), 2)[0] is None
    assert ER.tl_box([s for s in stats(P1, P2) if s["name"] != "Aces"], 1)[0] is None


def test_service_games_from_the_score_and_the_first_server():
    assert ER.service_games("6-4 6-4", True) == (10, 10)
    assert ER.service_games("6-3", True) == (5, 4) and ER.service_games("6-3", False) == (4, 5)
    # a tiebreak takes its turn but is no service game: 6 each, then the next set opens with the other server
    assert ER.service_games("7-6(4) 6-4", True) == (11, 11)
    assert ER.service_games("7-6(4) 6-3", True) == (10, 11) and ER.service_games("7-6(4) 6-3", False) == (11, 10)
    assert ER.service_games("6-3 2-0 RET", True) == (6, 5)
    box, note = ER.tl_box(stats(P1, P2), 1, first_server_index=0, score="6-4 6-4")
    assert (box["w_SvGms"], box["l_SvGms"]) == ("10", "10") and note == "TennisLive match page"
    box, _ = ER.tl_box(stats(P2, P1), 2, first_server_index=0, score="6-3")        # the loser listed first, served
    assert (box["w_SvGms"], box["l_SvGms"]) == ("4", "5")
    # no first server: the "Service games won" line, only when its games are the score's (Ibragimova v Saigo,
    # Guangzhou 2026 Q1: 14 + 13 for 3-6 6-2 6-4; Machac v Moutet, Vienna 2026 Q1: 7 + 6 for 6-4 6-4, not used)
    line = lambda a, b: [{"period": "match", "name": "Service games won", "player1_detail": a, "player2_detail": b,  # noqa: E731
                          "player1_value": None, "player2_value": None}]
    box, note = ER.tl_box(stats(P1, P2) + line("9/14", "7/13"), 1, None, "3-6 6-2 6-4")
    assert (box["w_SvGms"], box["l_SvGms"]) == ("14", "13") and note == "TennisLive match page"
    box, note = ER.tl_box(stats(P1, P2) + line("7/7", "4/6"), 1, None, "6-4 6-4")
    assert box["w_SvGms"] == "" and "service games unknown" in note


PAGE = (ROOT / "data" / "raw" / "point_sources" / "tennislive" / "matches" / "atp"
        / "tomas-machac-VS-corentin-moutet" / "erste-bank-open-vienna-2026.html.gz")


@pytest.mark.skipif(not PAGE.exists(), reason="the Vienna 2026 Q1 page is not on disk")
def test_a_real_page():
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import tennislive as TL
    parsed = TL.parse_match_page(PS.read_bytes(PAGE).decode("utf-8", errors="replace"))
    pw = 2 if str(parsed["meta"]["winner_id"]) == str(parsed["meta"]["player2_id"]) else 1
    box, note = ER.tl_box(parsed["statistics"], pw)
    assert box is not None, note
    assert int(box["w_svpt"]) == int(box["w_1stWon"]) + int(box["w_2ndWon"]) + (
        int(box["w_svpt"]) - int(box["w_1stWon"]) - int(box["w_2ndWon"]))      # parsed as numbers
    assert int(box["w_1stIn"]) <= int(box["w_svpt"]) and int(box["l_1stIn"]) <= int(box["l_svpt"])


def results(*matches) -> pd.DataFrame:
    return pd.DataFrame([{"draw": "qualifying", "discipline": "singles", "round": r, "player1_name": a,
                          "player2_name": b, "winner_side": w, "played": "TRUE" if p else "FALSE",
                          "state": "finished" if p else "walkover"} for r, a, b, w, p in matches])


def test_a_players_earlier_wins():
    rows = results(("Q1", "Tomas Machac", "Corentin Moutet", 1, True), ("Q1", "Vit Kopriva", "Lukas Neumayer", 2, True),
                   ("Q2", "Tomas Machac", "Fabian Marozsan", 1, True))
    w = Q.earlier_wins(rows, Q.player_keys("Tomas Machac"), "Q2")
    assert list(w["round"]) == ["Q1"] and list(w["_side"]) == [1]           # the round asked is not an earlier one
    w = Q.earlier_wins(rows, Q.player_keys("Lukas Neumayer"), "Q2")
    assert list(w["_side"]) == [2]                                           # a win listed second
    assert Q.earlier_wins(rows, Q.player_keys("Corentin Moutet"), "Q2").empty    # a loss is no win
    assert Q.earlier_wins(rows, Q.player_keys("Tomas Machac"), "Q1").empty
    assert Q.earlier_wins(pd.DataFrame(), Q.player_keys("Tomas Machac"), "Q2").empty


def test_stage0_keeps_a_played_row_until_its_source_publishes_it():
    from src.eda.predictability_diagnostic import stage0_build as B

    def frame(rows):
        return pd.DataFrame(rows, columns=["group", "live_role", "tour", "tid", "round", "pair", "rid"])
    q1 = ("atp", "2026-337", "Q1", "a|b")
    alone = frame([("live", "played", *q1, 1), ("live", "live", "atp", "2026-337", "Q2", "a|c", 2)])
    out = B.drop_replaced(alone, {})
    assert list(out["rid"]) == [1, 2]                                        # nothing published: the fill stays
    published = frame([("atp_qualifying", None, *q1, 0), ("live", "played", *q1, 1)])
    out = B.drop_replaced(published, {})
    assert list(out["rid"]) == [0]                                           # the source's row wins
    # a replay that names the source's row to leave out keeps the fill in its place
    replay = frame([("atp_qualifying", None, *q1, 0), ("live", "drop", *q1, 1), ("live", "played", *q1, 2)])
    out = B.drop_replaced(replay, {})
    assert list(out["rid"]) == [2]
    # without played rows, as before: a live row replaces its played match
    before = frame([("atp_qualifying", None, *q1, 0), ("live", "live", *q1, 1)])
    assert list(B.drop_replaced(before, {})["rid"]) == [1]


def test_the_timeline_pins_an_earlier_round_as_a_live_match(monkeypatch, tmp_path):
    """inject.pin: an earlier round Stage 0 holds takes its tour's window around its day, as a live match does, and the
    live matches' windows are measured as without it (before their own first day)."""
    from src.eda.match_timing import common as MTC
    from src.eda.prediction_run import inject as INJ
    epoch = pd.Timestamp("1970-01-01")
    day = lambda s: float((pd.Timestamp(s) - epoch).days)                     # noqa: E731
    rows, tm = [], []
    for i in range(120):                                                      # dated main-draw matches before the day
        for tour, before in (("atp", 0.0), ("wta", 1.0)):
            mid = f"{tour}|2026-9|R32|{i}|x"
            d = pd.Timestamp("2026-10-20") - pd.Timedelta(days=i % 40)
            rows.append(dict(match_id=mid, level="T250", qualifying=False, tournament_date=d))
            tm.append(dict(match_id=mid, tour=tour, exact=True, obs=day(d), es=day(d) - before, lf=day(d),
                           width_days=before))
    live, q1, gone = "atp|2026-337|Q2|a|b", "atp|2026-337|Q1|a|c", "atp|2026-337|Q1|b|d"
    for mid, tour in ((live, "atp"), (q1, "atp")):
        rows.append(dict(match_id=mid, level="T500", qualifying=True, tournament_date=pd.Timestamp("2026-10-26")))
        tm.append(dict(match_id=mid, tour=tour, exact=False, obs=day("2026-10-26"), es=day("2026-10-18"),
                       lf=day("2026-10-27"), width_days=9.0))
    pd.DataFrame(rows).to_parquet(tmp_path / "stage0_matches.parquet")
    (tmp_path / "mt").mkdir()
    pd.DataFrame(tm).to_parquet(tmp_path / "mt" / "timing.parquet")
    pd.DataFrame([dict(match_id=q1, day="2026-10-24", venue="Vienna", tour="atp"),          # held: pinned
                  dict(match_id=gone, day="2026-10-24", venue="Vienna", tour="atp")]        # not held: skipped
                 ).to_parquet(tmp_path / "played_meta.parquet")
    monkeypatch.setattr(MTC, "OUT", tmp_path / "mt")
    monkeypatch.setattr(INJ.C, "MATCHES", tmp_path / "stage0_matches.parquet")
    monkeypatch.setattr(INJ, "PLAYED", tmp_path / "played_meta.parquet")
    meta = pd.DataFrame([dict(match_id=live, day="2026-10-25", venue="Vienna", tour="atp")])
    out = INJ.pin(meta)
    assert out["pinned"] == 2 and out["earlier_rounds_pinned"] == 1 and out["days_before"]["atp"] == 0.0
    t = pd.read_parquet(tmp_path / "mt" / "timing.parquet").set_index("match_id")
    assert (t.loc[q1, "es"], t.loc[q1, "lf"]) == (day("2026-10-24"), day("2026-10-24"))
    assert (t.loc[live, "es"], t.loc[live, "lf"]) == (day("2026-10-25"), day("2026-10-25"))
    assert t.loc[q1, "lf"] + 1 <= t.loc[live, "es"]                           # its result counts for the round 2


def test_data_check_reads_the_sidecar(tmp_path):
    """The 22 Oct test's tables (atp:4 has no Q1 row in Stage 0), now with atp:4's Q1 in the CSV's sidecar."""
    from src.pipeline import readiness as DCK
    s0 = tmp_path / "stage0"
    s0.mkdir()
    lf = (pd.Timestamp("2026-10-17") - pd.Timestamp("1970-01-01")).days
    matches, players, timing = [], [], []
    for pid, opp in (("atp:1", "atp:91"), ("atp:2", "atp:92"), ("atp:3", "atp:93")):
        mid = f"atp|2026-9410|Q1|{pid}|{opp}"
        matches.append(dict(match_id=mid, tour="atp", year=2026, level="T250", qualifying=True, round="Q1",
                            round_order=1, tournament_id="2026-9410", tournament_name="Almaty",
                            tournament_date=pd.Timestamp("2026-10-20"), status="completed", has_box=True,
                            box_status="full", source="tml"))
        players += [dict(match_id=mid, player_id=pid, player_name=pid, entry=None),
                    dict(match_id=mid, player_id=opp, player_name=opp, entry=None)]
        timing.append(dict(match_id=mid, lf=lf))
    other = "atp|2026-1|R32|atp:4|atp:94"
    matches.append(dict(match_id=other, tour="atp", year=2026, level="T250", qualifying=False, round="R32",
                        round_order=13, tournament_id="2026-1", tournament_name="Elsewhere",
                        tournament_date=pd.Timestamp("2026-10-05"), status="completed", has_box=True, box_status="full",
                        source="tml"))
    players += [dict(match_id=other, player_id="atp:4", player_name="atp:4", entry=None),
                dict(match_id=other, player_id="atp:94", player_name="atp:94", entry=None)]
    timing.append(dict(match_id=other, lf=lf - 10))
    pd.DataFrame(matches).to_parquet(s0 / "stage0_matches.parquet")
    pd.DataFrame(players).to_parquet(s0 / "stage0_match_players.parquet")
    pd.DataFrame(timing).to_parquet(tmp_path / "timing.parquet")
    mu = pd.DataFrame([dict(tour="atp", tourney_id="2026-9410", round="Q2", player_a="atp:3", player_b="atp:4",
                            day="2026-10-18", tourney_name="Almaty", start_utc="2026-10-18T06:00:00Z",
                            stage0_id_a="atp:3", stage0_id_b="atp:4")])
    mu.to_csv(tmp_path / "matchups.csv", index=False)

    def check(svpt):
        pd.DataFrame([dict(tour="atp", tourney_id="2026-9410", tourney_name="Almaty", round="Q1", winner_name="atp:4",
                           loser_name="atp:95", score="6-4 6-4", day="2026-10-17", w_svpt=svpt,
                           box_note="TennisLive match page" if svpt else "no match page")]).to_csv(
            ER.sidecar(tmp_path / "matchups.csv"), index=False)
        out = DCK.data_check(tmp_path / "matchups.csv", stage0=s0, timing=tmp_path / "timing.parquet", held=set(),
                             packages=False, now=dt.datetime(2026, 10, 18, 2, 0, tzinfo=dt.timezone.utc), write=False,
                             show=False)
        return out.iloc[0]
    r = check("60")
    assert r["Verdict"] == "ready" and "from TennisLive with its box score" in r["Noted only"]
    r = check("")
    assert r["Verdict"] == "needs a 1-point edge" and "without a box score" in r["Why"]


def _tml_row(winner, loser, score, box: bool, row: int) -> dict:
    """A staged Tennis My Life qualifying row (live_rows.staged_tml's columns that matter here)."""
    r = {"tour": "atp", "tourney_id": "2026-337", "tourney_name": "Vienna", "round": "Q1", "winner_name": winner,
         "loser_name": loser, "score": score, "winner_id": "W1", "loser_id": "L1", "_source_file": "q.csv", "_row": row}
    for p in ("w", "l"):
        for c in ER.BOX_TML:
            r[f"{p}_{c}"] = "5" if box else ""
    return r


def test_a_published_round_without_a_box_score_takes_tennislives():
    """24 Oct 2026: Tennis My Life posted Vienna's round 1 as results only after the linker had written the sidecar;
    its row stands and takes TennisLive's box score as an override (prediction_run/run.tml_box_fills)."""
    from pathlib import Path as _P
    import tempfile
    from src.eda.prediction_run import run as RUN
    raw = pd.DataFrame([_tml_row("Tomas Machac", "Corentin Moutet", "6-4 6-4", False, 1),
                        _tml_row("Lukas Neumayer", "Vit Kopriva", "6-4 6-3", True, 2),
                        _tml_row("Alex Molcan", "Hamad Medjedovic", "6-2 6-4", False, 3)])
    raw["_row"] = raw["_row"].astype("Int64")
    ev = dict(tournament_id="2026-337", round="Q1")   # the match found by its event, round and players (28 Oct 2026)
    m = pd.DataFrame([dict(match_id="atp|2026-337|Q1|atp:1|atp:2", tour="atp", source="tml", has_box=False,
                           player_a_id="atp:1", player_b_id="atp:2", a_won=True, source_file="q.csv", source_row=1, **ev),
                      dict(match_id="atp|2026-337|Q1|atp:3|atp:4", tour="atp", source="tml", has_box=True,
                           player_a_id="atp:3", player_b_id="atp:4", a_won=True, source_file="q.csv", source_row=2, **ev),
                      dict(match_id="atp|2026-337|Q1|atp:5|atp:6", tour="atp", source="tml", has_box=False,
                           player_a_id="atp:5", player_b_id="atp:6", a_won=False, source_file="q.csv", source_row=3,
                           **ev)])
    keyed = pd.DataFrame([dict(tour="atp", player_id=f"atp:{i}", key=Q.name_key(n)) for i, n in
                          enumerate(["Tomas Machac", "Corentin Moutet", "Lukas Neumayer", "Vit Kopriva", "Alex Molcan",
                                     "Hamad Medjedovic"], 1)])
    box = {f"{p}_{c}": ("" if c == "SvGms" else "7") for p in ("w", "l") for c in ER.BOX_TML}
    earlier = pd.DataFrame([dict(tour="atp", tourney_id="2026-337", tourney_name="Vienna", round="Q1",
                                 winner_name=w, loser_name=lo, score=s, tl_url=f"/atp/match/{i}/", **box)
                            for i, (w, lo, s) in enumerate([("Tomas Machac", "Corentin Moutet", "6-4 6-4"),
                                                            ("Lukas Neumayer", "Vit Kopriva", "6-4 6-3"),
                                                            ("Alex Molcan", "Hamad Medjedovic", "6-2 6-4")])])
    with tempfile.TemporaryDirectory() as d:
        m.to_parquet(_P(d) / "stage0_matches.parquet")
        over, rest, notes = RUN.tml_box_fills(earlier, raw, _P(d), keyed, lambda e: "2026-337")
    assert len(over) == 1 and over.iloc[0]["winner_key"] == Q.name_key("Tomas Machac")      # results only: boxed
    assert over.iloc[0]["w_svpt"] == "7" and over.iloc[0]["box_source"] == "tennislive_live"
    outcomes = [n["outcome"] for n in notes]
    assert any("with a box score" in o for o in outcomes)                    # Tennis My Life's own box score stands
    assert any("not as TennisLive reads it" in o for o in outcomes)          # the two disagree on the winner: none
    assert rest.empty                                                         # nothing left to fill as a played row


class _NoPages:
    stopped = None

    def page(self, url):
        return None


class _Ctx:
    def tennislive(self):
        return _NoPages()


def test_the_linker_keeps_a_round_tennis_my_life_holds_without_a_box_score():
    from src.pipeline import live as L
    rows = results(("Q1", "Tomas Machac", "Corentin Moutet", 1, True)).assign(
        player1_sets="6 6", player2_sets="4 4", end_reason=None, url="/atp/match/x/", match_id="m1",
        start_utc="2026-10-24 09:00", finished_at=0, observed_finished_at=0)
    stage0 = pd.DataFrame([dict(player_id="atp:2", player_name="Corentin Moutet", key=Q.name_key("Corentin Moutet"))])
    held = lambda svpt: pd.DataFrame([dict(round="Q1", _wk=Q.name_key("Tomas Machac"), _lk=Q.name_key("Corentin Moutet"),  # noqa: E731
                                           w_svpt=svpt)])
    args = dict(rnd="Q2", players=[("Tomas Machac", Q.player_keys("Tomas Machac"))], tour="atp", tid="2026-337",
                name="Vienna", stage0=stage0, tour_rows=pd.DataFrame(columns=["winner_name", "loser_name", "_wk", "_lk"]),
                aliases={}, ctx=_Ctx(), level="500", prev=None, built=None, main="20261026")
    out, _ = L._earlier(rows, event_rows=held("64"), **args)
    assert out == []                                                          # held with its box score: skipped
    out, _ = L._earlier(rows, event_rows=held(""), **args)
    assert len(out) == 1 and out[0]["score"] == "6-4 6-4"                     # results only: kept for its box score
    assert out[0]["best_of"] == 3                                             # always written: never the main draw's


def test_a_main_draw_players_qualifying_matches():
    """25 Oct 2026: before a main-draw round every qualifying round is earlier, and a lucky loser's lost round counts
    when losses are asked for."""
    rows = results(("Q1", "Jan Choinski", "Dalibor Svrcina", 1, True), ("Q2", "Jan Choinski", "Hugo Gaston", 2, True),
                   ("Q1", "Hugo Gaston", "Ugo Blanchet", 1, True), ("Q3", "Some One", "Other Two", 1, False))
    rows.loc[3, "state"] = "live"                                            # under way, not a walkover
    w = Q.earlier_matches(rows, Q.player_keys("Jan Choinski"), "R32")
    assert list(w["round"]) == ["Q1"] and list(w["_won"]) == [True]          # his lost Q2: not without losses
    w = Q.earlier_matches(rows, Q.player_keys("Jan Choinski"), "R32", losses=True)
    assert list(w["round"]) == ["Q1", "Q2"] and list(w["_won"]) == [True, False] and list(w["_side"]) == [1, 1]
    w = Q.earlier_matches(rows, Q.player_keys("Hugo Gaston"), "R32", losses=True)
    assert list(w["round"]) == ["Q2", "Q1"] and all(w["_won"])               # a qualifier: both wins
    assert Q.earlier_matches(rows, Q.player_keys("Some One"), "R32", losses=True).empty     # not finished
    assert Q.earlier_matches(rows, Q.player_keys("Jan Choinski"), "Q2", losses=True)["round"].tolist() == ["Q1"]


def _match_rows(*matches) -> pd.DataFrame:
    """TennisLive results rows with the columns _earlier reads."""
    return results(*[(r, a, b, w, True) for r, a, b, w in matches]).assign(
        player1_sets="6 6", player2_sets="4 4", end_reason=None, start_utc="2026-10-25 09:00", finished_at=0,
        observed_finished_at=0, url=[f"/atp/match/{i}/" for i in range(len(matches))],
        match_id=[f"m{i}" for i in range(len(matches))])


def _keys(*names) -> pd.DataFrame:
    return pd.DataFrame([dict(player_id=f"atp:{i}", player_name=n, key=Q.name_key(n)) for i, n in enumerate(names, 1)])


def test_the_linker_fills_a_lucky_losers_lost_round():
    from src.pipeline import live as L
    rows = _match_rows(("Q1", "Jan Choinski", "Dalibor Svrcina", 1), ("Q2", "Hugo Gaston", "Jan Choinski", 1))
    out, notes = L._earlier(rows, "R32", [("Jan Choinski", Q.player_keys("Jan Choinski"))],
                            pd.DataFrame(columns=["round", "_wk", "_lk", "w_svpt"]), "atp", "2026-337", "Vienna",
                            _keys("Jan Choinski", "Dalibor Svrcina", "Hugo Gaston"),
                            pd.DataFrame(columns=["winner_name", "loser_name", "_wk", "_lk"]), {}, _Ctx(), "500", None,
                            None, None, losses=True)
    assert notes == [] and [(o["round"], o["winner_name"], o["loser_name"]) for o in out] == [
        ("Q1", "Jan Choinski", "Dalibor Svrcina"), ("Q2", "Hugo Gaston", "Jan Choinski")]
    assert out[1]["score"] == "6-4 6-4" and out[1]["winner_tl"] == "Hugo Gaston"   # the winner's games first
    assert all(o["best_of"] == 3 and not o.get("event_main_date") for o in out)
    # the lost round is skipped when Tennis My Life holds it with its box score
    held = pd.DataFrame([dict(round="Q2", _wk=Q.name_key("Hugo Gaston"), _lk=Q.name_key("Jan Choinski"), w_svpt="70")])
    out, _ = L._earlier(rows, "R32", [("Jan Choinski", Q.player_keys("Jan Choinski"))], held, "atp", "2026-337",
                        "Vienna", _keys("Jan Choinski", "Dalibor Svrcina", "Hugo Gaston"),
                        pd.DataFrame(columns=["winner_name", "loser_name", "_wk", "_lk"]), {}, _Ctx(), "500", None,
                        None, None, losses=True)
    assert [o["round"] for o in out] == ["Q1"]


def test_tennislives_spellings_of_a_stage0_name():
    """TennisLive adds given names and joins or splits them (Shanghai and Beijing 2026 qualifying); the linker takes
    such a spelling only when exactly one Stage 0 player fits it."""
    from src.pipeline import live as L
    assert ER.same_player("Chak Lam Coleman Wong", "Coleman Wong")
    assert ER.same_player("Jodie Anna Burrage", "Jodie Burrage")
    assert ER.same_player("Seongchan Hong", "Seong Chan Hong")
    assert not ER.same_player("Billy Harris", "Lloyd Harris")
    assert not ER.same_player("Harris", "Lloyd Harris")                     # one word never stands for a name
    stage0 = _keys("Coleman Wong", "Seong Chan Hong", "Lloyd Harris", "Billy Harris")
    none = pd.DataFrame(columns=["winner_name", "loser_name", "_wk", "_lk"])
    assert L._tl_player("Chak Lam Coleman Wong", "atp", stage0, none, {})[:2] == ("Coleman Wong", "atp:1")
    assert L._tl_player("Seongchan Hong", "atp", stage0, none, {})[:2] == ("Seong Chan Hong", "atp:2")
    assert L._tl_player("Lloyd George Muirhead Harris", "atp", stage0, none, {})[:2] == ("Lloyd Harris", "atp:3")
    # two Stage 0 players fit: unknown, as before
    two = _keys("Mary Smith", "Ann Smith")
    assert L._tl_player("Mary Ann Smith", "wta", two, none, {})[0] is None


class _Live:
    """TennisLive for _qualifiers: one event, its results, no match page."""
    stopped = None

    def __init__(self, rows):
        self.rows = rows

    def event(self, tour, name, day):
        return {"key": "vienna"}, ""

    def results(self, ev):
        return self.rows

    def page(self, url):
        return None


class _MainCtx:
    def __init__(self, rows):
        self.tl = _Live(rows)

    def tennislive(self):
        return self.tl

    def previous(self, tml, tour, event, day):
        return None, "none"


def test_the_linker_adds_a_main_draw_qualifiers_rounds():
    """A main-draw match (live._qualifiers): the qualifier's rounds Tennis My Life lacks, found under the main draw's id
    or the event's name; his direct-entry opponent gives none."""
    from src.pipeline import live as L
    rows = _match_rows(("Q1", "Jan Choinski", "Dalibor Svrcina", 1), ("Q2", "Jan Choinski", "Hugo Gaston", 1),
                       ("Q1", "Hugo Gaston", "Ugo Blanchet", 1))
    tml = pd.DataFrame([dict(tour="atp", round="Q1", tourney_name="Vienna", _date=pd.Timestamp("2026-10-26"),
                             _tid="2026-337", winner_name="Jan Choinski", loser_name="Dalibor Svrcina",
                             _wk=Q.name_key("Jan Choinski"), _lk=Q.name_key("Dalibor Svrcina"), w_svpt="61")])
    ev = pd.Series(dict(_tid="2026-337", tourney_name="Vienna", tourney_level="500", last=pd.Timestamp("2026-10-26")))
    r = pd.Series(dict(tour="atp", event="Vienna", home="Jan Choinski", away="Alexander Zverev"))
    rec = {"round": "R32"}
    notes = L._qualifiers(rec, r, ev, "Jan Choinski", "Alexander Zverev", tml,
                          _keys("Jan Choinski", "Dalibor Svrcina", "Hugo Gaston", "Alexander Zverev"), {},
                          pd.Timestamp("2026-10-26 10:00", tz="Europe/London"), _MainCtx(rows))
    assert [(e["round"], e["loser_name"]) for e in rec["earlier"]] == [("Q2", "Hugo Gaston")]   # Q1 held with its box
    assert "1 qualifying round(s) of its qualifiers from TennisLive" in notes[0]
    assert "event_main_date" not in rec                                       # no main-draw match on TennisLive yet
    begun = pd.concat([rows, rows.iloc[[0]].assign(draw="main", round="R32", start_utc="2026-10-26 10:00")])
    rec = {"round": "R32"}
    L._qualifiers(rec, r, ev, "Jan Choinski", "Alexander Zverev", tml,
                  _keys("Jan Choinski", "Dalibor Svrcina", "Hugo Gaston", "Alexander Zverev"), {},
                  pd.Timestamp("2026-10-27 10:00", tz="Europe/London"), _MainCtx(begun))
    assert rec["event_main_date"] == "20261026" and len(rec["earlier"]) == 1    # the main draw's first day (27 Oct)
    rec = {"round": "R32"}                                                    # nothing finished yet: the listed start
    listed = pd.Series({**r.to_dict(), "start_utc": "2026-10-27T11:00:00+00:00"})
    L._qualifiers(rec, listed, ev, "Jan Choinski", "Alexander Zverev", tml,
                  _keys("Jan Choinski", "Dalibor Svrcina", "Hugo Gaston", "Alexander Zverev"), {},
                  pd.Timestamp("2026-10-27 10:00", tz="Europe/London"), _MainCtx(rows))
    assert rec["event_main_date"] == "20261027"
    gone = _MainCtx(None)                                                    # TennisLive did not answer: said so
    rec = {"round": "R32"}
    notes = L._qualifiers(rec, r, ev, "Jan Choinski", "Alexander Zverev", tml, _keys("Jan Choinski"), {},
                          pd.Timestamp("2026-10-26 10:00", tz="Europe/London"), gone)
    assert "earlier" not in rec and "event_main_date" not in rec and notes[0].startswith("qualifiers' rounds not checked")


def test_the_main_draw_first_day_on_tennislive():
    """27 Oct 2026: a main-draw match's event date (live_rows.main_draw_date) can take TennisLive's first main-draw
    day, read as Tennis My Life dates a match: by its local day (Auckland's Monday 11:00 is Sunday 22:00 UTC)."""
    def rows(*starts, draw="main"):
        return pd.DataFrame([{"draw": draw, "discipline": "singles", "start_utc": s} for s in starts])
    brussels = {"name": "European Open - Brussels", "country": "Belgium"}
    assert Q.main_draw_first_day(rows("2026-10-20T09:00:00Z", "2026-10-19T10:10:00Z"), brussels) == "20261019"
    auckland = {"name": "ASB Classic - Auckland", "country": "New Zealand"}
    assert Q.main_draw_first_day(rows("2026-01-11T22:00:00Z"), auckland) == "20260112"
    assert Q.main_draw_first_day(rows("2026-01-11T22:00:00Z"), {}) == "20260111"          # no zone: the UK day
    assert Q.venue_zone({"name": "Adelaide International", "country": "Australia"}, "Adelaide") == "Australia/Adelaide"
    assert Q.venue_zone({"name": "Australian Open", "country": "Australia"}) is None      # several zones, no city
    assert Q.main_draw_first_day(rows("2026-10-18T09:10:00Z", draw="qualifying"), brussels) is None
    assert Q.main_draw_first_day(None) is None and Q.main_draw_first_day(pd.DataFrame()) is None
    # before a main-draw match has finished: the listed match's own start, in the venue's zone
    assert Q.main_draw_first_day(rows(draw="qualifying"), auckland, None, "2026-01-11T22:00:00+00:00") == "20260112"
    assert Q.main_draw_first_day(rows("2026-10-19T10:10:00Z"), brussels, None, "2026-10-21T09:00:00Z") == "20261019"


def test_data_check_lets_a_main_draw_qualifier_through_with_the_sidecar(tmp_path):
    """A round 2 whose player entered through qualifying (his round-1 row says Q) and Stage 0 holds none of his
    qualifying: blocked, unless the CSV's sidecar holds his qualifying rounds."""
    from src.pipeline import readiness as DCK
    s0 = tmp_path / "stage0"
    s0.mkdir()
    lf = (pd.Timestamp("2026-10-26") - pd.Timestamp("1970-01-01")).days
    r1 = "atp|2026-337|R32|atp:1|atp:9"
    pd.DataFrame([dict(match_id=r1, tour="atp", year=2026, level="T500", qualifying=False, round="R32", round_order=13,
                       tournament_id="2026-337", tournament_name="Vienna", tournament_date=pd.Timestamp("2026-10-26"),
                       status="completed", has_box=True, box_status="full", source="tml")]).to_parquet(
        s0 / "stage0_matches.parquet")
    pd.DataFrame([dict(match_id=r1, player_id="atp:1", player_name="atp:1", entry="Q"),
                  dict(match_id=r1, player_id="atp:9", player_name="atp:9", entry=None)]).to_parquet(
        s0 / "stage0_match_players.parquet")
    pd.DataFrame([dict(match_id=r1, lf=lf)]).to_parquet(tmp_path / "timing.parquet")
    pd.DataFrame([dict(tour="atp", tourney_id="2026-337", round="R16", player_a="atp:1", player_b="atp:9",
                       day="2026-10-28", tourney_name="Vienna", start_utc="2026-10-28T10:00:00Z", stage0_id_a="atp:1",
                       stage0_id_b="atp:9")]).to_csv(tmp_path / "matchups.csv", index=False)

    def check(side_rows):
        pd.DataFrame(side_rows, columns=["tour", "tourney_id", "tourney_name", "round", "winner_name", "loser_name",
                                         "score", "day", "w_svpt", "box_note"]).to_csv(
            ER.sidecar(tmp_path / "matchups.csv"), index=False)
        return DCK.data_check(tmp_path / "matchups.csv", stage0=s0, timing=tmp_path / "timing.parquet", held=set(),
                              packages=False, now=dt.datetime(2026, 10, 28, 2, 0, tzinfo=dt.timezone.utc),
                              write=False, show=False).iloc[0]
    out = check([])
    assert out["Verdict"] == "will be blocked" and "came through qualifying" in out["Why"]
    out = check([("atp", "2026-337", "Vienna", "Q1", "atp:1", "atp:31", "6-4 6-4", "2026-10-24", "60", "page"),
                 ("atp", "2026-337", "Vienna", "Q2", "atp:1", "atp:32", "6-4 6-4", "2026-10-25", "", "no page")])
    assert out["Verdict"] == "ready" and "2 round(s), 1 with a box score" in out["Noted only"]
