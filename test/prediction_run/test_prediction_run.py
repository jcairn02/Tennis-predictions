"""Tests of the prediction run (src/eda/prediction_run/; docs/decisions/2026-10-08-prediction-run-box-scores.md), offline:

1. Stage 0 takes live rows only in a prediction run's sandbox or an --out-dir, and a live row replaces the played row of
   the same match (a replay) while "drop" rows leave matches out; nothing else moves.
2. A replay row is the match's own TML row less its outcome, the placeholder won by the player asked for.
3. The WTA API's box score maps to Stage 0's counts with break points read on the returner's side, and a fill is kept
   only when every set's games agree with TML's score.
4. The gate (rule of 14 Oct 2026, docs/decisions/2026-10-14-box-score-gate.md) passes a match whose players' earlier
   matches all have box scores; a missing one of a kind the training rows nearly always hold (main tour, Challenger /
   WTA 125, qualifying above ITF level) sets the 1-point edge bar, one of a kind they mostly lack (team events, ITF) is
   only noted, and neither blocks; a qualifier without qualifying matches, or an unknown indoor input, still blocks.

Run: ./python.sh -m pytest test/prediction_run -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import fills as FL  # noqa: E402
from src.eda.prediction_run import gate as G  # noqa: E402
from src.eda.prediction_run import live_rows as LR  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402


# ------------------------------------------------------------------------------------------------ 1. Stage 0's live rows

def tml_row(tid="2026-321", name="Stuttgart", rnd="R16", w="Anna Alpha", lo="Bea Beta", score="6-3 6-4", **extra):
    row = {c: "" for c in B.KEEP}
    row.update({"tourney_id": tid, "tourney_name": name, "surface": "Grass", "draw_size": "32", "tourney_level": "A",
                "tourney_date": "20260608", "match_num": "1", "score": score, "best_of": "3", "round": rnd,
                "indoor": "O", "winner_name": w, "loser_name": lo, "winner_id": "1", "loser_id": "2",
                "_source_file": "x.csv", "_row": "1"})
    row.update(extra)
    return row


def raw_frame(rows):
    raw = pd.DataFrame(rows).reindex(columns=B.KEEP)
    raw["source"], raw["group"], raw["tour"], raw["file_season"] = "tml", "atp_main", "atp", 2026
    raw["rid"] = np.arange(len(raw), dtype="int64")
    return raw


def test_live_rows_are_refused_in_the_repositorys_stage0(monkeypatch, tmp_path):
    monkeypatch.setattr(B, "SANDBOX_MARKER", tmp_path / "no_marker")
    with pytest.raises(SystemExit, match="sandbox"):
        B.build(live_rows=tmp_path / "live.parquet")


def test_a_live_row_replaces_its_played_row_and_drop_rows_leave_matches_out():
    played = [tml_row(), tml_row(rnd="QF", w="Anna Alpha", lo="Cara Gamma"), tml_row(w="Dana Delta", lo="Eve Eps")]
    live = pd.DataFrame([tml_row(w="Bea Beta", lo="Anna Alpha", score="6-4 6-4"),           # the R16, sides exchanged
                         tml_row(rnd="QF", w="Anna Alpha", lo="Cara Gamma")]).assign(tour="atp")
    live["live_role"] = ["live", "drop"]
    df = B.normalise(B.add_live_rows(raw_frame(played), live))
    summary: dict = {}
    out = B.drop_replaced(df, summary)
    assert summary["live_rows"] == {"rows": 1, "played_rows_replaced": 2, "left_out_by_name": 1}
    kept = set(zip(out["round"], out["winner_name"], out["group"]))
    assert kept == {("R16", "Bea Beta", "live"), ("R16", "Dana Delta", "atp_main")}
    assert "live_role" not in out.columns


def test_upcoming_matches_replace_nothing():
    live = pd.DataFrame([tml_row(rnd="QF", w="Dana Delta", lo="Bea Beta", score="6-4 6-4")]).assign(tour="atp")
    df = B.normalise(B.add_live_rows(raw_frame([tml_row(), tml_row(w="Dana Delta", lo="Eve Eps")]), live))
    summary: dict = {}
    out = B.drop_replaced(df, summary)
    assert summary["live_rows"]["played_rows_replaced"] == 0 and len(out) == 3


def test_a_main_draw_live_row_is_dated_by_its_main_draws_first_date(monkeypatch):
    """25 Oct 2026: Tennis My Life dates each 2026 match by its day, the qualifying's before the main draw's. A live
    main-draw row takes the main draw's first date (Stage 0's C05), not the event's earliest row's: on since 27 Oct 2026
    (the owner), "0" reproduces the rule before. The earliest day known wins: Tennis My Life's file of events under way
    dated Almaty's and Brussels' first main-draw day late from 19 to 22 Oct 2026."""
    raw = pd.DataFrame([tml_row(rnd="Q1", tourney_date="20261017", w="Gil Qual", lo="Hal Quill", match_num="1"),
                        tml_row(rnd="R32", tourney_date="20261019", w="Anna Alpha", lo="Cara Gamma", match_num="2"),
                        tml_row(rnd="R32", tourney_date="20261020", w="Bea Beta", lo="Dana Delta", match_num="3")]
                       ).assign(tour="atp")
    mu = pd.DataFrame([dict(tour="atp", tourney_id="2026-321", tourney_name="Stuttgart", round="R16",
                            player_a="Anna Alpha", player_b="Bea Beta", day="2026-10-21")])
    monkeypatch.delenv(LR.MAIN_DATE_SWITCH, raising=False)
    assert LR.upcoming_rows(mu, raw).iloc[0]["tourney_date"] == "20261019"       # on by default: the main draw's first
    monkeypatch.setenv(LR.MAIN_DATE_SWITCH, "0")
    assert LR.upcoming_rows(mu, raw).iloc[0]["tourney_date"] == "20261017"       # "0": the earliest row, a qualifying one
    monkeypatch.delenv(LR.MAIN_DATE_SWITCH)
    late = raw.assign(tourney_date=["20261017", "20261020", "20261020"])         # the first day read a day late
    assert LR.upcoming_rows(mu, late).iloc[0]["tourney_date"] == "20261020"      # nothing earlier known
    fixed = LR.upcoming_rows(mu.assign(event_main_date="20261019"), late).iloc[0]    # the linker's (TennisLive's) day
    assert fixed["tourney_date"] == "20261019" and "event_main_date" not in fixed.index   # no hint to Stage 0
    assert LR.upcoming_rows(mu.assign(event_main_date="20261020"), raw).iloc[0]["tourney_date"] == "20261019"
    with_first_day = pd.concat([mu, mu.assign(player_a="Gil Qual", player_b="Hal Quill", round="R32", day="2026-10-19")])
    assert list(LR.upcoming_rows(with_first_day, late)["tourney_date"]) == ["20261019", "20261019"]   # a listed day 1
    # a round 1 whose event Tennis My Life holds only the qualifying of: the CSV's earliest main-draw day of the event
    mu1 = pd.DataFrame([dict(tour="atp", tourney_id="2026-321", tourney_name="Stuttgart", round="R32",
                             player_a="Gil Qual", player_b="Hal Quill", day=d) for d in ("2026-10-20", "2026-10-19")])
    assert list(LR.upcoming_rows(mu1, raw.iloc[[0]])["tourney_date"]) == ["20261019", "20261019"]
    # the linker's day, in the venue's zone, stands for a row's own UK day (Auckland's Monday 11:00 is Sunday 22:00 UTC)
    far = mu1.assign(day="2026-01-11", event_main_date="20260112")
    assert list(LR.upcoming_rows(far, raw.iloc[[0]])["tourney_date"]) == ["20260112", "20260112"]
    # a qualifying row keeps the event's own date (its main draw's start comes as event_main_date)
    mq = mu.assign(round="Q2", player_a="Gil Qual", player_b="Hal Quill")
    assert LR.upcoming_rows(mq, raw).iloc[0]["tourney_date"] == "20261017"


# ------------------------------------------------------------------------------------------------ 2. replay rows

def test_a_replay_row_is_the_match_less_its_outcome():
    box = {f"{s}_{c}": "5" for s in ("w", "l") for c in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms",
                                                          "bpSaved", "bpFaced")}
    raw = pd.DataFrame([tml_row(minutes="95", winner_age="24.5", loser_age="30.1", winner_rank="10", loser_rank="40",
                                **box)])
    raw["_row"] = pd.array([1], dtype="Int64")
    target = pd.DataFrame({"match_id": ["atp|2026-321|R16|atp:1|atp:2"], "tour": ["atp"], "source_file": ["x.csv"],
                           "source_row": [1], "player_a_id": ["atp:2"], "player_b_id": ["atp:1"], "a_won": [False]})
    players = pd.DataFrame({"match_id": [target["match_id"][0]] * 2, "player_id": ["atp:1", "atp:2"],
                            "player_name": ["Anna Alpha", "Bea Beta"]})
    rows = LR.replay_rows(target, target.iloc[0:0], raw, players, placeholder_winner="A")    # A is Bea, the loser
    r = rows.iloc[0]
    assert r["winner_name"] == "Bea Beta" and r["loser_name"] == "Anna Alpha"
    assert (r["winner_age"], r["loser_age"], r["winner_rank"], r["loser_rank"]) == ("30.1", "24.5", "40", "10")
    assert r["score"] == "6-4 6-4" and r["minutes"] == "" and all(r[c] == "" for c in LR.BOX)
    assert r["tourney_id"] == "2026-321" and r["live_role"] == "live"


# ------------------------------------------------------------------------------------------------ 3. WTA fills

def test_the_wta_box_score_reads_break_points_on_the_returners_side():
    total = {"acesa": "3", "acesb": "5", "dblflta": "2", "dblfltb": "4", "totservplayeda": "60", "totservplayedb": "70",
             "ptsplayed1stserva": "40", "ptsplayed1stservb": "45", "ptswon1stserva": "30", "ptswon1stservb": "28",
             "ptstotwonserva": "40", "ptstotwonservb": "41", "servgamesplayeda": "9", "servgamesplayedb": "9",
             "breakptsplayeda": "6", "breakptsplayedb": "2", "breakptsconva": "3", "breakptsconvb": "1"}
    a = FL.api_counts(total, "a")
    assert (a["ace"], a["svpt"], a["first_in"], a["first_won"], a["second_won"]) == (3, 60, 40, 30, 10)
    assert (a["bp_faced"], a["bp_saved"]) == (2, 1)       # B's chances on A's serve: 2, converted 1


def test_set_scores_are_compared_from_the_winners_side():
    m = {"ScoreSet1A": "4", "ScoreSet1B": "6", "ScoreSet2A": "7", "ScoreSet2B": "6", "ScoreSet3A": "3", "ScoreSet3B": "6"}
    assert FL.api_games(m, "B") == FL.games("6-4 6-7(5) 6-3")
    assert FL.api_games(m, "A") != FL.games("6-4 6-7(5) 6-3")


# ------------------------------------------------------------------------------------------------ 3a. ATP fills (14 Oct)

def keystats(completed=False, p1="Z355", p2="BK92", sv=("15", "15"), first_won="63/78"):
    """A decrypted keystats object as the ATP Stats Centre sends it (the labels of 2026/5014/MS008)."""
    stats = {"Aces": ("15", "20"), "Double Faults": ("1", "8"), "1st Serve": ("78/101 (77%)", "60/90 (67%)"),
             "1st Serve Points Won": (first_won, "45/60"), "2nd Serve Points Won": ("13/23", "15/30"),
             "Break Points Saved": ("1/3 (33%)", "4/6 (67%)"), "Service Games Played": sv}
    return {"matchCompleted": completed, "players": [{"player1Id": p1, "player1Name": "Alexander Zverev"},
                                                      {"player1Id": p2, "player1Name": "Alexander Bublik"}],
            "setStats": {"set0": [{"name": k, "player1": a, "player2": b} for k, (a, b) in stats.items()]}}


def test_the_atp_box_score_maps_to_stage0s_nine_counts():
    a, b = FL.keystats_counts(keystats(), "Z355"), FL.keystats_counts(keystats(), "BK92")
    assert {k: a[k] for k in FL.COUNTS} == {"ace": 15, "df": 1, "svpt": 101, "first_in": 78, "first_won": 63,
                                            "second_won": 13, "sv_gms": 15, "bp_saved": 1, "bp_faced": 3}
    assert (b["svpt"], b["first_in"], b["bp_faced"]) == (90, 60, 6) and a["consistent"] and b["consistent"]
    assert FL.keystats_counts(keystats(), "XXXX") is None
    assert not FL.keystats_counts(keystats(first_won="63/77"), "Z355")["consistent"]   # 77 != the 78 first serves in


def test_an_atp_file_covers_the_match_by_its_service_games():
    k = {"winner_code": "Z355", "loser_code": "BK92", "tml_score": "3-6 7-5 6-3"}           # 30 games, 15 + 15
    assert FL.covers_match(keystats(completed=False), k)          # the flag reads False on finished matches
    assert not FL.covers_match(keystats(completed=False, sv=("9", "9")), k)                 # a match in progress
    assert FL.covers_match(keystats(completed=False, sv=("18", "18")), {**k, "tml_score": "6-7(4) 7-6(3) 7-6(7)"})
    assert FL.covers_match(keystats(completed=True, sv=("9", "9")), k)


def test_atp_codes_follow_the_bracket():
    assert FL.atp_codes("R32", False) == [f"MS{n:03d}" for n in range(16, 32)]
    assert FL.atp_codes("F", False) == ["MS001"] and FL.atp_codes("QF", False)[0] == "MS004"
    assert FL.atp_codes("Q2", True) == [f"QS{n:03d}" for n in range(1, 64)]


def test_atp_main_draw_gaps_are_fillable_and_the_rest_are_not(tmp_path):
    # the ATP's qualifying keystats count first serves differently from TML's (Shanghai 2026: 9 of 26 rows equal)
    rows = [dict(match_id=f"m{i}", tour=t, level=lv, qualifying=q, source="tml", status="completed", has_box=False,
                 tournament_date=pd.Timestamp("2026-10-10")) for i, (t, lv, q) in enumerate(
        [("atp", "T500", False), ("atp", "T1000", False), ("atp", "CH", False), ("atp", "GS", False),
         ("atp", "TEAM", False), ("wta", "T250", False), ("atp", "T250", True)])]
    (tmp_path / "s0").mkdir()
    pd.DataFrame(rows).to_parquet(tmp_path / "s0" / "stage0_matches.parquet")
    g = FL.gaps(tmp_path / "s0", pd.Timestamp("2026-10-14"), held={"m1"}).set_index("match_id")["class"]
    assert g.to_dict() == {"m0": "fillable", "m1": "held", "m2": "unserved", "m3": "unserved", "m4": "unserved",
                           "m5": "fillable", "m6": "unserved"}


def test_the_atp_fill_links_by_codes_and_keeps_tmls_orientation(tmp_path, monkeypatch):
    from src.eda.serve_speed_tabpfn.live import atp_daily as AD
    held = {"MS019": keystats(p1="AAAA", p2="BBBB", completed=True),               # another match of the round
            "MS020": keystats(p1="BK92", p2="Z355", completed=False)}             # ours, players listed B first
    monkeypatch.setattr(FL, "held_keystats", lambda year, event, code: held.get(code))
    monkeypatch.setattr(AD, "raw_path", lambda year, event, code, route="keystats-api": tmp_path / f"{code}.json.gz")
    (tmp_path / "MS020.json.gz").write_bytes(b"envelope")
    gap = pd.DataFrame([{"match_id": "s0id", "qualifying": False, "tour": "atp"}])
    keys = pd.DataFrame([{"tour": "atp", "tid": "2026-5014", "round": "R32", "winner_key": "zverev a",
                          "loser_key": "bublik a", "winner_name": "Alexander Zverev", "loser_name": "Alexander Bublik",
                          "tml_score": "3-6 7-5 6-3", "stage0_match_id": "s0id", "winner_code": "Z355",
                          "loser_code": "BK92"}])
    fills, notes = FL.fill_atp(gap, keys, max_requests=0, ask=False)
    assert notes == [{"match_id": "s0id", "outcome": "filled", "feed_key": "atp:2026/5014/MS020", "how": "held"}]
    r = fills.iloc[0]
    assert r["box_source"] == "atp_keystats_live" and r["stage0_match_id"] == "s0id"
    # the winner is Zverev, listed second in the file: his counts are the file's player-2 values
    assert (r["w_ace"], r["w_svpt"], r["l_ace"], r["l_svpt"]) == (20, 90, 15, 101)
    assert set(FL.override_table(fills).columns) >= {"w_ace", "l_bpFaced", "box_source"}


# ------------------------------------------------------------------------------------------------ 3b. live windows

def test_a_live_match_takes_its_tours_current_window(tmp_path, monkeypatch):
    """ATP matches dated a day wide until June, exactly since July (as TDI's point logs began): a live match in October
    takes the recent norm (0 days before its day); WTA, with too few recent matches, takes the year's (1)."""
    from src.eda.match_timing import common as MTC
    from src.eda.prediction_run import inject as I
    from src.eda.predictability_diagnostic import common as C

    rows, timing = [], []
    day = lambda s: float((pd.Timestamp(s) - pd.Timestamp("1970-01-01")).days)  # noqa: E731
    for i in range(400):
        tour = "atp" if i < 300 else "wta"              # ATP: two a day back to May (120 in the last 60 days)
        back = i % 150 if tour == "atp" else (i - 300) * 3    # WTA: one every three days (20 in the last 60)
        when = pd.Timestamp("2026-10-07") - pd.Timedelta(days=back)
        gap = 0 if (tour == "atp" and when >= pd.Timestamp("2026-07-01")) else 1
        mid = f"m{i}"
        rows.append({"match_id": mid, "level": "T250", "qualifying": False, "tournament_date": when})
        # the timeline repeats Stage 0's level, qualifying and tournament date, as timing.parquet does
        timing.append({"match_id": mid, "tour": tour, "level": "T250", "qualifying": False, "tournament_date": when,
                       "es": day(when) - gap, "lf": day(when), "obs": day(when), "exact": True,
                       "width_days": float(gap)})
    rows += [{"match_id": "live_a", "level": "T500", "qualifying": False, "tournament_date": pd.Timestamp("2026-10-05")},
             {"match_id": "live_w", "level": "T500", "qualifying": False, "tournament_date": pd.Timestamp("2026-10-05")}]
    timing += [{"match_id": k, "tour": tour, "level": "T500", "qualifying": False,
                "tournament_date": pd.Timestamp("2026-10-05"), "es": 0.0, "lf": 0.0, "obs": 0.0, "exact": False,
                "width_days": 0.0} for k, tour in (("live_a", "atp"), ("live_w", "wta"))]
    (tmp_path / "mt").mkdir()
    pd.DataFrame(rows).to_parquet(tmp_path / "matches.parquet")
    pd.DataFrame(timing).to_parquet(tmp_path / "mt" / "timing.parquet")
    monkeypatch.setattr(C, "MATCHES", tmp_path / "matches.parquet")
    monkeypatch.setattr(MTC, "OUT", tmp_path / "mt")
    meta = pd.DataFrame({"match_id": ["live_a", "live_w"], "tour": ["atp", "wta"],
                         "day": [pd.Timestamp("2026-10-08")] * 2})
    out = I.pin(meta)
    assert out["days_before"] == {"atp": 0.0, "wta": 1.0}
    assert out["measured_on"]["atp"]["days"] == I.PIN_DAYS and out["measured_on"]["wta"]["days"] == I.PIN_FALLBACK
    t = pd.read_parquet(tmp_path / "mt" / "timing.parquet").set_index("match_id")
    assert t.loc["live_a", "es"] == day("2026-10-08") and t.loc["live_w", "es"] == day("2026-10-07")
    assert bool(t.loc["live_a", "exact"])


# ------------------------------------------------------------------------------------------------ 4. the gate

def gate_tables(tmp_path, earlier_box=True, entry="", earlier_level="T250"):
    ms = pd.DataFrame([
        {"match_id": "e1", "tour": "wta", "tournament_id": "2026-1", "tournament_name": "X", "round": "R32",
         "round_order": 13, "status": "completed", "has_box": earlier_box, "qualifying": False,
         "level": earlier_level, "tournament_date": pd.Timestamp("2026-10-01")},
        {"match_id": "e0", "tour": "wta", "tournament_id": "2026-0", "tournament_name": "W", "round": "R16",
         "round_order": 14, "status": "retired", "has_box": False, "qualifying": False, "level": "T250",
         "tournament_date": pd.Timestamp("2026-09-24")},
        {"match_id": "live", "tour": "wta", "tournament_id": "2026-1", "tournament_name": "X", "round": "R16",
         "round_order": 14, "status": "completed", "has_box": False, "qualifying": False, "level": "T250",
         "tournament_date": pd.Timestamp("2026-10-01")}])
    ps = pd.DataFrame([{"match_id": m, "player_id": pid, "player_name": n, "entry": e}
                       for m, pid, n, e in (("e1", "p1", "One", ""), ("e1", "p3", "Three", ""), ("e0", "p2", "Two", ""),
                                            ("e0", "p4", "Four", ""), ("live", "p1", "One", ""),
                                            ("live", "p2", "Two", entry))])
    folder = tmp_path / "s0"
    folder.mkdir()
    ms.to_parquet(folder / "stage0_matches.parquet")
    ps.to_parquet(folder / "stage0_match_players.parquet")
    day = lambda s: float((pd.Timestamp(s) - pd.Timestamp("1970-01-01")).days)  # noqa: E731
    pd.DataFrame({"match_id": ["e1", "e0", "live"], "lf": [day("2026-10-02"), day("2026-09-27"),
                                                           day("2026-10-04")]}).to_parquet(tmp_path / "timing.parquet")
    meta = pd.DataFrame({"match_id": ["live"], "day": [pd.Timestamp("2026-10-04")]})
    return folder, tmp_path / "timing.parquet", meta


def test_the_gate_passes_complete_inputs(tmp_path):
    table, missing = G.check(*gate_tables(tmp_path))
    assert bool(table["complete"].iloc[0]) and table["earlier_matches_checked"].iloc[0] == 1 and missing.empty
    assert table["edge_bar"].iloc[0] == 0 and G.verdict(table).iloc[0] == G.BET


def test_a_missing_main_tour_box_score_sets_the_bar_and_does_not_block(tmp_path):
    table, missing = G.check(*gate_tables(tmp_path, earlier_box=False))
    assert bool(table["complete"].iloc[0]) and missing["match_id"].tolist() == ["e1"]
    assert bool(missing["same_event"].iloc[0])
    assert (missing["kind"].iloc[0], missing["effect"].iloc[0]) == ("main tour", "edge bar")
    assert table["edge_bar"].iloc[0] == G.EDGE_BAR == 0.01 and table["bar_gaps"].iloc[0] == 1
    assert G.verdict(table).iloc[0] == G.BET_BAR and "clear 1 point" in table["reason"].iloc[0]


@pytest.mark.parametrize("level", ["TEAM", "ITF"])
def test_a_missing_box_score_of_a_kind_training_lacks_is_only_noted(tmp_path, level):
    table, missing = G.check(*gate_tables(tmp_path, earlier_box=False, earlier_level=level))
    assert bool(table["complete"].iloc[0]) and table["edge_bar"].iloc[0] == 0
    assert table["noted_gaps"].iloc[0] == 1 and missing["effect"].iloc[0] == "note"
    assert G.verdict(table).iloc[0] == G.BET


def test_kinds_put_the_itf_qualifying_with_the_itf():
    # the women's ITF qualifying has no box score in training; the tour's and the 125s' qualifying nearly always have one
    assert G.kind("ITF", True) == "ITF" and G.kind("TEAM", False) == "team event"
    assert G.kind("GS", True) == G.kind("CH", True) == G.kind("T250", True) == "qualifying"
    assert G.kind("T1000", False) == "main tour" and G.kind("CH", False) == "Challenger / WTA 125"
    assert [G.effect(k) for k in ("ITF", "team event", "qualifying", "main tour", "Challenger / WTA 125", "other")] == \
        ["note", "note", "edge bar", "edge bar", "edge bar", "edge bar"]


def test_the_gate_fails_a_qualifier_without_qualifying_matches(tmp_path):
    table, _ = G.check(*gate_tables(tmp_path, entry="Q"))
    assert not bool(table["complete"].iloc[0]) and "through qualifying" in table["reason"].iloc[0]
    assert G.verdict(table).iloc[0] == G.NO_BET


def test_an_unknown_indoor_input_blocks_even_with_the_bar(tmp_path):
    table, _ = G.check(*gate_tables(tmp_path, earlier_box=False))
    table = G.with_indoor(table, {"live"})
    assert not bool(table["complete"].iloc[0]) and G.verdict(table).iloc[0] == G.NO_BET
    assert table["reason"].iloc[0].startswith("indoor or outdoor unknown")


def test_a_qualifiers_matches_under_another_event_id_count(tmp_path):
    # TML files some qualifying under an id of its own: the qualifying match of 1 Oct is found by its days
    folder, timing, meta = gate_tables(tmp_path, entry="Q")
    ms = pd.read_parquet(folder / "stage0_matches.parquet")
    ms.loc[ms["match_id"].eq("e0"), ["qualifying", "status", "has_box", "tournament_id"]] = [True, "completed", True,
                                                                                             "2026-1-q"]
    ms.to_parquet(folder / "stage0_matches.parquet")
    table, _ = G.check(folder, timing, meta)
    assert bool(table["complete"].iloc[0])
