"""Stage C of the study "ideas borrowed from UFC-predictions", part 1: strength of schedule (SoS) and the
retrospective credit for old opponents, for every match of the shared pool (common.load_pool()).

Family 1, strength of schedule. For each earlier match of a player (every singles level from 2010, completed or
retired, under the Brief's time rule), the opponent's PRE-MATCH strength at that meeting:
    elo      Stage 1's surface Elo (retirements counted), the blend (1 - w) overall + w surface that Stage 1's
             probability uses, on the log-odds scale ln(10)/400 x rating
    rating   the Stage 3 serve rating + return rating of the opponent (pre-match)
    bt       Stage A's Bradley-Terry rating, if data/studies/ufc_ideas/stageA_bt.parquet exists when this runs
A player's SoS is the mean of those strengths over the last 52 weeks (or decayed with a 52-week half-life), shrunk with
K phantom opponents of the tour's mean strength over 2010-2018: (sum + K m) / (n + K). Also the strength of the
opponents beaten ("quality wins") and lost to, and results above Elo's expectation: sum (won - p_elo) / (n + K), over
all opponents and over strong ones only (opponent's blended Elo above the tour's 2010-2018 main-tour median). An
empty subset (no win in the window, say) takes the prior, the limit of the shrunk mean as its count goes to zero.
Every feature is A's value minus B's; it exists where both players have a played match in the window.

Family 2, retrospective credit ("beat players who turned out to be good"). For each of a player's matches of the last
52 weeks (the encounter e with opponent O): O's strength NOW minus O's strength THEN, on the log-odds scale.
    then     O's blended surface Elo before the meeting (Stage 1's pre-match values)
    now      O's latest pre-match Elo at a match of an EARLIER WEEK than the pool match, read on the meeting's
             surface: the overall part from O's latest such row, the surface part from O's latest such row on that
             surface, each only if that row comes after the meeting under Elo's own time rule (it "sees" the
             meeting); otherwise that part has no later evidence and contributes zero. "Earlier week" is read on
             tennis weeks (Monday to Sunday main-draw weeks; an event dated on a Sunday belongs to the following
             Monday's week), because Stage 0 dates 287 evaluation-level events on another weekday than Monday
    rematches   a later meeting of the same two players before the reading is taken out of "now": its own Elo update
             for O (k(n) x (result - expectation), Stage 1's formula and frozen constants) is subtracted
    later only  ("_later" rows) the meeting's own update for O is also subtracted, so that only O's LATER matches
             revise the credit. This is the UFC retrospective rule (strictly between the meeting and the consumer,
             rematches excluded): a later rating level mechanically contains the meeting itself, which would
             otherwise debit every win (O lost rating points to the player) and credit every loss.
Averaged over the window's encounters (all, beaten, lost to) and shrunk by (n + K) toward zero. The pairs (pool
player-match x earlier encounter, about 28 million) are enumerated by searches over sorted per-player arrays, in
chunks; no per-row look-back.

Constants: K from {0, 2, 5, 10, 20}, chosen per row and tour by the in-sample log-loss gain of [logit(p_elo), A - B]
over logit(p_elo) on the evaluation matches of 2013-2018 (stage4_rundown.newton), then frozen. The priors (tour mean
opponent strength) and the strong-opponent line use 2010-2018.

Checks: Stage 1's Elo update reproduced from its stored ratings (the debit/credit that "later only" removes); the
vectorised revaluation against a row-by-row reading on a sample of pool rows; a probe cut by date, event and round on
a 2025-2026 slice (as stage4_features.probe): everything the cut may not see is redrawn and the protected matches'
features must not move, with a deliberately leaky control that must.

Writes, in data/studies/ufc_ideas/:
    stageC_sos_part.parquet   match_id (the pool's order) and every family 1 and 2 feature column (A - B)
    stageC_sos_part.json      the constants (K per row and tour with its tuning grid; priors; the strong line), the
                              coverage, the self-checks, the probe and the timings; stageC_rundown.py folds it into
                              stageC_summary.json

Run: ./python.sh src/eda/ufc_ideas/stageC_sos.py   (about 5 minutes; 312 seconds on 2 Oct 2026; measured runtime in
stageC_sos_part.json, timings)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage3_traits as T  # noqa: E402
from src.eda.predictability_diagnostic import stage4_features as F  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

PART = U.OUT / "stageC_sos_part.parquet"
PART_JSON = U.OUT / "stageC_sos_part.json"
BT_FILE = U.OUT / "stageA_bt.parquet"
BASELINES = C.OUT / "stage1_baselines.parquet"

LN = float(np.log(10.0) / 400.0)          # Elo points -> log-odds
K_GRID = (0, 2, 5, 10, 20)                # phantom opponents (family 1); phantom encounters (family 2)
TUNE_YEARS = range(2013, 2019)
PRIOR_YEARS = range(2010, 2019)
WEEK52 = F.WEEK52                         # 364 days
HALF_LIFE = F.HALF_LIFE                   # 52 weeks
MAIN_TOUR = F.MAIN_TOUR
BIG = 100_000                             # day codes are below this
CHUNK = 60_000                            # pool player-rows per chunk of the pair enumeration
SEED = 20261002
T0 = time.time()

SOS_ROWS = {   # column -> (name, what)
    "sos_elo|52 weeks": "Opponents' surface Elo, last 52 weeks",
    "sos_elo|decayed": "Opponents' surface Elo, decayed (52-week half-life)",
    "sos_rating|52 weeks": "Opponents' serve + return ratings, last 52 weeks",
    "sos_bt|52 weeks": "Opponents' Bradley-Terry ratings, last 52 weeks",
    "sos_won_elo|52 weeks": "Quality of wins: surface Elo of opponents beaten, last 52 weeks",
    "sos_lost_elo|52 weeks": "Surface Elo of opponents lost to, last 52 weeks",
    "over_elo|52 weeks": "Results above Elo's expectation, last 52 weeks",
    "over_elo_strong|52 weeks": "Results above Elo's expectation against strong opponents, last 52 weeks",
}
REVALUE_ROWS = {
    "revalue|52 weeks": "Old opponents' Elo now minus then, all opponents, last 52 weeks",
    "revalue_won|52 weeks": "Old opponents' Elo now minus then, opponents beaten, last 52 weeks",
    "revalue_lost|52 weeks": "Old opponents' Elo now minus then, opponents lost to, last 52 weeks",
    "revalue_later|52 weeks": "Old opponents revalued by their later matches only, all opponents, last 52 weeks",
    "revalue_won_later|52 weeks": "Old opponents revalued by their later matches only, opponents beaten, last 52 weeks",
    "revalue_lost_later|52 weeks": "Old opponents revalued by their later matches only, opponents lost to, last 52 weeks",
}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Inputs

def elo_constants() -> dict:
    """Stage 1's frozen constants (retirements counted) per tour: k0, offset, shape and the surface weight w."""
    summ = json.loads(F.BASE_SUMMARY.read_text(encoding="utf-8"))
    return {c["tour"]: {k: float(c[k]) for k in ("k0", "offset", "shape", "w")} for c in summ["chosen"]
            if c["rule"] == "ret"}


def per_row(rows: pd.DataFrame, consts: dict, key: str) -> np.ndarray:
    t = rows["tour"].to_numpy()
    return np.where(t == "atp", consts["atp"][key], consts["wta"][key]).astype("float64")


def load_inputs() -> tuple[pd.DataFrame, dict]:
    """stage4_features.load_rows() (two rows per match, A then B, the table's order) plus each player's pre-match
    rated-match counts from Stage 1 (overall and on the surface), which Elo's update needs, and Stage A's BT rating
    where the file exists."""
    rows, typical = F.load_rows()
    assert (rows["side"].to_numpy()[0::2] == "A").all()
    mid = rows["match_id"].to_numpy()[0::2]
    bl = pd.read_parquet(BASELINES, columns=["match_id", "n_a_ret", "n_b_ret", "n_surf_a_ret", "n_surf_b_ret"]
                         ).set_index("match_id").reindex(mid)
    rows["elo_n_own"] = np.column_stack([bl["n_a_ret"].to_numpy(), bl["n_b_ret"].to_numpy()]).reshape(-1).astype("float64")
    rows["elo_nsurf_own"] = np.column_stack([bl["n_surf_a_ret"].to_numpy(), bl["n_surf_b_ret"].to_numpy()]).reshape(-1).astype("float64")
    info = {"bt_file": str(BT_FILE.relative_to(ROOT)), "bt_found": BT_FILE.exists()}
    if BT_FILE.exists():
        bt = pd.read_parquet(BT_FILE, columns=["match_id", "bt_a", "bt_b"]).drop_duplicates("match_id").set_index("match_id")
        bt = bt.reindex(mid)
        rows["bt_own"] = np.column_stack([bt["bt_a"].to_numpy(dtype="float64"), bt["bt_b"].to_numpy(dtype="float64")]).reshape(-1)
        info["bt_matches_with_values"] = int(np.isfinite(bt["bt_a"].to_numpy(dtype="float64")).sum())
    return rows, info


def blended(rows: pd.DataFrame, consts: dict) -> np.ndarray:
    """Each row's own pre-match surface-blended Elo rating (Elo points): (1 - w) overall + w surface, the overall alone
    where the surface rating is missing (Stage 1's blend)."""
    w = per_row(rows, consts, "w")
    ov = rows["elo_own"].to_numpy(dtype="float64")
    sv = rows["elo_surf_own"].to_numpy(dtype="float64")
    return (1 - w) * ov + w * np.where(np.isnan(sv), ov, sv)


def priors(rows: pd.DataFrame, consts: dict) -> dict:
    """The tour's mean opponent strength over the played player-matches of 2010-2018 (the phantom opponent of the
    shrinkage) for each strength, and the strong-opponent line: the median blended Elo of the players of main-tour
    matches (Grand Slam to 250 main draws) of 2010-2018."""
    s = strengths(rows, consts)
    played = rows["played"].to_numpy()
    yr = rows["year"].to_numpy()
    tour = rows["tour"].to_numpy()
    main = np.isin(rows["level"].to_numpy(), MAIN_TOUR) & ~rows["qualifying"].to_numpy(dtype=bool)
    own = blended(rows, consts)
    out = {}
    for t in C.TOURS:
        base = played & np.isin(yr, list(PRIOR_YEARS)) & (tour == t)
        out[t] = {"m_elo": float(s["elo"][base].mean()),
                  "m_rating": float(np.nanmean(s["rating"][base])),
                  "strong_line_elo_points": float(np.median(own[base & main])),
                  "player_matches": int(base.sum()), "main_tour_player_matches": int((base & main).sum())}
        if "bt" in s:
            v = s["bt"][base]
            out[t]["m_bt"] = float(np.nanmean(v)) if np.isfinite(v).any() else 0.0
    return out


def strengths(rows: pd.DataFrame, consts: dict) -> dict:
    """Per row, the OPPONENT's pre-match strength at that meeting: Elo (log-odds), Stage 3 rating sum, BT; and the
    opponent's blended Elo in points (for the strong-opponent line)."""
    own = blended(rows, consts)
    out = {"elo": LN * F.opp(own), "elo_points": F.opp(own),
           "rating": F.opp(rows["serve_own"].to_numpy(dtype="float64") + rows["return_own"].to_numpy(dtype="float64"))}
    if "bt_own" in rows:
        out["bt"] = F.opp(rows["bt_own"].to_numpy(dtype="float64"))
    return out


def p_own(rows: pd.DataFrame) -> np.ndarray:
    """Surface Elo's pre-match probability that the row's player wins (Stage 1's p_elo_surf_ret)."""
    p = rows["p_elo_a"].to_numpy(dtype="float64")
    return np.where(np.arange(len(rows)) % 2 == 0, p, 1 - p)


# ------------------------------------------------------------------------------------------------
# Family 1: strength of schedule

SUM_NAMES = ["n", "elo", "n_won", "elo_won", "n_lost", "elo_lost", "over", "n_strong", "over_strong", "n_rating",
             "rating", "n_bt", "bt"]


def sos_sums(rows: pd.DataFrame, ctx: dict) -> dict:
    """As-of sums per row (career, decayed, last 52 weeks) of the opponent strengths and results; one call of Stage 3's
    lookback_sums (career and decayed) and one of sums_before (the part older than 52 weeks)."""
    s = strengths(rows, ctx["elo"])
    played = rows["played"].to_numpy()
    won = rows["won"].to_numpy().astype(bool)
    tour = rows["tour"].to_numpy()
    line = np.where(tour == "atp", ctx["priors"]["atp"]["strong_line_elo_points"], ctx["priors"]["wta"]["strong_line_elo_points"])
    strong = s["elo_points"] > line
    over = won.astype("float64") - p_own(rows)
    rat_ok = played & np.isfinite(s["rating"])
    bt = s.get("bt", np.full(len(rows), np.nan))
    bt_ok = played & np.isfinite(bt)
    cols = {"n": played, "elo": np.where(played, s["elo"], 0.0),
            "n_won": played & won, "elo_won": np.where(played & won, s["elo"], 0.0),
            "n_lost": played & ~won, "elo_lost": np.where(played & ~won, s["elo"], 0.0),
            "over": np.where(played, over, 0.0), "n_strong": played & strong,
            "over_strong": np.where(played & strong, over, 0.0),
            "n_rating": rat_ok, "rating": np.where(rat_ok, s["rating"], 0.0),
            "n_bt": bt_ok, "bt": np.where(bt_ok, bt, 0.0)}
    V = np.column_stack([np.asarray(cols[k], dtype="float64") for k in SUM_NAMES])
    car, dec = T.lookback_sums(rows, V, (HALF_LIFE,))
    bef = T.sums_before(rows["pcode"].to_numpy(), rows["day"].to_numpy(), V, rows["pcode"].to_numpy(),
                        rows["day"].to_numpy() - WEEK52)
    ix = {k: i for i, k in enumerate(SUM_NAMES)}
    return {"car": car, "dec": dec[HALF_LIFE], "w52": car - bef, "ix": ix}


def sos_value(sums: dict, col: str, rows: pd.DataFrame, ctx: dict, K: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per row: a family 1 feature's value with K (per row) phantom opponents, and whether it exists."""
    cid, form = col.split("|")
    blk = sums["dec"] if form == "decayed" else sums["w52"]
    ix = sums["ix"]
    tour = rows["tour"].to_numpy()

    def prior(key):
        return np.where(tour == "atp", ctx["priors"]["atp"].get(key, 0.0), ctx["priors"]["wta"].get(key, 0.0))
    n_all = (sums["car"] if form == "decayed" else blk)[:, ix["n"]]
    exists = n_all > 0.5

    def shrunk(sk, nk, m):
        s, n = blk[:, ix[sk]], blk[:, ix[nk]]
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(n + K > 1e-9, (s + K * m) / np.maximum(n + K, 1e-12), m)
    if cid == "sos_elo":
        return shrunk("elo", "n", prior("m_elo")), exists
    if cid == "sos_won_elo":
        return shrunk("elo_won", "n_won", prior("m_elo")), exists
    if cid == "sos_lost_elo":
        return shrunk("elo_lost", "n_lost", prior("m_elo")), exists
    if cid == "sos_rating":
        n_r = (sums["car"] if form == "decayed" else blk)[:, ix["n_rating"]]
        return shrunk("rating", "n_rating", prior("m_rating")), n_r > 0.5
    if cid == "sos_bt":
        n_b = blk[:, ix["n_bt"]]
        return shrunk("bt", "n_bt", prior("m_bt")), n_b > 0.5
    if cid == "over_elo":
        return shrunk("over", "n", 0.0), exists
    if cid == "over_elo_strong":
        return shrunk("over_strong", "n_strong", 0.0), exists
    raise ValueError(col)


# ------------------------------------------------------------------------------------------------
# Family 2: the retrospective credit

def elo_deltas(rows: pd.DataFrame, consts: dict) -> tuple[np.ndarray, np.ndarray]:
    """Each row's own Elo update from that match in Elo points (Stage 1's pass, retirements counted): overall
    k(n) (result - expectation) with k(n) = k0 / (n + offset) ** shape and the pre-match overall ratings and count;
    the surface rating's likewise with the surface's count and ratings (zero where the surface is unknown). Zero for
    walkovers and other statuses, which do not move ratings."""
    k0, off, sh = (per_row(rows, consts, k) for k in ("k0", "offset", "shape"))
    played = rows["played"].to_numpy()
    won = rows["won"].to_numpy().astype("float64")
    ov = rows["elo_own"].to_numpy(dtype="float64")
    sv = rows["elo_surf_own"].to_numpy(dtype="float64")
    n_o = rows["elo_n_own"].to_numpy(dtype="float64")
    n_s = rows["elo_nsurf_own"].to_numpy(dtype="float64")
    e_all = 1.0 / (1.0 + 10.0 ** ((F.opp(ov) - ov) / 400.0))
    d_all = np.where(played, k0 / (n_o + off) ** sh * (won - e_all), 0.0)
    ok_s = played & np.isfinite(sv) & np.isfinite(F.opp(sv)) & (rows["surf"].to_numpy() > 0) & np.isfinite(n_s)
    with np.errstate(invalid="ignore"):
        e_s = 1.0 / (1.0 + 10.0 ** ((F.opp(sv) - sv) / 400.0))
        d_s = np.where(ok_s, k0 / (np.where(ok_s, n_s, 0.0) + off) ** sh * (won - e_s), 0.0)
    return d_all, d_s


def sorted_view(rows: pd.DataFrame, key: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rows sorted by (key, day, event, round, table order), the order prev_visible uses; and the search keys
    key * BIG + day."""
    o = np.lexsort((rows["order"].to_numpy(), rows["round_order"].to_numpy(), rows["ev"].to_numpy(),
                    rows["day"].to_numpy(), key))
    return o, key[o].astype("int64") * BIG + rows["day"].to_numpy()[o].astype("int64")


def week_monday(day) -> np.ndarray:
    """The Monday of a day's calendar week (days since 1970-01-01, a Thursday)."""
    d = np.asarray(day, dtype="int64")
    return d - (d + 3) % 7


def now_cut(day) -> np.ndarray:
    """The first day the credit's "now" reading may NOT use for a pool match dated ``day``: rows dated before it are
    of an earlier tennis week. Stage 0 dates 287 evaluation-level events on a weekday other than Monday, so "an
    earlier date" is not always "an earlier week": a tennis week is a main-draw week, Monday to Sunday, and an event
    dated on a Sunday (a draw that starts on the Sunday) belongs to the following Monday's week. The cut is the Sunday
    before the pool match's tennis week: rows dated up to the Saturday before are read."""
    d = np.asarray(day, dtype="int64")
    return week_monday(d + 1) - 1


def sees(day_j, ev_j, rnd_j, day_m, ev_m, rnd_m) -> np.ndarray:
    """Whether a rating read before row j includes the update of match m under Stage 1's rule: m is of an earlier
    week, or an earlier round of the same event."""
    return (day_j > day_m) | ((day_j == day_m) & (ev_j == ev_m) & (rnd_j > rnd_m))


def group_rest(gkey: np.ndarray, inc: np.ndarray) -> np.ndarray:
    """For pairs in chronological order within each group (gkey contiguous after a stable sort): the sum of ``inc``
    over the LATER pairs of the same group."""
    o = np.argsort(gkey, kind="stable")
    g, v = gkey[o], inc[o]
    cs = np.cumsum(v)
    last = np.r_[g[1:] != g[:-1], True]
    end_pos = np.flatnonzero(last)
    grp_end = np.repeat(cs[end_pos], np.diff(np.r_[-1, end_pos]))
    out = np.empty_like(inc)
    out[o] = grp_end - cs
    return out


def revalue_pairs(rows: pd.DataFrame, consts: dict, R_idx: np.ndarray, deltas=None, keep_pairs: bool = False) -> dict:
    """The retrospective credit for the player-rows R_idx (global row indices): per row the number of encounters in
    the window (all, won), the sums of the revaluation (as specified, and from later matches only), and diagnostics.
    With keep_pairs, the pair-level arrays are returned as well (the self-check reads them).

    LEAKS across overlapping events (the match-timing audit, 5 Oct 2026; docs/decisions/2026-10-05-match-timing.md):
    an opponent's "now" is their latest row of an earlier tournament week, which can be a Grand Slam quarter-final
    played days after the match being revalued. Rebuild on the leak-proof timeline before any further use."""
    n = len(rows)
    pcode = rows["pcode"].to_numpy().astype("int64")
    day = rows["day"].to_numpy().astype("int64")
    ev = rows["ev"].to_numpy().astype("int64")
    rnd = rows["round_order"].to_numpy().astype("int64")
    surf = rows["surf"].to_numpy().astype("int64")
    played = rows["played"].to_numpy()
    won = rows["won"].to_numpy().astype(bool)
    ov = rows["elo_own"].to_numpy(dtype="float64")
    sv = rows["elo_surf_own"].to_numpy(dtype="float64")
    w_row = per_row(rows, consts, "w")
    d_all, d_s = deltas if deltas is not None else elo_deltas(rows, consts)
    evm = int(ev.max()) + 1
    assert (int(pcode.max()) + 1) * BIG * evm * 32 < 2 ** 62, "composite key overflow"
    o_all, key_all = sorted_view(rows, pcode)
    ks = pcode * 8 + surf
    o_s, key_s = sorted_view(rows, ks)
    o_p = o_all[played[o_all]]
    key1 = pcode[o_p] * BIG + day[o_p]
    key2 = ((pcode[o_p] * BIG + day[o_p]) * evm + ev[o_p]) * 32 + rnd[o_p]
    R_idx = np.asarray(R_idx, dtype="int64")
    out = {k: np.zeros(len(R_idx)) for k in ("n", "n_won", "spec", "spec_won", "later", "later_won",
                                             "with_evidence", "rematch_pairs", "date_rule_same_week")}
    kept = []
    for lo in range(0, len(R_idx), CHUNK):
        r = R_idx[lo:lo + CHUNK]
        pr, dr = pcode[r], day[r]
        lo1 = np.searchsorted(key1, pr * BIG + dr - WEEK52, "left")
        hi1 = np.searchsorted(key1, pr * BIG + dr, "left")
        b2 = ((pr * BIG + dr) * evm + ev[r]) * 32
        lo2 = np.searchsorted(key2, b2, "left")
        hi2 = np.searchsorted(key2, b2 + rnd[r], "left")
        c1, c2 = hi1 - lo1, hi2 - lo2
        cnt = c1 + c2
        tot = int(cnt.sum())
        if tot == 0:
            continue
        rep = np.repeat(np.arange(len(r)), cnt)
        k = np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        pos = np.where(k < c1[rep], lo1[rep] + k, lo2[rep] + (k - c1[rep]))
        e = o_p[pos]                                     # the player's encounter row
        m = e ^ 1                                        # the opponent's row of the same match
        O = pcode[m]
        Tday = now_cut(dr[rep])                          # "now" is read before the pool match's tennis week
        # diagnostic: readings an earlier-date rule would take from a row of the pool match's own tennis week
        pd_ = np.searchsorted(key_all, O * BIG + dr[rep], "left") - 1
        okd = (pd_ >= 0) & (pcode[o_all[np.maximum(pd_, 0)]] == O)
        jd = o_all[np.maximum(pd_, 0)]
        same_week = okd & (day[jd] >= Tday) & sees(day[jd], ev[jd], rnd[jd], day[m], ev[m], rnd[m])
        # "now", overall: the opponent's latest row of an earlier week than the pool match
        pj = np.searchsorted(key_all, O * BIG + Tday, "left") - 1
        okj = (pj >= 0) & (pcode[o_all[np.maximum(pj, 0)]] == O)
        j = o_all[np.maximum(pj, 0)]
        see_all = okj & sees(day[j], ev[j], rnd[j], day[m], ev[m], rnd[m])
        diff_all = np.where(see_all, ov[j] - ov[m], 0.0)
        # "now", surface: the opponent's latest row on the meeting's surface of an earlier week
        s_e = surf[e]
        known = s_e > 0
        ps = np.searchsorted(key_s, (O * 8 + s_e) * BIG + Tday, "left") - 1
        oks = known & (ps >= 0) & (ks[o_s[np.maximum(ps, 0)]] == O * 8 + s_e)
        js = o_s[np.maximum(ps, 0)]
        see_s = oks & sees(day[js], ev[js], rnd[js], day[m], ev[m], rnd[m])
        diff_s = np.where(see_s, sv[js] - sv[m], 0.0)
        diff_s = np.where(np.isfinite(diff_s), diff_s, 0.0)
        inc_all = np.where(see_all, d_all[m], 0.0)      # the meeting's own update for O, inside "now"
        inc_s = np.where(see_s, d_s[m], 0.0)
        # later rematches of the same two players inside "now": their updates for O are taken out
        g1 = rep.astype("int64") * (int(pcode.max()) + 1) + O
        rem_all = group_rest(g1, inc_all)
        rem_s = group_rest(g1 * 8 + s_e, inc_s)
        ws = np.where(known, w_row[e], 0.0)
        spec = LN * ((1 - ws) * (diff_all - rem_all) + ws * (diff_s - rem_s))
        later = spec - LN * ((1 - ws) * inc_all + ws * inc_s)
        wn = won[e].astype("float64")
        L = len(r)
        sl = slice(lo, lo + L)
        out["n"][sl] = np.bincount(rep, minlength=L)
        out["n_won"][sl] = np.bincount(rep, weights=wn, minlength=L)
        out["spec"][sl] = np.bincount(rep, weights=spec, minlength=L)
        out["spec_won"][sl] = np.bincount(rep, weights=spec * wn, minlength=L)
        out["later"][sl] = np.bincount(rep, weights=later, minlength=L)
        out["later_won"][sl] = np.bincount(rep, weights=later * wn, minlength=L)
        out["with_evidence"][sl] = np.bincount(rep, weights=(see_all | see_s).astype("float64"), minlength=L)
        out["rematch_pairs"][sl] = np.bincount(rep, weights=((rem_all != 0) | (rem_s != 0)).astype("float64"), minlength=L)
        out["date_rule_same_week"][sl] = np.bincount(rep, weights=same_week.astype("float64"), minlength=L)
        if keep_pairs:
            kept.append(pd.DataFrame({"r": r[rep], "e": e, "m": m, "spec": spec, "later": later}))
    if keep_pairs:
        out["pairs"] = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=["r", "e", "m", "spec", "later"])
    return out


def revalue_value(sums: dict, cid: str, K: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per player-row of the enumeration: a family 2 feature's value (shrunk by n + K toward zero) and existence."""
    kind = "later" if cid.endswith("_later") else "spec"
    sub = cid.replace("_later", "")
    n, nw = sums["n"], sums["n_won"]
    tot, tw = sums[kind], sums[f"{kind}_won"]
    if sub == "revalue":
        s, c = tot, n
    elif sub == "revalue_won":
        s, c = tw, nw
    else:
        s, c = tot - tw, n - nw
    with np.errstate(invalid="ignore", divide="ignore"):
        v = np.where(c + K > 1e-9, s / np.maximum(c + K, 1e-12), 0.0)
    return v, n > 0.5


# ------------------------------------------------------------------------------------------------
# Building every feature for the pool (also used by the probe on a perturbed slice)

def pool_rows(rows: pd.DataFrame, pool: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The pool mask (per match; stage4_features.pool_mask unless given, as the probe gives the unperturbed one) and
    the A and B rows of the pool matches."""
    pool = F.pool_mask(rows) if pool is None else pool
    A = np.flatnonzero(pool) * 2
    return pool, A, A + 1


def k_rows(rows: pd.DataFrame, K: dict, col: str) -> np.ndarray:
    return np.where(rows["tour"].to_numpy() == "atp", K[col]["atp"], K[col]["wta"]).astype("float64")


def build(rows: pd.DataFrame, ctx: dict, K: dict, cols: list[str] | None = None, pool: np.ndarray | None = None) -> dict:
    """Every family 1 and 2 column (A - B, missing where either player lacks it) for the pool matches of ``rows``,
    with the frozen constants in ``ctx`` and K per column and tour."""
    pool, A, Bi = pool_rows(rows, pool)
    cols = cols or [c for c in list(SOS_ROWS) + list(REVALUE_ROWS) if c in K]
    out = {}
    sums = sos_sums(rows, ctx)
    for col in [c for c in cols if c in SOS_ROWS]:
        v, e = sos_value(sums, col, rows, ctx, k_rows(rows, K, col))
        out[col] = np.where(e[A] & e[Bi], v[A] - v[Bi], np.nan)
    rv_cols = [c for c in cols if c in REVALUE_ROWS]
    if rv_cols:
        Ridx = np.column_stack([A, Bi]).reshape(-1)
        rs = revalue_pairs(rows, ctx["elo"], Ridx)
        kr = {c: k_rows(rows, K, c)[Ridx] for c in rv_cols}
        for col in rv_cols:
            v, e = revalue_value(rs, col.split("|")[0], kr[col])
            va, vb, ea, eb = v[0::2], v[1::2], e[0::2], e[1::2]
            out[col] = np.where(ea & eb, va - vb, np.nan)
    return out


# ------------------------------------------------------------------------------------------------
# Tuning K (2013-2018, in-sample, given Elo)

def gain_given_elo(f: np.ndarray, p_elo: np.ndarray, y: np.ndarray) -> float:
    """In-sample milli-log-loss gain of [logit(p_elo), f] over logit(p_elo) (logistic regression without an
    intercept, stage4_rundown.newton)."""
    sd = f.std()
    if not np.isfinite(sd) or sd == 0:
        return 0.0
    base = logit(np.clip(p_elo, 1e-9, 1 - 1e-9))
    Z = np.column_stack([base, f / sd])[None]
    b = R.newton(Z, y, np.zeros((1, 2)))[0]
    llm = R.ll(expit(Z[0] @ b), y).mean()
    bb = R.newton(base[None, :, None], y, np.zeros((1, 1)))[0, 0]
    llb = R.ll(expit(base * bb), y).mean()
    return float(1000 * (llb - llm))


def tune(pool_frame: pd.DataFrame, value_fn, cols: list[str]) -> tuple[dict, list]:
    """For each column and tour, the K of the grid with the largest in-sample gain given Elo on the evaluation matches
    of 2013-2018 where the column exists. ``value_fn(col, K)`` returns the column over the pool with K for both
    tours."""
    tour = pool_frame["tour"].to_numpy()
    yr = pool_frame["year"].to_numpy()
    ev = pool_frame["evaluation"].to_numpy(dtype=bool)
    p = pool_frame["p_elo"].to_numpy(dtype="float64")
    y = pool_frame["a_won"].to_numpy(dtype=bool)
    chosen, grid = {}, []
    for col in cols:
        vals = {Kv: value_fn(col, Kv) for Kv in K_GRID}
        chosen[col] = {}
        for t in C.TOURS:
            base = ev & (tour == t) & np.isin(yr, list(TUNE_YEARS)) & np.isfinite(p)
            res = {}
            for Kv, f in vals.items():
                m = base & np.isfinite(f)
                res[Kv] = gain_given_elo(f[m], p[m], y[m])
                grid.append({"column": col, "tour": t, "K": Kv, "matches": int(m.sum()), "gain_milli": res[Kv]})
            chosen[col][t] = float(max(res, key=lambda k: res[k]))
        log(f"  tuned {col}: K = {chosen[col]['atp']:g} (men), {chosen[col]['wta']:g} (women)")
    return chosen, grid


# ------------------------------------------------------------------------------------------------
# Checks

def delta_check(rows: pd.DataFrame, consts: dict, d_all: np.ndarray) -> dict:
    """Stage 1's update reproduced: where a player's next row in their history is of a later week and nothing else of
    theirs lies between (no other row in the meeting's week), the stored pre-match overall rating there minus the one
    before the meeting equals the computed update."""
    pcode = rows["pcode"].to_numpy()
    day = rows["day"].to_numpy()
    o, _ = sorted_view(rows, pcode.astype("int64"))
    nxt = np.r_[o[1:], -1]
    same = np.r_[pcode[o[1:]] == pcode[o[:-1]], False]
    later = same & (day[np.maximum(nxt, 0)] > day[o])
    # nothing else of the player's in the meeting's week: the previous row in the sort is of an earlier week too
    alone = np.r_[True, (pcode[o[1:]] != pcode[o[:-1]]) | (day[o[1:]] > day[o[:-1]])]
    rated = rows["played"].to_numpy()[o]
    sel = later & alone & rated
    i, j = o[sel], nxt[sel]
    ov = rows["elo_own"].to_numpy(dtype="float64")
    err = np.abs((ov[j] - ov[i]) - d_all[i])
    return {"checked": int(sel.sum()), "within_0.01_points": float((err < 0.01).mean()),
            "within_0.1_points": float((err < 0.1).mean()), "max_abs_error_points": float(err.max()),
            "median_abs_update_points": float(np.median(np.abs(d_all[i])))}


def player_index(rows: pd.DataFrame) -> dict:
    """Each player's row indices (for the row-by-row readings)."""
    s = pd.Series(np.arange(len(rows))).groupby(rows["pcode"].to_numpy())
    return {int(k): v.to_numpy() for k, v in s}


def brute_revalue(rows: pd.DataFrame, consts: dict, r: int, d_all: np.ndarray, d_s: np.ndarray,
                  by_player: dict | None = None) -> tuple[int, float, float]:
    """A row-by-row reading of the retrospective credit for one player-row r: (encounters, sum as specified, sum from
    later matches only)."""
    pc, day, ev, rnd, order = (rows[c].to_numpy() for c in ("pcode", "day", "ev", "round_order", "order"))
    surf, played = rows["surf"].to_numpy(), rows["played"].to_numpy()
    ov, sv = rows["elo_own"].to_numpy(dtype="float64"), rows["elo_surf_own"].to_numpy(dtype="float64")
    w = per_row(rows, consts, "w")
    by_player = by_player or player_index(rows)
    T_, E_, R_ = day[r], ev[r], rnd[r]
    own = by_player[int(pc[r])]
    mine = own[played[own] & (((day[own] >= T_ - WEEK52) & (day[own] < T_)) | ((day[own] == T_) & (ev[own] == E_) & (rnd[own] < R_)))]
    n, s_spec, s_later = 0, 0.0, 0.0
    for e in mine:
        m = e ^ 1
        O = pc[m]
        n += 1
        theirs = by_player[int(O)]

        def latest(idx):
            if not len(idx):
                return None
            # the latest in the history's sort (day, event, round, table order)
            keys = list(zip(day[idx], ev[idx], rnd[idx], order[idx]))
            return idx[max(range(len(idx)), key=lambda q: keys[q])]

        def seen(j, x):
            return j is not None and (day[j] > day[x] or (day[j] == day[x] and ev[j] == ev[x] and rnd[j] > rnd[x]))
        t1 = T_ + 1                                     # rows of an earlier tennis week only (a Sunday counts with
        cut = t1 - (t1 + 3) % 7 - 1                     # the following Monday): dated before the Sunday before it
        j = latest(theirs[day[theirs] < cut])
        js = latest(theirs[(day[theirs] < cut) & (surf[theirs] == surf[e])]) if surf[e] > 0 else None
        ws = w[e] if surf[e] > 0 else 0.0
        part_all = (ov[j] - ov[m]) if seen(j, m) else 0.0
        part_s = (sv[js] - sv[m]) if (surf[e] > 0 and seen(js, m)) else 0.0
        # later rematches whose update for O is inside the reading
        rem_all = rem_s = 0.0
        for u in mine:
            if u == e or not ((day[u], ev[u], rnd[u], order[u]) > (day[e], ev[e], rnd[e], order[e])):
                continue
            if pc[u ^ 1] != O:
                continue
            if seen(j, u ^ 1):
                rem_all += d_all[u ^ 1]
            if surf[e] > 0 and surf[u] == surf[e] and seen(js, u ^ 1):
                rem_s += d_s[u ^ 1]
        spec = LN * ((1 - ws) * (part_all - rem_all) + ws * (part_s - rem_s))
        own_all = d_all[m] if seen(j, m) else 0.0
        own_s = d_s[m] if (surf[e] > 0 and seen(js, m)) else 0.0
        s_spec += spec
        s_later += spec - LN * ((1 - ws) * own_all + ws * own_s)
    return n, s_spec, s_later


# ------------------------------------------------------------------------------------------------
# The probe cut by date, event and round

OUTCOMES = ["won", "minutes"] + [f"{r}_{x}" for r in C.RATES for x in ("n", "d")]
PRE_MATCH = ["elo_own", "elo_surf_own", "elo_n_own", "elo_nsurf_own", "p_elo_a", "serve_own", "return_own",
             "serve_opp", "return_opp", "rank", "age"]
PROBE_ATOL = 1e-9


def perturb(rows: pd.DataFrame, c: int, rng: np.random.Generator, outcomes=OUTCOMES, pre_match=PRE_MATCH) -> tuple[pd.DataFrame, np.ndarray]:
    """The history as the cut match c (a match index) may NOT see it redrawn: what was played in its own round and later
    rounds of its event, the week's other events and later weeks (results, statuses, box scores, minutes); the
    pre-match values of every match outside the protected set. Returns the redrawn rows and, per match, whether it is
    protected (earlier weeks; the cut event's rounds up to and including the cut's)."""
    week, ev, rnd = rows["day"].to_numpy()[0::2], rows["ev"].to_numpy()[0::2], rows["round_order"].to_numpy()[0::2]
    later = (week > week[c]) | ((week == week[c]) & ((ev != ev[c]) | (rnd >= rnd[c])))
    keep = (week < week[c]) | ((week == week[c]) & (ev == ev[c]) & (rnd <= rnd[c]))
    pert = rows.copy()
    lr, after = np.repeat(later, 2), np.repeat(later & ~keep, 2)
    for cols, sel in ((outcomes, lr), (pre_match, after)):
        for col in cols:
            if col not in pert:
                continue
            v = pert[col].to_numpy().copy()
            if col == "won":
                flip = np.repeat(rng.random(len(later)) < 0.5, 2) & sel
                v = np.where(flip, ~v.astype(bool), v.astype(bool))
            elif v.dtype.kind in "fi":
                v = v.astype("float64")
                top = np.nanmax(np.abs(v[np.isfinite(v)])) if np.isfinite(v).any() else 1.0
                v[sel] = np.floor(rng.random(int(sel.sum())) * (top + 1))
            pert[col] = v
    st = pert["status"].to_numpy().copy()
    redraw = np.repeat(later & (rng.random(len(later)) < 0.1), 2)
    st[redraw] = np.where(np.repeat(rng.random(len(later)) < 0.5, 2)[redraw], "retired", "completed")
    pert["status"] = st
    return F.prepare(pert), keep


def leaky_control(rows: pd.DataFrame, pool: np.ndarray | None = None) -> np.ndarray:
    """A positive control: career wins counted with the match itself (the commonest leak), A minus B."""
    tmp = rows[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    tmp["w"] = rows["won"].to_numpy().astype("float64")
    s = C.asof_sums(tmp, ["w"])["w"].to_numpy() + tmp["w"].to_numpy()
    _, A, Bi = pool_rows(rows, pool)
    return s[A] - s[Bi]


def probe(rows: pd.DataFrame, build_fn, n_cuts: int = 4, seed: int = SEED, outcomes=OUTCOMES,
          pre_match=PRE_MATCH, aux=None, perturb_aux=None, cuts=None) -> dict:
    """Black-box check of the time rule on a slice (stage4_features.probe's design): at each cut match (by default
    random pool matches of the slice's last season; or the match indices ``cuts``), redraw what the cut may not see and
    rebuild every column with ``build_fn(rows, aux, pool)``; the features of the protected matches must not move.
    The pool is the unperturbed one (a later walkover redrawn as played does not join it), as in Stage 4's probe.
    ``perturb_aux(aux, rows, c, rng)`` redraws an auxiliary table (the point-by-point records) for the cut."""
    rng = np.random.default_rng(seed)
    pool, _, _ = pool_rows(rows)
    control = "leak_control|inclusive_wins"
    base = build_fn(rows, aux, pool)
    base[control] = leaky_control(rows, pool)
    names = sorted(base)
    real = np.array([k != control for k in names])
    yr = rows["year"].to_numpy()[0::2]
    if cuts is None:
        cand = np.flatnonzero(pool & (yr == yr.max()))
        cuts = rng.choice(cand, size=min(n_cuts, len(cand)), replace=False)
    res = {"cuts": 0, "protected_checked": 0, "later_checked": 0, "columns": int(real.sum()), "atol": PROBE_ATOL,
           "protected_changed": 0, "later_changed": 0, "control_protected_changed": 0,
           "largest_protected_difference": 0.0, "changed_by_column": {}, "cut_matches": []}
    for c in cuts:
        pert, keep = perturb(rows, int(c), rng, outcomes, pre_match)
        got = build_fn(pert, perturb_aux(aux, rows, int(c), rng) if perturb_aux is not None else aux, pool)
        got[control] = leaky_control(pert, pool)
        B0 = np.column_stack([base[k] for k in names])
        G = np.column_stack([got[k] for k in names])
        diff = ~np.isclose(G, B0, equal_nan=True, rtol=0, atol=PROBE_ATOL)
        kp = keep[pool]
        gap = np.where(np.isfinite(G) & np.isfinite(B0) & kp[:, None], np.abs(G - B0), 0.0)
        res["cuts"] += 1
        res["protected_checked"] += int(kp.sum())
        res["later_checked"] += int((~kp).sum())
        res["protected_changed"] += int((diff[:, real].any(axis=1) & kp).sum())
        res["later_changed"] += int((diff[:, real].any(axis=1) & ~kp).sum())
        res["control_protected_changed"] += int((diff[:, ~real].any(axis=1) & kp).sum())
        res["largest_protected_difference"] = max(res["largest_protected_difference"], float(gap[:, real].max()))
        for jx, k in enumerate(names):
            ch = int((diff[:, jx] & kp).sum())
            if real[jx] and ch:
                res["changed_by_column"][k] = res["changed_by_column"].get(k, 0) + ch
        a = rows.iloc[2 * int(c)]
        res["cut_matches"].append({"match_id": a["match_id"], "tournament": a["tournament_name"],
                                   "date": str(a["tournament_date"])[:10], "round_order": int(a["round_order"])})
        log(f"  probe cut {res['cuts']}: protected changed {res['protected_changed']} of {res['protected_checked']}, "
            f"later changed {res['later_changed']}, control caught at {res['control_protected_changed']}")
    return res


def probe_slice(rows: pd.DataFrame, start: str = "2025-01-01") -> pd.DataFrame:
    """Both tours from ``start`` (history inside the slice only), as stage4_features.run_probe."""
    sl = rows["tournament_date"].ge(pd.Timestamp(start)).to_numpy()
    return F.prepare(rows[sl].reset_index(drop=True).drop(columns=["day", "pcode"]))


# ------------------------------------------------------------------------------------------------

def main() -> int:
    t_start = time.time()
    timings = {}
    rows, bt_info = load_inputs()
    consts = elo_constants()
    timings["load_s"] = round(time.time() - t_start, 1)
    log(f"player-matches: {len(rows):,}; BT file found: {bt_info['bt_found']}")
    pool, A, Bi = pool_rows(rows)
    frame = U.load_pool()
    assert (rows["match_id"].to_numpy()[A] == frame["match_id"].to_numpy()).all(), "pool order"
    ctx = {"elo": consts, "priors": priors(rows, consts)}
    log(f"priors: {json.dumps(ctx['priors'])}")
    cols1 = [c for c in SOS_ROWS if not (c.startswith("sos_bt") and "bt_own" not in rows)]
    # family 1 sums once; the tuning re-divides them
    t1 = time.time()
    sums = sos_sums(rows, ctx)
    timings["family1_sums_s"] = round(time.time() - t1, 1)
    log("family 1 sums done")

    def value1(col, Kv):
        v, e = sos_value(sums, col, rows, ctx, np.full(len(rows), float(Kv)))
        return np.where(e[A] & e[Bi], v[A] - v[Bi], np.nan)
    t2 = time.time()
    d_all, d_s = elo_deltas(rows, consts)
    Ridx = np.column_stack([A, Bi]).reshape(-1)
    rs = revalue_pairs(rows, consts, Ridx, deltas=(d_all, d_s))
    timings["family2_pairs_s"] = round(time.time() - t2, 1)
    log(f"family 2 pairs done: {int(rs['n'].sum()):,} pairs")

    def value2(col, Kv):
        v, e = revalue_value(rs, col.split("|")[0], np.full(len(Ridx), float(Kv)))
        return np.where(e[0::2] & e[1::2], v[0::2] - v[1::2], np.nan)
    t3 = time.time()
    K1, grid1 = tune(frame, value1, cols1)
    K2, grid2 = tune(frame, value2, list(REVALUE_ROWS))
    K = {**K1, **K2}
    timings["tuning_s"] = round(time.time() - t3, 1)
    is_atp = frame["tour"].to_numpy() == "atp"
    feats = {}
    for c in cols1 + list(REVALUE_ROWS):
        fn = value1 if c in SOS_ROWS else value2
        feats[c] = np.where(is_atp, fn(c, K[c]["atp"]), fn(c, K[c]["wta"]))
    # the same columns through build() (the probe's builder) must agree
    t4 = time.time()
    rebuilt = build(rows, ctx, K)
    agree = {c: float(np.nanmax(np.abs(rebuilt[c] - feats[c]))) if np.isfinite(feats[c]).any() else 0.0 for c in feats}
    same_missing = {c: bool(np.array_equal(np.isnan(rebuilt[c]), np.isnan(feats[c]))) for c in feats}
    assert all(v < 1e-9 for v in agree.values()) and all(same_missing.values()), (agree, same_missing)
    timings["rebuild_check_s"] = round(time.time() - t4, 1)
    # checks: Stage 1's update; the vectorised revaluation against a row-by-row reading
    dchk = delta_check(rows, consts, d_all)
    log(f"Elo update check: {json.dumps(dchk)}")
    rng = np.random.default_rng(SEED)
    sample = rng.choice(len(Ridx), size=300, replace=False)
    worst = 0.0
    nbad = 0
    by_player = player_index(rows)
    for q in sample:
        n_b, s_b, l_b = brute_revalue(rows, consts, int(Ridx[q]), d_all, d_s, by_player)
        nbad += int(n_b != rs["n"][q])
        worst = max(worst, abs(s_b - rs["spec"][q]), abs(l_b - rs["later"][q]))
    brute = {"rows_checked": int(len(sample)), "count_mismatches": nbad, "largest_sum_difference": worst}
    log(f"row-by-row check of the revaluation: {json.dumps(brute)}")
    assert nbad == 0 and worst < 1e-9
    # coverage (evaluation matches) and descriptive scale of the inputs
    ev = frame["evaluation"].to_numpy(dtype=bool)
    tour = frame["tour"].to_numpy()
    coverage = {c: {t: {"evaluation_matches": int((ev & (tour == t)).sum()),
                        "exists": int((ev & (tour == t) & np.isfinite(feats[c])).sum()),
                        "sd": float(np.nanstd(feats[c][ev & (tour == t)]))} for t in C.TOURS} for c in feats}
    pair_stats = {"pairs": int(rs["n"].sum()), "pairs_with_later_evidence": int(rs["with_evidence"].sum()),
                  "pairs_with_a_later_rematch_taken_out": int(rs["rematch_pairs"].sum()),
                  "pairs_an_earlier_date_rule_would_read_in_the_pool_week": int(rs["date_rule_same_week"].sum()),
                  "mean_encounters_per_pool_player_row": float(rs["n"].mean())}
    # a data note: evaluation-level events whose tournament date is not a Monday
    a = rows.iloc[0::2]
    evl = a[a["level"].isin(C.EVAL_LEVELS)]
    evs = evl.drop_duplicates(["tour", "tournament_id", "tournament_date"])
    wd = evs["tournament_date"].dt.dayofweek
    data_notes = {"evaluation_level_events": int(len(evs)), "events_not_dated_monday": int((wd != 0).sum()),
                  "evaluation_matches": int(a["evaluation"].sum()),
                  "evaluation_matches_in_events_not_dated_monday": int((a["evaluation"] & (a["tournament_date"].dt.dayofweek != 0)).sum()),
                  "by_weekday": {str(k): int(v) for k, v in wd.value_counts().sort_index().items()}}
    log(f"pairs: {json.dumps(pair_stats)}")
    out = pd.DataFrame({"match_id": frame["match_id"].to_numpy()})
    for c in feats:
        out[c] = feats[c].astype("float64")
    out.to_parquet(PART, index=False)
    log(f"wrote {PART.name}: {out.shape}")
    # the probe on the 2025-2026 slice, with the frozen constants
    t5 = time.time()
    sl = probe_slice(rows)
    log(f"probe slice: {len(sl):,} player-matches")
    pr = probe(sl, lambda r, aux, pool: build(r, ctx, K, pool=pool))
    timings["probe_s"] = round(time.time() - t5, 1)
    timings["total_s"] = round(time.time() - t_start, 1)
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "settings": {"K_grid": list(K_GRID), "tune_years": [TUNE_YEARS[0], TUNE_YEARS[-1]],
                            "prior_years": [PRIOR_YEARS[0], PRIOR_YEARS[-1]], "week52_days": WEEK52,
                            "half_life_weeks": HALF_LIFE, "log_odds_per_elo_point": LN, "chunk": CHUNK, "seed": SEED},
               "elo_constants": consts, "bt": bt_info, "priors": ctx["priors"], "K": K,
               "tuning_grid": grid1 + grid2, "coverage": coverage, "pairs": pair_stats, "data_notes": data_notes,
               "checks": {"elo_update": dchk, "revalue_row_by_row": brute,
                          "build_equals_tuning_columns": {"largest_difference": max(agree.values()) if agree else 0.0}},
               "probe": pr, "timings": timings,
               "columns": {**{c: SOS_ROWS[c] for c in cols1}, **REVALUE_ROWS}}
    PART_JSON.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    log(f"wrote {PART_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
