"""Tour-level qualifying in the bet-day path (the owner's decision of 22 Oct 2026, docs/decisions/2026-10-22-qualifying-
bets.md; master pipeline process log, Part 8). Offline: no request (TennisLive is replaced by a stand-in), no build.

    * the round from TennisLive's results and from Tennis My Life's rows (src/pipeline/qualifying.py);
    * the main draw's start, the previous edition and the event built from it;
    * the matchups CSV's event columns as the live rows read them back (prediction_run/live_rows.py);
    * the gate's and the data check's rule for a round whose round before is missing;
    * the linker on Pinnacle's pull of 16 Oct 2026 22:58 UTC, with Tennis My Life cut back to what it held then.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import live as L  # noqa: E402
from src.pipeline import qualifying as Q  # noqa: E402

PULL_1016 = ROOT / "data" / "dump" / "odds" / "pinnacle" / "pulls" / "2026-10-16" / "225800Z.parquet"


def results(*matches) -> pd.DataFrame:
    """TennisLive results rows: (round, player1, player2, winner side, played)."""
    return pd.DataFrame([{"draw": "qualifying", "discipline": "singles", "round": r, "player1_name": a,
                          "player2_name": b, "winner_side": w, "played": "TRUE" if p else "FALSE",
                          "state": "finished" if p else "walkover"} for r, a, b, w, p in matches],
                        columns=["draw", "discipline", "round", "player1_name", "player2_name", "winner_side",
                                 "played", "state"])


def keys(name):
    return Q.player_keys(name)


def test_round_from_tennislive_results():
    names = ("Adam Walton", "Nikoloz Basilashvili")
    a, b = keys(names[0]), keys(names[1])
    assert Q.round_from_results(results(), a, b, names)[0] == "Q1"                       # nothing played yet
    q1 = results(("Q1", "Adam Walton", "Beibit Zhukayev", 1, True),
                 ("Q1", "Nikoloz Basilashvili", "Taro Daniel", 1, True))
    assert Q.round_from_results(q1, a, b, names) == ("Q2", "both players won Q1 on TennisLive")
    # a player out, the match already played, one player ahead of the other
    lost = results(("Q1", "Beibit Zhukayev", "Adam Walton", 1, True), ("Q1", "Nikoloz Basilashvili", "Taro Daniel", 1, True))
    assert Q.round_from_results(lost, a, b, names)[0] is None
    assert "already lost" in Q.round_from_results(lost, a, b, names)[1]
    played = results(("Q2", "Nikoloz Basilashvili", "Adam Walton", 1, True))
    assert "already played" in Q.round_from_results(played, a, b, names)[1]
    ahead = results(("Q1", "Adam Walton", "Beibit Zhukayev", 1, True))
    assert Q.round_from_results(ahead, a, b, names)[0] is None
    # neither has played, but round 1 looks complete, or round 2 has begun: not read as a round 1
    others = results(*[("Q1", f"Aa{i} Bb", f"Cc{i} Dd", 1, True) for i in range(8)])
    assert Q.round_from_results(others, a, b, names, round1_size=8)[0] is None
    assert Q.round_from_results(others, a, b, names, round1_size=12)[0] == "Q1"
    begun = results(("Q2", "Ee Ff", "Gg Hh", 2, True))
    assert Q.round_from_results(begun, a, b, names)[0] is None
    # a walkover advances its winner; a middle name on one side only still matches
    wo = results(("Q1", "Adam Walton", "Beibit Zhukayev", 1, False), ("Q1", "Nikoloz Basilashvili", "Taro Daniel", 1, True))
    assert Q.round_from_results(wo, a, b, names)[0] == "Q2"
    mid = results(("Q1", "Joel Schwaerzler", "Federico Cina", 1, True), ("Q1", "Gauthier Onclin", "Harry Wendelken", 1, True))
    assert Q.round_from_results(mid, keys("Joel Josef Schwaerzler"), keys("Gauthier Onclin"),
                                ("Joel Josef Schwaerzler", "Gauthier Onclin"))[0] == "Q2"
    # the last round of a three-round draw has no round after it
    q3 = results(("Q3", "Adam Walton", "Xx Yy", 1, True), ("Q3", "Nikoloz Basilashvili", "Zz Ww", 1, True))
    assert Q.round_from_results(q3, a, b, names)[0] is None


def test_round_from_tennis_my_life_never_reads_a_round_1():
    rows = pd.DataFrame({"round": ["Q1", "Q1"], "_wk": [L.name_key("Adam Walton"), L.name_key("Nikoloz Basilashvili")],
                         "_lk": [L.name_key("Beibit Zhukayev"), L.name_key("Taro Daniel")]})
    assert Q.round_from_tml(rows, "Adam Walton", "Nikoloz Basilashvili")[0] == "Q2"
    assert Q.round_from_tml(rows.iloc[:0], "Adam Walton", "Nikoloz Basilashvili")[0] is None    # silence: unknown
    assert Q.round_from_tml(rows.iloc[:1], "Adam Walton", "Nikoloz Basilashvili")[0] is None
    assert Q.tml_agrees(rows, "Adam Walton", "Nikoloz Basilashvili", "Q2") is None
    assert "past Q1" in Q.tml_agrees(rows, "Adam Walton", "Nikoloz Basilashvili", "Q1")


def test_main_draw_start():
    ts = pd.Timestamp
    # a weekend qualifying: the next Monday (Almaty 2026: Q1 Saturday 17 Oct; its 2025 edition dated a Monday)
    assert Q.main_draw_start(ts("2026-10-17"), False, ts("2025-10-13")) == ts("2026-10-19")
    assert Q.main_draw_start(ts("2026-10-18"), False, ts("2025-10-13")) == ts("2026-10-19")
    # a Monday and Tuesday qualifying of a Wednesday start (Madrid 2026; its 2025 edition dated a Wednesday)
    assert Q.main_draw_start(ts("2026-04-20"), False, ts("2025-04-23")) == ts("2026-04-22")
    assert Q.main_draw_start(ts("2026-04-21"), False, ts("2025-04-23")) == ts("2026-04-22")
    # a Friday qualifying of a Sunday start (Dubai and Doha)
    assert Q.main_draw_start(ts("2026-02-06"), False, ts("2025-02-09")) == ts("2026-02-08")
    # a Slam: the next week, on its Sunday or Monday start
    assert Q.main_draw_start(ts("2026-08-24"), True, ts("2025-08-24")) == ts("2026-08-30")
    assert Q.main_draw_start(ts("2026-05-18"), True, ts("2025-05-26")) == ts("2026-05-25")
    assert Q.main_draw_start(ts("2026-10-17"), False) == ts("2026-10-19")              # no previous edition: Monday
    assert Q.main_draw_start(ts("2026-10-21"), False, ts("2025-10-13")) == ts("2026-10-21")   # never before the day


def tml_rows(rows) -> pd.DataFrame:
    """Rows as live._tml leaves them (its _tid, _date, _wk, _lk)."""
    t = pd.DataFrame(rows)
    t["_tid"] = t["tourney_id"]
    t["_date"] = pd.to_datetime(t["tourney_date"], format="%Y%m%d")
    t["_wk"], t["_lk"] = t["winner_name"].map(L.name_key), t["loser_name"].map(L.name_key)
    return t


def test_previous_edition_and_the_event_built_from_it():
    base = dict(tour="atp", tourney_name="Almaty", surface="Hard", indoor="I", tourney_level="250", draw_size="28",
                best_of="3", winner_name="Aa Bb", loser_name="Cc Dd")
    tml = tml_rows([{**base, "tourney_id": "2025-9410", "tourney_date": "20251013", "round": r} for r in ("Q1", "R32")]
                   + [{**base, "tourney_id": "2025-9999", "tourney_name": "Almaty Challenger", "tourney_level": "C",
                       "tourney_date": "20251013", "round": "R32"}])
    prev, _ = Q.previous_edition(tml, "atp", "Almaty", pd.Timestamp("2026-10-17"), L.MAIN_TML_LEVELS)
    assert prev["tid"] == "2025-9410" and prev["code"] == "9410" and prev["level"] == "250"
    built = Q.built_event(prev, pd.Timestamp("2026-10-17"))
    assert built["tourney_id"] == "2026-9410" and built["event_indoor"] == "I" and built["event_draw_size"] == 28
    assert built["event_date"] == "20261017"
    # nothing a year earlier, or two editions named alike: no event is built
    assert Q.previous_edition(tml, "atp", "Almaty", pd.Timestamp("2027-12-01"), L.MAIN_TML_LEVELS)[0] is None
    two = tml_rows([{**base, "tourney_id": t, "tourney_date": "20251013", "round": "R32"} for t in ("2025-1", "2025-2")])
    assert Q.previous_edition(two, "atp", "Almaty", pd.Timestamp("2026-10-17"), L.MAIN_TML_LEVELS)[0] is None
    # a men's Slam qualifying round played at best of 5 the year before
    slam = {"best_of": {"Q1": "3", "Q2": "3", "Q3": "5"}}
    assert Q.best_of("atp", "G", "Q3", slam) == 5 and Q.best_of("atp", "G", "Q1", slam) is None
    assert Q.best_of("wta", "G", "Q3", slam) is None and Q.best_of("atp", "250", "Q2", slam) is None


def test_the_csv_event_read_back():
    """A CSV read back gives TML's level "250" as 250.0 beside blank rows; the live rows must give "250" again."""
    from src.eda.prediction_run import live_rows as LR
    row = pd.Series({"tour": "atp", "tourney_id": "2026-9410", "tourney_name": "Almaty", "event_surface": "Hard",
                     "event_draw_size": 28.0, "event_level": 250.0, "event_indoor": "I", "event_date": 20261017.0})
    got = LR.csv_event(row)
    assert got == {"tourney_id": "2026-9410", "tourney_name": "Almaty", "best_of": "3", "surface": "Hard",
                   "draw_size": "28", "tourney_level": "250", "indoor": "I", "tourney_date": "20261017"}
    assert LR.csv_event(pd.Series({"tour": "atp", "tourney_id": "x", "event_surface": np.nan})) is None
    with pytest.raises(SystemExit):                                     # half an event is refused
        LR.csv_event(pd.Series({"tour": "atp", "tourney_id": "x", "tourney_name": "X", "event_surface": "Hard"}))


def test_the_gate_blocks_a_round_whose_round_before_is_missing():
    from src.eda.prediction_run import gate as G
    day = 20380                                                          # days since 1970
    h = pd.DataFrame({"qualifying": [True, False], "round_order": [1, 13], "tournament_id": ["2026-1", "2026-0"],
                      "lf": [day - 1.0, day - 6.0]})
    assert not G.previous_round_missing(h, "2026-1", 2, day)             # Q1 at the event: Q2 may be bet
    assert G.previous_round_missing(h.iloc[1:], "2026-1", 2, day)        # no Q1: blocked
    assert not G.previous_round_missing(h.iloc[1:], "2026-1", 1, day)    # a round 1 has no round before
    # the feed's own id for a women's qualifying: the round before found by its days
    assert not G.previous_round_missing(h.assign(tournament_id=["2026-W-WTAID-1-2026", "2026-0"]), "2026-1", 2, day)
    assert "weekly lower-level feed" in G.previous_round_reason("Ann Bee", "Q2", 2, "wta")


def test_data_check_blocks_a_round_2_without_its_round_1(tmp_path):
    from src.pipeline import readiness as DCK
    s0 = tmp_path / "stage0"
    s0.mkdir()
    lf = (pd.Timestamp("2026-10-17") - pd.Timestamp("1970-01-01")).days
    matches, players, timing = [], [], []
    for pid, opp in (("atp:1", "atp:91"), ("atp:2", "atp:92"), ("atp:3", "atp:93")):     # atp:4 has no Q1 row
        mid = f"atp|2026-9410|Q1|{pid}|{opp}"
        matches.append(dict(match_id=mid, tour="atp", year=2026, level="T250", qualifying=True, round="Q1",
                            round_order=1, tournament_id="2026-9410", tournament_name="Almaty",
                            tournament_date=pd.Timestamp("2026-10-20"), status="completed", has_box=True,
                            box_status="full", source="tml"))
        players += [dict(match_id=mid, player_id=pid, player_name=pid, entry=None),
                    dict(match_id=mid, player_id=opp, player_name=opp, entry=None)]
        timing.append(dict(match_id=mid, lf=lf))
    other = "atp|2026-1|R32|atp:4|atp:94"                                # atp:4's only match: elsewhere, earlier
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
    mu = pd.DataFrame([dict(tour="atp", tourney_id="2026-9410", round=r, player_a=a, player_b=b, day="2026-10-18",
                            tourney_name="Almaty", start_utc="2026-10-18T06:00:00Z", stage0_id_a=a, stage0_id_b=b)
                       for r, a, b in (("Q2", "atp:1", "atp:2"), ("Q2", "atp:3", "atp:4"), ("Q1", "atp:4", "atp:91"))])
    mu.to_csv(tmp_path / "matchups.csv", index=False)
    out = DCK.data_check(tmp_path / "matchups.csv", stage0=s0, timing=tmp_path / "timing.parquet", held=set(),
                         packages=False, now=dt.datetime(2026, 10, 18, 2, 0, tzinfo=dt.timezone.utc), write=False,
                         show=False)
    got = dict(zip(out["Match"], out["Verdict"]))
    assert got == {"atp:1 v atp:2": "ready", "atp:3 v atp:4": "will be blocked", "atp:4 v atp:91": "ready"}
    why = dict(zip(out["Match"], out["Why"]))
    assert "no Q1 match before this Q2" in why["atp:3 v atp:4"] and "atp:4" in why["atp:3 v atp:4"]
    assert out.loc[out["Match"].eq("atp:1 v atp:2"), "Earlier matches checked"].iloc[0] == 2     # the two Q1 matches


class StandIn:
    """TennisLive's stand-in: every event found, and no qualifying result yet (the morning of a round 1)."""
    stopped = None

    def event(self, tour, name, day):
        return {"key": f"{tour}:{name}", "name": name, "url": "/x/"}, ""

    def results(self, ev):
        return results()


@pytest.mark.skipif(not PULL_1016.exists(), reason="no Pinnacle pull of 16 Oct 2026")
def test_the_linker_on_the_16_oct_qualifying(monkeypatch, tmp_path):
    """Pinnacle's pull of 16 Oct 22:58 UTC lists the Q1 of Almaty, Brussels, Ningbo and Osaka (17 Oct). With Tennis My
    Life cut back to what it held then (no row of those editions: Tennis My Life dated their Q1 the 18th), each is
    built from its previous edition, read as round 1, and dated by its main draw's start; the CSV reads back."""
    real = L._tml
    monkeypatch.setattr(L, "_tml", lambda years: (lambda t: t[t["_date"] <= pd.Timestamp("2026-10-16")])(real(years)))
    pull = pd.read_parquet(PULL_1016)
    m = L.todays_matches(pull=pull, hours_ahead=30, now=dt.datetime(2026, 10, 16, 23, 0, tzinfo=dt.timezone.utc),
                         tennislive=StandIn())
    q = m[m["league"].astype(str).str.contains(r"^(?:ATP|WTA) (?:Almaty|Brussels|Ningbo|Osaka) - Qualifiers$")]
    ok = q[q["status"].eq("ok")]
    assert len(q) >= 20 and len(ok) >= 0.8 * len(q)
    assert set(ok["round"]) == {"Q1"}
    assert set(ok.loc[ok["tour"].eq("atp"), "tourney_id"]) <= {"2026-9410", "2026-7485"}
    assert ok["event_from"].astype(str).str.startswith("previous edition").all()
    assert set(ok["event_main_date"]) == {"20261019"}                    # the Monday after the weekend's qualifying
    assert ok["stage0_id_a"].notna().all() or ok["notes"].astype(str).str.contains("new since").any()
    csv = L.build_matchups(m, path=tmp_path / "matchups.csv")
    back = pd.read_csv(csv)
    from src.eda.prediction_run import live_rows as LR
    built = [LR.csv_event(r) for _, r in back.iterrows() if str(r["round"]).startswith("Q")]
    assert built and all(b is not None and b["tourney_level"] in L.MAIN_TML_LEVELS for b in built)
    assert back.loc[back["round"].astype(str).str.startswith("Q"), "event_main_date"].astype(int).eq(20261019).all()
