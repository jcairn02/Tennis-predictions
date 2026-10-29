"""The closing-line ledger (src/pipeline/closing_line.py; master pipeline process log, Part 18) on a made-up world.

Fast and offline. Five matches, two bet sheets, two runs, Pinnacle pulls of the bet-day recorder and of the capture,
TennisExplorer's tables and a Stage 0, all invented:
    m1  ATP main draw, two sheets: our capture reads Pinnacle 10 minutes before the match leaves the listing (a true
        close), beating the site's earlier last record; a curve, so the model is re-read at the close
    m2  WTA main draw, Pinnacle's home player is side B and the site lists side B first: the site's last record beats our
        early pull; Stage 0's side A is the record's side B
    m3  qualifying: only an early pull of ours (the site has no qualifying); its result under another event id, beside
        an earlier meeting of the pair at another event that must not be taken
    m4  not started
    m5  a pairing Stage 0 shows replaced (a withdrawal)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import closing_line as CL  # noqa: E402

NOW = "2026-10-23T00:00:00Z"
RUN1, RUN2 = "live_2026-10-19_160000", "live_2026-10-20_085000"
LEAN = 0.2                                   # the made-up model: logit q = logit p + LEAN at every price


def _q(p: float) -> float:
    return 1 / (1 + math.exp(-(math.log(p / (1 - p)) + LEAN)))


def _p(d_a: float, d_b: float) -> float:
    return (1 / d_a) / (1 / d_a + 1 / d_b)


def _sheet_row(mid, tour, tournament, rnd, day, start, a, b, ida, idb, quoted, d_a, d_b, pick, home_side, run):
    p = _p(d_a, d_b)
    return {"day": day, "start_utc": start, "tour": tour, "tournament": tournament, "round": rnd, "player_a": a,
            "player_b": b, "player_a_id": ida, "player_b_id": idb, "price_source": "pinnacle", "quoted_at": quoted,
            "pinnacle_odds_a": d_a, "pinnacle_odds_b": d_b, "p_market_a": round(p, 6), "model": "tabpfn35",
            "q_a": round(_q(p), 6), "edge_a": round(_q(p) - p, 6), "pick": pick,
            "pick_player": a if pick == "A" else (b if pick == "B" else None), "status": "predicted",
            "decision": "BET" if pick else "PASS", "home_side": home_side, "match_id": mid, "run": run}


M1 = ("atp|2026-1|R32|atp:1|atp:2", "atp", "Testopen", "R32", "2026-10-20", "2026-10-20T10:00:00Z", "Alpha One",
      "Beta Two", "atp:1", "atp:2")
M2 = ("wta|2026-2|R16|wta:3|wta:4", "wta", "Testcup", "R16", "2026-10-20", "2026-10-20T12:00:00Z", "Gamma Three",
      "Delta Four", "wta:3", "wta:4")
M3 = ("atp|2025-9|Q2|atp:5|atp:6", "atp", "Qualtown", "Q2", "2026-10-19", "2026-10-19T20:00:00Z", "Epsilon Five",
      "Zeta Six", "atp:5", "atp:6")
M4 = ("atp|2026-1|R32|atp:10|atp:11", "atp", "Testopen", "R32", "2026-10-24", "2026-10-24T10:00:00Z", "Eta Ten",
      "Theta Eleven", "atp:10", "atp:11")
M5 = ("atp|2026-1|R16|atp:7|atp:8", "atp", "Testopen", "R16", "2026-10-21", "2026-10-21T10:00:00Z", "Iota Seven",
      "Kappa Eight", "atp:7", "atp:8")


def _write_sheet(folder: Path, stem: str, made_at: str, rows: list[dict]) -> None:
    rec = folder / "records"
    rec.mkdir(parents=True, exist_ok=True)
    left_out = {"status": "not predicted", "decision": "NOT PREDICTED", "player_a": "X", "player_b": "Y",
                "run": rows[0]["run"]}
    pd.DataFrame(rows + [left_out]).to_csv(rec / f"{stem}.csv", index=False)
    (rec / f"{stem}.provenance.json").write_text(json.dumps({"made_at": made_at, "instance": "template_test",
                                                             "reprice_file": None}), encoding="utf-8")


def _pull(when: str, rows: list[tuple]) -> pd.DataFrame:
    """rows: (matchup_id, home, away, decimal_home, decimal_away, start_utc, is_live, usable, reason)."""
    out = []
    for mid, home, away, dh, da, start, live, usable, reason in rows:
        over = 1 / dh + 1 / da
        out.append({"retrieved_at": when, "matchup_id": mid, "league": "ATP Test - R32", "league_id": 1, "tour": "atp",
                    "event": "Test", "phase": "R32", "level": "tour", "qualifying": False, "best_of": 3,
                    "start_utc": start, "status": "started" if live else "pending", "is_live": live, "home": home,
                    "away": away, "price_home": 100, "price_away": -100, "decimal_home": dh, "decimal_away": da,
                    "overround": over, "p_home": (1 / dh) / over, "max_risk_stake": 1000, "cutoff_at": start,
                    "market_version": 1, "usable": usable, "reason": reason})
    return pd.DataFrame(out)


@pytest.fixture()
def world(tmp_path):
    pred = tmp_path / "predictions"
    # sheet 1 (19 Oct, 17:00 quote): m1-m5; sheet 2 (20 Oct, 08:55 quote): m1 again, from another run
    s1 = [_sheet_row(*M1, "2026-10-19T17:00:00Z", 2.10, 1.80, "A", "A", RUN1),
          _sheet_row(*M2, "2026-10-19T17:00:00Z", 2.50, 1.60, "B", "B", RUN1),
          _sheet_row(*M3, "2026-10-19T17:00:00Z", 1.50, 2.60, "A", "A", RUN1),
          _sheet_row(*M4, "2026-10-19T17:00:00Z", 1.90, 1.90, "", "A", RUN1),
          _sheet_row(*M5, "2026-10-19T17:00:00Z", 1.70, 2.20, "A", None, RUN1)]
    _write_sheet(pred / "2026-10-19", "bet_sheet_2026-10-19_1000", "2026-10-19T17:05:00+00:00", s1)
    s2 = [_sheet_row(*M1, "2026-10-20T08:55:00Z", 2.00, 1.87, "A", "A", RUN2)]
    _write_sheet(pred / "2026-10-20", "bet_sheet_2026-10-20_0200", "2026-10-20T09:00:00+00:00", s2)
    # the agents' check files and the engine's archive are not sheets
    (pred / "2026-10-20" / "records" / "check_something.csv").write_text("status,match_id\npredicted,zzz\n")
    # the runs: their matchups (Pinnacle's home first; m5 typed in, no matchup id) and m1's curve
    runs = tmp_path / "runs"
    mu = pd.DataFrame([
        {"player_a": "Alpha One", "player_b": "Beta Two", "stage0_id_a": "atp:1", "stage0_id_b": "atp:2",
         "pinnacle_matchup_id": 101},
        {"player_a": "Delta Four", "player_b": "Gamma Three", "stage0_id_a": "wta:4", "stage0_id_b": "wta:3",
         "pinnacle_matchup_id": 102},
        {"player_a": "Epsilon Five", "player_b": "Zeta Six", "stage0_id_a": "atp:5", "stage0_id_b": "atp:6",
         "pinnacle_matchup_id": 103},
        {"player_a": "Eta Ten", "player_b": "Theta Eleven", "stage0_id_a": "atp:10", "stage0_id_b": "atp:11",
         "pinnacle_matchup_id": 104}])
    x = np.linspace(math.log(0.05 / 0.95), math.log(0.95 / 0.05), 91)
    curve = pd.DataFrame({"match_id": M1[0], "odds_logit": x, "q_a": 1 / (1 + np.exp(-(x + LEAN)))})
    for run in (RUN1, RUN2):
        (runs / run).mkdir(parents=True)
        mu.to_csv(runs / run / "matchups_input.csv", index=False)
        curve.to_parquet(runs / run / "curves.parquet", index=False)
    # Pinnacle: the bet-day pull of 19 Oct 17:00; the capture's pulls of 20 Oct 09:50 and 10:00 (m1 gone at 10:00)
    bet, cap = tmp_path / "pulls_bet", tmp_path / "pulls_cap"
    for folder, day, stamp, rows in (
            (bet, "2026-10-19", "170000Z", [(101, "Alpha One", "Beta Two", 2.10, 1.80, M1[5], False, True, None),
                                            (102, "Delta Four", "Gamma Three", 1.60, 2.50, M2[5], False, True, None),
                                            (103, "Epsilon Five", "Zeta Six", 1.50, 2.60, M3[5], False, True, None),
                                            (104, "Eta Ten", "Theta Eleven", 1.90, 1.90, M4[5], False, True, None)]),
            (cap, "2026-10-20", "095000Z", [(101, "Alpha One", "Beta Two", 1.95, 1.95, M1[5], False, True, None),
                                            (104, "Eta Ten", "Theta Eleven", 1.90, 1.90, M4[5], False, True, None)]),
            (cap, "2026-10-20", "100000Z", [(104, "Eta Ten", "Theta Eleven", 1.92, 1.88, M4[5], False, True, None)])):
        (folder / day).mkdir(parents=True, exist_ok=True)
        _pull(f"{day}T{stamp[:2]}:{stamp[2:4]}:{stamp[4:6]}+00:00", rows).to_parquet(folder / day / f"{stamp}.parquet")
    # TennisExplorer: m1 and m2 (m2 with side B first); every price with its time
    te = tmp_path / "te"
    te.mkdir()
    pd.DataFrame([
        {"te_id": 1, "tour": "atp", "date": "2026-10-20", "start_utc": "2026-10-20T10:00:00+00:00", "event": "Testopen",
         "round": "1. round", "p1": "One Alpha", "p2": "Two Beta", "has_pinnacle": True},
        {"te_id": 2, "tour": "wta", "date": "2026-10-20", "start_utc": "2026-10-20T12:00:00+00:00", "event": "Testcup",
         "round": "round of 16", "p1": "Four Delta", "p2": "Three Gamma", "has_pinnacle": True}]).to_parquet(
        te / "matches.parquet")
    pd.DataFrame([
        {"te_id": 1, "book": "Pinnacle", "k1_last": 1.97, "k1_open": 2.10, "k1_open_t": "2026-10-18T10:00:00+00:00",
         "k1_n_moves": 1, "k1_last_t": "2026-10-20T09:20:00+00:00", "k2_last": 1.93, "k2_open": 1.80,
         "k2_open_t": "2026-10-18T10:00:00+00:00", "k2_n_moves": 1, "k2_last_t": "2026-10-20T09:20:00+00:00"},
        {"te_id": 2, "book": "Pinnacle", "k1_last": 1.55, "k1_open": 1.60, "k1_open_t": "2026-10-18T10:00:00+00:00",
         "k1_n_moves": 1, "k1_last_t": "2026-10-20T11:20:00+00:00", "k2_last": 2.62, "k2_open": 2.50,
         "k2_open_t": "2026-10-18T10:00:00+00:00", "k2_n_moves": 1, "k2_last_t": "2026-10-20T11:20:00+00:00"}]
    ).to_parquet(te / "odds.parquet")
    pd.DataFrame([(1, "Pinnacle", "k1", "2026-10-18T10:00:00+00:00", 2.10, True),
                  (1, "Pinnacle", "k2", "2026-10-18T10:00:00+00:00", 1.80, True),
                  (1, "Pinnacle", "k1", "2026-10-20T09:20:00+00:00", 1.97, False),
                  (1, "Pinnacle", "k2", "2026-10-20T09:20:00+00:00", 1.93, False),
                  (2, "Pinnacle", "k1", "2026-10-18T10:00:00+00:00", 1.60, True),
                  (2, "Pinnacle", "k2", "2026-10-18T10:00:00+00:00", 2.50, True),
                  (2, "Pinnacle", "k1", "2026-10-20T11:20:00+00:00", 1.55, False),
                  (2, "Pinnacle", "k2", "2026-10-20T11:20:00+00:00", 2.62, False)],
                 columns=["te_id", "book", "side", "t_utc", "odds", "opening"]).to_parquet(te / "moves.parquet")
    # Stage 0: m1 by its id; m2 by its id with the sides the other way; m3 under the edition's own id, beside an
    # earlier meeting of the pair elsewhere; m5's round played by another pairing
    s0 = pd.DataFrame([
        (M1[0], "atp", "R32", "Testopen", "2026-10-19", "completed", 1, "atp:1", "atp:2"),
        (M2[0], "wta", "R16", "Testcup", "2026-10-19", "completed", 1, "wta:4", "wta:3"),
        ("atp|2026-9|Q2|atp:5|atp:6", "atp", "Q2", "Qualtown", "2026-10-20", "completed", 0, "atp:5", "atp:6"),
        ("atp|2026-3|Q2|atp:5|atp:6", "atp", "Q2", "Elsewhere", "2026-10-12", "completed", 1, "atp:5", "atp:6"),
        ("atp|2026-1|R16|atp:7|atp:9", "atp", "R16", "Testopen", "2026-10-19", "completed", 1, "atp:7", "atp:9")],
        columns=["match_id", "tour", "round", "tournament_name", "tournament_date", "status", "a_won", "player_a_id",
                 "player_b_id"])
    s0.to_parquet(tmp_path / "stage0_matches.parquet")
    led, meta = CL.build(predictions=pred, runs=runs, pulls=(bet, cap), te=te, stage0=tmp_path / "stage0_matches.parquet",
                         now=NOW)
    return led, meta


def _one(led, match, sheet_day=None):
    rows = led[led["match_id"].eq(match[0])]
    if sheet_day:
        rows = rows[rows["sheet_file"].str.contains(sheet_day)]
    assert len(rows) == 1, rows
    return rows.iloc[0]


def test_every_sheet_row_is_kept_and_only_sheets_are_read(world):
    led, meta = world
    assert len(led) == 6 and meta["sheets"] == 2 and led["match_id"].nunique() == 5
    assert list(led.columns) == CL.COLUMNS
    assert not led["match_id"].eq("zzz").any()                       # the check file is not a sheet


def test_a_true_close_of_our_own_beats_the_sites_earlier_record(world):
    led, _ = world
    r = _one(led, M1, "2026-10-20")
    assert r["close_kind"] == "close" and r["close_source"] == "pinnacle pull"
    assert r["own_next_state"] == "gone" and r["own_next_gap_min"] == pytest.approx(10)
    assert (r["close_odds_a"], r["close_odds_b"]) == (1.95, 1.95) and r["close_min_before_start"] == pytest.approx(10)
    assert r["te_odds_a"] == 1.97                                    # the site's record is kept beside it


def test_the_sites_last_record_beats_an_early_pull_and_both_sides_are_turned(world):
    led, _ = world
    r = _one(led, M2)
    assert r["close_kind"] == "close" and r["close_source"] == "tennisexplorer"
    # Pinnacle's home is side B; the site lists side B first: both turned to side A
    assert (r["own_odds_a"], r["own_odds_b"]) == (2.50, 1.60)
    assert (r["close_odds_a"], r["close_odds_b"]) == (2.62, 1.55)
    assert (r["te_at_quote_a"], r["te_at_quote_b"]) == (2.50, 1.60)  # the site's price at the sheet's quote time
    assert r["close_min_before_start"] == pytest.approx(40)


def test_clv_drift_and_the_model_at_the_close(world):
    led, _ = world
    first, last = _one(led, M1, "2026-10-19"), _one(led, M1, "2026-10-20")
    assert first["clv_price"] == pytest.approx(2.10 / 1.95 - 1) and first["clv_ev"] == pytest.approx(0.5 * 2.10 - 1)
    assert last["clv_price"] == pytest.approx(2.00 / 1.95 - 1) and last["clv_ev"] == pytest.approx(0.0, abs=1e-12)
    assert last["drift_pick_pts"] == pytest.approx(100 * (0.5 - _p(2.00, 1.87)), abs=1e-4)
    assert last["toward_model_logit"] > 0                           # the model leaned to A and the line came to A
    # the model re-read off its curve at the closing price (0.5): logit q = LEAN there
    assert last["q_close_a"] == pytest.approx(_q(0.5), abs=1e-9)
    assert last["ev_close_pick"] == pytest.approx(_q(0.5) * 1.95 - 1, abs=1e-9)
    assert last["edge_close_pick"] == pytest.approx(_q(0.5) - 1 / 1.95, abs=1e-9)
    assert last["curve_q_at_quote"] == pytest.approx(last["q_a"], abs=1e-6)
    m2 = _one(led, M2)                                               # pick B, against B's close; no curve in its run
    p_close_b = 1 - _p(2.62, 1.55)
    assert m2["clv_price"] == pytest.approx(1.60 / 1.55 - 1) and m2["clv_ev"] == pytest.approx(p_close_b * 1.60 - 1)
    assert math.isnan(m2["q_close_a"])


def test_the_views(world):
    led, _ = world
    m1 = led[led["match_id"].eq(M1[0])]
    assert m1["first_sheet"].tolist() == [True, False] and m1["last_before_start"].tolist() == [False, True]
    assert led.groupby("match_id")["last_before_start"].sum().eq(1).all()


def test_qualifying_pending_and_a_changed_pairing(world):
    led, _ = world
    m3, m4, m5 = _one(led, M3), _one(led, M4), _one(led, M5)
    assert m3["close_kind"] == "last seen" and m3["close_source"] == "pinnacle pull" and math.isnan(m3["clv_price"])
    assert math.isnan(m3["te_id"])                                   # qualifying is never linked to the site
    assert m4["close_kind"] == "pending" and pd.isna(m4["close_source"])
    assert m5["close_kind"] == "awaiting" and m5["result_status"] == "not played as listed"


def test_results_by_id_with_the_sides_turned_and_by_event_never_another_meeting(world):
    led, _ = world
    assert _one(led, M1, "2026-10-20")["a_won"] == 1 and _one(led, M1, "2026-10-20")["pick_won"] == 1
    m2 = _one(led, M2)
    assert m2["a_won"] == 0 and m2["pick_won"] == 1                  # Stage 0's side A (wta:4) won: the record's B
    m3 = _one(led, M3)
    assert m3["result_by"] == "players, round and event" and m3["a_won"] == 0   # not the 1 of the earlier meeting
    assert m3["ll_q"] == pytest.approx(-math.log(1 - m3["q_a"]))


def test_the_checks(world):
    _, meta = world
    site = meta["checks"]["site_vs_sheet_price"]
    # m1's first quote and m2's equal the site's; m1's second (08:55) does not (the site shows no change before 09:20)
    assert site == {"rows": 3, "same": 2, "sides_swapped": 0}
    assert meta["checks"]["curve_vs_sheet_q"]["max_abs"] < 1e-5


def test_the_summary_reads_each_match_once_and_leaves_out_the_void(world):
    led, meta = world
    s = CL.summarize(led, meta)
    assert s["counts"]["close_kind"] == {"close": 2, "last seen": 1, "pending": 1}      # m5 (void) left out
    assert s["clv_price"]["n"] == 2 and s["clv_price"]["mean"] == pytest.approx(
        ((2.00 / 1.95 - 1) + (1.60 / 1.55 - 1)) / 2)
    assert any("void" in line for line in s["lines"])
    t = CL.table(led)
    assert len(t) == 4 and t["Close from"].tolist().count("earlier price only, 3.0 h before") == 1


def test_a_later_pull_with_another_price_overtakes_the_sites_record_and_a_late_match_stays_open():
    now = pd.Timestamp("2026-10-23T00:00:00Z")
    start = "2026-10-20T12:00:00Z"
    m = pd.DataFrame([{"tour": "wta", "tournament": "T", "round": "R16", "day": "2026-10-20", "start_utc": start,
                       "player_a": "Gamma Three", "player_b": "Delta Four", "player_a_id": "wta:3",
                       "player_b_id": "wta:4", "home_side": "A", "pinnacle_matchup_id": 7}],
                     index=pd.Index(["w|1|R16|wta:3|wta:4"], name="match_id"))
    m["pinnacle_matchup_id"] = m["pinnacle_matchup_id"].astype("Int64")
    # our pulls: 11:00 (a price), 12:10 and 12:20 after the listed start with the market still open (start passed),
    # 12:30 with the pre-match market shut: the 12:20 price is the true close
    rows = [(7, "Gamma Three", "Delta Four", 2.00, 1.80, start, False, True, None)]
    late, shut = "start not after the pull", "market cutoff not after the pull"     # the staging's own words
    pulls = pd.concat([_pull("2026-10-20T11:00:00+00:00", rows),
                       _pull("2026-10-20T12:10:00+00:00", [(7, "Gamma Three", "Delta Four", 2.10, 1.75, start, False,
                                                            False, late)]),
                       _pull("2026-10-20T12:20:00+00:00", [(7, "Gamma Three", "Delta Four", 2.20, 1.70, start, False,
                                                            False, late)]),
                       _pull("2026-10-20T12:30:00+00:00", [(7, "Gamma Three", "Delta Four", 2.20, 1.70, start, False,
                                                            False, shut)])], ignore_index=True)
    own = CL.own_closes(pulls)
    assert own.loc[7, "close_pull"] == pd.Timestamp("2026-10-20T12:20:00Z") and bool(own.loc[7, "true_close"])
    assert own.loc[7, "next_state"] == "cutoff passed"
    # without the last two pulls the 11:00 price is only seen, and a site record of 11:20 with another price wins...
    tm = pd.DataFrame([{"te_id": 9, "tour": "wta", "start_utc": "2026-10-20T12:00:00+00:00", "round": "round of 16",
                        "p1": "Three Gamma", "p2": "Four Delta"}])
    pin = pd.DataFrame([{"k1_last": 2.05, "k2_last": 1.78, "k1_last_t": "2026-10-20T11:20:00+00:00",
                         "k2_last_t": "2026-10-20T11:20:00+00:00"}], index=pd.Index([9], name="te_id"))
    early = CL.own_closes(pulls.iloc[:1])
    x = CL.match_closes(m, early, (tm, pin, {}), now).iloc[0]
    assert x["close_kind"] == "close" and x["close_source"] == "tennisexplorer"
    # ...but a later pull of ours with another price than the site's last record shows the site missed a move
    later = CL.own_closes(pd.concat([_pull("2026-10-20T11:40:00+00:00", [(7, "Gamma Three", "Delta Four", 2.30, 1.65,
                                                                        start, False, True, None)]),
                                     _pull("2026-10-21T08:00:00+00:00", [(8, "X", "Y", 1.9, 1.9, start, False, True,
                                                                         None)])], ignore_index=True))
    y = CL.match_closes(m, later, (tm, pin, {}), now).iloc[0]
    assert y["close_kind"] == "last seen" and y["close_source"] == "pinnacle pull" and y["own_odds_a"] == 2.30
    assert math.isnan(y["close_odds_a"])                            # an earlier price is never taken as the close


def _match(start: str, pid=7) -> pd.DataFrame:
    m = pd.DataFrame([{"tour": "wta", "tournament": "T", "round": "R16", "day": start[:10], "start_utc": start,
                       "player_a": "Gamma Three", "player_b": "Delta Four", "player_a_id": "wta:3",
                       "player_b_id": "wta:4", "home_side": "A", "pinnacle_matchup_id": pid}],
                     index=pd.Index(["w|1|R16|wta:3|wta:4"], name="match_id"))
    m["pinnacle_matchup_id"] = m["pinnacle_matchup_id"].astype("Int64")
    return m


def _site(last_t: str, d1: float, d2: float, start: str) -> tuple:
    tm = pd.DataFrame([{"te_id": 9, "tour": "wta", "start_utc": start, "round": "round of 16", "p1": "Three Gamma",
                        "p2": "Four Delta"}])
    pin = pd.DataFrame([{"k1_last": d1, "k2_last": d2, "k1_last_t": last_t, "k2_last_t": last_t}],
                       index=pd.Index([9], name="te_id"))
    return tm, pin, {}


def test_the_sites_record_is_the_close_only_when_known_to_hold_near_the_start():
    now, start = pd.Timestamp("2026-10-23T00:00:00Z"), "2026-10-20T12:00:00+00:00"
    site = _site("2026-10-20T08:00:00+00:00", 2.05, 1.78, start)          # four hours before the start
    x = CL.match_closes(_match(start), pd.DataFrame(), site, now).iloc[0]
    assert x["close_kind"] == "last seen" and x["close_source"] == "tennisexplorer" and math.isnan(x["close_odds_a"])
    assert x["close_min_before_start"] == pytest.approx(240)
    # a pull of ours at 11:30 with the same price shows it held until then: within two hours, so the close
    ours = CL.own_closes(pd.concat([_pull("2026-10-20T11:30:00+00:00", [(7, "Gamma Three", "Delta Four", 2.05, 1.78,
                                                                        start, False, True, None)]),
                                    _pull("2026-10-21T08:00:00+00:00", [(8, "X", "Y", 1.9, 1.9, start, False, True,
                                                                         None)])], ignore_index=True))
    y = CL.match_closes(_match(start), ours, site, now).iloc[0]
    assert y["close_kind"] == "close" and y["close_source"] == "tennisexplorer" and y["close_odds_a"] == 2.05
    assert y["close_t"] == pd.Timestamp("2026-10-20T11:30:00Z") and y["close_min_before_start"] == pytest.approx(30)


def test_a_true_close_dates_the_start_no_later_than_the_market_shutting():
    # Pinnacle moved the listed start to 07:30, but the pre-match market was gone by 06:50 (the match was on)
    rows = lambda d_h, start, usable, why: [(7, "Gamma Three", "Delta Four", d_h, 1.70, start, False, usable, why)]  # noqa: E731
    pulls = pd.concat([_pull("2026-10-22T06:20:00+00:00", rows(2.30, "2026-10-22T06:30:00Z", True, None)),
                       _pull("2026-10-22T06:30:00+00:00", rows(2.30, "2026-10-22T06:30:00Z", False,
                                                               "market cutoff not after the pull")),
                       _pull("2026-10-22T06:40:00+00:00", rows(2.25, "2026-10-22T07:30:00Z", True, None)),
                       _pull("2026-10-22T06:50:00+00:00", [(8, "X", "Y", 1.9, 1.9, "2026-10-23T06:00:00Z", False,
                                                            True, None)])], ignore_index=True)
    x = CL.match_closes(_match("2026-10-22T06:30:00Z"), CL.own_closes(pulls), (pd.DataFrame(), pd.DataFrame(), {}),
                        pd.Timestamp("2026-10-23T00:00:00Z")).iloc[0]
    assert x["close_kind"] == "close" and x["close_odds_a"] == 2.25
    assert x["start_final"] == pd.Timestamp("2026-10-22T06:50:00Z") and x["close_min_before_start"] == pytest.approx(10)


def test_pulls_from_both_folders_are_read_in_time_order(tmp_path):
    bet, cap = tmp_path / "bet", tmp_path / "cap"
    for folder, stamp, start in ((bet, "120000Z", "2026-10-20T14:00:00Z"), (cap, "110000Z", "2026-10-20T13:00:00Z")):
        (folder / "2026-10-20").mkdir(parents=True)
        _pull(f"2026-10-20T{stamp[:2]}:{stamp[2:4]}:00+00:00", [(7, "A", "B", 1.9, 1.9, start, False, True, None)]) \
            .to_parquet(folder / "2026-10-20" / f"{stamp}.parquet")
    own = CL.own_closes(CL.pinnacle_pulls((bet, cap)))
    assert own.loc[7, "close_pull"] == pd.Timestamp("2026-10-20T12:00:00Z")
    assert own.loc[7, "final_start"] == pd.Timestamp("2026-10-20T14:00:00Z")      # the later pull's, not the last read


def test_the_reasons_read_are_the_stagings_own():
    staging = (ROOT / "src" / "ingest" / "pinnacle.py").read_text(encoding="utf-8")
    assert f'"{CL.CUTOFF_PASSED}"' in staging and f'"{CL.START_PASSED}"' in staging


def test_a_started_main_draw_match_awaits_the_sites_page_and_qualifying_never_does():
    m = pd.DataFrame([{"tour": "atp", "tournament": "T", "round": rnd, "day": "2026-10-22",
                       "start_utc": "2026-10-22T10:00:00Z", "player_a": "A A", "player_b": "B B", "player_a_id": "1",
                       "player_b_id": "2", "pinnacle_matchup_id": pd.NA} for rnd in ("R32", "Q1")],
                     index=pd.Index(["atp|1|R32|1|2", "atp|1|Q1|1|2"], name="match_id"))
    empty = (pd.DataFrame(), pd.DataFrame(), {})
    x = CL.match_closes(m, pd.DataFrame(), empty, pd.Timestamp("2026-10-23T00:00:00Z"))
    assert x["close_kind"].tolist() == ["awaiting", "none"]
    y = CL.match_closes(m, pd.DataFrame(), empty, pd.Timestamp("2026-10-25T00:00:00Z"))
    assert y["close_kind"].tolist() == ["none", "none"]


def test_verdicts_follow_the_reporting_rule():
    assert CL.verdict({"n": 0}) == "none yet"
    spans = CL.mean_ci([0.03, -0.01, 0.02, -0.02, 0.01])
    assert "unresolved, P(above 0)" in CL.verdict(spans) and "tie" not in CL.verdict(spans)
    assert CL.verdict(CL.mean_ci([0.02, 0.021, 0.019, 0.022])).endswith("above 0")
    assert CL.verdict(CL.mean_ci([-0.02, -0.021, -0.019])).endswith("below 0")
    s = CL.slope_ci([1, -1, 2, -2], [0.5, -0.5, 1.0, -1.0])
    assert s["slope"] == pytest.approx(0.5) and s["lo"] == pytest.approx(0.5)


def test_clv_ledger_writes_its_three_files(world, tmp_path, monkeypatch, capsys):
    led, meta = world
    monkeypatch.setattr(CL, "build", lambda now=None: (led, meta))
    monkeypatch.setattr(CL, "OUT", tmp_path / "clv")
    out = CL.clv_ledger()
    assert len(out) == 6
    assert {p.name for p in (tmp_path / "clv").iterdir()} == {"ledger.csv", "ledger.provenance.json", "summary.json"}
    prov = json.loads((tmp_path / "clv" / "ledger.provenance.json").read_text(encoding="utf-8"))
    assert prov["parameters"]["close_gap_min"] == CL.CLOSE_GAP_MIN and "not the owner's words" in prov["rules"]
    assert "Closing-line value" in capsys.readouterr().out
