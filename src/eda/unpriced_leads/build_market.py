"""S2c, the market-and-incentives builder of the unpriced-leads study (docs/studies/unpriced_leads/, 13 Oct 2026).

Brief: docs/studies/unpriced_leads/briefs/07_market_builder.md (binding); definitions: team/market_practitioner.md
sections 3.1, 3.3, 3.4, 3.5 and 5. Memo: docs/studies/unpriced_leads/team/market_builder.md.
Outputs (data/studies/unpriced_leads/candidates/market/): values.parquet (the statistics for every frame match, no result
column), splits.parquet (registered splits, flags and the books' own log-odds: prices only, gitignored), long.csv,
summary.csv, probes.json, coverage.json, extras.json (fits, reliability, correlations, checks), and the post-hoc
diagnostics_long.csv, diagnostics_summary.csv.

Every choice below was fixed before any screen of these statistics was run.

PRICES (no result is read to build them). Margins removed proportionally, as in the model's own odds input.
    BetOnline   OddsTrader's opening and last lines (data/dump/odds/oddstrader/betonline_matches.parquet: moneyline and
                total games), linked to the frame by the current instance's odds_sources.parquet `eid` (its a_won column
                is never read). The moneyline is oriented to A by matching the last line's (home, away) prices with
                odds_sources' ot8_a / ot8_b (BetOnline's last line from the every-book pull, already oriented to A): the
                closer assignment wins when the two differ by more than 0.001 in summed |log price ratio| and the closer
                one is within 0.05; else bet_timing's oriented lines decide (opening, then last line); else, when both
                lines are symmetric, either; else unknown. A valid opening: both sides, overround 1.00-1.20, not flagged
                broken by the adapter, stamped before the listed start. A valid last line: both sides, overround
                1.00-1.20, not flagged uncertain by the adapter (stamped > 30 min after the listed start, or not
                two-sided). Totals: the line as quoted (the over/under prices are not used: their margin-free over
                chance has IQR 0.489-0.511); a valid opening is not broken and stamped before the listed start; a valid
                last line is not flagged uncertain.
    Pinnacle    OddsTrader's timed opening (ot20o) and last line (ot20), oriented to A in odds_sources.parquet, to 7 Sep
                2025. The last line is valid when coherent, stamped <= 30 min after the listed start and, where
                tennis-data's faithful Pinnacle close exists (to 31 Jul 2025), within 0.5 log-odds of it (this drops
                OddsTrader's recording failures, e.g. the 2021 US Open). The opening is valid when coherent and stamped
                before the listed start.

MP-01, the totals market's view against the moneyline's (match level; two-sided).
    E[total line | moneyline] by least squares on frame matches of 2019-2024 (no outcome), separately for men's best of
    3, men's best of 5 and women's best of 3: total = b0 + b1 |L| + b2 L^2 + surface, indoor and level dummies + the
    pair's serve levels (the feature store's level sums lv__iosO_hold, lv__iosD_hold, lv__iosO_ace = U-222, U-229, U-217;
    leak-proof clock, probe passed), L = logit of BetOnline's own margin-free moneyline at the same moment (opening with
    opening, last with last). Frozen and applied to every season. Rows without the store's sums (the store ends 28 Jul
    2026; half of 2018's ids) use the same fit without the sums (flag mp01_nosums in splits.parquet).
    excess = (line - E) / SD (the group's residual SD in the fit).
    mp01_lop_close  context: -excess at the last lines. + = the totals market expects a more lopsided match than the
                    moneyline implies, so the price should be steeper (the harness's kind="context" slope modifier)
    mp01_lop_open   context: the same at the opening lines
    mp01_lop_move   context: minus the standardised residual of the totals' open-to-last move on the moneyline's move
                    (tg_last - tg_open = a + c1 d|L| + c2 d(L^2), least squares on 2019-2024 by group). + = the totals
                    moved toward a lopsided match beyond what the moneyline's move implies
    mp01_diff_close diff: the total-implied favourite strength minus the moneyline's, oriented to A:
                    sign(L_A) (u* - |L_A|), u* solving E_last(u*) = the last total line on the fitted curve's decreasing
                    branch within [0, the group's 99.5th percentile of |L|]. + = the totals say A is stronger than the
                    moneyline does
MP-02, line momentum (match level; two-sided).
    mp02_bol        logit(BetOnline's last line) - logit(its opening), oriented to A (2018 on)
    mp02_pin        logit(Pinnacle's last line) - logit(its opening) at OddsTrader, oriented to A (2018 - 7 Sep 2025)
    Tiers (splits.parquet): tour; level hi (Slam, 1000, Finals) / lo (500, 250); round: first (neither player has an
    earlier match at this event: same tournament id and date, qualifying included) / later; price: the favourite's
    chance by the book's own last line < 0.60, 0.60-0.75, >= 0.75; BetOnline's last line fresh (stamped within 60
    minutes before the listed start, or after it) / stale.
MP-10, each player's record against the close (player level; A - B).
    r = won - p over frame matches with tournament_date < 1 Jan 2025, p = the frame's p_mkt for that player (the close,
    Pinnacle first, margin-free). For a frame match M and player P: the last <= 60 of P's residual matches with
    lf + 1 <= es(M) (the match clock), ordered by (lf, k); value = sum r / (n + 30), 0 without history. The residual pool
    holds no match from 1 Jan 2025, so every 2025-26 value is the state frozen at 31 Dec 2024.
    Reliability gate (fixed before it was computed): players with >= 40 residual matches in 2013-2024; mean residual of
    their odd-numbered and even-numbered matches in time order; Pearson r across players; "shows reliability" = its 95%
    bootstrap interval (1,000 resamples of players, seed 20261013) lies above 0. Only then the role members are built:
    mp10_fav (the player's matches as the close's favourite, p > 0.5) and mp10_dog (as underdog, p < 0.5), each its own
    last <= 60.
MP-08, ranking cliffs (player level; A - B). Grand Slam Mondays T from Stage 0 (main draw; a Sunday start counts from the
    next day); the seeding ranking date is T - 7 days, the direct-entry ranking date T - 42 days; a match is in a window
    when its best-estimate day (the clock's obs) falls in the 28 days before that date. Lines: 32 seeds (band 28-40) and
    104 direct acceptances (band 90-120), both tours, every year. W = this match's win points (POINTS below: the next
    round's points minus this round's). P* = the line rank's points in the same week's ranking list (Stage 0's rank and
    rank_points of every player row whose event starts that week, any level; the median at the rank, else linear
    between the nearest ranks within 3): a published list, known before every match of its week.
    mp08_seed / mp08_entry: in the window and in the band, +1 if outside the line and P + W >= P* (this match's points
    could carry him across), else -1; 0 otherwise; NaN without a rank (or, when outside the line, without P* or W).
    mp08_seed_band / mp08_entry_band (secondary): the unsigned 1[in the window and in the band].
MP-09, points to defend (player level; A - B). The event's previous edition: same tour, same normalised tournament name
    (else the same id after its year prefix), starting 300-420 days earlier, the one closest to 364 days (a name match
    is preferred). The player's last main-draw row there gives the round reached; points from POINTS (qualifying points
    ignored; a win in a row with no later row counts as reaching the next round; the Finals: the sum of its
    round-robin, semifinal and final wins). mp09_defend = those points / his ranking points at this match (Stage 0),
    capped at 1, NaN without points; mp09_champ = 1[won the previous edition]. 0 when he did not play its main draw or
    no previous edition is found (flag mp09_prev_found in splits.parquet).

DATA-QUALITY RULES (fixed after an outcome-free look at the built values, before any screen): total-games lines outside
12.5-30.5 (best of 3) or 23.5-50.5 (best of 5) are recording faults and dropped (lines of 0.5, 106.5, 190.5, 211.5;
best-of-3-sized lines on best-of-5 matches), before the fit; MP-01's standardised statistics are clipped at +-4 SD;
an opening line that mirrors the last line (|L_open| > 0.7, opposite sign, |L_open + L_last| < 0.15) is a swapped-side
fault and gives no MP-02 move; MP-02's moves are clipped at +-1.5 log-odds.

TIMING. MP-10, MP-08 and MP-09 are built from H.long_table and checked with H.timing_probe (probes.json). MP-01 and MP-02
read only the match's own lines (no other match's facts); MP-01's expectation is a fit across 2019-2024 matches' lines
with no outcome (the brief's construction, applied in-sample to 2019-2024); MP-08's P* reads other players' published
ranking points of the same week's list, which predates every match of the week.
SCREENING on seasons <= 2024 (H.load_frame), raw and orthogonal part: beyond the odds input (L) and, for the books' own
statistics, beyond the book's own last line (L_bol: BetOnline; L_pin_ot: Pinnacle at OddsTrader). For a context
statistic the orthogonal part is s minus its projection on symmetric functions of the model's inputs (|A - B| of the 49
non-price inputs and the context dummies, by tour, with an intercept: orth_context), screened as context; r2_sym is the
R^2 of that projection (the harness's r2_inputs pairs a symmetric s with symmetric regressors).
POST-HOC DIAGNOSTICS (added after the main readings were seen; diagnostics_long.csv, diagnostics_summary.csv): the
close lens has no curvature term, so a context statistic correlated with |L| can borrow the favourite-longshot curvature.
D1 screens the curvature alone (s = |L|; s = |L_bol| beyond BetOnline's close); D2 re-screens each MP-01 context
statistic residualised on 1, |L|, L^2 by tour.
BLINDING. Outcomes only through H: load_frame and the lenses, and (MP-10) H.long_table's won of matches with
tournament_date < 1 Jan 2025. Coverage counts stop at 28 Jul 2026 (the sealed set is computed, never counted).

Run: ./python.sh src/eda/unpriced_leads/build_market.py      (deterministic; CPU; about 15 minutes)
     --no-probe    skip the timing probes        --no-screen   build the values, splits and coverage only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402

OUT = ROOT / "data" / "studies" / "unpriced_leads" / "candidates" / "market"
ODDS_SOURCES = H.INSTANCE / "odds_sources.parquet"
BOL_MATCHES = ROOT / "data" / "dump" / "odds" / "oddstrader" / "betonline_matches.parquet"
STORE = ROOT / "data" / "studies" / "feature_universe" / "store.parquet"
SEALED = pd.Timestamp("2026-07-29")
FIT = (2019, 2024)
PS_FAITHFUL_UNTIL = pd.Timestamp("2025-07-31")
PIN_GROSS = 0.5
LATE_MIN = 30.0
SEED = 20261013
SUMS = ("lv__iosO_hold", "lv__iosD_hold", "lv__iosO_ace")
GROUPS = ("atp-bo3", "atp-bo5", "wta-bo3")
MAIN = ("GS", "T1000", "T500", "T250", "FIN")
BIG = 1e6
CTX = ("in_surface", "in_level", "in_indoor", "in_best_of", "in_round")

# Ranking points of the round reached (the loser's points in that round; "W" the champion's), one standard table per
# tour for 2013-2026 (approximations, recorded in the memo). The Finals: points per win by round.
POINTS = {
    "atp": {"GS": {"R128": 10, "R64": 45, "R32": 90, "R16": 180, "QF": 360, "SF": 720, "F": 1200, "W": 2000},
            "T1000": {"R128": 10, "R64": 10, "R32": 45, "R16": 90, "QF": 180, "SF": 360, "F": 600, "W": 1000},
            "T500": {"R64": 0, "R32": 0, "R16": 45, "QF": 90, "SF": 180, "F": 300, "W": 500},
            "T250": {"R64": 0, "R32": 0, "R16": 20, "QF": 45, "SF": 90, "F": 150, "W": 250}},
    "wta": {"GS": {"R128": 10, "R64": 70, "R32": 130, "R16": 240, "QF": 430, "SF": 780, "F": 1300, "W": 2000},
            "T1000": {"R128": 10, "R64": 35, "R32": 65, "R16": 120, "QF": 215, "SF": 390, "F": 650, "W": 1000},
            "T500": {"R64": 1, "R32": 1, "R16": 60, "QF": 108, "SF": 195, "F": 325, "W": 500},
            "T250": {"R64": 1, "R32": 1, "R16": 30, "QF": 60, "SF": 110, "F": 180, "W": 280}}}
FINALS_WIN = {"atp": {"RR": 200, "SF": 400, "F": 500}, "wta": {"RR": 160, "SF": 330, "F": 420}}
NEXT = {"R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF", "SF": "F", "F": "W"}
CLIFFS = {"seed": {"line": 32, "lo": 28, "hi": 40, "offset": 7},
          "entry": {"line": 104, "lo": 90, "hi": 120, "offset": 42}}
# Data-quality rules fixed after an outcome-free look at the lines and before any screen (see the memo):
TG_RANGE = {"bo3": (12.5, 30.5), "bo5": (23.5, 50.5)}   # plausible total-games lines; others are recording faults
WINSOR_SD = 4.0                                          # MP-01's standardised excesses clipped at +-4
MOVE_CLIP = 1.5                                          # MP-02's moves clipped at +-1.5 log-odds
MIRROR = (0.7, 0.15)    # an opening that mirrors the last line (|L_open| > 0.7, opposite sign, |L_open + L_last| < 0.15)
#                         is a swapped-side recording fault: no move

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def write_json(path: Path, obj) -> None:
    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)
    path.write_text(json.dumps(obj, indent=1, default=default), encoding="utf-8")


# ------------------------------------------------------------------------------------------------------- prices

def dec(ap) -> np.ndarray:
    """American odds -> decimal."""
    ap = np.asarray(ap, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ap > 0, 1 + ap / 100, np.where(ap < 0, 1 + 100 / np.abs(ap), np.nan))


def coherent(da, db) -> np.ndarray:
    da, db = np.asarray(da, float), np.asarray(db, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = 1 / da + 1 / db
    return np.isfinite(da) & np.isfinite(db) & (da > 1) & (db > 1) & (s >= 1.0) & (s <= 1.2)


def devig(da, db) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        ia, ib = 1 / np.asarray(da, float), 1 / np.asarray(db, float)
        return ia / (ia + ib)


def utc_ms(iso) -> np.ndarray:
    t = pd.to_datetime(pd.Series(iso), utc=True, errors="coerce")
    return ((t - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds() * 1000.0).to_numpy(float)


def frame_all() -> pd.DataFrame:
    """Every frame match (2013-2026) with context and prices; no result column."""
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt", "odds_input", "in_odds_logit",
            "in_sets_14d", "in_tour", "in_surface", "in_level", "in_indoor", "in_best_of", "in_round"]
    f = pd.read_parquet(H.FRAME, columns=cols)
    if "a_won" in f.columns:
        raise RuntimeError("no result column may be read here")
    f["match_id"] = f["match_id"].astype(str)
    ids = pd.read_parquet(H.STAGE0_M, columns=["match_id", "player_a_id", "player_b_id"]).astype({"match_id": str})
    f = f.merge(ids, on="match_id", how="left", validate="one_to_one")
    return f.reset_index(drop=True)


def _dist(p1, p2, q1, q2) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.abs(np.log(np.asarray(p1, float) / np.asarray(q1, float))) + \
            np.abs(np.log(np.asarray(p2, float) / np.asarray(q2, float)))


def market_lines(fa: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Per frame match: BetOnline's opening and last moneyline (oriented to A) and total-games lines, Pinnacle's opening
    and last line at OddsTrader (oriented to A). Prices only."""
    os_ = pd.read_parquet(ODDS_SOURCES, columns=["match_id", "td_date", "eid", "ot8_a", "ot8_b", "p_ot20", "p_ot20o",
                                                 "after_ot20_min", "after_ot20o_min", "p_ps"])
    os_["match_id"] = os_["match_id"].astype(str)
    bm = pd.read_parquet(BOL_MATCHES, columns=[
        "eid", "dt_ms", "mw_open_home", "mw_open_away", "mw_open_utc", "mw_open_uncertain", "mw_close_home",
        "mw_close_away", "mw_close_after_listed_min", "mw_close_uncertain", "tg_open_line", "tg_open_utc",
        "tg_open_uncertain", "tg_close_line", "tg_close_uncertain"])
    bm["eid"] = bm["eid"].astype(float)
    bt = pd.read_parquet(H.BET_TIMING, columns=["match_id", "bol_open_a", "bol_open_b", "bol_close_a", "bol_close_b",
                                                "p_bol_open", "p_bol_close"])
    bt["match_id"] = bt["match_id"].astype(str)
    bt = bt.rename(columns={"p_bol_open": "bt_p_open", "p_bol_close": "bt_p_close"})
    x = fa[["match_id", "season", "tournament_date"]].merge(os_, on="match_id", how="left", validate="one_to_one")
    x = x.merge(bm, on="eid", how="left", validate="many_to_one")
    x = x.merge(bt, on="match_id", how="left", validate="one_to_one")
    n = len(x)
    oh, oa = dec(x["mw_open_home"]), dec(x["mw_open_away"])
    ch, ca = dec(x["mw_close_home"]), dec(x["mw_close_away"])

    # orientation of BetOnline's lines to A (prices only)
    home_a = np.full(n, np.nan)
    method = np.full(n, "", dtype=object)
    d_same = _dist(ch, ca, x["ot8_a"], x["ot8_b"])
    d_swap = _dist(ch, ca, x["ot8_b"], x["ot8_a"])
    good = np.isfinite(d_same) & np.isfinite(d_swap)
    s1 = good & (d_same + 1e-3 < d_swap) & (d_same < 0.05)
    s0 = good & (d_swap + 1e-3 < d_same) & (d_swap < 0.05)
    home_a[s1], home_a[s0] = 1.0, 0.0
    method[s1 | s0] = "ot8"
    for (h, a_, A_, B_) in ((oh, oa, x["bol_open_a"], x["bol_open_b"]), (ch, ca, x["bol_close_a"], x["bol_close_b"])):
        e_same, e_swap = _dist(h, a_, A_, B_), _dist(h, a_, B_, A_)
        need = ~np.isfinite(home_a) & np.isfinite(e_same) & np.isfinite(e_swap)
        t1 = need & (e_same + 1e-3 < e_swap) & (e_same < 0.05)
        t0 = need & (e_swap + 1e-3 < e_same) & (e_swap < 0.05)
        home_a[t1], home_a[t0] = 1.0, 0.0
        method[t1 | t0] = "bet_timing"
    with np.errstate(divide="ignore", invalid="ignore"):
        sym_o = ~(np.isfinite(oh) & np.isfinite(oa)) | (np.abs(np.log(oh / oa)) < 1e-9)
        sym_c = ~(np.isfinite(ch) & np.isfinite(ca)) | (np.abs(np.log(ch / ca)) < 1e-9)
    has_any = (np.isfinite(oh) & np.isfinite(oa)) | (np.isfinite(ch) & np.isfinite(ca))
    sy = ~np.isfinite(home_a) & sym_o & sym_c & has_any
    home_a[sy] = 1.0
    method[sy] = "symmetric"
    ha, hb = home_a == 1.0, home_a == 0.0
    a_o, b_o = np.where(ha, oh, np.where(hb, oa, np.nan)), np.where(ha, oa, np.where(hb, oh, np.nan))
    a_c, b_c = np.where(ha, ch, np.where(hb, ca, np.nan)), np.where(ha, ca, np.where(hb, ch, np.nan))
    listed = x["dt_ms"].to_numpy(float)
    t_open = utc_ms(x["mw_open_utc"])
    open_flag_ok = ~x["mw_open_uncertain"].astype("boolean").fillna(True).to_numpy(bool)
    close_flag_ok = ~x["mw_close_uncertain"].astype("boolean").fillna(True).to_numpy(bool)
    before = np.isfinite(t_open) & np.isfinite(listed) & (t_open < listed)
    ok_open = coherent(a_o, b_o) & open_flag_ok & before
    ok_close = coherent(a_c, b_c) & close_flag_ok
    p_open = np.where(ok_open, devig(a_o, b_o), np.nan)
    p_close = np.where(ok_close, devig(a_c, b_c), np.nan)
    # orientation-free |L| (MP-01 uses only |L| and L^2)
    sok_open = coherent(oh, oa) & open_flag_ok & before
    sok_close = coherent(ch, ca) & close_flag_ok
    absL_open = np.where(sok_open, np.abs(H.lg(devig(oh, oa))), np.nan)
    absL_close = np.where(sok_close, np.abs(H.lg(devig(ch, ca))), np.nan)
    # totals
    t_tg_open = utc_ms(x["tg_open_utc"])
    tg_o_ok = np.isfinite(x["tg_open_line"].to_numpy(float)) & \
        ~x["tg_open_uncertain"].astype("boolean").fillna(True).to_numpy(bool) & \
        np.isfinite(t_tg_open) & np.isfinite(listed) & (t_tg_open < listed)
    tg_c_ok = np.isfinite(x["tg_close_line"].to_numpy(float)) & \
        ~x["tg_close_uncertain"].astype("boolean").fillna(True).to_numpy(bool)
    tg_open = np.where(tg_o_ok, x["tg_open_line"].to_numpy(float), np.nan)
    tg_close = np.where(tg_c_ok, x["tg_close_line"].to_numpy(float), np.nan)
    # Pinnacle at OddsTrader
    p20, p20o, pps = x["p_ot20"].to_numpy(float), x["p_ot20o"].to_numpy(float), x["p_ps"].to_numpy(float)
    ref = (pd.to_datetime(x["td_date"]) <= PS_FAITHFUL_UNTIL).to_numpy() & np.isfinite(pps)
    gross = ref & np.isfinite(p20) & (np.abs(H.lg(p20) - H.lg(pps)) > PIN_GROSS)
    last_ok = np.isfinite(p20) & (x["after_ot20_min"].to_numpy(float) <= LATE_MIN) & ~gross
    open_ok = np.isfinite(p20o) & (x["after_ot20o_min"].to_numpy(float) < 0)
    out = pd.DataFrame({
        "match_id": x["match_id"].to_numpy(), "orient_method": method, "home_is_a": home_a,
        "p_bol_open": p_open, "p_bol_close": p_close, "absL_bol_open": absL_open, "absL_bol_close": absL_close,
        "bol_close_after_listed_min": np.where(ok_close, x["mw_close_after_listed_min"].to_numpy(float), np.nan),
        "tg_open": tg_open, "tg_close": tg_close,
        "L_pin_last": np.where(last_ok, H.lg(p20), np.nan), "L_pin_open": np.where(open_ok, H.lg(p20o), np.nan)})
    # checked against bet_timing's oriented prices (same OddsTrader pull, oriented through tennis-data's rows)
    keep = (pd.to_datetime(x["tournament_date"]) < SEALED).to_numpy()
    counts = {"rows_counted": "frame matches with tournament_date < 2026-07-29",
              "orientation_method": pd.Series(method[keep]).value_counts().to_dict(),
              "pinnacle_gross_dropped": int((gross & keep).sum()),
              "check_vs_bet_timing": chk_keep(out, x, keep)}
    return out, counts


def chk_keep(out: pd.DataFrame, x: pd.DataFrame, keep: np.ndarray) -> dict:
    """My oriented BetOnline chances against bet_timing's (rows before 29 Jul 2026)."""
    chk = {}
    for mine, theirs in (("p_bol_open", "bt_p_open"), ("p_bol_close", "bt_p_close")):
        a, b = out[mine].to_numpy(float)[keep], x[theirs].to_numpy(float)[keep]
        both = np.isfinite(a) & np.isfinite(b)
        chk[mine] = {"both": int(both.sum()), "max_abs_diff": float(np.max(np.abs(a[both] - b[both]))) if both.any()
                     else None, "n_diff_gt_1e-9": int((np.abs(a[both] - b[both]) > 1e-9).sum()),
                     "mine_only": int((np.isfinite(a) & ~np.isfinite(b)).sum()),
                     "theirs_only": int((~np.isfinite(a) & np.isfinite(b)).sum())}
    return chk


# -------------------------------------------------------------------------------------------------------- MP-01

def _design(d: pd.DataFrame, absL: np.ndarray, spec: dict) -> np.ndarray:
    """1, |L|, L^2, surface / level dummies (categories frozen in spec), indoor, the level sums (if spec says)."""
    cols = [np.ones(len(d)), absL, absL ** 2]
    for c in spec["surface"]:
        cols.append((d["in_surface"].to_numpy(float) == c).astype(float))
    for c in spec["level"]:
        cols.append((d["in_level"].to_numpy(float) == c).astype(float))
    cols.append(d["in_indoor"].to_numpy(float))
    if spec["sums"]:
        for s in SUMS:
            cols.append(d[s].to_numpy(float))
    return np.column_stack(cols)


def _fit_group(d: pd.DataFrame, y: np.ndarray, absL: np.ndarray, fit: np.ndarray, sums: bool) -> dict:
    """Least squares of y on the design over the fit rows of one group; returns the frozen spec."""
    m = fit & np.isfinite(y) & np.isfinite(absL) & np.isfinite(d["in_surface"].to_numpy(float)) & \
        np.isfinite(d["in_level"].to_numpy(float)) & np.isfinite(d["in_indoor"].to_numpy(float))
    if sums:
        for s in SUMS:
            m &= np.isfinite(d[s].to_numpy(float))
    sv = pd.Series(d.loc[m, "in_surface"]).value_counts()
    lv = pd.Series(d.loc[m, "in_level"]).value_counts()
    spec = {"surface": [float(c) for c in sorted(sv.index) if c != sv.index[0]],
            "level": [float(c) for c in sorted(lv.index) if c != lv.index[0]],
            "surface_ref": float(sv.index[0]), "level_ref": float(lv.index[0]), "sums": sums}
    X = _design(d[m], absL[m], spec)
    b, *_ = np.linalg.lstsq(X, y[m], rcond=None)
    r = y[m] - X @ b
    spec.update({"b": b.tolist(), "sd": float(r.std()), "n": int(m.sum()), "r2": float(1 - r.var() / y[m].var()),
                 "u_max": float(np.quantile(absL[m], 0.995))})
    return spec


def _apply(d: pd.DataFrame, absL: np.ndarray, spec: dict) -> tuple[np.ndarray, np.ndarray]:
    """(E, the non-price part c0) for every row of d."""
    X = _design(d, absL, spec)
    b = np.asarray(spec["b"], float)
    E = X @ b
    c0 = E - b[1] * absL - b[2] * absL ** 2
    return E, c0


def _invert(c0, b1, b2, tg, U) -> np.ndarray:
    """u in [0, U'] with c0 + b1 u + b2 u^2 = tg on the decreasing branch (U' = U, or the vertex if b2 > 0 puts it
    earlier); clamped at the ends; NaN when the curve does not decrease at 0."""
    c0, tg = np.asarray(c0, float), np.asarray(tg, float)
    if b1 >= 0:
        return np.full(len(c0), np.nan)
    Up = U if b2 <= 0 else min(U, -b1 / (2 * b2))
    f = lambda u: c0 + b1 * u + b2 * u ** 2 - tg  # noqa: E731
    lo, hi = np.zeros(len(c0)), np.full(len(c0), Up)
    out = np.where(f(lo) <= 0, 0.0, np.where(f(hi) >= 0, Up, np.nan))
    sol = ~np.isfinite(out) & np.isfinite(c0) & np.isfinite(tg)
    a, b = lo[sol], hi[sol]
    cc, tt = c0[sol], tg[sol]
    for _ in range(60):
        mid = (a + b) / 2
        fm = cc + b1 * mid + b2 * mid ** 2 - tt
        a = np.where(fm > 0, mid, a)
        b = np.where(fm > 0, b, mid)
    out[sol] = (a + b) / 2
    out[~(np.isfinite(c0) & np.isfinite(tg))] = np.nan
    return out


def mp01(fa: pd.DataFrame, mk: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    st = pd.read_parquet(STORE, columns=["match_id"] + list(SUMS))
    st["match_id"] = st["match_id"].astype(str)
    d = fa.merge(mk, on="match_id", how="left", validate="one_to_one").merge(st, on="match_id", how="left",
                                                                             validate="one_to_one")
    d["group"] = d["tour"] + "-bo" + d["in_best_of"].astype(int).astype(str)
    has_sums = np.all(np.isfinite(d[list(SUMS)].to_numpy(float)), axis=1)
    fit = d["season"].between(*FIT).to_numpy()
    rec = {"groups": {}, "note": "least squares on frame matches of 2019-2024, no outcome; frozen; applied to all",
           "plausible_lines": TG_RANGE, "winsor_sd": WINSOR_SD}
    # recording faults (lines of 0.5, 106.5, 211.5; best-of-3-sized lines on best-of-5 matches): implausible lines out
    bo = d["in_best_of"].to_numpy(float)
    lo_ = np.where(bo == 5, TG_RANGE["bo5"][0], TG_RANGE["bo3"][0])
    hi_ = np.where(bo == 5, TG_RANGE["bo5"][1], TG_RANGE["bo3"][1])
    keep = (pd.to_datetime(d["tournament_date"]) < SEALED).to_numpy()
    for c in ("tg_open", "tg_close"):
        v = d[c].to_numpy(float)
        bad = np.isfinite(v) & ((v < lo_) | (v > hi_))
        d.loc[bad, c] = np.nan
        rec[f"{c}_implausible_dropped_before_2026_07_29"] = int((bad & keep).sum())
    res = {k: np.full(len(d), np.nan) for k in ("exc_open", "exc_close", "mv_net", "u_star", "E_close", "U_used")}
    for g in GROUPS:
        gm = (d["group"] == g).to_numpy()
        dg = d[gm]
        rg = {}
        for side, ycol, acol in (("open", "tg_open", "absL_bol_open"), ("close", "tg_close", "absL_bol_close")):
            y, absL = dg[ycol].to_numpy(float), dg[acol].to_numpy(float)
            sp_s = _fit_group(dg, y, absL, fit[gm], sums=True)
            sp_n = _fit_group(dg, y, absL, fit[gm], sums=False)
            E_s, c0_s = _apply(dg, absL, sp_s)
            E_n, c0_n = _apply(dg, absL, sp_n)
            hs = has_sums[gm]
            E = np.where(hs, E_s, E_n)
            sd = np.where(hs, sp_s["sd"], sp_n["sd"])
            res[f"exc_{side}"][gm] = (y - E) / sd
            rg[side] = {"with_sums": sp_s, "without_sums": sp_n}
            if side == "close":
                res["E_close"][gm] = E
                us = _invert(c0_s, sp_s["b"][1], sp_s["b"][2], y, sp_s["u_max"])
                un = _invert(c0_n, sp_n["b"][1], sp_n["b"][2], y, sp_n["u_max"])
                res["u_star"][gm] = np.where(hs, us, un)
                up_s = sp_s["u_max"] if sp_s["b"][2] <= 0 else min(sp_s["u_max"], -sp_s["b"][1] / (2 * sp_s["b"][2]))
                up_n = sp_n["u_max"] if sp_n["b"][2] <= 0 else min(sp_n["u_max"], -sp_n["b"][1] / (2 * sp_n["b"][2]))
                res["U_used"][gm] = np.where(hs, up_s, up_n)
        # the totals' move net of what the moneyline's move implies (regression on 2019-2024, by group)
        mv = dg["tg_close"].to_numpy(float) - dg["tg_open"].to_numpy(float)
        dA = dg["absL_bol_close"].to_numpy(float) - dg["absL_bol_open"].to_numpy(float)
        dA2 = dg["absL_bol_close"].to_numpy(float) ** 2 - dg["absL_bol_open"].to_numpy(float) ** 2
        X = np.column_stack([np.ones(len(dg)), dA, dA2])
        ok = np.isfinite(mv) & np.isfinite(dA)
        fm = ok & fit[gm]
        b, *_ = np.linalg.lstsq(X[fm], mv[fm], rcond=None)
        r = mv - X @ b
        sd = float(r[fm].std())
        res["mv_net"][gm] = np.where(ok, r / sd, np.nan)
        rg["move"] = {"b": b.tolist(), "sd": sd, "n": int(fm.sum()), "r2": float(1 - r[fm].var() / mv[fm].var()),
                      "mean_move": float(mv[fm].mean()), "share_move_ge_1_game": float((np.abs(mv[fm]) >= 1).mean())}
        rec["groups"][g] = rg
    LA = H.lg(d["p_bol_close"].to_numpy(float))
    LA = np.where(np.isfinite(d["p_bol_close"].to_numpy(float)), LA, np.nan)
    diff = np.sign(LA) * (res["u_star"] - np.abs(LA))
    w = WINSOR_SD
    out = pd.DataFrame({"match_id": d["match_id"].to_numpy(),
                        "mp01_lop_close": np.clip(-res["exc_close"], -w, w),
                        "mp01_lop_open": np.clip(-res["exc_open"], -w, w),
                        "mp01_lop_move": np.clip(-res["mv_net"], -w, w), "mp01_diff_close": diff,
                        "mp01_nosums": (~has_sums).astype(float),
                        "tg_open_clean": d["tg_open"].to_numpy(float), "tg_close_clean": d["tg_close"].to_numpy(float)})
    for c in ("mp01_lop_close", "mp01_lop_open", "mp01_lop_move", "mp01_diff_close"):
        out.loc[~np.isfinite(out[c].to_numpy(float)), c] = np.nan
    f0 = fit
    rec["winsorised_share_2019_24"] = {
        c: float(np.mean(np.abs(v[f0 & np.isfinite(v)]) > w))
        for c, v in (("lop_close", res["exc_close"]), ("lop_open", res["exc_open"]), ("lop_move", res["mv_net"]))}
    # outcome-free descriptives on the fit seasons
    f = fit & np.isfinite(res["exc_open"]) & np.isfinite(res["exc_close"])
    rec["corr_excess_open_close_2019_24"] = float(np.corrcoef(res["exc_open"][f], res["exc_close"][f])[0, 1])
    f2 = fit & np.isfinite(diff)
    rec["share_u_star_at_bounds_2019_24"] = {
        "at_0": float(np.mean(res["u_star"][f2] == 0)),
        "at_upper": float(np.mean(np.isclose(res["u_star"][f2], res["U_used"][f2])))}
    return out, rec


# -------------------------------------------------------------------------------------------------------- MP-02

def first_at_event(L: pd.DataFrame) -> pd.DataFrame:
    """Per (match, player): 1 when the player has no earlier row (smaller k) at this event (tournament id and date;
    qualifying shares both)."""
    key = L["tournament_id"].astype(str) + "|" + L["tday"].astype(str)
    prev = key.groupby(L["player_id"]).shift(1)
    first = prev.isna() | (prev != key)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": L["player_id"].to_numpy(),
                         "first_at_event": first.to_numpy(bool)})


def momentum(L_last, L_open, keep) -> tuple[np.ndarray, dict]:
    """logit(last) - logit(opening), oriented to A; a mirror-image opening (a swapped-side fault) gives no move; moves
    clipped at +-MOVE_CLIP. Counts on rows before 29 Jul 2026."""
    lc, lo = np.asarray(L_last, float), np.asarray(L_open, float)
    mv = lc - lo
    mirror = np.isfinite(mv) & (np.sign(lo) == -np.sign(lc)) & (np.abs(lo) > MIRROR[0]) & \
        (np.abs(lo + lc) < MIRROR[1])
    big = np.isfinite(mv) & ~mirror & (np.abs(mv) > MOVE_CLIP)
    out = np.where(mirror, np.nan, np.clip(mv, -MOVE_CLIP, MOVE_CLIP))
    return out, {"mirror_dropped": int((mirror & keep).sum()), "clipped": int((big & keep).sum()),
                 "moves": int((np.isfinite(out) & keep).sum())}


def price_tier(p) -> np.ndarray:
    p = np.asarray(p, float)
    fav = np.maximum(p, 1 - p)
    return np.where(~np.isfinite(fav), "", np.where(fav < 0.60, "even", np.where(fav < 0.75, "mid", "fav")))


# -------------------------------------------------------------------------------------------------------- MP-10

def mp10_build(L: pd.DataFrame, prices: pd.Series, roles: bool = False) -> pd.DataFrame:
    """prices: match_id -> A's close (p_mkt) for every frame match. Per (match, player) of the frame: the shrunk record
    against the close over the last <= 60 residual matches (frame, tournament_date < 2025) that surely finished before
    this match could start (lf + 1 <= es)."""
    fm = L.loc[L["match_id"].isin(prices.index), ["match_id", "player_id", "side", "won", "tournament_date", "es", "lf",
                                                  "k"]].copy()
    pa = prices.reindex(fm["match_id"]).to_numpy(float)
    fm["p"] = np.where(fm["side"].to_numpy() == "A", pa, 1 - pa)
    pool = fm[(pd.to_datetime(fm["tournament_date"]) < H.DISCOVERY_END).to_numpy() &
              np.isfinite(fm["lf"].to_numpy(float))].copy()
    pool["r"] = pool["won"].astype(float).to_numpy() - pool["p"].to_numpy(float)
    codes = pd.Index(pd.unique(fm["player_id"]))
    qc = codes.get_indexer(fm["player_id"]).astype(float)
    qes = fm["es"].to_numpy(float)
    okq = np.isfinite(qes)
    key_q = np.where(okq, qc * BIG + np.where(okq, qes, 0), np.inf)
    out = fm[["match_id", "player_id"]].copy()
    variants = {"mp10_rec": np.ones(len(pool), bool)}
    if roles:
        variants["mp10_fav"] = pool["p"].to_numpy(float) > 0.5
        variants["mp10_dog"] = pool["p"].to_numpy(float) < 0.5
    for name, sel in variants.items():
        P = pool[sel]
        pc = codes.get_indexer(P["player_id"]).astype(float)
        order = np.lexsort((P["k"].to_numpy(float), P["lf"].to_numpy(float), pc))
        pc, lf, r = pc[order], P["lf"].to_numpy(float)[order], P["r"].to_numpy(float)[order]
        # cumulative sums within each player (reset per player, so other players' rows never touch a value)
        cw = pd.Series(r).groupby(pc).cumsum().to_numpy()
        key_p = pc * BIG + (lf + 1.0)
        idx = np.searchsorted(key_p, key_q, side="right")
        start = np.searchsorted(key_p, np.where(okq, qc * BIG, np.inf), side="left")
        idx = np.where(okq, idx, start)
        lo = np.maximum(start, idx - 60)
        nn = idx - lo
        s_hi = np.where(idx > start, cw[np.clip(idx - 1, 0, max(len(cw) - 1, 0))] if len(cw) else 0.0, 0.0)
        s_lo = np.where(lo > start, cw[np.clip(lo - 1, 0, max(len(cw) - 1, 0))] if len(cw) else 0.0, 0.0)
        val = (s_hi - s_lo) / (nn + 30.0)
        out[name] = np.where(okq, val, np.nan)
        out[name + "_n"] = np.where(okq, nn, np.nan)
    return out.drop_duplicates(["match_id", "player_id"]).reset_index(drop=True)


def mp10_pool(L: pd.DataFrame, prices: pd.Series) -> pd.DataFrame:
    """The residual pool (frame matches with tournament_date < 2025), one row per (match, player)."""
    fm = L.loc[L["match_id"].isin(prices.index), ["match_id", "player_id", "side", "won", "tournament_date", "lf",
                                                  "k"]].copy()
    fm = fm[(pd.to_datetime(fm["tournament_date"]) < H.DISCOVERY_END).to_numpy()]
    pa = prices.reindex(fm["match_id"]).to_numpy(float)
    fm["p"] = np.where(fm["side"].to_numpy() == "A", pa, 1 - pa)
    fm["r"] = fm["won"].astype(float).to_numpy() - fm["p"].to_numpy(float)
    return fm


def reliability(pool: pd.DataFrame, season: pd.Series, tour: pd.Series) -> dict:
    """Split-half reliability of the player residuals, seasons 2013-2024 (outcomes <= 2024 only)."""
    rng = np.random.default_rng(SEED)
    p = pool.copy()
    p["season"] = season.reindex(p["match_id"]).to_numpy()
    p["tour"] = tour.reindex(p["match_id"]).to_numpy()
    p = p[(p["season"] >= 2013) & (p["season"] <= 2024)].sort_values(["player_id", "lf", "k"], kind="stable")
    p["i"] = p.groupby("player_id").cumcount()
    p["half"] = p["i"] % 2

    def split(df: pd.DataFrame, by: list[str], min_n: int) -> dict:
        g = df.groupby(by + ["half"])["r"].mean().unstack("half")
        n = df.groupby(by).size()
        g = g[(n.reindex(g.index) >= min_n).to_numpy()].dropna()
        if len(g) < 10:
            return {"units": int(len(g))}
        r = float(np.corrcoef(g[0], g[1])[0, 1])
        boots = []
        a0, a1 = g[0].to_numpy(), g[1].to_numpy()
        for _ in range(1000):
            ix = rng.integers(0, len(g), len(g))
            boots.append(np.corrcoef(a0[ix], a1[ix])[0, 1])
        lo_, hi_ = np.quantile(boots, [0.025, 0.975])
        return {"units": int(len(g)), "r_split_half": r, "ci95": [float(lo_), float(hi_)],
                "spearman_brown": float(2 * r / (1 + r)) if r > -1 else None,
                "mean_matches_per_unit": float(n.reindex(g.index).mean())}

    out = {"players_ge40_all": split(p, ["player_id"], 40)}
    for t in ("atp", "wta"):
        out[f"players_ge40_{t}"] = split(p[p["tour"] == t], ["player_id"], 40)
    q = p.copy()
    q["i"] = q.groupby(["player_id", "season"]).cumcount()
    q["half"] = q["i"] % 2
    out["player_seasons_ge20"] = split(q, ["player_id", "season"], 20)
    ci = out["players_ge40_all"].get("ci95")
    out["gate_passes"] = bool(ci is not None and ci[0] > 0)
    return out


# -------------------------------------------------------------------------------------------------------- MP-08

def _points_table() -> pd.DataFrame:
    rows = []
    for tour, lev in POINTS.items():
        for level, tab in lev.items():
            for rnd, pts in tab.items():
                if rnd == "W":
                    continue
                nxt = NEXT[rnd]
                rows.append({"tour": tour, "level": level, "round": rnd, "pts_round": pts,
                             "win_gain": tab[nxt] - pts if nxt in tab else np.nan})
    for tour, tab in FINALS_WIN.items():
        for rnd, pts in tab.items():
            rows.append({"tour": tour, "level": "FIN", "round": rnd, "pts_round": np.nan, "win_gain": pts})
    return pd.DataFrame(rows)


def _week(tday) -> np.ndarray:
    t = np.asarray(tday, float)
    return t - np.mod(t + 3, 7)            # 1 Jan 1970 was a Thursday: Monday of the week


def _line_points(L: pd.DataFrame, lines=(32, 104)) -> pd.DataFrame:
    """Per tour and week: the ranking points at each line rank in that week's list (Stage 0's rank, rank_points)."""
    w = L[["tour", "tday", "rank", "rank_points"]].copy()
    w = w[np.isfinite(w["rank"].to_numpy(float)) & np.isfinite(w["rank_points"].to_numpy(float)) &
          (w["rank_points"].to_numpy(float) > 0)]
    w["week"] = _week(w["tday"].to_numpy(float))
    t = w.groupby(["tour", "week", "rank"])["rank_points"].median().reset_index()
    out = t[["tour", "week"]].drop_duplicates().reset_index(drop=True)
    for ln in lines:
        near = t[(t["rank"] >= ln - 3) & (t["rank"] <= ln + 3)]
        vals = {}
        for (tour, wk), g in near.groupby(["tour", "week"]):
            rk, pt = g["rank"].to_numpy(float), g["rank_points"].to_numpy(float)
            if (rk == ln).any():
                vals[(tour, wk)] = float(np.median(pt[rk == ln]))
                continue
            below, above = rk < ln, rk > ln
            if below.any() and above.any():
                i0, i1 = np.argmax(np.where(below, rk, -np.inf)), np.argmin(np.where(above, rk, np.inf))
                r0, r1, p0, p1 = rk[i0], rk[i1], pt[i0], pt[i1]
                vals[(tour, wk)] = float(p0 + (p1 - p0) * (ln - r0) / (r1 - r0))
        out[f"P{ln}"] = [vals.get((a, b), np.nan) for a, b in zip(out["tour"], out["week"])]
    return out


def mp08_build(L: pd.DataFrame, frame_ids: pd.Index) -> pd.DataFrame:
    """Ranking cliffs before each Grand Slam's seeding and direct-entry ranking dates (pre-match facts only)."""
    rows = L.loc[L["match_id"].isin(frame_ids), ["match_id", "player_id", "tour", "level", "round", "tday", "obs",
                                                 "rank", "rank_points"]].copy()
    g = L[(L["level"] == "GS") & ~L["qualifying"].astype(bool)].drop_duplicates(["tour", "tournament_id", "tday"])
    t1 = g["tday"].to_numpy(float) + 1
    slams = pd.DataFrame({"tour": g["tour"].to_numpy(), "T": t1 - np.mod(t1 + 3, 7)}).drop_duplicates()
    lp = _line_points(L)
    rows["week"] = _week(rows["tday"].to_numpy(float))
    rows = rows.merge(lp, on=["tour", "week"], how="left")
    pt = _points_table()
    rows = rows.merge(pt[["tour", "level", "round", "win_gain"]], on=["tour", "level", "round"], how="left")
    r = rows["rank"].to_numpy(float)
    P = rows["rank_points"].to_numpy(float)
    W = rows["win_gain"].to_numpy(float)
    d = rows["obs"].to_numpy(float)
    out = rows[["match_id", "player_id"]].copy()
    for name, c in CLIFFS.items():
        inwin = np.zeros(len(rows), bool)
        for tour in ("atp", "wta"):
            Ts = np.sort(slams.loc[slams["tour"] == tour, "T"].to_numpy(float)) - c["offset"]   # ranking dates
            m = (rows["tour"] == tour).to_numpy() & np.isfinite(d)
            j = np.searchsorted(Ts, d[m], side="right")          # first ranking date after the match's day
            ok = j < len(Ts)
            D = np.where(ok, Ts[np.minimum(j, len(Ts) - 1)], np.nan)
            inwin[np.flatnonzero(m)] = ok & (d[m] >= D - 28) & (d[m] < D)
        band = (r >= c["lo"]) & (r <= c["hi"])
        Pstar = rows[f"P{c['line']}"].to_numpy(float)
        outside = r > c["line"]
        live = outside & (P + W >= Pstar)
        undetermined = outside & ~(np.isfinite(P) & np.isfinite(W) & np.isfinite(Pstar))
        val = np.where(inwin & band, np.where(live, 1.0, -1.0), 0.0)
        val = np.where(inwin & band & undetermined, np.nan, val)
        val = np.where(np.isfinite(r), val, np.nan)
        out[f"mp08_{name}"] = val
        out[f"mp08_{name}_band"] = np.where(np.isfinite(r), (inwin & band).astype(float), np.nan)
    return out.drop_duplicates(["match_id", "player_id"]).reset_index(drop=True)


# -------------------------------------------------------------------------------------------------------- MP-09

def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def previous_editions(L: pd.DataFrame, frame_ids: pd.Index) -> pd.DataFrame:
    """Each frame event instance (tour, tournament id, date) -> its previous edition (calendar facts only)."""
    ev = L.drop_duplicates(["tour", "tournament_id", "tday"])[["tour", "tournament_id", "tournament_name", "tday",
                                                               "level"]].copy()
    ev["nk"] = ev["tournament_name"].map(_norm)
    ev["sfx"] = ev["tournament_id"].astype(str).str.split("-", n=1).str[1]
    cur_keys = L.loc[L["match_id"].isin(frame_ids), ["tour", "tournament_id", "tday"]].drop_duplicates()
    cur = ev.merge(cur_keys, on=["tour", "tournament_id", "tday"], how="inner")
    prv = ev[ev["level"].isin(MAIN)]
    parts = []
    for how, key, rank in (("name", "nk", 0), ("id", "sfx", 1)):
        a = cur.merge(prv[["tour", key, "tournament_id", "tday", "level"]], on=["tour", key], suffixes=("", "_p"))
        gap = a["tday"] - a["tday_p"]
        a = a[(gap >= 300) & (gap <= 420)].copy()
        a["how"], a["how_rank"], a["dist"] = how, rank, np.abs(a["tday"] - a["tday_p"] - 364)
        parts.append(a[["tour", "tournament_id", "tday", "tournament_id_p", "tday_p", "level_p", "how", "how_rank",
                        "dist"]])
    c = pd.concat(parts, ignore_index=True).sort_values(["tour", "tournament_id", "tday", "how_rank", "dist",
                                                         "tournament_id_p"], kind="stable")
    c = c.drop_duplicates(["tour", "tournament_id", "tday"], keep="first")
    return cur[["tour", "tournament_id", "tday"]].merge(c, on=["tour", "tournament_id", "tday"], how="left")


def mp09_build(L: pd.DataFrame, frame_ids: pd.Index) -> pd.DataFrame:
    """Points to defend: the player's own result at the event's previous edition."""
    prev = previous_editions(L, frame_ids)
    md = L[L["level"].isin(MAIN) & ~L["qualifying"].astype(bool)][["player_id", "tour", "tournament_id", "tday",
                                                                    "level", "round", "won", "k"]].copy()
    md["won"] = md["won"].astype(bool)
    pt = _points_table()
    ko = md[md["level"] != "FIN"].sort_values("k", kind="stable")
    last = ko.groupby(["player_id", "tour", "tournament_id", "tday"]).tail(1).copy()
    tab = {(t, lv): POINTS[t][lv] for t in POINTS for lv in POINTS[t]}
    pts, champ = [], []
    for t, lv, rnd, w in zip(last["tour"], last["level"], last["round"], last["won"]):
        tb = tab.get((t, lv), {})
        if rnd not in tb:
            pts.append(np.nan)
            champ.append(False)
            continue
        if w:
            pts.append(float(tb.get(NEXT[rnd], np.nan)))
            champ.append(rnd == "F")
        else:
            pts.append(float(tb[rnd]))
            champ.append(False)
    last["pts"], last["champ"] = pts, champ
    fin = md[md["level"] == "FIN"].copy()
    if len(fin):
        fin = fin.merge(pt[pt["level"] == "FIN"][["tour", "round", "win_gain"]], on=["tour", "round"], how="left")
        fin["gain"] = np.where(fin["won"].to_numpy(bool), fin["win_gain"].to_numpy(float), 0.0)
        fin = fin.sort_values("k", kind="stable")
        fg = fin.groupby(["player_id", "tour", "tournament_id", "tday"]).agg(
            pts=("gain", "sum"), last_round=("round", "last"), last_won=("won", "last")).reset_index()
        fg["champ"] = (fg["last_round"] == "F") & fg["last_won"].astype(bool)
        res = pd.concat([last[["player_id", "tour", "tournament_id", "tday", "pts", "champ"]],
                         fg[["player_id", "tour", "tournament_id", "tday", "pts", "champ"]]], ignore_index=True)
    else:
        res = last[["player_id", "tour", "tournament_id", "tday", "pts", "champ"]]
    res = res.rename(columns={"tournament_id": "tournament_id_p", "tday": "tday_p"})
    rows = L.loc[L["match_id"].isin(frame_ids), ["match_id", "player_id", "tour", "tournament_id", "tday",
                                                 "rank_points"]].copy()
    rows = rows.merge(prev[["tour", "tournament_id", "tday", "tournament_id_p", "tday_p", "how"]],
                      on=["tour", "tournament_id", "tday"], how="left")
    rows = rows.merge(res, on=["player_id", "tour", "tournament_id_p", "tday_p"], how="left")
    found = rows["tournament_id_p"].notna().to_numpy()
    defend = np.where(np.isfinite(rows["pts"].to_numpy(float)), rows["pts"].to_numpy(float), 0.0)
    rp = rows["rank_points"].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(np.isfinite(rp) & (rp > 0), np.minimum(defend / rp, 1.0), np.nan)
    out = pd.DataFrame({"match_id": rows["match_id"].to_numpy(), "player_id": rows["player_id"].to_numpy(),
                        "mp09_defend": ratio,
                        "mp09_champ": rows["champ"].astype("boolean").fillna(False).to_numpy(bool).astype(float),
                        "mp09_points": defend, "mp09_prev_found": found.astype(float),
                        "mp09_prev_how": rows["how"].fillna("").to_numpy()})
    return out.drop_duplicates(["match_id", "player_id"]).reset_index(drop=True)


# ----------------------------------------------------------------------------------------------------- screening

def orth_context(frame: pd.DataFrame, s) -> tuple[np.ndarray, dict]:
    """A context (symmetric) statistic minus its least-squares projection on symmetric functions of the model's inputs:
    |A - B| of the 49 non-price inputs and the context dummies, with an intercept, by tour, on rows where s is present.
    Returns (residual, R^2 by tour and pooled)."""
    names = H.diff_input_names()
    s = np.asarray(s, float)
    res = np.full(len(s), np.nan)
    r2 = {}
    ss_res = ss_tot = 0.0
    for tour in ("atp", "wta"):
        m = (frame["tour"] == tour).to_numpy() & np.isfinite(s)
        if m.sum() < 200:
            continue
        X = np.abs(frame.loc[m, [f"in_{n}" for n in names]].to_numpy(float))
        X = np.where(np.isfinite(X), X, 0.0)
        D = []
        for c in CTX:
            v = frame.loc[m, c].to_numpy(float)
            cats = pd.Series(v).value_counts().index.tolist()
            for k in cats[1:]:
                D.append((v == k).astype(float))
        Z = np.column_stack([np.ones(int(m.sum())), X] + D)
        b, *_ = np.linalg.lstsq(Z, s[m], rcond=None)
        e = s[m] - Z @ b
        res[m] = e
        r2[tour] = float(1 - e.var() / s[m].var())
        ss_res += float((e ** 2).sum())
        ss_tot += float(((s[m] - s[m].mean()) ** 2).sum())
    r2["both"] = float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan
    return res, r2


def correlations(frame: pd.DataFrame, x, kind: str) -> dict:
    """Outcome-free correlations on seasons <= 2024 with the model's odds input and sets_14d (absolute values for a
    context statistic, which is symmetric)."""
    x = np.asarray(x, float)
    L, s14 = frame["in_odds_logit"].to_numpy(float), frame["in_sets_14d"].to_numpy(float)
    out = {}
    for tour in ("both", "atp", "wta"):
        m = np.isfinite(x) & (np.ones(len(x), bool) if tour == "both" else (frame["tour"] == tour).to_numpy())
        if m.sum() < 200 or np.nanstd(x[m]) == 0:
            continue
        if kind == "context":
            o = {"corr_abs_odds_input": float(np.corrcoef(x[m], np.abs(L[m]))[0, 1]),
                 "corr_abs_sets_14d": float(np.corrcoef(x[m], np.abs(np.where(np.isfinite(s14[m]), s14[m], 0)))[0, 1])}
        else:
            o = {"corr_odds_input": float(np.corrcoef(x[m], L[m])[0, 1]),
                 "corr_sets_14d": float(np.corrcoef(x[m], np.where(np.isfinite(s14[m]), s14[m], 0))[0, 1])}
        o["n"] = int(m.sum())
        out[tour] = o
    return out


def coverage_table(fa: pd.DataFrame, vals: pd.DataFrame, names: list[str]) -> dict:
    """Outcome-free: share of frame matches (tournament_date < 29 Jul 2026) where each statistic is present and where
    it is nonzero, by tour and season; and H.coverage_2025_26 on the same rows."""
    keep = (pd.to_datetime(fa["tournament_date"]) < SEALED).to_numpy()
    f = fa[keep].reset_index(drop=True)
    v = vals.set_index("match_id").reindex(f["match_id"])
    out = {"rows_counted": "frame matches with tournament_date < 2026-07-29 (the sealed set is not counted)",
           "matches_by_tour_season": f.groupby(["tour", "season"]).size().rename("n").reset_index()
           .assign(key=lambda d: d["tour"] + "|" + d["season"].astype(str)).set_index("key")["n"].to_dict(),
           "statistics": {}}
    for nm in names:
        x = v[nm].to_numpy(float)
        g = pd.DataFrame({"tour": f["tour"], "season": f["season"], "present": np.isfinite(x),
                          "nonzero": np.isfinite(x) & (x != 0)})
        by = g.groupby(["tour", "season"])[["present", "nonzero"]].mean().round(4)
        out["statistics"][nm] = {
            "by_tour_season": {f"{t}|{s}": {"present": float(r.present), "nonzero": float(r.nonzero)}
                               for (t, s), r in by.iterrows()},
            "harness_coverage_2025_26": H.coverage_2025_26(f, x),
            "nonzero_share": {f"{t}_{lab}": float(g.loc[(g["tour"] == t) & g["season"].between(a, b), "nonzero"].mean())
                              for t in ("atp", "wta") for lab, (a, b) in (("2013_24", (2013, 2024)),
                                                                           ("2025_26", (2025, 2026)))}}
    return out


def run_screens(fr: pd.DataFrame, V: pd.DataFrame, plan: list[dict]) -> tuple[pd.DataFrame, dict]:
    """plan: dicts with name, col, kind, bases (extra close-lens bases), lenses."""
    parts, extra = [], {}
    for p in plan:
        x = V[p["col"]].to_numpy(float)
        kind, nm = p["kind"], p["name"]
        if kind == "diff":
            xo, _ = H.orthogonal_part(fr, x)
            r2s = None
        else:
            xo, r2s = orth_context(fr, x)
        for xx, lab in ((x, nm), (xo, nm + "__orth")):
            lg_ = H.screen(fr, xx, lab, kind, lenses=p.get("lenses", ("close", "model", "move")))
            if r2s is not None:
                lg_["r2_sym"] = r2s.get("both") if lab == nm else np.nan
            parts.append(lg_)
            for b in p.get("bases", ()):
                parts.append(H.screen(fr, xx, lab, kind, lenses=("close",), base=b))
        extra[nm] = {"kind": kind, "correlations_le_2024": correlations(fr, x, kind),
                     "r2_sym_inputs": r2s, "present_le_2024": float(np.mean(np.isfinite(x)))}
        log(f"screened {nm}")
    return pd.concat(parts, ignore_index=True), extra


def run_tiers(fr: pd.DataFrame, V: pd.DataFrame, S: pd.DataFrame) -> pd.DataFrame:
    parts = []
    spec = [("mp02_bol", "L_bol", {"level": "level_tier", "round": "round_tier", "price": "price_tier_bol",
                                   "fresh": "bol_fresh"}),
            ("mp02_pin", "L_pin_ot", {"level": "level_tier", "round": "round_tier", "price": "price_tier_pin"})]
    for col, base, tiers in spec:
        x = V[col].to_numpy(float)
        for tname, scol in tiers.items():
            lab = S[scol].astype(str).to_numpy()
            for val in sorted(set(lab) - {"", "nan", "None"}):
                m = lab == val
                if m.sum() < 500:
                    continue
                g = fr[m].reset_index(drop=True)
                parts.append(H.screen(g, x[m], f"{col}__{tname}={val}", "diff", lenses=("close",), base=base))
        log(f"tiers {col}")
    return pd.concat(parts, ignore_index=True)


def diagnostics(fr: pd.DataFrame, V: pd.DataFrame) -> pd.DataFrame:
    """POST HOC (added after the main readings were seen; reported whatever they show): is a context reading of MP-01
    the favourite-longshot curvature? The close lens has no curvature term, so a slope modifier correlated with |L|
    can borrow it. D1: the curvature alone (s = |L|, and s = |L_bol| beyond BetOnline's close). D2: each MP-01 context
    statistic residualised on 1, |L|, L^2 (by tour; the base's own L), screened again (raw only)."""
    parts = []
    for base in ("L", "L_bol"):
        Lb = fr[base].to_numpy(float)
        parts.append(H.screen(fr, np.abs(Lb), f"diag_curvature_absL@{base}", "context", lenses=("close",), base=base))
        for col in ("mp01_lop_close", "mp01_lop_open", "mp01_lop_move"):
            s = V[col].to_numpy(float)
            r = np.full(len(s), np.nan)
            for tour in ("atp", "wta"):
                m = (fr["tour"] == tour).to_numpy() & np.isfinite(s) & np.isfinite(Lb)
                Z = np.column_stack([np.ones(int(m.sum())), np.abs(Lb[m]), Lb[m] ** 2])
                b, *_ = np.linalg.lstsq(Z, s[m], rcond=None)
                r[m] = s[m] - Z @ b
            parts.append(H.screen(fr, r, f"diag_{col}__resid_absL@{base}", "context", lenses=("close",), base=base))
    out = pd.concat(parts, ignore_index=True)
    out["post_hoc"] = True
    return out


def summary_table(long: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lens, label in (("close", "odds_input"), ("close[L_bol]", "bol_close"), ("close[L_pin_ot]", "pin_ot_close")):
        names = long.loc[long["lens"] == lens, "name"].unique()
        sub = long[long["name"].isin(names)]
        s = H.summarize(sub, lens=lens)
        s.insert(2, "base", label)
        if label != "odds_input":
            s["z_model_2020_24"] = np.nan
            s["z_move_2018_24"] = np.nan
        rows.append(s)
    out = pd.concat(rows, ignore_index=True)
    if "r2_sym" in long.columns:
        r2s = long.dropna(subset=["r2_sym"]).drop_duplicates(["name"]).set_index("name")["r2_sym"]
        out["r2_sym"] = out["name"].map(r2s)
    from scipy.stats import norm
    out["q_pool_all"] = H.bh(2 * norm.sf(np.abs(out["z_pool"].to_numpy(float))))
    return out


# ------------------------------------------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probe", action="store_true")
    ap.add_argument("--no-screen", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    extras: dict = {"points_table": POINTS, "finals_points_per_win": FINALS_WIN, "cliffs": CLIFFS}

    fa = frame_all()
    frame_ids = pd.Index(fa["match_id"])
    log(f"frame: {len(fa):,} matches (2013-2026)")

    # ---- prices and MP-01 / MP-02 (match level)
    mk, mk_counts = market_lines(fa)
    extras["prices"] = mk_counts
    log(f"market lines: {mk_counts['orientation_method']}")
    m1, m1_rec = mp01(fa, mk)
    extras["mp01_expectation"] = m1_rec
    log("MP-01 built")
    mk2 = mk.set_index("match_id").reindex(fa["match_id"])
    pc_, po_ = mk2["p_bol_close"].to_numpy(float), mk2["p_bol_open"].to_numpy(float)
    Lbc = np.where(np.isfinite(pc_), H.lg(pc_), np.nan)
    Lbo = np.where(np.isfinite(po_), H.lg(po_), np.nan)
    keep = (pd.to_datetime(fa["tournament_date"]) < SEALED).to_numpy()
    mp02_bol, c_bol = momentum(Lbc, Lbo, keep)
    mp02_pin, c_pin = momentum(mk2["L_pin_last"].to_numpy(float), mk2["L_pin_open"].to_numpy(float), keep)
    extras["mp02_cleaning_before_2026_07_29"] = {"betonline": c_bol, "pinnacle": c_pin, "clip": MOVE_CLIP,
                                                 "mirror_rule": MIRROR}

    # ---- the long table (player statistics)
    L = H.long_table()
    log(f"long table: {len(L):,} rows")
    slim_cols = ["match_id", "player_id", "side", "won", "rank", "rank_points", "tour", "level", "qualifying", "round",
                 "round_order", "tournament_id", "tournament_name", "tournament_date", "tday", "es", "lf", "obs", "k"]
    Ls = L[slim_cols].copy()
    del L
    prices = fa.set_index("match_id")["p_mkt"]
    prices = prices[~prices.index.duplicated()]

    # MP-10: the reliability gate first (seasons <= 2024 residuals; skipped by the outcome-free --no-screen pass)
    pool = mp10_pool(Ls, prices)
    if args.no_screen:
        roles = False
    else:
        rel = reliability(pool, fa.set_index("match_id")["season"], fa.set_index("match_id")["tour"])
        extras["mp10_reliability"] = rel
        roles = rel["gate_passes"]
        log(f"MP-10 reliability: {rel['players_ge40_all']} gate {roles}")
    v10 = mp10_build(Ls, prices, roles=roles)
    v08 = mp08_build(Ls, frame_ids)
    v09 = mp09_build(Ls, frame_ids)
    fe = first_at_event(Ls)
    log("player statistics built")

    # ---- probes
    if not args.no_probe:
        probes = {}
        c10 = ["mp10_rec"] + (["mp10_fav", "mp10_dog"] if roles else [])
        probes["mp10"] = H.timing_probe(lambda Q: mp10_build(Q, prices, roles=roles), Ls, c10)
        log(f"probe MP-10: {probes['mp10']}")
        probes["mp08"] = H.timing_probe(lambda Q: mp08_build(Q, frame_ids), Ls,
                                        ["mp08_seed", "mp08_entry", "mp08_seed_band", "mp08_entry_band"])
        log(f"probe MP-08: {probes['mp08']}")
        probes["mp09"] = H.timing_probe(lambda Q: mp09_build(Q, frame_ids), Ls, ["mp09_defend", "mp09_champ"])
        log(f"probe MP-09: {probes['mp09']}")
        probes["columns_passed"] = slim_cols
        probes["note"] = ("MP-01 and MP-02 read only each match's own lines (no other match's facts), so no probe "
                          "applies; MP-08 reads no result column (pre-match ranks, the calendar, the points table), so "
                          "its probe is a formality; MP-10 and MP-09 read won.")
        write_json(OUT / "probes.json", probes)

    # ---- values (every frame match) and splits
    V = pd.DataFrame({"match_id": fa["match_id"].to_numpy()})
    V = V.merge(m1[["match_id", "mp01_lop_close", "mp01_lop_open", "mp01_lop_move", "mp01_diff_close"]],
                on="match_id", how="left", validate="one_to_one")
    V["mp02_bol"], V["mp02_pin"] = mp02_bol, mp02_pin
    player_stats = {"mp10_rec": v10, "mp08_seed": v08, "mp08_entry": v08, "mp08_seed_band": v08,
                    "mp08_entry_band": v08, "mp09_defend": v09, "mp09_champ": v09}
    if roles:
        player_stats.update({"mp10_fav": v10, "mp10_dog": v10})
    for nm, src in player_stats.items():
        a, b = H.at_frame(src, nm, fa)
        V[f"{nm}_a"], V[f"{nm}_b"], V[nm] = a, b, a - b
    V.to_parquet(OUT / "values.parquet", index=False)
    a_first, b_first = H.at_frame(fe.astype({"first_at_event": float}), "first_at_event", fa)
    n10a, n10b = H.at_frame(v10, "mp10_rec_n", fa)
    pfa, pfb = H.at_frame(v09, "mp09_prev_found", fa)
    lvl = fa["in_level"].to_numpy(float)
    fresh = mk2["bol_close_after_listed_min"].to_numpy(float)
    m1x = m1.set_index("match_id").reindex(fa["match_id"])
    S = pd.DataFrame({
        "match_id": fa["match_id"].to_numpy(),
        "L_bol_close": Lbc, "L_bol_open": Lbo,
        "L_pin_last": mk2["L_pin_last"].to_numpy(float), "L_pin_open": mk2["L_pin_open"].to_numpy(float),
        "tg_open": m1x["tg_open_clean"].to_numpy(float), "tg_close": m1x["tg_close_clean"].to_numpy(float),
        "orient_method": mk2["orient_method"].fillna("").to_numpy(),
        "mp01_nosums": m1x["mp01_nosums"].to_numpy(float),
        "bol_close_after_listed_min": fresh,
        "bol_fresh": np.where(np.isfinite(fresh), np.where(fresh >= -60, "fresh", "stale"), ""),
        "level_tier": np.where(np.isin(lvl, [0.0, 1.0, 2.0]), "hi", np.where(np.isin(lvl, [3.0, 4.0]), "lo", "")),
        "round_tier": np.where(np.isfinite(a_first) & np.isfinite(b_first),
                               np.where((a_first == 1) & (b_first == 1), "first", "later"), ""),
        "price_tier_bol": price_tier(mk2["p_bol_close"].to_numpy(float)),
        "price_tier_pin": price_tier(1 / (1 + np.exp(-mk2["L_pin_last"].to_numpy(float)))),
        "mp10_n_a": n10a, "mp10_n_b": n10b, "mp09_prev_found_a": pfa, "mp09_prev_found_b": pfb})
    S.to_parquet(OUT / "splits.parquet", index=False)
    log("values.parquet and splits.parquet written")

    stats = ["mp01_lop_close", "mp01_lop_open", "mp01_lop_move", "mp01_diff_close", "mp02_bol", "mp02_pin",
             "mp10_rec"] + (["mp10_fav", "mp10_dog"] if roles else []) + \
        ["mp08_seed", "mp08_entry", "mp08_seed_band", "mp08_entry_band", "mp09_defend", "mp09_champ"]
    cov = coverage_table(fa, V, stats)
    keep = (pd.to_datetime(fa["tournament_date"]) < SEALED).to_numpy()
    cov["mp01_rows_without_store_sums_le_2026_07_28"] = int(S.loc[keep, "mp01_nosums"].fillna(0).sum())
    cov["mp09_previous_edition_found_share"] = {
        f"{t}_{lab}": float(np.nanmean(pfa[keep & (fa["tour"] == t).to_numpy() & fa["season"].between(a, b).to_numpy()]))
        for t in ("atp", "wta") for lab, (a, b) in (("2013_24", (2013, 2024)), ("2025_26", (2025, 2026)))}
    write_json(OUT / "coverage.json", cov)
    log("coverage.json written")

    if args.no_screen:
        write_json(OUT / "extras.json", extras)
        return 0

    # ---- screening (seasons <= 2024 through the harness)
    fr = H.load_frame()
    Sx = S.set_index("match_id").reindex(fr["match_id"])
    fr["L_bol"] = Sx["L_bol_close"].to_numpy(float)
    fr["L_pin_ot"] = Sx["L_pin_last"].to_numpy(float)
    Vx = V.set_index("match_id").reindex(fr["match_id"]).reset_index()
    Sxr = Sx.reset_index()
    # MP-10 cross-check: residuals from the long table's won equal load_frame's y - p on frame side A (<= 2024)
    pa_ = pool[pool["side"] == "A"].set_index("match_id")["r"]
    rr = pa_.reindex(fr["match_id"]).to_numpy(float)
    yy = fr["y"].to_numpy(float) - fr["p_mkt"].to_numpy(float)
    both = np.isfinite(rr)
    extras["mp10_residual_check"] = {"rows": int(both.sum()), "max_abs_diff": float(np.max(np.abs(rr[both] - yy[both]))),
                                     "frame_rows_le_2024": int(len(fr))}
    plan = [
        {"name": "mp01_lop_close", "col": "mp01_lop_close", "kind": "context", "bases": ("L_bol",)},
        {"name": "mp01_lop_open", "col": "mp01_lop_open", "kind": "context", "bases": ("L_bol",)},
        {"name": "mp01_lop_move", "col": "mp01_lop_move", "kind": "context", "bases": ("L_bol",)},
        {"name": "mp01_diff_close", "col": "mp01_diff_close", "kind": "diff", "bases": ("L_bol",)},
        {"name": "mp02_bol", "col": "mp02_bol", "kind": "diff", "bases": ("L_bol",), "lenses": ("close", "model")},
        {"name": "mp02_pin", "col": "mp02_pin", "kind": "diff", "bases": ("L_pin_ot",), "lenses": ("close", "model")},
        {"name": "mp10_rec", "col": "mp10_rec", "kind": "diff"}]
    if roles:
        plan += [{"name": "mp10_fav", "col": "mp10_fav", "kind": "diff"},
                 {"name": "mp10_dog", "col": "mp10_dog", "kind": "diff"}]
    plan += [{"name": n, "col": n, "kind": "diff"} for n in
             ("mp08_seed", "mp08_entry", "mp08_seed_band", "mp08_entry_band", "mp09_defend", "mp09_champ")]
    long, ex = run_screens(fr, Vx, plan)
    extras["per_statistic"] = ex
    tiers = run_tiers(fr, Vx, Sxr)
    long = pd.concat([long, tiers], ignore_index=True)
    long.to_csv(OUT / "long.csv", index=False)
    summ = summary_table(long)
    summ.to_csv(OUT / "summary.csv", index=False)
    write_json(OUT / "extras.json", extras)
    log("long.csv, summary.csv, extras.json written")
    diag = diagnostics(fr, Vx)
    diag.to_csv(OUT / "diagnostics_long.csv", index=False)
    ds = []
    for base, lens in (("L", "close"), ("L_bol", "close[L_bol]")):
        sub = diag[diag["name"].str.endswith(f"@{base}")]
        s = H.summarize(sub, lens=lens)
        s.insert(2, "base", base)
        ds.append(s)
    pd.concat(ds, ignore_index=True).to_csv(OUT / "diagnostics_summary.csv", index=False)
    log("diagnostics (post hoc) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
