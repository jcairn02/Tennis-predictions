"""The closing-line ledger (A8): every bet sheet's predictions against Pinnacle's close, the line's drift since the
sheet, and the closing-line value (CLV) of each pick.

The owner's request (25 Oct 2026): "comparing the "best model predictionsat the time of the run" to the closing line (as
well as see how much the line drifted since then to calculate CLV)". How it is done, and every rule below, is an agent's
choice of 25 Oct 2026, not the owner's words (docs/studies/master_pipeline/process_log.md, Part 18).

    predictions/clv/ledger.csv               one row per bet sheet and predicted match: every prediction is kept
    predictions/clv/ledger.provenance.json   the sources read, their times, the checks, the counts, these rules
    predictions/clv/summary.json             what A8 shows

Rebuilt in full at each call from files that are never replaced (the sheets' records, the run folders, the odds pulls,
the site's pages), so it is never hand-kept: run it again after the 07:30 download for the newest closes.

The rows: each predictions/<day>/records/bet_sheet_*.csv row with status "predicted" (the agents' check_* files and the
engine's live_* archives are not sheets). Sides A and B are the record's, Stage 0's. Each match keeps every sheet that
predicted it, and two views mark one row each: first_sheet (its earliest sheet) and last_before_start (its latest sheet
made before the start: the one a bet most likely rested on). Pinnacle's matchup id is read from the run's matchups, as
the bet sheet reads them.

The close, per match (an agent's choice):
    pinnacle pull     Pinnacle's own listing, by matchup id: the bet-day pulls (data/dump/odds/pinnacle/pulls/) and P11's
                      10-minute capture (data/dump/odds/pinnacle_capture/pulls/). Its last pre-match pull (priced, not in
                      play, the market's cutoff ahead; pinnacle_capture.closes) is the last price seen, and a true close
                      when the next pull, at most CLOSE_GAP_MIN minutes later, shows the match in play, its pre-match
                      market shut, or no longer lists it
    tennisexplorer    the site's last Pinnacle price (src/ingest/tennisexplorer.py: the daily pinnacle_closes job, the
                      tour's main draws only, no qualifying), its last record (a change, else the opening) a median 47
                      minutes before the listed start in 2026: the price the model's training data takes as Pinnacle's
                      close from 1 Nov 2025 (src/eda/current_best_model/odds_input.py). Left out when it carries no time,
                      is incoherent, or sits far from the site's other books (the odds input's own tests)
In that order: a true close of our own; else the site's last record, unless a later pull of ours saw another price (the
site missed a late move), as the close when known to hold within CLOSE_LEAD_MAX_MIN of the start (its record, or a
later pull of ours with the same price), else as an earlier price; else our last pull. The start is the latest listed
(Pinnacle's last pull, the site's page), never after our pulls saw the pre-match market shut. close_kind: "close";
"last seen" (an earlier price only, observed at close_t, close_min_before_start before the start: its odds stay in
own_odds_a/_b or te_odds_a/_b, and no drift or CLV is computed on it); "pending" (not started); "awaiting" (a main-draw
match started under AWAIT_HOURS ago with no close yet: the site's page comes with the next daily download); "none".

Per row (side A's chance unless named; the pick's side for the pick's columns):
    drift          p_close_a - p_market_a, in points and in log-odds: the sheet's margin-free price to the close's
    toward_model   the drift's log-odds in the direction of the model's lean at the sheet (logit q_a - logit p_market_a):
                   above 0, the line moved toward the model. The summary's slope of the drift on the lean is the bet
                   timing study's "move toward the model" (docs/studies/bet_timing/README.md)
    clv            clv_price = d_taken / d_close - 1: the closing-line value, the odds taken against the closing odds,
                   both with the margin (0: the line did not move); clv_ev = p_close(pick) x d_taken - 1: the pick's
                   expected profit per unit staked if the close's margin-free chance is right (a bet at the closing
                   price itself scores 1/overround - 1 by it: minus Pinnacle's margin); drift_pick_pts: the line's move
                   toward the pick, in points
    at the close   q_close_a: the model's chance re-read off the run's curve at the closing price (NaN off its 0.05-0.95);
                   edge_close_pick and ev_close_pick: the pick against the close's posted price, its margin included (the
                   sheet's market chance since 24 Oct 2026)
    result         from the freshest Stage 0 (the repository's, the data check's or the newest live run's own): by match
                   id, else by tour, the two players' ids and the event's date; log losses of q_a, of the sheet's price,
                   of the close and of q_close_a on completed and retired matches (A7's rule)
d_taken is the sheet's price (Pinnacle's; BetOnline's where the sheet's price came from BetOnline): these are the sheets'
picks, not the bets placed, which nothing records yet. CLV is a check on prices, not on the model: the market does not
move toward this model before the close (the production-integrity plan, principle 8). The summary's intervals are
normal approximations, said "unresolved" with P(above 0) when they span 0.
A tour switched off for the bet day (config.BET_TOURS; the owner, 28 Oct 2026: the women's) stays in the ledger file,
and the reading (the summary and its table) leaves it out, saying how many predictions it leaves out.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import bet_sheet as BS
from . import config as CFG
from . import diagnostics as DG

if str(CFG.ROOT) not in sys.path:
    sys.path.insert(0, str(CFG.ROOT))

OUT = CFG.PREDICTIONS / "clv"
PULLS = (CFG.PINNACLE_DUMP / "pulls", CFG.ODDS_DUMP / "pinnacle_capture" / "pulls")
TE = CFG.ODDS_DUMP / "tennisexplorer"
CLOSE_GAP_MIN = 15       # a last pre-match pull is a true close when the next pull, at most this many minutes later, shows
                         # the match in play, its pre-match market shut, or gone (P11's 15 minutes:
                         # docs/studies/gap_downloads/README.md)
AWAIT_HOURS = 48         # a started main-draw match without a true close waits this long for the site's page
LINK_DAYS = 2            # the site's listed start within this many days of the sheet's
RESULT_DAYS = (14, 4)    # by players: a Stage 0 event dated from 14 days before the match's day to 4 days after (a
                         # qualifying match's event is dated by its main draw's first day, rule C05)
SAME_PRICE = 0.01        # two readings of Pinnacle's decimal odds within this on both sides are the same price
CLOSE_LEAD_MAX_MIN = 120  # the site's price counts as the close only when known to hold within this many minutes of the
                          # start (its record, or a later pull of ours with the same price): the site keeps only some of
                          # Pinnacle's changes, and its record ends a median 47 minutes before the start (2026), a quarter
                          # more than 117 (an agent's choice of 25 Oct 2026, about that quarter; process log, Part 18)
DONE = ("completed", "retired")                  # graded as A7 grades (dp_steps.step_grade)
VOID = ("walkover", "not played as listed")       # no bet stands: left out of the summary's readings
BET_TIMING_SLOPE = "+0.01 [-0.02, +0.04]"        # the backtest's move toward the model (docs/studies/bet_timing/)
TIMES = ("made_at", "start_final", "close_t", "own_t", "own_start", "te_t", "te_start")

COLUMNS = [
    # the sheet and the match
    "sheet_file", "made_at", "repriced", "run", "model", "instance", "match_id", "pinnacle_matchup_id", "te_id", "tour",
    "tournament", "round", "day", "start_utc", "start_final", "player_a", "player_b", "player_a_id", "player_b_id",
    "first_sheet", "last_before_start", "made_after_start",
    # the sheet's price and forecast
    "price_source", "quoted_at", "quote_lead_min", "pinnacle_odds_a", "pinnacle_odds_b", "p_market_a", "q_a",
    "q_a_patterns_off", "q_a_local", "q_a_thinking", "edge_a", "decision", "pick", "pick_player", "d_taken",
    "ev_pinnacle_pick", "stake_units_owner_8oct_research",
    # the close
    "close_kind", "close_source", "close_t", "close_min_before_start", "close_odds_a", "close_odds_b", "p_close_a",
    "overround_close", "own_t", "own_odds_a", "own_odds_b", "own_true_close", "own_next_state", "own_next_gap_min",
    "own_pulls", "te_link", "te_t", "te_odds_a", "te_odds_b", "te_note", "te_at_quote_a", "te_at_quote_b",
    # the drift and the pick's closing-line value
    "drift_pts_a", "drift_logit_a", "lean_logit_a", "toward_model_logit", "d_close_pick", "p_close_pick", "clv_ev",
    "clv_price", "drift_pick_pts",
    # the model at the close
    "curve_q_at_quote", "q_close_a", "q_close_pick", "edge_close_pick", "ev_close_pick",
    # the result
    "result_status", "result_by", "a_won", "pick_won", "ll_q", "ll_quote", "ll_close", "ll_q_close"]


def _f(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return float("nan")
    return v if math.isfinite(v) else float("nan")


def _logit(p) -> float:
    p = _f(p)
    return math.log(p / (1 - p)) if 0 < p < 1 else float("nan")


def _devig(d_a, d_b) -> float:
    """Side A's chance with the margin removed proportionally (the model's input rule)."""
    d_a, d_b = _f(d_a), _f(d_b)
    return (1 / d_a) / (1 / d_a + 1 / d_b) if d_a > 1 and d_b > 1 else float("nan")


def _utc(x):
    return pd.to_datetime(x, utc=True, errors="coerce")


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _written(p: Path | None) -> str | None:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds") \
        if p is not None and p.exists() else None


# --- the sheets -----------------------------------------------------------------------------------------------------

def sheet_rows(predictions: Path = CFG.PREDICTIONS) -> pd.DataFrame:
    """Every bet sheet's predicted rows, each with its sheet file, the sheet's time and the provenance's instance. A
    record that cannot be read is said with "!!!" and left out; the others are read (28 Oct 2026: one row never holds up
    the rest, docs/decisions/2026-10-28-one-bad-match-left-out.md)."""
    parts = []
    for f in sorted(Path(predictions).glob("*/records/bet_sheet_*.csv")):
        try:
            rec = pd.read_csv(f, dtype={"match_id": str, "player_a_id": str, "player_b_id": str})
            rec = rec[rec["status"].eq("predicted")] if "status" in rec.columns else rec.iloc[0:0]
            if rec.empty:
                continue
            prov = DG._read_json(f.with_suffix(".provenance.json"))
            made = _utc(prov.get("made_at"))
            if pd.isna(made):
                made = pd.Timestamp(f.stat().st_mtime, unit="s", tz="UTC")
            parts.append(rec.assign(sheet_file=CFG.rel(f), made_at=made, instance=prov.get("instance"),
                                    repriced=bool(prov.get("reprice_file"))))
        except Exception as exc:  # noqa: BLE001 - one record's error is said; the ledger reads the others
            print(f"!!! ERROR reading the bet sheet record {CFG.rel(f)} ({type(exc).__name__}: {exc}): left out of "
                  "the ledger; every other sheet is read")
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _matchup_ids(rows: pd.DataFrame, runs: Path) -> pd.Series:
    """Pinnacle's matchup id of each row, from its run's matchups (the bet sheet's own reading: by the players' Stage 0
    ids, else by their names). Missing for a run whose prices were BetOnline's or typed in."""
    out = pd.Series(pd.NA, index=rows.index, dtype="Int64")
    for run, g in rows.groupby("run"):
        p = Path(runs) / str(run) / "matchups_input.csv"
        if not p.exists():
            continue
        mu = pd.read_csv(p)
        if "pinnacle_matchup_id" not in mu.columns:
            continue
        for i, m in zip(g.index, DG._matchup_rows(g, mu)):
            if m is not None and not pd.isna(m.get("pinnacle_matchup_id")):
                out[i] = int(m["pinnacle_matchup_id"])
    return out


# --- Pinnacle's own pulls -------------------------------------------------------------------------------------------

def pinnacle_pulls(roots=PULLS) -> pd.DataFrame:
    """Every staged pull of Pinnacle's tennis listing (the bet-day recorder's and P11's capture), one row per matchup and
    pull; empty when none is on disk."""
    files = [f for r in roots for f in sorted(Path(r).glob("20*/*.parquet"))]
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    # in time order across both folders: pinnacle_capture.closes reads a matchup's final listed start as its last row
    return df.assign(_t=_utc(df["retrieved_at"])).sort_values("_t", kind="stable").drop(columns="_t") \
        .reset_index(drop=True)


# the staging's reasons (src/ingest/pinnacle.py, in its order): the pre-match market's cutoff has passed (bets shut), or
# only the listed start has (the cutoff still ahead: a match running late, its pre-match price still open)
CUTOFF_PASSED = "market cutoff not after the pull"
START_PASSED = "start not after the pull"
CLOSED = ("in play", "gone", "cutoff passed")


def own_closes(pulls: pd.DataFrame) -> pd.DataFrame:
    """Per matchup id: its last pre-match pull (pinnacle_capture.closes, P11's definition, on its usable rows and on the
    rows of a match running late: not in play, priced, the cutoff ahead, only the listed start passed) and what the next
    pull of the listing showed, how many minutes later: "in play", "gone" (no longer listed), "cutoff passed" (listed,
    its pre-match market shut) or "unpriced" (listed, not usable for another reason). A true close when one of the first
    three comes within CLOSE_GAP_MIN."""
    if pulls.empty:
        return pd.DataFrame()
    from src.eda.gap_downloads import pinnacle_capture as PC
    reason = pulls["reason"] if "reason" in pulls.columns else pd.Series(None, index=pulls.index)
    live = pulls["is_live"].astype(bool)
    open_ = ~live & (pulls["usable"].astype(bool) | reason.eq(START_PASSED))
    c = PC.closes(pulls.assign(usable=open_)).set_index("matchup_id")
    t = _utc(pulls["retrieved_at"])
    times = pd.DatetimeIndex(sorted(t.unique()))
    state = {k: ("in play" if lv else ("cutoff passed" if why == CUTOFF_PASSED else "unpriced"))
             for k, lv, why in zip(zip(pulls["matchup_id"], t), live, reason)}
    nxt, gap, how = [], [], []
    for mid, r in c.iterrows():
        i = times.searchsorted(r["close_pull"], side="right")
        if i >= len(times):                          # no later pull: nothing says the market closed
            nxt.append(pd.NaT), gap.append(float("nan")), how.append(None)
            continue
        nxt.append(times[i])
        gap.append((times[i] - r["close_pull"]).total_seconds() / 60)
        how.append(state.get((mid, times[i]), "gone"))
    c["next_pull"], c["next_gap_min"], c["next_state"] = nxt, gap, how
    c["true_close"] = c["next_state"].isin(CLOSED) & (c["next_gap_min"] <= CLOSE_GAP_MIN)
    return c


# --- TennisExplorer -------------------------------------------------------------------------------------------------

def te_tables(root: Path = TE) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """The site's tour matches, Pinnacle's row of each (with the site's other books as its referee: the odds input's
    test) and Pinnacle's every price record by site id; empty when the site's tables are not staged."""
    root = Path(root)
    if not (root / "matches.parquet").exists() or not (root / "odds.parquet").exists():
        return pd.DataFrame(), pd.DataFrame(), {}
    from src.ingest import tennisexplorer as TEI
    tm = pd.read_parquet(root / "matches.parquet")
    od = pd.read_parquet(root / "odds.parquet")
    pin = od[od["book"].eq("Pinnacle")].drop_duplicates("te_id").set_index("te_id").join(TEI.books_referee(od))
    moves = {}
    if (root / "moves.parquet").exists():
        mv = pd.read_parquet(root / "moves.parquet", filters=[("book", "==", "Pinnacle")])
        mv = mv.assign(t=_utc(mv["t_utc"])).sort_values("t", kind="stable")
        moves = {int(k): g for k, g in mv.groupby("te_id")}
    return tm, pin, moves


def te_link(m: pd.DataFrame, tm: pd.DataFrame) -> pd.DataFrame:
    """Each match (columns match_id, tour, round, player_a, player_b, start) linked to one of the site's matches of the
    same tour listed within LINK_DAYS: both players' name words the same, either order (the adapter's test), else its
    looser test (a surname word shared, a first initial in common); two candidates split by the round. Qualifying is
    never linked: the site's tour pages hold none. Index match_id; columns te_id, a_is_p2 (A is the site's second
    player), te_link (which test)."""
    rows = {}
    if not tm.empty and not m.empty:
        from src.ingest import tennisexplorer as TEI
        tm = tm.assign(t1=tm["p1"].map(TEI.name_tokens), t2=tm["p2"].map(TEI.name_tokens), start=_utc(tm["start_utc"]))
        by_tour = {k: g for k, g in tm.groupby("tour")}
        for r in m.itertuples():
            g = by_tour.get(r.tour)
            if g is None or pd.isna(r.start) or str(r.round).startswith("Q"):
                continue
            w = g[(g["start"] - r.start).abs() <= pd.Timedelta(days=LINK_DAYS)]
            ta, tb = TEI.name_tokens(r.player_a), TEI.name_tokens(r.player_b)
            hits, how = [], None
            for test, how in ((TEI._same_tokens, "names"), (TEI._close_tokens, "close names")):
                hits = [(x, False) for x in w.itertuples() if test(x.t1, ta) and test(x.t2, tb)] + \
                       [(x, True) for x in w.itertuples() if test(x.t1, tb) and test(x.t2, ta)]
                if len(hits) > 1:
                    hits = [h for h in hits if TEI._same_round(str(r.round), h[0].round)] or hits
                if hits:
                    break
            if len(hits) == 1:
                rows[r.match_id] = {"te_id": int(hits[0][0].te_id), "a_is_p2": bool(hits[0][1]), "te_link": how,
                                    "te_start": hits[0][0].start}
    out = pd.DataFrame.from_dict(rows, orient="index")
    return out.rename_axis("match_id") if rows else \
        pd.DataFrame(columns=["te_id", "a_is_p2", "te_link", "te_start"], index=pd.Index([], name="match_id"))


def te_close(p: pd.Series) -> dict:
    """The site's last Pinnacle prices of its first and second player, the time of its last record (a change, else the
    opening), and why it is not used (te_note): untimed, incoherent, or far from the site's other books (odds_input's
    test of 22 Oct 2026, with the odds study's thresholds); None when used."""
    from src.eda.odds_sources import common as OC
    from src.eda.odds_sources import quality as Q
    d1, d2 = _f(p.get("k1_last")), _f(p.get("k2_last"))
    stamps = [_utc(x) for x in (p.get("k1_last_t"), p.get("k2_last_t"), p.get("k1_open_t"), p.get("k2_open_t"))
              if isinstance(x, str) and x]
    stamps = [x for x in stamps if not pd.isna(x)]
    out = {"te_d1": d1, "te_d2": d2, "te_t": max(stamps) if stamps else pd.NaT, "te_note": None}
    if not bool(OC.coherent(d1, d2)):
        out["te_note"] = "incoherent prices"
    elif not stamps:
        out["te_note"] = "no time on the site's price"
    else:
        p1, z, n, iqr = _devig(d1, d2), _f(p.get("z")), _f(p.get("n")), _f(p.get("iqr"))
        if n >= Q.MIN_REF and iqr < Q.AGREE and abs(_logit(p1) - z) > Q.GROSS and \
                abs(p1 - 1 / (1 + math.exp(-z))) > Q.GROSS_PP:
            out["te_note"] = "the site's Pinnacle far from its other books"
    return out


def te_price_at(moves: pd.DataFrame | None, side: str, t) -> float:
    """The site's Pinnacle price of a side ("k1", "k2") at time t: its latest record (the opening or a change) at or
    before t; NaN before the first."""
    if moves is None or pd.isna(t):
        return float("nan")
    s = moves[moves["side"].eq(side) & (moves["t"] <= t)]
    return float(s["odds"].iloc[-1]) if len(s) else float("nan")


# --- results --------------------------------------------------------------------------------------------------------

def stage0_path(runs: Path = CFG.DAILY_RUNS) -> Path | None:
    """The freshest Stage 0 on disk: the repository's (rebuilt by B6), the data check's (A3b) or the newest live run's
    own (built from that run's downloads)."""
    cands = [CFG.STAGE0 / "stage0_matches.parquet", CFG.OUT / "data_check" / "stage0" / "stage0_matches.parquet"]
    cands += sorted(Path(runs).glob("live_*/stage0/stage0_matches.parquet"))[-1:]
    cands = [p for p in cands if p.exists()]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def _event_key(name) -> str:
    return " ".join(str(name).lower().replace("-", " ").split()) if isinstance(name, str) else ""


def results(m: pd.DataFrame, path: Path | None) -> pd.DataFrame:
    """Each match's result, side A's: by its id (a played match keeps the live row's id), else the one Stage 0 match of
    the same tour, pair of players, round and event name dated from RESULT_DAYS[0] days before the match's day to
    RESULT_DAYS[1] after (a qualifying event built from its previous edition, a women's event id that differs). Never
    an earlier meeting at another event. A pairing Stage 0 shows replaced (that event and round has one of its two
    players against someone else: a withdrawal) is "not played as listed". Columns result_status, a_won, result_by."""
    out = pd.DataFrame(index=m.index, columns=["result_status", "a_won", "result_by"], dtype=object)
    if path is None or m.empty:
        return out
    cols = ["match_id", "tour", "round", "tournament_name", "tournament_date", "status", "a_won", "player_a_id",
            "player_b_id"]
    s0 = pd.read_parquet(path, columns=cols).astype({"match_id": str, "player_a_id": str, "player_b_id": str})
    s0["date"] = pd.to_datetime(s0["tournament_date"], errors="coerce")
    players = set(m["player_a_id"].astype(str)) | set(m["player_b_id"].astype(str))
    since = pd.to_datetime(m["day"], errors="coerce").min() - pd.Timedelta(days=RESULT_DAYS[0])
    s0 = s0[s0["match_id"].isin(m.index) | ((s0["player_a_id"].isin(players) | s0["player_b_id"].isin(players))
                                            & (s0["date"] >= since))].copy()
    by_id = s0.drop_duplicates("match_id").set_index("match_id")
    s0["pair"] = [frozenset(x) for x in zip(s0["player_a_id"], s0["player_b_id"])]
    s0["event"] = s0["tournament_name"].map(_event_key)
    tournaments = m["tournament"] if "tournament" in m.columns else pd.Series("", index=m.index)
    for mid, r in m.iterrows():
        hit, how = None, None
        if mid in by_id.index:
            hit, how = by_id.loc[mid], "match id"
        else:
            day = pd.to_datetime(r["day"], errors="coerce")
            if pd.isna(day):
                continue
            pair = frozenset((str(r["player_a_id"]), str(r["player_b_id"])))
            g = s0[s0["tour"].eq(r["tour"]) & s0["round"].eq(r["round"]) & s0["event"].eq(_event_key(tournaments[mid]))
                   & (s0["date"] >= day - pd.Timedelta(days=RESULT_DAYS[0]))
                   & (s0["date"] <= day + pd.Timedelta(days=RESULT_DAYS[1]))]
            same = g[g["pair"].eq(pair)]
            if len(same) == 1:
                hit, how = same.iloc[0], "players, round and event"
            elif same.empty and g["pair"].map(lambda p: len(p & pair) == 1).any():
                out.loc[mid] = ["not played as listed", None, "the event's draw"]
        if hit is None:
            continue
        won = hit["a_won"]
        if not pd.isna(won) and str(hit["player_a_id"]) != str(r["player_a_id"]):
            won = 1 - int(won)                        # Stage 0's side A is the record's side B
        out.loc[mid] = [hit["status"], None if pd.isna(won) else int(won), how]
    return out


# --- the ledger -----------------------------------------------------------------------------------------------------

def _curves(runs: Path, names) -> dict:
    """Each run's curve per match: (odds_logit, q_a) sorted by price; a run without curves.parquet gives none."""
    out = {}
    for run in names:
        p = Path(runs) / str(run) / "curves.parquet"
        if p.exists():
            c = pd.read_parquet(p, columns=["match_id", "odds_logit", "q_a"]).astype({"match_id": str})
            for mid, g in c.groupby("match_id"):
                g = g.sort_values("odds_logit")
                out[(str(run), mid)] = (g["odds_logit"].to_numpy(float), g["q_a"].to_numpy(float))
    return out


def _home_is_a(home_side, home, player_a, player_b) -> bool | None:
    """Whether Pinnacle's home player is side A: the record's home_side, else the names."""
    if home_side in ("A", "B"):
        return home_side == "A"
    k = DG.name_key(home) if isinstance(home, str) else None
    if k and isinstance(player_a, str) and k == DG.name_key(player_a):
        return True
    if k and isinstance(player_b, str) and k == DG.name_key(player_b):
        return False
    return None


def match_closes(m: pd.DataFrame, own: pd.DataFrame, te: tuple, now: pd.Timestamp) -> pd.DataFrame:
    """Per match (m's index): the close by the module's rules, with each source's own reading beside it."""
    tm, pin, _ = te
    link = te_link(m.assign(start=_utc(m["start_utc"])).reset_index(), tm)
    rows = {}
    for mid, r in m.iterrows():
        x = {"close_kind": None, "close_source": None, "close_t": pd.NaT, "close_odds_a": np.nan,
             "close_odds_b": np.nan}
        # Pinnacle's own pulls
        pid = r["pinnacle_matchup_id"]
        o = own.loc[pid] if not pd.isna(pid) and len(own) and pid in own.index else None
        home_a = _home_is_a(r.get("home_side"), o["home"], r["player_a"], r["player_b"]) if o is not None else None
        if o is not None and home_a is not None:
            da, db = (o["decimal_home"], o["decimal_away"]) if home_a else (o["decimal_away"], o["decimal_home"])
            x.update(own_t=o["close_pull"], own_odds_a=_f(da), own_odds_b=_f(db), own_start=o["final_start"],
                     own_next_t=o["next_pull"], own_next_state=o["next_state"],
                     own_next_gap_min=_f(o["next_gap_min"]), own_true_close=bool(o["true_close"]),
                     own_pulls=int(o["n_pulls"]))
        # the site's last Pinnacle price
        if mid in link.index:
            lk = link.loc[mid]
            tid = int(lk["te_id"])
            x.update(te_id=tid, te_link=lk["te_link"], te_start=lk["te_start"], te_side_a="k2" if lk["a_is_p2"] else "k1")
            if tid in pin.index:
                c = te_close(pin.loc[tid])
                a, b = ("te_d2", "te_d1") if lk["a_is_p2"] else ("te_d1", "te_d2")
                x.update(te_odds_a=c[a], te_odds_b=c[b], te_t=c["te_t"], te_note=c["te_note"])
            else:
                x["te_note"] = "no Pinnacle price on the site's page"
        # the start: the latest listed (Pinnacle's last pull, the site's page), else the sheet's; never after our pulls
        # saw the pre-match market shut (Pinnacle can list a later start for a match that is already on)
        starts = [s for s in (x.get("own_start"), x.get("te_start")) if s is not None and not pd.isna(s)]
        start = max(starts) if starts else _utc(r["start_utc"])
        if x.get("own_true_close") and not pd.isna(x.get("own_next_t")):
            start = x["own_next_t"] if pd.isna(start) else min(start, x["own_next_t"])
        x["start_final"] = start
        own_c = ("pinnacle pull", x["own_t"], x["own_odds_a"], x["own_odds_b"]) if "own_t" in x else None
        te_c = ("tennisexplorer", x["te_t"], x["te_odds_a"], x["te_odds_b"]) \
            if not pd.isna(x.get("te_t", pd.NaT)) and x.get("te_note") is None else None
        same = own_c is not None and te_c is not None and abs(own_c[2] - te_c[2]) <= SAME_PRICE and \
            abs(own_c[3] - te_c[3]) <= SAME_PRICE
        # a later pull of ours that saw another price than the site's last record: the site missed a late move; one that
        # saw the same price shows it held until then
        overtaken = own_c is not None and te_c is not None and own_c[1] > te_c[1] and not same
        if te_c is not None and same and own_c[1] > te_c[1]:
            te_c = (te_c[0], own_c[1], te_c[2], te_c[3])
        recent = not pd.isna(start) and now < start + pd.Timedelta(hours=AWAIT_HOURS)
        held = te_c is not None and not pd.isna(start) and (start - te_c[1]).total_seconds() / 60 <= CLOSE_LEAD_MAX_MIN
        c = None
        if own_c is not None and x["own_true_close"]:
            kind, c = "close", own_c
        elif not pd.isna(start) and now < start:
            kind = "pending"
        elif te_c is not None and not overtaken:
            # the site's last record (the close the training data uses), as the close only when known to hold near
            # the start
            kind, c = ("close" if held else "last seen"), te_c
        elif te_c is None and "te_id" not in x and recent and not str(r["round"]).startswith("Q"):
            kind = "awaiting"                         # the site's page of a finished match comes with the daily download
        elif own_c is not None:
            kind, c = "last seen", own_c              # an earlier price only (or one the site's record missed)
        else:
            kind = "none"
        x["close_kind"] = kind
        if c is not None:                             # an earlier price only: its time, never its odds as the close
            x.update(close_source=c[0], close_t=c[1])
            if kind == "close":
                x.update(close_odds_a=c[2], close_odds_b=c[3])
            if not pd.isna(start):
                x["close_min_before_start"] = (start - c[1]).total_seconds() / 60
        rows[mid] = x
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("match_id")


def _row_metrics(r: dict, curves: dict, moves: dict) -> dict:
    """One row's drift, CLV, the model at the close, the log losses and the site's price at the sheet's quote time."""
    out = {}
    p_q, q = _f(r.get("p_market_a")), _f(r.get("q_a"))
    p_c = _devig(r.get("close_odds_a"), r.get("close_odds_b"))
    quoted, start = _utc(r.get("quoted_at")), r.get("start_final")
    out["quote_lead_min"] = (start - quoted).total_seconds() / 60 \
        if not pd.isna(quoted) and start is not None and not pd.isna(start) else float("nan")
    out["p_close_a"] = p_c
    out["overround_close"] = (1 / _f(r.get("close_odds_a")) + 1 / _f(r.get("close_odds_b"))) \
        if math.isfinite(p_c) else float("nan")
    out["drift_pts_a"] = 100 * (p_c - p_q)
    out["drift_logit_a"] = _logit(p_c) - _logit(p_q)
    lean = _logit(q) - _logit(p_q)
    out["lean_logit_a"] = lean
    out["toward_model_logit"] = math.copysign(1.0, lean) * out["drift_logit_a"] \
        if math.isfinite(lean) and lean != 0 else float("nan")
    curve = curves.get((str(r.get("run")), str(r.get("match_id"))))
    out["curve_q_at_quote"] = DG.q_at(*curve, p_q) if curve and math.isfinite(p_q) else float("nan")
    out["q_close_a"] = DG.q_at(*curve, p_c) if curve and math.isfinite(p_c) else float("nan")
    pick = r.get("pick") if r.get("pick") in ("A", "B") else ""
    if pick:
        a = pick == "A"
        d_taken = _f(r.get("pinnacle_odds_a") if a else r.get("pinnacle_odds_b"))
        d_c = _f(r.get("close_odds_a") if a else r.get("close_odds_b"))
        pc, pq, qc = (p_c, p_q, out["q_close_a"]) if a else (1 - p_c, 1 - p_q, 1 - out["q_close_a"])
        out.update(d_taken=d_taken, d_close_pick=d_c, p_close_pick=pc, clv_ev=pc * d_taken - 1,
                   clv_price=d_taken / d_c - 1, drift_pick_pts=100 * (pc - pq), q_close_pick=qc,
                   edge_close_pick=qc - 1 / d_c, ev_close_pick=qc * d_c - 1)
    # the result, and the log losses (lower is better) of the model, the sheet's price, the close, the model at it
    won = r.get("a_won")
    if r.get("result_status") in DONE and won is not None and not pd.isna(won):
        y = int(won)
        for name, p in (("ll_q", q), ("ll_quote", p_q), ("ll_close", p_c), ("ll_q_close", out["q_close_a"])):
            if math.isfinite(p):
                p = min(max(p, 1e-9), 1 - 1e-9)
                out[name] = -math.log(p) if y else -math.log(1 - p)
        if pick:
            out["pick_won"] = int((pick == "A") == bool(y))
    # the site's Pinnacle price at the sheet's quote time, beside the sheet's own (a check of the link and the sides)
    side_a = r.get("te_side_a")
    if isinstance(side_a, str) and not pd.isna(r.get("te_id")):
        mv = moves.get(int(r["te_id"]))
        out["te_at_quote_a"] = te_price_at(mv, side_a, quoted)
        out["te_at_quote_b"] = te_price_at(mv, "k1" if side_a == "k2" else "k2", quoted)
    return out


def _metrics_or_error(r: dict, curves: dict, moves: dict) -> dict:
    """_row_metrics, or none for a row whose figures fail (said with "!!!"): the other rows keep theirs."""
    try:
        return _row_metrics(r, curves, moves)
    except Exception as exc:  # noqa: BLE001 - one row's error is said; the others are measured
        print(f"!!! ERROR measuring {r.get('player_a')} v {r.get('player_b')} of {r.get('sheet_file')} "
              f"({type(exc).__name__}: {exc}): its closing-line figures are left empty")
        return {}


def build(*, predictions: Path = CFG.PREDICTIONS, runs: Path = CFG.DAILY_RUNS, pulls=PULLS, te: Path = TE,
          stage0: Path | None = None, now=None) -> tuple[pd.DataFrame, dict]:
    """The ledger (one row per sheet and predicted match, the columns COLUMNS) and what it was built from. stage0: a
    Stage 0 matches file for the results (default: the freshest, stage0_path)."""
    now = _utc(now) if now is not None else pd.Timestamp.now(tz="UTC")
    rows = sheet_rows(predictions)
    meta = {"built_at": now.isoformat(timespec="seconds"), "sheets": 0}
    if rows.empty:
        return pd.DataFrame(columns=COLUMNS), meta
    rows["pinnacle_matchup_id"] = _matchup_ids(rows, runs)
    rows = rows.sort_values(["made_at", "sheet_file"], kind="stable").reset_index(drop=True)
    # each match as its newest sheet lists it; Pinnacle's matchup id from the newest sheet that has one
    keep = ["tour", "tournament", "round", "day", "start_utc", "player_a", "player_b", "player_a_id", "player_b_id"]
    keep += ["home_side"] if "home_side" in rows.columns else []
    m = rows.groupby("match_id").tail(1).set_index("match_id")[keep].copy()
    ids = rows.dropna(subset=["pinnacle_matchup_id"]).groupby("match_id")["pinnacle_matchup_id"].last()
    m["pinnacle_matchup_id"] = ids.reindex(m.index).astype("Int64")
    pl = pinnacle_pulls(pulls)
    own = own_closes(pl)
    tet = te_tables(te)
    s0 = Path(stage0) if stage0 else stage0_path(runs)
    led = rows.drop(columns=["pinnacle_matchup_id"]).join(match_closes(m, own, tet, now), on="match_id") \
        .join(results(m, s0), on="match_id")
    led["pinnacle_matchup_id"] = led["match_id"].map(m["pinnacle_matchup_id"]).astype("Int64")
    for c in TIMES:
        if c in led.columns:
            led[c] = _utc(led[c])
    curves = _curves(runs, led["run"].dropna().unique())
    metrics = pd.DataFrame([_metrics_or_error(r, curves, tet[2]) for r in led.to_dict("records")], index=led.index)
    led = pd.concat([led, metrics], axis=1)
    # the views: the match's first sheet, and its last sheet made before the start (rows are in the sheets' order); a
    # match whose every sheet came after its listed start keeps its last one (tennis starts run late), so flagged
    led["first_sheet"] = ~led.duplicated("match_id", keep="first")
    led["made_after_start"] = led["start_final"].notna() & (led["made_at"] >= led["start_final"])
    before = led[~led["made_after_start"]]
    late = led[~led["match_id"].isin(before["match_id"])]
    led["last_before_start"] = led.index.isin(before.groupby("match_id").tail(1).index.union(
        late.groupby("match_id").tail(1).index))
    led = led.reindex(columns=COLUMNS)
    meta.update({
        "sheets": int(rows["sheet_file"].nunique()), "rows": int(len(led)), "matches": int(led["match_id"].nunique()),
        "first_sheet_at": rows["made_at"].min().isoformat(), "last_sheet_at": rows["made_at"].max().isoformat(),
        "pulls": {CFG.rel(r): len(list(Path(r).glob("20*/*.parquet"))) for r in pulls}, "pull_rows": int(len(pl)),
        "tennisexplorer": {n: _written(Path(te) / n) for n in ("matches.parquet", "odds.parquet", "moves.parquet")},
        "tennisexplorer_matches": int(len(tet[0])),
        "stage0": CFG.rel(s0) if s0 else None, "stage0_written": _written(s0),
        "checks": checks(led)})
    return led, meta


def checks(led: pd.DataFrame) -> dict:
    """Two readings a wrong link, side or curve would show: the run's curve read at the sheet's price against the
    sheet's own model chance, and the site's Pinnacle price at the sheet's quote time against the sheet's Pinnacle price
    (both sides within 0.01: the site records each change to the minute, so a change in that minute differs)."""
    d = (pd.to_numeric(led["curve_q_at_quote"]) - pd.to_numeric(led["q_a"])).abs().dropna()
    s = led[led["price_source"].eq("pinnacle")].dropna(subset=["te_at_quote_a", "te_at_quote_b"])
    near = lambda a, b: (s[a].astype(float) - s[b].astype(float)).abs() <= 0.01   # noqa: E731
    same = near("te_at_quote_a", "pinnacle_odds_a") & near("te_at_quote_b", "pinnacle_odds_b")
    swapped = near("te_at_quote_a", "pinnacle_odds_b") & near("te_at_quote_b", "pinnacle_odds_a") & ~same
    return {"curve_vs_sheet_q": {"rows": int(len(d)), "max_abs": float(d.max()) if len(d) else None},
            "site_vs_sheet_price": {"rows": int(len(s)), "same": int(same.sum()), "sides_swapped": int(swapped.sum())}}


# --- the summary ----------------------------------------------------------------------------------------------------

def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def mean_ci(x) -> dict:
    """n, the mean, its 95% interval (normal approximation), P(above 0) and the share above 0."""
    x = pd.to_numeric(pd.Series(x, dtype=object), errors="coerce").dropna().to_numpy(float)
    n = len(x)
    if n == 0:
        return {"n": 0}
    mean = float(x.mean())
    out = {"n": n, "mean": mean, "share_above_0": float((x > 0).mean())}
    se = float(x.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    if math.isfinite(se) and se > 0:
        out.update(lo=mean - 1.96 * se, hi=mean + 1.96 * se, p_above_0=_phi(mean / se))
    return out


def slope_ci(x, y) -> dict:
    """The slope of y on x through the origin (sides A and B are arbitrary), its 95% interval, n."""
    d = pd.DataFrame({"x": pd.to_numeric(pd.Series(x, dtype=object), errors="coerce").to_numpy(float),
                      "y": pd.to_numeric(pd.Series(y, dtype=object), errors="coerce").to_numpy(float)}).dropna()
    d = d[d["x"] != 0]
    n = len(d)
    if n < 3:
        return {"n": n}
    sxx = float((d["x"] ** 2).sum())
    b = float((d["x"] * d["y"]).sum() / sxx)
    se = math.sqrt(float(((d["y"] - b * d["x"]) ** 2).sum()) / (n - 1) / sxx)
    return {"n": n, "slope": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se}


def verdict(r: dict, *, pct: bool = True, unit: str = "", digits: int = 1) -> str:
    """"+1.2% [-0.8%, +3.2%], n = 25: unresolved, P(above 0) 0.88": above or below 0 only when the 95% interval clears
    it, never "tie" (the project's reporting rule)."""
    if not r.get("n"):
        return "none yet"
    f = (lambda v: f"{100 * v:+.{digits}f}%") if pct else (lambda v: f"{v:+.{digits}f}")
    if "lo" not in r:
        return f"{f(r['mean'])}{unit} (n = {r['n']}: no interval)"
    word = "above 0" if r["lo"] > 0 else ("below 0" if r["hi"] < 0 else f"unresolved, P(above 0) {r['p_above_0']:.2f}")
    return f"{f(r['mean'])}{unit} [{f(r['lo'])}, {f(r['hi'])}], n = {r['n']}: {word}"


def summarize(led: pd.DataFrame, meta: dict | None = None) -> dict:
    """The ledger read on each match's last sheet before the start: how many closes were found, the picks' CLV, the
    line's move toward the model, the picks still +EV at the close, and the log losses of the graded matches."""
    meta = meta or {}
    if led.empty:
        return {"lines": ["No bet sheet yet: the ledger fills from A5's sheets."], "counts": {}}
    v = led[led["last_before_start"].astype(bool)]
    n_bets = int(v["decision"].eq("BET").sum())
    void = v["result_status"].isin(VOID)                  # no bet stands on a match not played as listed
    n_void, v = int(void.sum()), v[~void]
    kinds = v["close_kind"].value_counts().to_dict()
    closed, early = v[v["close_kind"].eq("close")], v[v["close_kind"].eq("last seen")]
    src = closed["close_source"].value_counts().to_dict()
    te_lead = _f(pd.to_numeric(closed.loc[closed["close_source"].eq("tennisexplorer"), "close_min_before_start"]).median())
    early_lead = _f(pd.to_numeric(early["close_min_before_start"]).median())
    no_close = v[v["close_kind"].isin(["last seen", "none"])]
    qual = int(no_close["round"].astype(str).str.startswith("Q").sum())
    bets = closed[closed["decision"].eq("BET")]
    price, clv = mean_ci(bets["clv_price"]), mean_ci(bets["clv_ev"])
    at_close = mean_ci(1 / pd.to_numeric(bets["overround_close"]) - 1)    # a bet at the closing price itself
    toward = mean_ci(bets["drift_pick_pts"])
    slope = slope_ci(closed["lean_logit_a"], closed["drift_logit_a"])
    still = pd.to_numeric(bets["ev_close_pick"]).dropna()
    graded = closed.dropna(subset=["ll_q", "ll_close"])
    vs_close = mean_ci(1000 * (graded["ll_close"].astype(float) - graded["ll_q"].astype(float)))   # mLL: + = model
    vs_quote = mean_ci(1000 * (graded["ll_quote"].astype(float) - graded["ll_q"].astype(float)))
    ck = meta.get("checks") or {}
    site, curve = ck.get("site_vs_sheet_price") or {}, ck.get("curve_vs_sheet_q") or {}
    lines = [
        f"{meta.get('sheets', led['sheet_file'].nunique())} bet sheets ({BS.when(led['made_at'].min())} to "
        f"{BS.when(led['made_at'].max())}) made {len(led)} predictions of {led['match_id'].nunique()} matches, "
        f"{n_bets} of them picks. Each match is read on its last sheet before the start, the one a bet most likely "
        "came from.",
        f"Closing price found for {len(closed)} matches: {src.get('pinnacle pull', 0)} true closes from Pinnacle's own "
        f"listing (read within {CLOSE_GAP_MIN} minutes of its pre-match market shutting) and "
        f"{src.get('tennisexplorer', 0)} from TennisExplorer's record of Pinnacle, the close the model's training data "
        f"uses, where it is known to hold within {CLOSE_LEAD_MAX_MIN // 60} hours of the start" +
        (f" (a median {te_lead:.0f} minutes before it)." if math.isfinite(te_lead) else "."),
        f"No close yet: {kinds.get('pending', 0)} not started, {kinds.get('awaiting', 0)} waiting for the next daily "
        f"download, {len(early)} with only an earlier price (ours, or TennisExplorer's record ending earlier)" +
        (f", a median {early_lead / 60:.1f} hours before the start: left out below" if math.isfinite(early_lead)
         else "") + f"; {kinds.get('none', 0)} with no price at all; {n_void} void (a walkover, or the pairing "
                    "changed before the match)." +
        (f" {qual} of the last two kinds are qualifying matches: TennisExplorer has no qualifying pages, so only "
         "Pinnacle's own listing read near the start gives their close." if qual else ""),
        f"Closing-line value of the {len(bets)} picks with a close (the odds taken against the closing odds, both with "
        f"Pinnacle's margin; higher is better): {verdict(price)}. The line moved toward the pick by "
        f"{verdict(toward, pct=False, unit=' points', digits=2)}.",
        f"Their expected profit if the closing price, margin removed, is the true chance: {verdict(clv)}. A bet at the "
        "closing price itself scores " + (f"{100 * at_close['mean']:+.1f}%" if at_close.get("n") else "minus the margin")
        + " by this measure (Pinnacle's margin), so the picks are judged against that, not against 0.",
        "Did the line move toward the model? Across the matches with a close, the market closed " +
        (f"{slope['slope']:+.2f} [{slope['lo']:+.2f}, {slope['hi']:+.2f}] of the model's disagreement with the "
         f"sheet's price (n = {slope['n']}; 0 = not at all, 1 = all the way; the backtest found {BET_TIMING_SLOPE})."
         if "slope" in slope else "(too few matches yet)."),
        f"At the closing price the model, re-read off its curve there, still gave {int((still > 0).sum())} of "
        f"{len(still)} picks a positive expected profit.",
        (f"Graded matches: the model at the sheet's price against the closing price, log loss "
         f"{verdict(vs_close, pct=False, unit=' mLL')} (above 0: the model was better); against the price it was fed, "
         f"{verdict(vs_quote, pct=False, unit=' mLL')}. A few hundred matches resolve little."
         if vs_close.get("n") else
         "Graded matches: none yet (results come with the next Stage 0 build: A3b, A4 or B6)."),
        "This checks the prices we got, not the model: the market does not move toward this model before the close, "
        "so the model's alarm is the strength of its lean (production-integrity plan, principle 8). These are the "
        "sheets' picks at the sheet's price, not the bets placed: nothing records those yet.",
        f"Checks: TennisExplorer's record of Pinnacle at each sheet's quote time equals the sheet's own price on "
        f"{site.get('same', 0)} of {site.get('rows', 0)} readings ({site.get('sides_swapped', 0)} with the sides "
        "swapped); the run's curve re-read at the sheet's price is within " +
        (f"{100 * curve['max_abs']:.2f} points" if curve.get("max_abs") is not None else "?") +
        " of the sheet's chance."]
    return {"lines": lines, "counts": {"close_kind": kinds, "close_source": src, "picks": n_bets},
            "clv_price": price, "clv_ev": clv, "ev_of_a_bet_at_the_close": at_close, "drift_toward_pick_pts": toward,
            "move_toward_model": slope, "picks_still_ev_at_close": {"n": int(len(still)), "still": int((still > 0).sum())},
            "mll_model_vs_close": vs_close, "mll_model_vs_quote": vs_quote, "checks": ck}


def table(led: pd.DataFrame, recent: int = 30) -> pd.DataFrame:
    """The picks, each on its last sheet before the start, newest first: what was taken, the close, the drift, the CLV."""
    b = led[led["last_before_start"].astype(bool) & led["decision"].eq("BET")]
    b = b.sort_values("start_final", ascending=False, na_position="last").head(recent)

    def source(r) -> str:
        k, mins = r["close_kind"], _f(r["close_min_before_start"])
        if k == "close":
            return "Pinnacle's own, close" if r["close_source"] == "pinnacle pull" else \
                "TennisExplorer" + (f", {mins:.0f} min before" if math.isfinite(mins) else "")
        if k == "last seen":
            return "earlier price only" + (f", {mins / 60:.1f} h before" if math.isfinite(mins) else "")
        return {"pending": "not started", "awaiting": "awaiting download"}.get(k, "no price")

    def result(r) -> str:
        if not pd.isna(r["pick_won"]):
            return "won" if int(r["pick_won"]) else "lost"
        return r["result_status"] if isinstance(r["result_status"], str) else ""

    closed = b["close_kind"].eq("close")                  # an earlier price only is shown as such, without figures
    pct = lambda s: s.where(closed).map(lambda x: f"{100 * x:+.1f}%" if math.isfinite(_f(x)) else "")   # noqa: E731
    us = lambda d: BS.us(d) if math.isfinite(_f(d)) else ""             # noqa: E731
    return pd.DataFrame({
        "Start": b["start_final"].map(BS.when),
        "Event": b["tour"].astype(str).str.upper() + " " + b["tournament"].astype(str) + " " + b["round"].astype(str),
        "Match": b["player_a"].astype(str) + " v " + b["player_b"].astype(str), "Pick": b["pick_player"],
        "Sheet": b["made_at"].map(BS.when), "Taken": b["d_taken"].map(us),
        "Close": b["d_close_pick"].where(closed).map(us), "Close from": b.apply(source, axis=1),
        "Line toward pick": b["drift_pick_pts"].where(closed).map(
            lambda x: f"{_f(x):+.1f} pts" if math.isfinite(_f(x)) else ""),
        "Beat close by": pct(b["clv_price"]), "EV if close is fair": pct(b["clv_ev"]),
        "Model EV at close": pct(b["ev_close_pick"]), "Result": b.apply(result, axis=1)})


def _show(summary: dict, tab: pd.DataFrame, files: dict) -> None:
    lines = summary["lines"] + [f"{k}: {v}" for k, v in files.items()]
    if BS._in_notebook():
        from IPython.display import HTML, display
        body = "".join(f"<div style='margin:2px 0'>{html.escape(x)}</div>" for x in lines)
        grid = tab.to_html(index=False, escape=True, border=0) if len(tab) else "<div>No pick yet.</div>"
        display(HTML(f"<div style='font-family:Segoe UI,Calibri,sans-serif'><h3 style='margin:4px 0'>Closing line"
                     f"</h3>{body}<div style='margin-top:6px'>{grid}</div></div>"))
    else:
        print("\n".join(lines))
        if len(tab):
            with pd.option_context("display.width", 250, "display.max_columns", 20, "display.max_colwidth", 40):
                print(tab.to_string(index=False))


def clv_ledger(*, now=None, write: bool = True, show: bool = True, recent: int = 30) -> pd.DataFrame:
    """A8: the closing-line ledger rebuilt from every bet sheet (the module's notes), its summary shown (each match on
    its last sheet before the start; the newest `recent` picks in a table) and written to predictions/clv/. The reading
    leaves out a switched-off tour (config.BET_TOURS), the ledger file keeps it. Returns the ledger."""
    led, meta = build(now=now)
    off = CFG.off_mask(led)
    shown = led[~off]
    summary = summarize(shown, meta) if len(shown) or not len(led) else {"lines": [], "counts": {}}
    if off.any():
        summary["lines"].insert(0, f"{CFG.off_names().capitalize()} matches are switched off (the owner, 28 Oct 2026): "
                                   f"this reading leaves out the {int(off.sum())} {CFG.off_names()} predictions of "
                                   f"earlier sheets ({led.loc[off, 'match_id'].nunique()} matches). The ledger file "
                                   "keeps them; config.BET_TOURS switches them back on.")
        summary["switched_off"] = {"bet_tours": list(CFG.BET_TOURS), "predictions": int(off.sum()),
                                   "matches": int(led.loc[off, "match_id"].nunique())}
    files = {}
    if write and len(led):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / "ledger.csv"
        led.to_csv(path, index=False)
        meta.update({"rules": __doc__, "code_sha256": {"closing_line.py": _sha(Path(__file__))},
                     "parameters": {"close_gap_min": CLOSE_GAP_MIN, "await_hours": AWAIT_HOURS,
                                    "link_days": LINK_DAYS, "result_days": RESULT_DAYS}})
        (OUT / "ledger.provenance.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
        (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
        files = {"Ledger (every sheet's every prediction)": CFG.rel(path), "Summary": CFG.rel(OUT / "summary.json")}
    if show:
        _show(summary, table(shown, recent), files)
    return led


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-write", action="store_true", help="show the summary only")
    ap.add_argument("--recent", type=int, default=30, help="picks in the table (default 30)")
    a = ap.parse_args(argv)
    clv_ledger(write=not a.no_write, recent=a.recent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
