"""S2a, the rhythm-and-body builder of the unpriced-leads study (docs/studies/unpriced_leads/, 13 Oct 2026).

Brief: docs/studies/unpriced_leads/briefs/08_rhythm_builder.md (binding). Definitions: team/rhythm_body.md §§ 3, 5, 6 and
rhythm_body_ideas.csv; MP-22 from team/market_practitioner_ideas.csv. Memo: docs/studies/unpriced_leads/team/
rhythm_builder.md. Outputs: data/studies/unpriced_leads/candidates/rhythm/.

CLOCK TIMES (settled outcome-free by time_sources(), written to time_sources.json). The match clock (timing.parquet) is
day-level (`start` has no fraction). Hour-level starts come from the clock's link files; the first source with a time
wins, in this order: Flashscore, api-tennis, Live Tennis API (both copies of Flashscore's times), the WTA API, the Slam
feeds, TDI (all actual starts of play), then SofaScore and the Match Charting Project (scheduled times, a median 10
minutes before the first point). A 00:00 UTC time is kept (an 11:00 start in Melbourne is 00:00 UTC) except on a
date-only (`utc_date`) row. TennisLive's times are placeholders (09:00) and are never used; its dates are used.
A match's END is Flashscore's end where the implied duration is 15-420 minutes, else its start plus Stage 0's minutes
(15-420): the same rule in every season (variant "ii": minutes first, then Flashscore's end).

STATISTICS. Each is a per-player value from the player's STRICTLY EARLIER rows of H.long_table (own order), aligned to
the frame with H.at_frame; the screened column is A - B unless stated. d = the match's best-estimate day `obs`.
  RB01  rb01_d7, rb01_d7_here, rb01_d7_else, rb01_d1   log1p(doubles matches played on days d-7..d-1; at this event /
        elsewhere / on day d-1 only), TennisLive 2018-26 (walkovers out; same-day doubles out: order unknown). Members
        are mapped to Stage 0 ids through the lower-level team's TennisLive crosswalk (unique normalised names), events
        to Stage 0 tournament ids through the event's singles rows (majority id). Level variants: the primary counts
        tour-level doubles only (tour, Slam, Finals: TennisLive's ITF doubles enter in 2020, a covariate shift);
        rb01_d7_nonitf adds Challenger and WTA 125; rb01_d7_all adds ITF.
        rb01s_entered (men, Sackmann's tour-level doubles 2010-20, event-level): 1[in this event's doubles draw];
        rb01s_prev: log1p(doubles matches at events whose last singles day is in d-8..d-1 and that started at most 14
        days before this event's start). Flagged: a separate version, values for men's 2013-17 frame matches only.
  RB03  rb03_short = s(rest_h), s(h) = max(0, 24 - h)/24; rb03_lt20 = 1[rest_h < 20]. rest_h = this match's start minus
        the end of the player's previous played match (any level); valid 0.25 h-60 days. Where hours are unknown but
        the clock shows the previous match's latest finish day at least 2 days before this match's earliest start
        day, s = 0 (rest surely > 24 h); with no earlier played match, s = 0.
  RB04  rb04_gap (match-level): when both rests are under 72 h, clip(rest_A - rest_B, -36, 36)/12; 0 when either rest
        is at least 72 h (hours, or the clock's day gap of at least 4 days, or no earlier match); rb04_a/_b hold the
        rests in hours (inf = at least 72 h).
  RB05  rb05_ratio = log(1 + previous duration in hours / rest_h) when the previous match lasted 150+ minutes and
        rest_h < 72; 0 when it was shorter or rest is at least 72 h.
  RB06  rb06_late = 1[the previous played match was on day d-1 and was the last to end on its day at its event (the
        tour's tournament id; every played match of that event-day has an end, and all ended before this match started)]
        x 1[this match started within 150 minutes of the first start at its event that day]; time-zone free.
  RB13  for a qualifier (Q) or lucky loser (LL) in the first main-draw match at the event, else 0:
        rb13_qcost = log1p(points played in this event's qualifying: box-score tpw_d, else games x points per game
        fitted on 2010-12 matches by tour and best of); rb13_qrest = max(0, 48 - hours since the last qualifying
        match ended)/48; rb13_ll = 1[LL]. rb13_ll_on (secondary): 1[LL] x log1p(matches already played here), every
        main-draw round. Added before any screen, to tell the cost from the tag: rb13_qtag = 1[Q or LL in the first
        main-draw match]; rb13_qcost_dev = log1p(points) minus its 2010-12 mean for the same tour and number of
        qualifying matches (0 for direct entrants); rb13_qcost_box (values only) uses box scores alone.
  RB10  rb10_drift = (age - 29)+ x RS, RS = Dbar/(|Obar| + |Dbar| + 0.25); Obar, Dbar = means over the eight
        statistics of the player's surface-effective IOS offence and defence (surface_features.parquet, the store's
        pp__ios_srfO_* / pp__ios_srfD_* source; leak-proof), each z-scored by tour on 2013-24 frame rows and oriented
        so higher = better (double faults reversed); rb10_drift_spw: serve points won only.
  RB15  rb15_r28 = 1[retired or gave a walkover, any level, in the 28 days before] (the 42-day-break condition is
        vacuous inside 28 days); rb15_r90 = the same within 90 days with no 42-day break since; mp22_slam_r1 =
        rb15_r28 x 1[Slam main-draw first round] (withdrawals are not held).
  RB14  rb14_cold: the player's first main-draw match at the event comes after a bye (it is not in the event's first
        main-draw round) at a 48, 56 or 96 draw, and the opponent has already played here; value -1 for that player,
        so A - B is signed toward the opponent. rb14_cold28 adds 28-player draws. The draw is read from its structure
        (entrants = bracket / 2 + first-round matches, within 2): Stage 0's draw_size is the bracket in 2016-24.
        Placebo rb14_seed_r1_nobye: -1 for a seeded player in his first main-draw match in a draw without byes.
  U-138 u138_on_mine = log1p(played matches already at this event, qualifying included); u138_on_nobye: the same
        with the bye-seed matches set to 0. Pool columns screened beside: u138_pool (store fp__f17_info__bd11_on_n,
        log1p A - log1p B), u132_pool (store pp__rest_days, A - B), u132_log_mine (log1p days since the previous played
        match, A - B).
  RB02  rb02_dblrust = log1p(singles surface layoff) - log1p(layoff counting doubles on the surface), layoffs in days
        capped at 365 (seasons 2019+, a year after TennisLive starts).
  RB20  rb20_excess = log1p(points played at this event before) - its 2010-12 mean given tour, best of, surface and
        min(matches here, 6); 0 with no match here.
  RB23  rb23_offseason = max(0, ln(56 / days off before the season's first match)) in the player's first three
        matches of a calendar season, else 0.

TIMING. Own-sequence values use strictly earlier rows (shift(1) / exclusive cumulative sums). RB06 reads other players'
end times of the previous event-day only when they all precede this match's start (hours), and other matches' start
times of the same day only through the day's first start (at or before this match's own start). This match's own
start is a schedule fact (kept as a datetime column, so the harness's probe leaves it unscrambled); ends, minutes,
points, games and statuses are results. Every L-based builder runs H.timing_probe; doubles (an external table) and
RB10 (an external leak-proof table) get their own checks (probes.json).

BLINDING. Outcomes only through the harness (H.load_frame, the lenses: matches before 1 Jan 2025). Values are written
for every frame match; coverage and every count stop at 28 Jul 2026 (the sealed set is not counted).

Run: ./python.sh src/eda/unpriced_leads/build_rhythm.py          (CPU; deterministic)
     --no-probe   skip the timing probes (values and screens only)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402

OUT = H.OUT / "candidates" / "rhythm"
LINKS = ROOT / "data" / "studies" / "match_timing" / "links"
TL_LISTED = ROOT / "data" / "dump" / "points" / "tennislive" / "listed.parquet"
TL_XWALK = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "stage0" / "C0_now" / "evidence" / \
    "crosswalk_tennislive.csv"
SACK = ROOT / "data" / "dump" / "matches" / "sackmann_archive" / "atp"
SURF_IOS = ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet"
STORE = ROOT / "data" / "studies" / "feature_universe" / "store.parquet"
SEALED = pd.Timestamp("2026-07-29")
DAY0 = pd.Timestamp("1970-01-01")
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
CAL_END_DAY = float((pd.Timestamp("2013-01-01") - DAY0).days)
START_SOURCES = ("flashscore", "api_tennis", "live_tennis_api", "wta_api", "slam_feeds", "tdi", "sofascore",
                 "match_charting")
ACTUAL_SOURCES = ("flashscore", "api_tennis", "live_tennis_api", "wta_api", "slam_feeds", "tdi")
DUR_OK = (15.0, 420.0)            # plausible match durations, minutes
REST_OK = (0.25, 60 * 24.0)       # plausible rest, hours
STATS8 = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
RS_EPS = 0.25
TOUR_KINDS = ("tour", "slam", "finals")
NONITF_KINDS = TOUR_KINDS + ("challenger", "wta125")
U138_STORE = ("fp__f17_info__bd11_on_n_a", "fp__f17_info__bd11_on_n_b")
U132_STORE = ("pp__rest_days_a", "pp__rest_days_b")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def num(s) -> np.ndarray:
    """A float copy (writable) of a column or array."""
    return np.array(pd.to_numeric(pd.Series(s), errors="coerce").to_numpy(dtype=float, na_value=np.nan), dtype=float)


def minutes_utc(t) -> np.ndarray:
    """Minutes since the epoch of a UTC datetime column; NaN where missing."""
    t = pd.to_datetime(pd.Series(t), utc=True, errors="coerce")
    return np.array(((t - EPOCH).dt.total_seconds() / 60.0).to_numpy(dtype=float, na_value=np.nan), dtype=float)


def norm_name(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


def prev_index(pid: np.ndarray, flag: np.ndarray) -> np.ndarray:
    """For each row, the index of the same player's last STRICTLY EARLIER row where flag is true (rows in player
    order); -1 where none."""
    idx = pd.Series(np.where(flag, np.arange(len(pid), dtype=float), np.nan))
    g = pd.Series(pid)
    prev = idx.groupby(g.to_numpy()).shift(1)
    prev = prev.groupby(g.to_numpy()).ffill()
    return np.nan_to_num(prev.to_numpy(dtype=float), nan=-1.0).astype(np.int64)


def take(a: np.ndarray, j: np.ndarray, fill=np.nan) -> np.ndarray:
    """a[j] where j >= 0, else fill."""
    a = np.asarray(a)
    out = np.where(j >= 0, a[np.maximum(j, 0)], fill)
    return out


def segments(pid: np.ndarray, tid: np.ndarray) -> np.ndarray:
    """Event segments: consecutive rows of one player at one tournament id (feature_interactions f23's `seg`)."""
    new = np.r_[True, (pid[1:] != pid[:-1]) | (tid[1:] != tid[:-1])]
    return np.cumsum(new) - 1


def excl_cumsum(v: np.ndarray, grp: np.ndarray) -> np.ndarray:
    """Sum of v over the STRICTLY EARLIER rows of the same group (rows in order): the running sum shifted by one row,
    so the current row's own value never enters (cumsum - v would, in the last bits of a float)."""
    s = pd.Series(np.nan_to_num(v.astype(float)))
    return s.groupby(grp).cumsum().groupby(grp).shift(1).fillna(0.0).to_numpy(dtype=float)


# ------------------------------------------------------------------------------------------------- the clock times

def link_times() -> pd.DataFrame:
    """match_id -> t_start (UTC; the first source with a time, START_SOURCES order), start_src, and end_fs (Flashscore's
    end, minutes since the epoch; a result)."""
    parts = []
    for name in START_SOURCES:
        d = pd.read_parquet(LINKS / f"{name}.parquet", columns=["match_id", "start_utc", "date_basis"])
        d["t0"] = pd.to_datetime(d["start_utc"], errors="coerce", utc=True)
        midnight = (d["t0"].dt.hour == 0) & (d["t0"].dt.minute == 0) & (d["t0"].dt.second == 0)
        bad = d["t0"].isna() | (midnight & d["date_basis"].eq("utc_date"))
        if name == "match_charting":
            bad = bad | midnight
        d = d[~bad.to_numpy()]
        d["start_src"] = name
        parts.append(d[["match_id", "t0", "start_src"]])
    t = pd.concat(parts, ignore_index=True)
    t["match_id"] = t["match_id"].astype(str)
    t = t.drop_duplicates("match_id", keep="first")
    rec = pd.read_parquet(LINKS / "flashscore_records.parquet", columns=["fs_match_id", "end_utc"])
    fl = pd.read_parquet(LINKS / "flashscore.parquet", columns=["match_id", "source_key"])
    fl = fl.merge(rec, left_on="source_key", right_on="fs_match_id", how="left")
    fl["match_id"] = fl["match_id"].astype(str)
    fl = fl.drop_duplicates("match_id")
    fl["end_fs"] = minutes_utc(fl["end_utc"])
    t = t.merge(fl[["match_id", "end_fs"]], on="match_id", how="outer")
    return t.rename(columns={"t0": "t_start"})


def load_long() -> pd.DataFrame:
    """H.long_table with the box-score points (tpw_d) and the clock times: t_start (a datetime: a schedule fact, left
    unscrambled by the probe), start_src (a string) and end_fs (a float: a result, scrambled by the probe)."""
    L = H.long_table(player_cols=["tpw_d"])
    T = link_times()
    L = L.merge(T, on="match_id", how="left", validate="many_to_one")
    return L


# ------------------------------------------------------------------------------------- builders on the long table

def ends(L: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per row: start (minutes since the epoch), end by rule (i) (Flashscore's end, else start + minutes), end by rule
    (ii) (start + minutes, else Flashscore's end), duration (Stage 0's minutes, else Flashscore's end - start)."""
    t0 = minutes_utc(L["t_start"])
    efs = num(L["end_fs"])
    mins = num(L["minutes"])
    dfs = efs - t0
    ok_fs = np.isfinite(dfs) & (dfs >= DUR_OK[0]) & (dfs <= DUR_OK[1])
    ok_min = np.isfinite(mins) & (mins >= DUR_OK[0]) & (mins <= DUR_OK[1])
    ok_m = np.isfinite(t0) & ok_min
    end1 = np.where(ok_fs, efs, np.where(ok_m, t0 + mins, np.nan))
    end2 = np.where(ok_m, t0 + mins, np.where(ok_fs, efs, np.nan))
    dur = np.where(ok_min, mins, np.where(ok_fs, dfs, np.nan))
    return t0, end1, end2, dur


REST_COLS = ["rest_h", "rest_h2", "rb03_short", "rb03_short2", "rb03_lt20", "rb04_rest", "rb05_ratio", "prev_end",
             "prev_lf", "u132_days"]


def build_rest(L: pd.DataFrame) -> pd.DataFrame:
    """RB03, RB04's per-player rest, RB05, U-132 (mine); the previous played match's end for the stale-line check."""
    pid = L["player_id"].to_numpy()
    played = L["played"].to_numpy(bool)
    t0, end1, end2, dur = ends(L)
    j = prev_index(pid, played)
    has = j >= 0
    pe1, pe2, pdur = take(end1, j), take(end2, j), take(dur, j)
    rest = (t0 - pe1) / 60.0
    rest2 = (t0 - pe2) / 60.0
    for r in (rest, rest2):
        r[~((r >= REST_OK[0]) & (r <= REST_OK[1]))] = np.nan
    es, lf = num(L["es"]), num(L["lf"])
    plf = take(lf, j)
    gap = es - plf                                   # the clock's day-level lower bound on the rest, in days
    sure24 = ~has | (gap >= 2)
    s1 = np.where(np.isfinite(rest), np.clip(24.0 - rest, 0, 24) / 24.0, np.where(sure24, 0.0, np.nan))
    s2 = np.where(np.isfinite(rest2), np.clip(24.0 - rest2, 0, 24) / 24.0, np.where(sure24, 0.0, np.nan))
    lt20 = np.where(np.isfinite(rest), (rest < 20).astype(float), np.where(sure24, 0.0, np.nan))
    r72 = np.where(np.isfinite(rest), rest, np.where(~has | (gap >= 4), np.inf, np.nan))
    r72 = np.where(r72 >= 72, np.inf, r72)
    rb05 = np.full(len(pid), np.nan)
    rb05[r72 == np.inf] = 0.0
    kn = np.isfinite(r72)
    rb05[kn & (pdur < 150)] = 0.0
    m = kn & (pdur >= 150)
    rb05[m] = np.log1p((pdur[m] / 60.0) / r72[m])
    om = num(L["obs_mono"])
    days = np.where(has, om - take(om, j), np.nan)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "rest_h": rest, "rest_h2": rest2,
                         "rb03_short": s1, "rb03_short2": s2, "rb03_lt20": lt20, "rb04_rest": r72, "rb05_ratio": rb05,
                         "prev_end": pe1, "prev_lf": plf, "u132_days": days})


RB06_COLS = ["rb06_late"]


def build_rb06(L: pd.DataFrame) -> pd.DataFrame:
    """RB06: last to end on its event-day yesterday x early slot today (time-zone free)."""
    pid = L["player_id"].to_numpy()
    played = L["played"].to_numpy(bool)
    t0, end1, _, _ = ends(L)
    # the event is the tour's tournament id (the men's and women's events of a combined tournament share an id in
    # 2016-19 and not in other seasons)
    tid = (L["tour"].astype(str) + "|" + L["tournament_id"].astype(str)).to_numpy()
    obs = num(L["obs"])
    M = pd.DataFrame({"match_id": L["match_id"].to_numpy(), "tid": tid, "obs": obs, "t0": t0, "end": end1,
                      "played": played}).drop_duplicates("match_id")
    M["pe"] = M["played"] & np.isfinite(M["end"])
    M["end_p"] = np.where(M["played"], M["end"], np.nan)
    agg = M.groupby(["tid", "obs"]).agg(n_played=("played", "sum"), n_pe=("pe", "sum"), max_end=("end_p", "max"),
                                        first_start=("t0", "min"))
    j = prev_index(pid, played)
    jj = np.maximum(j, 0)
    yday = (j >= 0) & (obs[jj] == obs - 1)
    kp = pd.MultiIndex.from_arrays([np.where(j >= 0, tid[jj], ""), np.where(j >= 0, obs[jj], np.nan)])
    g_prev = agg.reindex(kp)
    complete = (g_prev["n_pe"].to_numpy(float) == g_prev["n_played"].to_numpy(float))
    max_end = g_prev["max_end"].to_numpy(float)
    e_j = np.where(j >= 0, end1[jj], np.nan)
    is_last = complete & np.isfinite(e_j) & (e_j >= max_end - 1.0)
    not_last = np.isfinite(e_j) & np.isfinite(max_end) & (max_end > e_j + 1.0)
    before = np.isfinite(t0) & np.isfinite(max_end) & (max_end < t0)
    g_today = agg.reindex(pd.MultiIndex.from_arrays([tid, obs]))
    early = np.isfinite(t0) & (t0 <= g_today["first_start"].to_numpy(float) + 150.0)
    late = np.full(len(pid), np.nan)
    late[~yday] = 0.0
    late[yday & not_last] = 0.0
    ok = yday & is_last & before
    late[ok] = early[ok].astype(float)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "rb06_late": late})


def ppg_table(L: pd.DataFrame) -> dict:
    """Points per game by tour and best of, from played matches of 2010-12 (surely finished before 2013) with both a
    box score's total points and a parsed score. Frozen; outcome-free (no winner)."""
    lf, tp, gm = num(L["lf"]), num(L["tpw_d"]), num(L["games"])
    m = (lf + 1 <= CAL_END_DAY) & L["played"].to_numpy(bool) & (tp > 0) & (gm > 0)
    d = pd.DataFrame({"tour": L["tour"].to_numpy()[m], "bo": num(L["best_of"])[m], "tp": tp[m], "gm": gm[m]})
    s = d.groupby(["tour", "bo"])[["tp", "gm"]].sum()
    return {f"{t}|{int(b)}": float(r["tp"] / r["gm"]) for (t, b), r in s.iterrows()}


def points_played(L: pd.DataFrame, ppg: dict) -> np.ndarray:
    """Points played in each row's match: the box score's total (tpw_d), else games x points per game; NaN if neither."""
    tp, gm, bo = num(L["tpw_d"]), num(L["games"]), num(L["best_of"])
    key = pd.Series(L["tour"].astype(str).to_numpy()) + "|" + pd.Series(np.nan_to_num(bo, nan=3).astype(int)).astype(str)
    rate = key.map(ppg).to_numpy(dtype=float)
    return np.where(np.isfinite(tp) & (tp > 0), tp, gm * rate)


RB13_COLS = ["rb13_qcost", "rb13_qrest", "rb13_ll", "rb13_ll_on", "rb13_qcost_box", "rb13_qtag", "rb13_qcost_dev"]


def build_rb13(L: pd.DataFrame, ppg: dict) -> pd.DataFrame:
    """RB13: qualifier and lucky-loser arrival cost in the first main-draw match."""
    pid = L["player_id"].to_numpy()
    tid = L["tournament_id"].astype(str).to_numpy()
    seg = segments(pid, tid)
    played = L["played"].to_numpy(bool)
    qual = L["qualifying"].to_numpy(bool)
    on_n = excl_cumsum(played.astype(float), seg)
    first_md = ~qual & (excl_cumsum((~qual).astype(float), seg) == 0)
    entry = L["entry"].astype(str).to_numpy()
    isq, isll = np.isin(entry, ["Q", "LL"]), entry == "LL"
    pts = points_played(L, ppg)
    qp = qual & played
    qpts = excl_cumsum(np.where(qp, np.nan_to_num(pts), 0.0), seg)
    nq = excl_cumsum(qual.astype(float), seg)
    nmiss = excl_cumsum((qp & ~np.isfinite(pts)).astype(float), seg)
    tp = num(L["tpw_d"])
    nbox_miss = excl_cumsum((qp & ~(tp > 0)).astype(float), seg)
    qbox = excl_cumsum(np.where(qp & (tp > 0), tp, 0.0), seg)
    cand = first_md & isq
    qcost = np.where(cand, np.where((nq >= 1) & (nmiss == 0), np.log1p(qpts), np.nan), 0.0)
    qcost_box = np.where(cand, np.where((nq >= 1) & (nbox_miss == 0), np.log1p(qbox), np.nan), 0.0)
    jq = prev_index(pid, qp)
    same = (jq >= 0) & (take(seg, jq, -1) == seg)
    t0, end1, _, _ = ends(L)
    hq = (t0 - take(end1, jq)) / 60.0
    hq[~((hq >= REST_OK[0]) & (hq <= REST_OK[1]))] = np.nan
    gapq = num(L["es"]) - take(num(L["lf"]), jq)
    qr = np.where(np.isfinite(hq), np.clip(48.0 - hq, 0, 48) / 48.0, np.where(gapq >= 3, 0.0, np.nan))
    qrest = np.where(cand, np.where(same, qr, np.nan), 0.0)
    ll = np.where(first_md & isll, 1.0, 0.0)
    ll_on = np.where(~qual & isll, np.log1p(on_n), 0.0)
    # the tag alone, and the cost beyond what the run's length implies: log1p(points) minus its mean over 2010-12
    # candidate rows (surely finished before 2013) of the same tour and number of qualifying matches (capped at 3)
    tag = np.where(cand, 1.0, 0.0)
    nqc = np.minimum(nq, 3)
    tour = L["tour"].astype(str).to_numpy()
    calm = cand & (nq >= 1) & (nmiss == 0) & (num(L["lf"]) + 1 <= CAL_END_DAY)
    mu = pd.DataFrame({"t": tour[calm], "n": nqc[calm], "y": np.log1p(qpts[calm])}).groupby(["t", "n"])["y"].mean()
    m_ = mu.reindex(pd.MultiIndex.from_arrays([tour, nqc])).to_numpy(float)
    dev = np.where(cand, np.where((nq >= 1) & (nmiss == 0), np.log1p(qpts) - m_, np.nan), 0.0)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "rb13_qcost": qcost,
                         "rb13_qrest": qrest, "rb13_ll": ll, "rb13_ll_on": ll_on, "rb13_qcost_box": qcost_box,
                         "rb13_qtag": tag, "rb13_qcost_dev": dev})


RB15_COLS = ["rb15_r28", "rb15_r90", "mp22_slam_r1"]


def build_rb15(L: pd.DataFrame) -> pd.DataFrame:
    """RB15: a retirement or walkover given (any level) recently; MP-22's Slam-first-round form."""
    pid = L["player_id"].to_numpy()
    won = L["won"].to_numpy(bool)
    status = L["status"].astype(str).to_numpy()
    rw = ~won & np.isin(status, ["retired", "walkover"])
    om = num(L["obs_mono"])
    j = prev_index(pid, rw)
    days = np.where(j >= 0, om - take(om, j), np.inf)
    brk = np.nan_to_num(num(L["rest_days"])) >= 42
    seg42 = pd.Series(brk.astype(np.int64)).groupby(pid).cumsum().to_numpy()
    r28 = (days <= 28).astype(float)
    r90 = ((days <= 90) & (take(seg42, j, -1) == seg42)).astype(float)
    slam_r1 = ((L["level"].astype(str) == "GS") & (L["round"].astype(str) == "R128")).to_numpy() & \
        ~L["qualifying"].to_numpy(bool)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "rb15_r28": r28, "rb15_r90": r90,
                         "mp22_slam_r1": r28 * slam_r1})


ONSITE_COLS = ["on_n", "u138_on_mine", "rb14_cold", "rb14_cold28", "rb14_seed_r1_nobye", "draw_entrants"]


def build_onsite(L: pd.DataFrame) -> pd.DataFrame:
    """U-138 (mine: played matches already at this event) and RB14 (the bye seed's cold start)."""
    pid = L["player_id"].to_numpy()
    tid = L["tournament_id"].astype(str).to_numpy()
    seg = segments(pid, tid)
    played = L["played"].to_numpy(bool)
    qual = L["qualifying"].to_numpy(bool)
    on_n = excl_cumsum(played.astype(float), seg)
    first_md = ~qual & (excl_cumsum((~qual).astype(float), seg) == 0)
    ro = num(L["round_order"])
    md = ~qual & (ro >= 11) & (ro <= 17)                      # main-draw knockout rounds (RR excluded)
    ev = [L["tour"].astype(str).to_numpy(), tid, num(L["tday"])]   # combined events share an id in 2016-19
    fr = pd.Series(np.where(md, ro, np.nan)).groupby(ev).transform("min").to_numpy(float)
    # Stage 0's draw_size is the entrant count in 2012-15 and 2025-26 but the bracket size in 2016-24, so the draw is
    # read from its structure: entrants = bracket / 2 + first-round matches (bracket 128, 64, 32, 16 for round order
    # 11..14); a 96-player draw has 32 first-round matches in a 128 bracket
    first = md & (ro == fr)
    n1 = pd.Series(np.where(first, 0.5, 0.0)).groupby(ev).transform("sum").to_numpy(float)   # two rows per match
    bracket = np.where(np.isfinite(fr), 2.0 ** (18 - np.nan_to_num(fr, nan=18)), np.nan)
    ds = bracket / 2 + n1
    bye = first_md & md & (ro > fr)
    big = ((ds >= 46) & (ds <= 58)) | ((ds >= 94) & (ds <= 98))
    key = pd.Series(on_n, index=pd.MultiIndex.from_arrays([L["match_id"].to_numpy(), pid]))
    key = key[~key.index.duplicated()]
    opp_on = key.reindex(pd.MultiIndex.from_arrays([L["match_id"].to_numpy(), L["opponent_id"].to_numpy()])) \
        .to_numpy(float)
    cold48 = np.where(bye & big & (opp_on >= 1), -1.0, 0.0)
    cold28 = np.where(bye & (big | ((ds >= 26) & (ds <= 30))) & (opp_on >= 1), -1.0, 0.0)
    # placebo (defined before it was read): a seeded player's first main-draw match in a draw WITHOUT byes (entrants
    # within 2 of the bracket), any opponent: if seeds simply under-perform the close in their first match at an event,
    # this reads like rb14; if the bye's cold start is the mechanism, it does not
    seeded = np.nan_to_num(num(L["seed"]), nan=0.0) > 0
    nobye = np.abs(ds - bracket) <= 2
    seed_r1 = np.where(first_md & md & (ro == fr) & seeded & nobye, -1.0, 0.0)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "on_n": on_n,
                         "u138_on_mine": np.log1p(on_n), "rb14_cold": cold48, "rb14_cold28": cold28,
                         "rb14_seed_r1_nobye": seed_r1, "draw_entrants": ds})


RB20_COLS = ["rb20_excess"]


def build_rb20(L: pd.DataFrame, ppg: dict) -> pd.DataFrame:
    """RB20: points played at this event before, beyond their 2010-12 expectation."""
    pid = L["player_id"].to_numpy()
    tid = L["tournament_id"].astype(str).to_numpy()
    seg = segments(pid, tid)
    played = L["played"].to_numpy(bool)
    on_n = excl_cumsum(played.astype(float), seg)
    pts = points_played(L, ppg)
    here = excl_cumsum(np.where(played, np.nan_to_num(pts), 0.0), seg)
    miss = excl_cumsum((played & ~np.isfinite(pts)).astype(float), seg)
    y = np.where((on_n >= 1) & (miss == 0), np.log1p(here), np.nan)
    k = pd.DataFrame({"tour": L["tour"].astype(str).to_numpy(), "bo": np.nan_to_num(num(L["best_of"]), nan=3),
                      "srf": L["surface"].astype(str).to_numpy(), "n": np.minimum(on_n, 6), "y": y})
    cal = (num(L["lf"]) + 1 <= CAL_END_DAY) & np.isfinite(y)
    e4 = k[cal].groupby(["tour", "bo", "srf", "n"])["y"].agg(["mean", "size"])
    e4 = e4[e4["size"] >= 30]["mean"]
    e3 = k[cal].groupby(["tour", "bo", "n"])["y"].mean()
    ex4 = e4.reindex(pd.MultiIndex.from_frame(k[["tour", "bo", "srf", "n"]])).to_numpy(float)
    ex3 = e3.reindex(pd.MultiIndex.from_frame(k[["tour", "bo", "n"]])).to_numpy(float)
    ex = np.where(np.isfinite(ex4), ex4, ex3)
    out = np.where(on_n == 0, 0.0, y - ex)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "rb20_excess": out})


RB23_COLS = ["rb23_offseason"]


def build_rb23(L: pd.DataFrame) -> pd.DataFrame:
    """RB23: a short off-season, in the player's first three matches of a season (season = year of obs + 14 days)."""
    pid = L["player_id"].to_numpy()
    om = num(L["obs_mono"])
    yr = pd.to_datetime(np.nan_to_num(om, nan=0.0) + 14.0, unit="D").year.to_numpy()
    new = np.r_[True, (pid[1:] != pid[:-1]) | (yr[1:] != yr[:-1])]
    first_player = np.r_[True, pid[1:] != pid[:-1]]
    sid = np.cumsum(new) - 1
    rank = pd.Series(np.ones(len(pid))).groupby(sid).cumsum().to_numpy() - 1
    prev_om = np.r_[np.nan, om[:-1]]
    off_first = np.where(new & ~first_player, om - prev_om, np.nan)
    off = pd.Series(off_first).groupby(sid).transform("first").to_numpy(float)
    v = np.where((rank < 3) & np.isfinite(off) & (off > 0), np.maximum(0.0, np.log(56.0 / np.maximum(off, 1e-9))), 0.0)
    return pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "rb23_offseason": v})


RB10_COLS = ["rb10_drift", "rb10_drift_spw", "rb10_rs"]


def ios_profile(frame_all: pd.DataFrame) -> pd.DataFrame:
    """Per (match_id, player_id) of the frame: RS (eight statistics) and RS_spw from the surface-effective IOS (the
    store's source), z-scored by tour on 2013-24 frame rows (A and B pooled), oriented higher = better."""
    cols = [f"srf_{k}_eff_{s}_{side}" for k in ("O", "D") for s in STATS8 for side in "ab"]
    sf = pd.read_parquet(SURF_IOS, columns=["match_id"] + cols)
    sf["match_id"] = sf["match_id"].astype(str)
    f = frame_all[["match_id", "tour", "season", "player_a_id", "player_b_id"]].merge(sf, on="match_id", how="left")
    disc = f["season"].between(2013, 2024).to_numpy()
    zs = {}
    for k in ("O", "D"):
        for s in STATS8:
            za, zb = np.full(len(f), np.nan), np.full(len(f), np.nan)
            for tour in ("atp", "wta"):
                m = (f["tour"] == tour).to_numpy()
                both = np.r_[f.loc[m & disc, f"srf_{k}_eff_{s}_a"].to_numpy(float),
                             f.loc[m & disc, f"srf_{k}_eff_{s}_b"].to_numpy(float)]
                mu, sd = np.nanmean(both), np.nanstd(both)
                sign = -1.0 if s == "df" else 1.0
                za[m] = sign * (f.loc[m, f"srf_{k}_eff_{s}_a"].to_numpy(float) - mu) / sd
                zb[m] = sign * (f.loc[m, f"srf_{k}_eff_{s}_b"].to_numpy(float) - mu) / sd
            zs[(k, s)] = (za, zb)
    rows = []
    for side, pcol in ((0, "player_a_id"), (1, "player_b_id")):
        O = np.column_stack([zs[("O", s)][side] for s in STATS8])
        D = np.column_stack([zs[("D", s)][side] for s in STATS8])
        ob, db = O.mean(axis=1), D.mean(axis=1)
        o1, d1 = zs[("O", "spw")][side], zs[("D", "spw")][side]
        rows.append(pd.DataFrame({"match_id": f["match_id"].to_numpy(), "player_id": f[pcol].to_numpy(),
                                  "rs": db / (np.abs(ob) + np.abs(db) + RS_EPS),
                                  "rs_spw": d1 / (np.abs(o1) + np.abs(d1) + RS_EPS)}))
    return pd.concat(rows, ignore_index=True).drop_duplicates(["match_id", "player_id"])


def build_rb10(L: pd.DataFrame, prof: pd.DataFrame) -> pd.DataFrame:
    """RB10: (age - 29)+ x RS; age is Stage 0's pre-match age (L's `age`)."""
    d = L[["match_id", "player_id", "age"]].merge(prof, on=["match_id", "player_id"], how="inner")
    over = np.maximum(0.0, num(d["age"]) - 29.0)
    return pd.DataFrame({"match_id": d["match_id"].to_numpy(), "player_id": d["player_id"].to_numpy(),
                         "rb10_drift": over * num(d["rs"]), "rb10_drift_spw": over * num(d["rs_spw"]),
                         "rb10_rs": num(d["rs"])})


# --------------------------------------------------------------------------------------------------- doubles (RB01)

def tl_name_map() -> tuple[dict, dict]:
    """The lower-level team's TennisLive crosswalk: (tour|TennisLive id -> Stage 0 id, tour|normalised name -> Stage 0
    id; names claimed by two Stage 0 ids are dropped)."""
    xw = pd.read_csv(TL_XWALK)
    xw["tour"] = xw["src"].str.split("|").str[0]
    xw["key"] = xw["tour"] + "|" + xw["src_name"].map(norm_name)
    amb = xw.groupby("key")["s0"].transform("nunique") > 1
    return dict(zip(xw["src"], xw["s0"])), dict(zip(xw.loc[~amb, "key"], xw.loc[~amb, "s0"]))


def tl_event_map(id2s0: dict, s0m: pd.DataFrame) -> tuple[dict, dict]:
    """TennisLive event_key -> Stage 0 tournament id: the majority id of the event's singles rows linked to Stage 0
    matches by the two players' ids and a day within 4 of the clock's obs. Also returns linkage counts."""
    sg = pd.read_parquet(TL_LISTED, columns=["event_key", "tour", "discipline", "start_utc", "player1_id", "player2_id"])
    sg = sg[sg["discipline"] == "singles"].copy()
    sg["day"] = (pd.to_datetime(sg["start_utc"], errors="coerce").dt.normalize() - DAY0).dt.days
    sg["a"] = (sg["tour"] + "|" + sg["player1_id"].astype(str)).map(id2s0)
    sg["b"] = (sg["tour"] + "|" + sg["player2_id"].astype(str)).map(id2s0)
    sg = sg.dropna(subset=["a", "b", "day"])
    a, b = sg["a"].to_numpy(dtype=object), sg["b"].to_numpy(dtype=object)
    sg["p1"], sg["p2"] = np.where(a < b, a, b), np.where(a < b, b, a)
    m = s0m[s0m["tournament_date"] >= pd.Timestamp("2017-11-01")].copy()
    a, b = m["player_a_id"].to_numpy(dtype=object), m["player_b_id"].to_numpy(dtype=object)
    m["p1"], m["p2"] = np.where(a < b, a, b), np.where(a < b, b, a)
    j = sg[["event_key", "p1", "p2", "day"]].merge(m[["p1", "p2", "obs", "tournament_id"]], on=["p1", "p2"])
    j = j[(j["day"] - j["obs"]).abs() <= 4]
    em = j.groupby(["event_key", "tournament_id"]).size().rename("n").reset_index()
    em["tot"] = em.groupby("event_key")["n"].transform("sum")
    em = em.sort_values(["event_key", "n", "tournament_id"], ascending=[True, False, True]).drop_duplicates("event_key")
    stats = {"singles_rows_linked": int(len(j)), "events_mapped": int(len(em)),
             "majority_share_p05": float(em["n"].div(em["tot"]).quantile(0.05))}
    return dict(zip(em["event_key"], em["tournament_id"].astype(str))), stats


def tl_doubles(name2s0: dict, ev2tid: dict) -> tuple[pd.DataFrame, dict]:
    """One row per (doubles match played, member mapped to a Stage 0 id): pid, day (TennisLive's date = the local day),
    tid (the mapped Stage 0 tournament id, '' if unmapped), kind (TennisLive's event kind), tour."""
    tl = pd.read_parquet(TL_LISTED, columns=["event_key", "event_kind", "tour", "round", "draw", "discipline", "mixed",
                                             "junior", "played", "identity", "start_utc", "player1_members",
                                             "player2_members"])
    tl = tl[(tl["discipline"] == "doubles") & (tl["mixed"] != "TRUE") & (tl["junior"] != "TRUE")].copy()
    n_all = len(tl)
    tl = tl[tl["played"] == "TRUE"]
    tl["day"] = (pd.to_datetime(tl["start_utc"], errors="coerce").dt.normalize() - DAY0).dt.days
    tl = tl.dropna(subset=["day"]).drop_duplicates(["identity", "round", "draw", "day"])
    rows = []
    for side in ("player1_members", "player2_members"):
        parts = tl[side].fillna("").str.split(" / ", expand=True)
        for k in range(min(2, parts.shape[1])):
            rows.append(pd.DataFrame({"tour": tl["tour"].to_numpy(), "day": tl["day"].to_numpy(),
                                      "event_key": tl["event_key"].to_numpy(), "kind": tl["event_kind"].to_numpy(),
                                      "nm": parts[k].to_numpy()}))
    D = pd.concat(rows, ignore_index=True)
    D = D[D["nm"].notna() & (D["nm"] != "")]
    D["pid"] = (D["tour"] + "|" + D["nm"].map(norm_name)).map(name2s0)
    stats = {"doubles_rows": int(n_all), "played_rows_deduplicated": int(len(tl)), "member_rows": int(len(D)),
             "member_rows_mapped": float(D["pid"].notna().mean())}
    D = D.dropna(subset=["pid"]).copy()
    D["tid"] = D["event_key"].map(ev2tid).fillna("")
    D["day"] = D["day"].astype(np.int64)
    stats["member_rows_event_mapped"] = float((D["tid"] != "").mean())
    stats["member_rows_by_kind_year"] = D.assign(y=pd.to_datetime(D["day"], unit="D").dt.year).groupby(["kind", "y"]) \
        .size().unstack(0).fillna(0).astype(int).to_dict()
    return D[["pid", "day", "tid", "kind", "tour"]].reset_index(drop=True), stats


BIG = 100_000                     # day numbers are below 1e5


def window_counts(qkey: np.ndarray, qday: np.ndarray, dkey: np.ndarray, dday: np.ndarray, lo: int, hi: int) -> np.ndarray:
    """For each query (key, day d): the number of doubles rows with the same key and day in [d - lo, d - hi]."""
    order = np.lexsort((dday, dkey))
    comb = dkey[order].astype(np.int64) * BIG + dday[order].astype(np.int64)
    base = qkey.astype(np.int64) * BIG
    a = np.searchsorted(comb, base + (qday - lo).astype(np.int64), side="left")
    b = np.searchsorted(comb, base + (qday - hi).astype(np.int64), side="right")
    return (b - a).astype(float)


def doubles_values(Q: pd.DataFrame, D: pd.DataFrame, kinds) -> dict:
    """Counts for query rows Q (pid, obs, tid): 7-day total, here, else, and day d-1, from doubles rows D whose kind is
    in `kinds` (None = all)."""
    if kinds is not None:
        D = D[D["kind"].isin(kinds)]
    codes, uniq = pd.factorize(pd.concat([Q["pid"], D["pid"]], ignore_index=True))
    qp, dp = codes[:len(Q)], codes[len(Q):]
    pt = pd.factorize(pd.concat([Q["pid"] + "#" + Q["tid"], D["pid"] + "#" + D["tid"]], ignore_index=True))[0]
    qpt, dpt = pt[:len(Q)], pt[len(Q):]
    d = Q["obs"].to_numpy(float).astype(np.int64)
    dd = D["day"].to_numpy(np.int64)
    tot = window_counts(qp, d, dp, dd, 7, 1)
    here = window_counts(qpt, d, dpt, dd, 7, 1)
    d1 = window_counts(qp, d, dp, dd, 1, 1)
    return {"tot": tot, "here": here, "else": tot - here, "d1": d1}


def frame_queries(L: pd.DataFrame, frame_ids: set) -> pd.DataFrame:
    """The frame's player-rows of L with the fields the doubles builders read (schedule facts only)."""
    q = L[L["match_id"].isin(frame_ids)][["match_id", "player_id", "tour", "obs", "es", "lf", "tournament_id",
                                          "tournament_date", "surface"]].copy()
    q["pid"] = q["player_id"].astype(str)
    q["tid"] = q["tournament_id"].astype(str)
    return q.reset_index(drop=True)


RB01_COLS = ["rb01_d7", "rb01_d7_here", "rb01_d7_else", "rb01_d1", "rb01_d7_tour", "rb01_d7_nonitf", "rb01_d7_all",
             "rb01_n7_itf", "rb01_n7_any"]
ITF_RULE = 0.01   # fixed before any screen: the ITF shift is "material" if >= 1% of 2020-24 frame player-rows have an
                  # ITF doubles match in days d-7..d-1 (TennisLive holds ITF doubles only from 2020); then the primary
                  # counts tour-level doubles only (the brief), else every level (the scout's definition)


def build_rb01(Q: pd.DataFrame, D: pd.DataFrame, primary_kinds) -> pd.DataFrame:
    """RB01 from TennisLive: values for query rows from 2018 on (NaN before: no doubles days held)."""
    ok = (Q["tournament_date"] >= pd.Timestamp("2018-01-01")).to_numpy()
    out = {"match_id": Q["match_id"].to_numpy(), "player_id": Q["player_id"].to_numpy()}
    p = doubles_values(Q, D, primary_kinds)
    out["rb01_d7"], out["rb01_d7_here"] = np.log1p(p["tot"]), np.log1p(p["here"])
    out["rb01_d7_else"], out["rb01_d1"] = np.log1p(p["else"]), np.log1p(p["d1"])
    out["rb01_d7_tour"] = np.log1p(doubles_values(Q, D, TOUR_KINDS)["tot"])
    out["rb01_d7_nonitf"] = np.log1p(doubles_values(Q, D, NONITF_KINDS)["tot"])
    allk = doubles_values(Q, D, None)["tot"]
    out["rb01_d7_all"] = np.log1p(allk)
    out["rb01_n7_itf"] = doubles_values(Q, D, ("itf",))["tot"]
    out["rb01_n7_any"] = allk
    o = pd.DataFrame(out)
    for c in RB01_COLS:
        o.loc[~ok, c] = np.nan
    return o


def doubles_probe(Q: pd.DataFrame, D: pd.DataFrame, primary_kinds,
                  cuts=("2019-06-01", "2021-03-01", "2023-09-01")) -> dict:
    """(a) future leak: drop every doubles row on or after the cut day; no value at a query row that surely finished
    before the cut (lf + 1 <= cut) may move. (b) same day: add a doubles row on the match's own day, at its event, for
    each player's last frame row(s) only (a doubles match on an earlier frame row's day is legitimately inside the
    window of the player's next match); no value at those rows may move."""
    base = build_rb01(Q, D, primary_kinds).set_index(["match_id", "player_id"])[RB01_COLS]
    out = {}

    def diff(a: pd.DataFrame, b: pd.DataFrame, rows) -> int:
        x, y = a.loc[rows].to_numpy(float), b.loc[rows].to_numpy(float)
        same = (x == y) | (np.isnan(x) & np.isnan(y))
        return int((~same.all(axis=1)).sum())

    for cut in cuts:
        cday = (pd.Timestamp(cut) - DAY0).days
        new = build_rb01(Q, D[D["day"] < cday], primary_kinds).set_index(["match_id", "player_id"])[RB01_COLS]
        rows = pd.MultiIndex.from_frame(Q.loc[Q["lf"].to_numpy(float) + 1 <= cday, ["match_id", "player_id"]])
        out[cut] = {"future_rows_compared": int(len(rows)), "future_rows_changed": diff(base, new, rows)}
    last = Q[Q["obs"].to_numpy(float) == Q.groupby("pid")["obs"].transform("max").to_numpy(float)]
    syn = pd.DataFrame({"pid": last["pid"], "day": last["obs"].to_numpy(float).astype(np.int64), "tid": last["tid"],
                        "kind": "tour", "tour": last["tour"]})
    new = build_rb01(Q, pd.concat([D, syn], ignore_index=True), primary_kinds).set_index(["match_id", "player_id"])[RB01_COLS]
    rows = pd.MultiIndex.from_frame(last[["match_id", "player_id"]])
    out["same_day_added"] = {"rows_compared": int(len(rows)), "rows_changed": diff(base, new, rows)}
    # and the check bites: the same rows on the day before the match must move (the window's first day)
    syn["day"] = syn["day"] - 1
    new = build_rb01(Q, pd.concat([D, syn], ignore_index=True), primary_kinds).set_index(["match_id", "player_id"])[RB01_COLS]
    out["day_before_added_must_change"] = {"rows_compared": int(len(rows)), "rows_changed": diff(base, new, rows)}
    return out


def sackmann_doubles() -> pd.DataFrame:
    """Sackmann's ATP tour-level doubles 2010-20: one row per (match, player): pid, tid (Stage 0's form), td (event
    start), played (not a walkover)."""
    rows = []
    for y in range(2010, 2021):
        d = pd.read_parquet(SACK / f"atp_matches_doubles_{y}.parquet",
                            columns=["tourney_id", "tourney_date", "score", "winner1_id", "winner2_id", "loser1_id",
                                     "loser2_id"])
        tid = d["tourney_id"].astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True)
        td = pd.to_datetime(d["tourney_date"].astype(str).str.slice(0, 8), format="%Y%m%d", errors="coerce")
        wo = d["score"].astype(str).str.contains("W/O", case=False, na=False)
        for c in ("winner1_id", "winner2_id", "loser1_id", "loser2_id"):
            pid = "atp:" + d[c].astype(str).str.replace(r"\.0$", "", regex=True)
            rows.append(pd.DataFrame({"pid": pid.to_numpy(), "tid": tid.to_numpy(), "td": td.to_numpy(),
                                      "played": (~wo).to_numpy()}))
    S = pd.concat(rows, ignore_index=True)
    return S[S["pid"] != "atp:nan"].reset_index(drop=True)


RB01S_COLS = ["rb01s_entered", "rb01s_prev"]


def build_rb01s(Q: pd.DataFrame, S: pd.DataFrame, ev_end: pd.Series) -> pd.DataFrame:
    """The men's event-level version (flagged): values for men's query rows of 2013-17 only."""
    q = Q[(Q["tour"] == "atp") & (Q["tournament_date"] >= pd.Timestamp("2013-01-01")) &
          (Q["tournament_date"] < pd.Timestamp("2018-01-01"))].copy()
    ent = set(zip(S["tid"], S["pid"]))
    q["rb01s_entered"] = [float((t, p) in ent) for t, p in zip(q["tid"], q["pid"])]
    P = S[S["played"]].groupby(["pid", "tid"]).agg(n=("played", "size"), td=("td", "first")).reset_index()
    P["end"] = P["tid"].map(ev_end).to_numpy(float)
    j = q[["match_id", "player_id", "pid", "tid", "obs", "tournament_date"]].merge(P, on="pid", suffixes=("", "_ev"))
    keep = (j["tid_ev"] != j["tid"]) & (j["td"] < j["tournament_date"]) & \
        (j["td"] >= j["tournament_date"] - pd.Timedelta(days=14)) & \
        (j["end"] <= j["obs"] - 1) & (j["end"] >= j["obs"] - 8)
    cnt = j[keep].groupby(["match_id", "player_id"])["n"].sum()
    k = pd.MultiIndex.from_frame(q[["match_id", "player_id"]])
    q["rb01s_prev"] = np.log1p(cnt.reindex(k).fillna(0.0).to_numpy(float))
    return q[["match_id", "player_id"] + RB01S_COLS]


RB02_COLS = ["rb02_dblrust"]


def build_rb02(L: pd.DataFrame, Q: pd.DataFrame, D: pd.DataFrame, kinds, tid_surface: dict) -> pd.DataFrame:
    """RB02 for query rows from 2019 on: log1p(singles surface layoff) - log1p(layoff counting doubles), capped 365."""
    pid = L["player_id"].to_numpy()
    played = L["played"].to_numpy(bool)
    srf = L["surface"].astype(str).to_numpy()
    om = num(L["obs_mono"])
    last = np.full(len(L), np.nan)
    for s in pd.unique(srf):
        j = prev_index(pid, played & (srf == s))
        m = srf == s
        last[m] = take(om, j)[m]
    sl = pd.DataFrame({"match_id": L["match_id"].to_numpy(), "player_id": pid, "last_s": last})
    q = Q.merge(sl, on=["match_id", "player_id"], how="left")
    Dk = D if kinds is None else D[D["kind"].isin(kinds)]
    Dk = Dk.assign(srf=Dk["tid"].map(tid_surface).fillna(""))
    Dk = Dk[Dk["srf"] != ""]
    codes = pd.factorize(pd.concat([q["pid"] + "#" + q["surface"].astype(str), Dk["pid"] + "#" + Dk["srf"]],
                                   ignore_index=True))[0]
    qc, dc = codes[:len(q)], codes[len(q):]
    order = np.lexsort((Dk["day"].to_numpy(), dc))
    comb = dc[order].astype(np.int64) * BIG + Dk["day"].to_numpy(np.int64)[order]
    d = q["obs"].to_numpy(float).astype(np.int64)
    pos = np.searchsorted(comb, qc.astype(np.int64) * BIG + (d - 1), side="right") - 1
    hit = (pos >= 0) & (comb[np.maximum(pos, 0)] // BIG == qc)
    last_d = np.where(hit, comb[np.maximum(pos, 0)] % BIG, np.nan)
    S_ = np.clip(np.where(np.isfinite(q["last_s"]), d - q["last_s"].to_numpy(float), 365.0), 0.0, 365.0)
    any_last = np.fmax(q["last_s"].to_numpy(float), last_d)
    A_ = np.clip(np.where(np.isfinite(any_last), d - any_last, 365.0), 0.0, 365.0)
    v = np.log1p(S_) - np.log1p(A_)
    v = np.where((q["tournament_date"] >= pd.Timestamp("2019-01-01")).to_numpy(), v, np.nan)
    return pd.DataFrame({"match_id": q["match_id"].to_numpy(), "player_id": q["player_id"].to_numpy(),
                         "rb02_dblrust": v})


# ---------------------------------------------------------------------------------------- the time-source audit

def qs(x, q=(0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)) -> dict:
    x = pd.Series(np.asarray(x, float)).dropna()
    return {str(k): round(float(v), 2) for k, v in x.quantile(list(q)).items()} if len(x) else {}


def time_sources(L: pd.DataFrame, fo: pd.DataFrame) -> dict:
    """Outcome-free: which clock times are real, by tour and season (frame matches before the sealed set)."""
    out: dict = {}
    f = fo[fo["tournament_date"] < SEALED][["match_id", "tour", "season"]]
    M = L.drop_duplicates("match_id")[["match_id", "t_start", "start_src", "end_fs", "minutes"]]
    M = f.merge(M, on="match_id", how="left")
    M["src"] = M["start_src"].fillna("none")
    tab = M.groupby(["tour", "season"])["src"].value_counts(normalize=True).unstack(fill_value=0.0)
    out["frame_start_source_share"] = {f"{t}|{s}": {k: round(float(v), 4) for k, v in r.items()}
                                       for (t, s), r in tab.iterrows()}
    t0 = minutes_utc(M["t_start"])
    dfs = num(M["end_fs"]) - t0
    mins = num(M["minutes"])
    M["fs_end_ok"] = (dfs >= DUR_OK[0]) & (dfs <= DUR_OK[1])
    M["minutes_ok"] = (mins >= DUR_OK[0]) & (mins <= DUR_OK[1])
    M["end_known"] = M["fs_end_ok"] | (M["minutes_ok"] & np.isfinite(t0))
    M["actual_start"] = M["src"].isin(ACTUAL_SOURCES)
    g = M.groupby(["tour", "season"])[["actual_start", "fs_end_ok", "minutes_ok", "end_known"]].mean().round(4)
    out["frame_time_coverage"] = {f"{t}|{s}": r.to_dict() for (t, s), r in g.iterrows()}
    d = M[M["fs_end_ok"] & M["minutes_ok"] & (M["season"] <= 2024)].copy()     # values of match facts: <= 2024 only
    d["diff"] = (num(d["end_fs"]) - minutes_utc(d["t_start"])) - num(d["minutes"])
    out["fs_duration_minus_stage0_minutes"] = {
        f"{t}|{s}": {"n": int(len(h)), "median": round(float(h["diff"].median()), 2),
                     "abs_le_10": round(float((h["diff"].abs() <= 10).mean()), 4)}
        for (t, s), h in d.groupby(["tour", "season"])}
    # the start sources against one another (outcome-free)
    def link(name):
        x = pd.read_parquet(LINKS / f"{name}.parquet", columns=["match_id", "start_utc"])
        x["match_id"] = x["match_id"].astype(str)
        x["m"] = minutes_utc(x["start_utc"])
        return x.drop_duplicates("match_id").set_index("match_id")["m"]
    fs = link("flashscore")
    ids = f["match_id"]
    for other in ("slam_feeds", "wta_api", "sofascore", "api_tennis", "live_tennis_api"):
        o = link(other)
        dd = (fs.reindex(ids) - o.reindex(ids)).dropna()
        out[f"flashscore_minus_{other}_minutes"] = {"n": int(len(dd)), **qs(dd),
                                                     "abs_le_15": round(float((dd.abs() <= 15).mean()), 4)}
    bt = pd.read_parquet(H.BET_TIMING, columns=["match_id", "tour", "season", "t_listed"])
    bt = bt[bt["season"] <= 2024]
    bt["match_id"] = bt["match_id"].astype(str)
    dd = fs.reindex(bt["match_id"]).to_numpy(float) - bt["t_listed"].to_numpy(float) / 60.0
    for tour in ("atp", "wta"):
        x = dd[(bt["tour"] == tour).to_numpy()]
        x = x[np.isfinite(x)]
        out[f"flashscore_minus_oddstrader_listed_{tour}_2018_24"] = {
            "n": int(len(x)), **qs(x), "abs_le_15": round(float(np.mean(np.abs(x) <= 15)), 4),
            "abs_le_60": round(float(np.mean(np.abs(x) <= 60)), 4)}
    tl = pd.read_parquet(TL_LISTED, columns=["event_kind", "discipline", "start_utc"])
    tl = tl[(tl["discipline"] == "singles") & tl["event_kind"].isin(["tour", "slam"])]
    hh = pd.to_datetime(tl["start_utc"], errors="coerce").dt.strftime("%H:%M")
    out["tennislive_tour_singles_share_at_0900"] = round(float((hh == "09:00").mean()), 4)
    tm = pd.read_parquet(H.TIMING, columns=["start"])
    out["clock_start_with_fraction_share"] = float(np.mean(np.mod(tm["start"].to_numpy(float), 1.0) > 0))
    return out


# ------------------------------------------------------------------------------------------------ the pipeline

def lsub(L: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """The long table with the probe's own fields and the columns a builder reads (the probe scrambles only these)."""
    keep = ["match_id", "player_id", "k", "es", "lf"] + [c for c in cols if c not in ("match_id", "player_id", "k",
                                                                                      "es", "lf")]
    return L[keep]


BUILD_READS = {
    "rest": ["played", "t_start", "end_fs", "minutes", "obs_mono"],
    "rb06": ["played", "t_start", "end_fs", "minutes", "tournament_id", "obs", "tour"],
    "rb13": ["tournament_id", "played", "qualifying", "entry", "tpw_d", "games", "best_of", "tour", "t_start",
             "end_fs", "minutes"],
    "rb15": ["won", "status", "obs_mono", "rest_days", "level", "round", "qualifying"],
    "onsite": ["tournament_id", "played", "qualifying", "round_order", "tday", "opponent_id", "tour", "seed"],
    "rb20": ["tournament_id", "played", "tpw_d", "games", "best_of", "tour", "surface"],
    "rb23": ["obs_mono"],
    "rb10": ["age"],
    "rb02": ["played", "surface", "obs_mono"],
}


def run_builders(L: pd.DataFrame, fo: pd.DataFrame, probe: bool) -> tuple[pd.DataFrame, dict, dict]:
    """Every per-player builder; returns the frame's per-player values (one row per frame match and player), the probe
    results and build facts."""
    frame_ids = set(fo["match_id"])
    facts: dict = {}
    probes: dict = {}
    ppg = ppg_table(L)
    facts["points_per_game_2010_12"] = ppg
    prof = ios_profile(fo)
    log("doubles sources")
    s0m = pd.read_parquet(H.STAGE0_M, columns=["match_id", "tournament_id", "tournament_date", "player_a_id",
                                               "player_b_id", "surface"])
    s0m["match_id"] = s0m["match_id"].astype(str)
    s0m = s0m.merge(pd.read_parquet(H.TIMING, columns=["match_id", "obs"]).astype({"match_id": str}), on="match_id")
    id2s0, name2s0 = tl_name_map()
    ev2tid, facts["tennislive_event_map"] = tl_event_map(id2s0, s0m)
    D, facts["tennislive_doubles"] = tl_doubles(name2s0, ev2tid)
    Q = frame_queries(L, frame_ids)
    if Q["obs"].isna().any():
        raise RuntimeError("a frame player-row has no clock day")
    itf = build_rb01(Q, D, None)
    yrs = Q["tournament_date"].dt.year.to_numpy()
    w = (yrs >= 2020) & (yrs <= 2024)
    share_itf = float(np.mean(itf["rb01_n7_itf"].to_numpy()[w] >= 1))
    share_any = float(np.mean(itf["rb01_n7_any"].to_numpy()[w] >= 1))
    primary = TOUR_KINDS if share_itf >= ITF_RULE else None
    facts["rb01_itf_shift"] = {"rule": f"material if >= {ITF_RULE} of 2020-24 frame player-rows have ITF doubles in "
                                       "d-7..d-1", "share_itf_2020_24": share_itf, "share_any_2020_24": share_any,
                               "by_tour": {t: float(np.mean(itf["rb01_n7_itf"].to_numpy()[w & (Q["tour"] == t)
                                                                                         .to_numpy()] >= 1))
                                           for t in ("atp", "wta")},
                               "primary_kinds": "tour-level (tour, slam, finals)" if primary else "all levels"}
    log(f"RB01 primary: {facts['rb01_itf_shift']['primary_kinds']} (ITF share {share_itf:.4f})")
    tid_surface = s0m.drop_duplicates("tournament_id").set_index("tournament_id")["surface"].astype(str).to_dict()
    S = sackmann_doubles()
    md = L[~L["qualifying"].to_numpy(bool)]
    ev_end = md.groupby(md["tournament_id"].astype(str))["obs"].max()
    builders = {
        "rest": (build_rest, REST_COLS),
        "rb06": (build_rb06, RB06_COLS),
        "rb13": (lambda X: build_rb13(X, ppg), RB13_COLS),
        "rb15": (build_rb15, RB15_COLS),
        "onsite": (build_onsite, ONSITE_COLS),
        "rb20": (lambda X: build_rb20(X, ppg), RB20_COLS),
        "rb23": (build_rb23, RB23_COLS),
        "rb10": (lambda X: build_rb10(X, prof), RB10_COLS),
        "rb02": (lambda X: build_rb02(X, Q, D, primary, tid_surface), RB02_COLS),
    }
    V = Q[["match_id", "player_id"]].copy()
    for name, (fn, cols) in builders.items():
        log(f"build {name}")
        sub = lsub(L, BUILD_READS[name])
        out = fn(sub)
        out = out[out["match_id"].isin(frame_ids)].drop_duplicates(["match_id", "player_id"])
        V = V.merge(out, on=["match_id", "player_id"], how="left", validate="one_to_one")
        if probe:
            log(f"probe {name}")
            probes[name] = H.timing_probe(fn, sub, cols)
            log(f"   {probes[name]}")
    log("build rb01 (TennisLive) and rb01s (Sackmann)")
    V = V.merge(build_rb01(Q, D, primary), on=["match_id", "player_id"], how="left", validate="one_to_one")
    V = V.merge(build_rb01s(Q, S, ev_end), on=["match_id", "player_id"], how="left", validate="one_to_one")
    if probe:
        log("probe rb01 (doubles: drop rows after each cut; add same-day rows)")
        probes["rb01_doubles"] = doubles_probe(Q, D, primary)
        log(f"   {probes['rb01_doubles']}")
        # Sackmann's version: drop every doubles event that started on or after the cut
        base = build_rb01s(Q, S, ev_end).set_index(["match_id", "player_id"])[RB01S_COLS]
        res = {}
        for cut in ("2014-06-01", "2016-03-01"):
            cday = (pd.Timestamp(cut) - DAY0).days
            new = build_rb01s(Q, S[S["td"] < pd.Timestamp(cut)], ev_end).set_index(["match_id", "player_id"])[RB01S_COLS]
            qq = Q[(Q["lf"].to_numpy(float) + 1 <= cday)]
            rows = pd.MultiIndex.from_frame(qq[["match_id", "player_id"]]).intersection(base.index)
            x, y = base.loc[rows].to_numpy(float), new.loc[rows].to_numpy(float)
            same = (x == y) | (np.isnan(x) & np.isnan(y))
            res[cut] = {"future_rows_compared": int(len(rows)), "future_rows_changed": int((~same.all(axis=1)).sum()),
                        "note": "rb01s_entered reads this event's doubles draw (known at the draw), so the check "
                                "drops only events that started on or after the cut"}
        probes["rb01s_sackmann"] = res
        log(f"   {res}")
    facts["store_coverage_note"] = "the store lacks about half of 2018's frame matches; RB10 reads its source file"
    return V, probes, facts


# ------------------------------------------------------------------------------------- values, screens, readings

# (name, per-player column or None for a match-level construction, family, time-based: read the stale-line split)
SCREEN = [
    ("rb01_d7", "rb01_d7", "RB01", False), ("rb01_d7_here", "rb01_d7_here", "RB01", False),
    ("rb01_d7_else", "rb01_d7_else", "RB01", False), ("rb01_d1", "rb01_d1", "RB01", False),
    ("rb01_d7_tour", "rb01_d7_tour", "RB01", False), ("rb01_d7_nonitf", "rb01_d7_nonitf", "RB01", False),
    ("rb01_d7_all", "rb01_d7_all", "RB01", False),
    ("rb01s_entered", "rb01s_entered", "RB01s", False), ("rb01s_prev", "rb01s_prev", "RB01s", False),
    ("rb03_short", "rb03_short", "RB03", True), ("rb03_lt20", "rb03_lt20", "RB03", True),
    ("rb04_gap", None, "RB04", True), ("rb05_ratio", "rb05_ratio", "RB05", True),
    ("rb06_late", "rb06_late", "RB06", True),
    ("rb13_qcost", "rb13_qcost", "RB13", False), ("rb13_qrest", "rb13_qrest", "RB13", True),
    ("rb13_ll", "rb13_ll", "RB13", False), ("rb13_ll_on", "rb13_ll_on", "RB13", False),
    ("rb13_qtag", "rb13_qtag", "RB13", False), ("rb13_qcost_dev", "rb13_qcost_dev", "RB13", False),
    ("rb10_drift", "rb10_drift", "RB10", False), ("rb10_drift_spw", "rb10_drift_spw", "RB10", False),
    ("rb15_r28", "rb15_r28", "RB15", False), ("rb15_r90", "rb15_r90", "RB15", False),
    ("mp22_slam_r1", "mp22_slam_r1", "RB15", False),
    ("rb14_cold", "rb14_cold", "RB14", False), ("rb14_cold28", "rb14_cold28", "RB14", False),
    ("rb14_seed_r1_nobye", "rb14_seed_r1_nobye", "RB14", False),
    ("rb02_dblrust", "rb02_dblrust", "RB02", False), ("rb20_excess", "rb20_excess", "RB20", False),
    ("rb23_offseason", "rb23_offseason", "RB23", False),
    ("u138_on_mine", "u138_on_mine", "pool", False), ("u138_on_nobye", None, "pool", False),
    ("u132_log_mine", None, "pool", False), ("u138_pool", None, "pool", False), ("u132_pool", None, "pool", False),
]
AUX = [("rb03_short2", "rb03_short2"), ("rb13_qcost_box", "rb13_qcost_box"), ("rb10_rs", "rb10_rs"),
       ("rb01_n7_itf", "rb01_n7_itf")]


def assemble(V: pd.DataFrame, fo: pd.DataFrame) -> pd.DataFrame:
    """Values for every frame match: <name>_a, <name>_b, <name> (A - B unless stated). No result column."""
    vals = {"match_id": fo["match_id"].to_numpy()}
    for name, col in [(n, c) for n, c, _, _ in SCREEN if c is not None] + AUX:
        a, b = H.at_frame(V, col, fo)
        vals[f"{name}_a"], vals[f"{name}_b"], vals[name] = a, b, a - b
    ra, rb = H.at_frame(V, "rb04_rest", fo)
    gap = np.where((ra == np.inf) | (rb == np.inf), 0.0,
                   np.where(np.isfinite(ra) & np.isfinite(rb), np.clip(ra - rb, -36, 36) / 12.0, np.nan))
    vals["rb04_gap_a"], vals["rb04_gap_b"], vals["rb04_gap"] = ra, rb, gap
    da, db = H.at_frame(V, "u132_days", fo)
    vals["u132_log_mine_a"], vals["u132_log_mine_b"] = np.log1p(da), np.log1p(db)
    vals["u132_log_mine"] = vals["u132_log_mine_a"] - vals["u132_log_mine_b"]
    ca, cb = H.at_frame(V, "rb14_cold28", fo)
    bye = (np.nan_to_num(ca) != 0) | (np.nan_to_num(cb) != 0)
    for s in ("a", "b"):
        vals[f"u138_on_nobye_{s}"] = np.where(bye, 0.0, vals[f"u138_on_mine_{s}"])
    vals["u138_on_nobye"] = vals["u138_on_nobye_a"] - vals["u138_on_nobye_b"]
    st = pd.read_parquet(STORE, columns=["match_id"] + list(U138_STORE) + list(U132_STORE))
    st["match_id"] = st["match_id"].astype(str)
    st = st.drop_duplicates("match_id").set_index("match_id").reindex(fo["match_id"].astype(str))
    vals["u138_pool_a"], vals["u138_pool_b"] = np.log1p(num(st[U138_STORE[0]])), np.log1p(num(st[U138_STORE[1]]))
    vals["u138_pool"] = vals["u138_pool_a"] - vals["u138_pool_b"]
    vals["u132_pool_a"], vals["u132_pool_b"] = num(st[U132_STORE[0]]), num(st[U132_STORE[1]])
    vals["u132_pool"] = vals["u132_pool_a"] - vals["u132_pool_b"]
    out = pd.DataFrame(vals)
    for c in ("a_won", "y", "won", "winner"):
        if c in out.columns:
            raise RuntimeError("a result column would be written")
    return out


def screened_names(facts: dict) -> list[str]:
    """Every SCREEN name, less the level variant that equals the RB01 primary."""
    dup = "rb01_d7_tour" if facts["rb01_itf_shift"]["primary_kinds"].startswith("tour") else "rb01_d7_all"
    return [n for n, _, _, _ in SCREEN if n != dup]


def lenses_for(F: pd.DataFrame, x: np.ndarray) -> tuple:
    """The close lens always; the model lens (2020-24) and the move lens (2018-24) only where the statistic has at
    least 200 non-zero frame rows in their seasons (the men's Sackmann version holds 2013-17 only, and an all-zero
    column makes the move lens's least squares singular)."""
    s = F["season"].to_numpy()
    nz = np.isfinite(x) & (x != 0)
    out = ["close"]
    if nz[(s >= 2020) & (s <= 2024)].sum() >= 200:
        out.append("model")
    if nz[(s >= 2018) & (s <= 2024)].sum() >= 200:
        out.append("move")
    return tuple(out)


def run_screens(F: pd.DataFrame, X: pd.DataFrame, names: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    parts, coefs = [], {}
    for n in names:
        x = X[n].to_numpy(float)
        ls = lenses_for(F, x)
        parts.append(H.screen(F, x, n, "diff", lenses=ls))
        xo, coef = H.orthogonal_part(F, x)
        coefs[n] = coef
        parts.append(H.screen(F, xo, f"{n}__orth", "diff", lenses=ls))
        r = parts[-2]
        p = r[(r["lens"] == "close") & (r["era"] == "2013-24 pooled") & (r["tour"] == "both")]
        log(f"   screened {n}: present {float(np.mean(np.isfinite(x))):.3f}"
            + (f", pooled z {float(p['z'].iloc[0]):+.2f}" if len(p) else ""))
    long = pd.concat(parts, ignore_index=True)
    return long, H.summarize(long), coefs


def coverage(fo: pd.DataFrame, vals: pd.DataFrame, names: list[str]) -> dict:
    """Outcome-free: present and non-zero shares by tour and season, 2013 to 28 Jul 2026 (the sealed set not counted)."""
    keep = (fo["tournament_date"] < SEALED).to_numpy()
    f, v = fo[keep].reset_index(drop=True), vals[keep].reset_index(drop=True)
    out = {}
    for n in names:
        x = v[n].to_numpy(float)
        d = pd.DataFrame({"tour": f["tour"], "season": f["season"], "present": np.isfinite(x),
                          "nonzero": np.isfinite(x) & (x != 0)})
        g = d.groupby(["tour", "season"])[["present", "nonzero"]].mean().round(4)
        out[n] = {"harness": H.coverage_2025_26(f, x),
                  "nonzero_2013_24": {t: float(d.loc[(d["tour"] == t) & d["season"].between(2013, 2024), "nonzero"]
                                               .mean()) for t in ("atp", "wta")},
                  "nonzero_2025_26": {t: float(d.loc[(d["tour"] == t) & d["season"].between(2025, 2026), "nonzero"]
                                               .mean()) for t in ("atp", "wta")},
                  "by_tour_season": {f"{t}|{s}": r.to_dict() for (t, s), r in g.iterrows()}}
    return out


def correlations(F: pd.DataFrame, X: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    """Pairwise-complete Pearson correlations on 2013-24 frame rows (outcome-free), with sets_14d."""
    M = X[names].copy()
    M.insert(0, "sets_14d", F["in_sets_14d"].to_numpy(float))
    return M.corr(min_periods=500).round(4)


LOCAL_DAY_END = 1.33     # a local day ends at most 1.33 days after its UTC midnight (bet_timing.common)


def stale_line(F: pd.DataFrame, X: pd.DataFrame, V: pd.DataFrame, names: list[str]) -> tuple[pd.DataFrame, dict]:
    """BetOnline's last line (t_bol_close) against the information the time-based statistics read (each player's
    previous match's end), 2018-24; close-lens readings on the matches whose line postdates it."""
    bt = pd.read_parquet(H.BET_TIMING, columns=["match_id", "season", "t_bol_close", "p_bol_close", "ok_bol_close",
                                                "h_bol_close"])
    bt = bt[bt["season"] <= 2024].copy()
    bt["match_id"] = bt["match_id"].astype(str)
    G = F.merge(bt[["match_id", "t_bol_close", "p_bol_close", "ok_bol_close", "h_bol_close"]], on="match_id",
                how="left")
    ok = G["ok_bol_close"].fillna(False).astype(bool).to_numpy() & np.isfinite(G["t_bol_close"].to_numpy(float))
    G["Lbol"] = np.where(ok, H.lg(G["p_bol_close"].to_numpy(float)), np.nan)
    tc = G["t_bol_close"].to_numpy(float) / 60.0
    state = []
    for side, pcol in (("a", "player_a_id"), ("b", "player_b_id")):
        pe = V.set_index(["match_id", "player_id"])["prev_end"]
        pl = V.set_index(["match_id", "player_id"])["prev_lf"]
        k = pd.MultiIndex.from_arrays([G["match_id"], G[pcol]])
        e = pe.reindex(k).to_numpy(float)
        lfd = pl.reindex(k).to_numpy(float)
        after = np.where(np.isfinite(e), tc >= e, np.where((lfd + LOCAL_DAY_END) * 1440.0 <= tc, True, np.nan))
        before = np.isfinite(e) & (tc < e)
        state.append((after, before))
    after_both = (state[0][0] == 1) & (state[1][0] == 1) & ok
    predates = (state[0][1] | state[1][1]) & ok
    known = ok & (predates | after_both)
    by_season = {int(s): {"bol_close_rows": int(ok[m].sum()), "determinable": int(known[m].sum()),
                          "share_predates": float(predates[m].sum() / max(known[m].sum(), 1))}
                 for s in range(2018, 2025) for m in [(G["season"] == s).to_numpy()]}
    h = G["h_bol_close"].to_numpy(float)
    near, far = ok & (h <= 1.0), ok & (h > 1.0)     # the practitioners' split (MP-25): last line within 60 min
    facts = {"share_predates_2018_24": float(predates.sum() / max(known.sum(), 1)),
             "bol_close_rows_2018_24": int(ok.sum()), "determinable": int(known.sum()), "by_season": by_season,
             "share_last_line_over_60_min_before_listed_start_2018_24": float(far.sum() / max(ok.sum(), 1)),
             "note": "a later round's line cannot be posted before the matchup exists, so it almost never predates "
                     "the previous match's end; the 60-minute split asks the practitioners' broader question"}
    rows = []
    for n in names:
        x = X[n].to_numpy(float)
        for lab, m, base in (("bol_all", ok, "L"), ("fresh", after_both, "L"), ("fresh", after_both, "Lbol"),
                             ("stale", predates, "L"), ("near60", near, "L"), ("near60", near, "Lbol"),
                             ("far60", far, "L"), ("far60", far, "Lbol")):
            r = H.close_lens(G[m].reset_index(drop=True), x[m], f"{n}@{lab}", "diff", base=base)
            if len(r):
                rows.append(r[r["era"] == "2013-24 pooled"])
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), facts


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(jsonable(obj), indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probe", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    log("long table and clock times")
    L = load_long()
    fo = H.frame_outcome_free()
    log("time-source audit (outcome-free)")
    write_json(OUT / "time_sources.json", time_sources(L, fo))
    V, probes, facts = run_builders(L, fo, probe=not args.no_probe)
    if probes:
        write_json(OUT / "probes.json", probes)
    vals = assemble(V, fo)
    vals.to_parquet(OUT / "values.parquet", index=False)
    log(f"values.parquet: {len(vals)} frame matches, {vals.shape[1] - 1} columns")
    names = screened_names(facts)
    write_json(OUT / "coverage.json", coverage(fo, vals, names + [a for a, _ in AUX]))
    log("screens (seasons <= 2024 through the harness)")
    F = H.load_frame()
    X = F[["match_id"]].merge(vals, on="match_id", how="left", validate="one_to_one")
    long, summ, coefs = run_screens(F, X, names)
    long.to_csv(OUT / "long.csv", index=False)
    summ.to_csv(OUT / "summary.csv", index=False)
    correlations(F, X, names + ["rb03_short2", "rb13_qcost_box"]).to_csv(OUT / "correlations.csv")
    log("stale-line split")
    tb = [n for n, _, _, t in SCREEN if t] + ["rb01_d7", "rb01_d7_else", "rb01_d1"]
    st, st_facts = stale_line(F, X, V, tb)
    st.to_csv(OUT / "stale_line.csv", index=False)
    facts["stale_line"] = st_facts
    facts["orthogonal_coefficients"] = coefs
    facts["screened"] = names
    facts["run_seconds"] = round(time.time() - T0, 1)
    write_json(OUT / "build.json", facts)
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
