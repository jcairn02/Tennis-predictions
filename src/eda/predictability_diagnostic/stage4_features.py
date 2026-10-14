"""Stage 4 of the predictability diagnostic, part 1: every feature of the approved candidate list, for every
evaluation-level match of 2010-2026, from one chronological pass.

The list and every definition are docs/studies/predictability_diagnostic/candidates.md (approved as written, 1 Oct
2026) with its table data/studies/predictability_diagnostic/stage4_candidates.csv. Nothing is added here. Features are
built from history only, under the Brief's time rule (earlier events, and earlier rounds of the same event), through
common.asof_sums and Stage 3's lookback_sums and sums_before: one vectorised pass over all 1.7 million player-matches,
never a per-row look-back.

What each form is (candidates.md, section 2), for a per-match statistic with count x and units d:
    career      each earlier match centred on its own surface's tour average (x - d mu_surface); the sum shrunk toward
                the tour's average on this match's surface: mu + sum / (units + K), K Stage 3's all-surface constant
    52 weeks    the same over events starting up to 364 days before this one, plus this event's earlier rounds
    decayed     the same with each earlier match weighted 1/2 per 52 weeks of age (the owner's half-life)
    surface     earlier matches on this match's surface only, with the surface's constant (carpet: the all-surface
                one; a surface where Stage 3 found no spread: the average for everyone)
    adjusted    the career form after each earlier match's rate is restated against a typical opponent: Stage 3's own
                adjusted rates for serve and return points won (and their constants); for the others the log-odds rate
                (x + 1/2) / (d + 1) moved by beta x (the opponent's pre-match Stage 3 rating - a typical opponent's),
                beta fitted per tour on 2013-2018 (a count per game moves on the log scale, a rate centred on zero on
                its own scale); the raw statistic's constant
A feature is A's value minus B's: shares on the log-odds scale, break points faced per game on the log scale, break
points above expectation and the adjusted head to head on their own scale. The four matchups set A's serve against
B's return through Stage 2's iid model (break points: the log-odds sum).

Constants the plan leaves to Stage 4 (set here, before anything is scored; stage4_constants.csv): K for match wins,
deciding sets, return points against the first and the second serve and break points above expectation (Stage 3's
method, stage3_traits.eb_constants, player-seasons of 2010-2018), and for big-point play on return (Grand Slam
point-by-point seasons 2011-2018); the opponent adjustment's beta per tour and statistic (2013-2018); the surface
averages of the new statistics and of the adjusted rates (Stage 3's pooling); the weighted Elos' scale (the mean
winner's share over 2010-2018).

Lag (the leak check, stage4_rundown.py): build(..., lag=True) recomputes a feature one match later than it should be:
each player's history is read as it stood at their previous match of that history (the same code, evaluated at the
earlier row), so a feature that leaked the match itself loses the leak while a real one loses one match of history.

Writes, in data/studies/predictability_diagnostic/:
    stage4_features.parquet         one row per evaluation-level match of 2010-2026 (completed or retired): the result,
                                    surface Elo's and the market's probabilities, the level group and each candidate x
                                    form's inputs (missing where the feature does not exist)
    stage4_constants.csv            the constants set in Stage 4
    stage4_features_summary.json    the plan's hash, the coverage reproduced against the plan's counts, the probe cut by
                                    date, event and round, and timings

Run: ./python.sh src/eda/predictability_diagnostic/stage4_features.py   (a few minutes)
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402
from src.eda.predictability_diagnostic import stage3_traits as T  # noqa: E402
from src.eda.predictability_diagnostic import stage4_candidates as P  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as CTRY  # noqa: E402
from src.eda.predictability_diagnostic.scheduled_format import scheduled_format  # noqa: E402
from src.eda.lower_level_evidence import level_layer as _LLE  # noqa: E402  level layer (LLE_LAYER)

PLAN = C.DOCS / "candidates.md"
CANDIDATES = C.OUT / "stage4_candidates.csv"
COVERAGE = C.OUT / "stage4_candidates_coverage.csv"
FEATURES = C.OUT / "stage4_features.parquet"
CONSTANTS = C.OUT / "stage4_constants.csv"
SUMMARY = C.OUT / "stage4_features_summary.json"
SHRINKAGE = C.OUT / "stage3_shrinkage.csv"
STAGE3 = C.OUT / "stage3_results.json"
RATINGS = C.OUT / "stage3_ratings.parquet"
BASELINES = C.OUT / "stage1_baselines.parquet"
BASE_SUMMARY = C.OUT / "stage1_baselines_summary.json"
ODDS = C.OUT / "stage1_odds.parquet"
PBP_PLAYERS = C.OUT / "stage2_pbp_players.parquet"

HALF_LIFE = 52                     # weeks: the owner's decision of 1 Oct 2026
WEEK52 = 364                       # days: the last 52 weeks (Stage 3's)
WINDOWS = (7, 14)                  # days between tournament Mondays: the fatigue windows
ELO_CHANGE = {"elo_change_26w": 182, "elo_change_52w": 364}
SURFACE_FIRST = 3                  # fewer than this many earlier matches on the surface this season
AGE_RANGE = (14.0, 50.0)           # ages outside read as missing
AGE_CENTRE = 25.0
SHARE_CLIP = 1e-4                  # a shrunk share is kept inside (1e-4, 1 - 1e-4) before its log-odds
K_YEARS = range(2010, 2019)        # constants for the statistics Stage 3 did not measure
BETA_YEARS = range(2013, 2019)     # the opponent adjustment's slopes (after the ratings' warm-up)
PBP_K_YEARS = range(2011, 2019)    # big-point play: the Grand Slam point-by-point seasons
BOOT = 200                         # bootstrap resamples of players for the new constants' ranges
SEED = 20261001
SURF = {"Hard": 1, "Clay": 2, "Grass": 3, "Carpet": 4}
SURF_NAME = {v: k for k, v in SURF.items()}
MAIN_TOUR = ("GS", "FIN", "T1000", "T500", "T250")
FORMS = ("career", "52 weeks", "decayed", "surface", "adjusted")
NEW_STATS = ("rpw_first", "rpw_second", "bp_over", "win", "deciding")
HIST = list(C.RATES) + list(NEW_STATS)                   # the 21 statistics kept as sums (the head to head apart)
STAGE3_ADJ = {"spw": "spw_adj", "rpw": "rpw_adj"}         # Stage 3's own adjusted rates
POISSON = {"bp_faced_pg"}                                 # a count per game: the log scale
LINEAR = {"bp_over"}                                      # a rate centred on zero: its own scale
SERVE_SIDE = ("spw", "hold", "ace", "df", "first_in", "first_won", "second_won", "bp_saved", "bp_faced_pg")
RETURN_SIDE = ("rpw", "brk", "bp_conv", "rpw_first", "rpw_second")
MATCH_SIDE = ("tpw", "tb_won", "sets_won", "games_won", "win", "deciding", "bp_over")
SCORE_STATS = ("tb_won", "sets_won", "games_won", "win", "deciding")
MATCHUPS = {"mu_points": ("spw", "rpw"), "mu_games": ("hold", "brk"), "mu_bp": ("bp_saved", "bp_conv"),
            "mu_components": ("first_in", "first_won", "second_won", "rpw_first", "rpw_second")}
ENTRY_TYPES = P.ENTRY_TYPES
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def opp(a: np.ndarray) -> np.ndarray:
    """The other player's value in the same match (rows come in A, B pairs)."""
    return P.opp(a)


def safe_logit(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype="float64"), SHARE_CLIP, 1 - SHARE_CLIP))


# ------------------------------------------------------------------------------------------------
# Inputs

def load_rows() -> tuple[pd.DataFrame, dict]:
    """Every player-match (two rows per match, A then B, in the table's order) with what any feature reads: Stage 0's
    counts and attributes, Stage 3's adjusted serve and return points (stage3_traits.load_rows, unchanged) and both
    players' pre-match ratings, Stage 1's surface Elo, and the closing odds."""
    rows, typical = T.load_rows()
    extra = C.load_match_players(["match_id", "side", "opponent_id", "won", "rank", "rank_points", "entry", "age",
                                  "height", "hand", "country"],
                                 match_columns=["best_of", "minutes", "tournament_name", "round"])
    assert (extra["match_id"].to_numpy() == rows["match_id"].to_numpy()).all()
    assert (extra["side"].to_numpy() == rows["side"].to_numpy()).all()
    for c in ["opponent_id", "won", "rank", "rank_points", "entry", "age", "height", "hand", "country", "best_of",
              "minutes", "tournament_name", "round"]:
        rows[c] = extra[c].to_numpy()
    side_a = rows["side"].eq("A").to_numpy()
    assert side_a[0::2].all() and not side_a[1::2].any()
    assert (rows["match_id"].to_numpy()[0::2] == rows["match_id"].to_numpy()[1::2]).all()
    mid = rows["match_id"].to_numpy()[0::2]

    rt = pd.read_parquet(RATINGS, columns=["match_id", "serve_a", "serve_b", "return_a", "return_b", "mu_logit",
                                           "updates"]).set_index("match_id").reindex(mid)
    bl = pd.read_parquet(BASELINES, columns=["match_id", "elo_a_ret", "elo_b_ret", "elo_surf_a_ret", "elo_surf_b_ret",
                                             "p_elo_surf_ret"]).set_index("match_id").reindex(mid)
    od = pd.read_parquet(ODDS, columns=["match_id", "p_avg_a"]).set_index("match_id").reindex(mid)

    def own_other(a, b):
        a, b = np.asarray(a, dtype="float64"), np.asarray(b, dtype="float64")
        own = np.column_stack([a, b]).reshape(-1)
        return own, opp(own)
    rows["serve_own"], rows["serve_opp"] = own_other(rt["serve_a"], rt["serve_b"])
    rows["return_own"], rows["return_opp"] = own_other(rt["return_a"], rt["return_b"])
    rows["mu_logit"] = np.repeat(rt["mu_logit"].to_numpy(dtype="float64"), 2)
    rows["rating_update"] = np.repeat(rt["updates"].to_numpy(dtype=bool), 2)
    rows["elo_own"], _ = own_other(bl["elo_a_ret"], bl["elo_b_ret"])
    rows["elo_surf_own"], _ = own_other(bl["elo_surf_a_ret"], bl["elo_surf_b_ret"])
    rows["p_elo_a"] = np.repeat(bl["p_elo_surf_ret"].to_numpy(dtype="float64"), 2)
    rows["p_mkt_a"] = np.repeat(od["p_avg_a"].to_numpy(dtype="float64"), 2)
    return prepare(rows), typical


def prepare(rows: pd.DataFrame) -> pd.DataFrame:
    """Codes every builder shares: surface, level group, the event, whether the match was played, its format."""
    rows = rows.copy()
    rows["surf"] = rows["surface"].map(SURF).fillna(0).astype("int64").to_numpy()
    rows["group"] = P.level_group(rows["level"], rows["qualifying"]).to_numpy()
    rows["ev"] = pd.factorize(rows["tournament_id"].astype(str) + "|" + rows["tournament_date"].astype(str))[0]
    st = rows["status"].to_numpy()
    rows["played"] = np.isin(st, ["completed", "retired"])
    rows["box_hist"] = (st == "completed") & (rows["format"].to_numpy() == "standard")
    if "day" not in rows:
        rows["day"] = rows["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    if "pcode" not in rows:
        rows["pcode"] = pd.factorize(rows["player_id"])[0]
    rows["opp_pcode"] = opp(rows["pcode"].to_numpy())
    rows["won"] = rows["won"].astype(bool)
    rows["eval_level"] = rows["level"].isin(C.EVAL_LEVELS).to_numpy()
    return rows


def best_of_five(rows: pd.DataFrame, source: str = "scheduled") -> np.ndarray:
    """Prematch indicator (0/1/NaN), from independently scheduled event rules.

    ``recorded`` is retained as an alias for old sensitivity/probe callers; both
    now use the repaired schedule rules. Score anatomy is available only through
    ``retrospective_best_of_five``, never through a prediction switch.
    """
    if source not in ("scheduled", "recorded"):
        raise ValueError("Forecast format must be scheduled; use retrospective_best_of_five for anatomy only")
    schedule = scheduled_format(rows)
    return np.where(schedule["supported"], schedule["best_of"].eq(5).astype(float), np.nan)


def retrospective_best_of_five(rows: pd.DataFrame) -> np.ndarray:
    """Completed-score anatomy for retrospective simulations only; not a forecast input."""
    recorded = (rows["best_of"].to_numpy()[0::2].astype("float64") == 5) | (rows["format"].to_numpy()[0::2] == "short_sets")
    sets = rows["sets_won_n"].to_numpy(dtype="float64").reshape(-1, 2)
    w = np.where(np.isnan(sets).all(axis=1), np.nan, np.fmax(sets[:, 0], sets[:, 1]))
    with np.errstate(invalid="ignore"):
        bo5 = (w >= 3) | recorded
    return np.repeat(bo5, 2)


def deciding_rules(rows: pd.DataFrame) -> np.ndarray:
    """Per row: scheduled Slam deciding-set rules; unknown formats stay masked by best_of_five."""
    a = rows.iloc[0::2]
    level = a["level"].where(scheduled_format(a)["supported"], "unknown")
    r = M.deciding_set_rule(level.reset_index(drop=True), a["tournament_name"].reset_index(drop=True),
                            a["year"].reset_index(drop=True), a["qualifying"].reset_index(drop=True)).to_numpy()
    return np.repeat(r, 2)


def iid_prob(pa, pb, bo5, rule, fmt) -> np.ndarray:
    """P(A wins) for an explicitly specified supported format; unknown/short sets return NaN.

    Forecast callers must pass scheduled metadata. A match tiebreak replaces the
    deciding set with a 10-point tiebreak; short/no-ad sets are not approximated
    by ordinary best of five. NaN best-of indicators cannot become truthy Bo5.
    """
    pa, pb = np.asarray(pa, dtype="float64"), np.asarray(pb, dtype="float64")
    bo5, rule, fmt = np.asarray(bo5, dtype="float64"), np.asarray(rule), np.asarray(fmt)
    bo = np.where(bo5 == 1, 5, 3)
    known = np.isin(bo5, [0, 1]) & np.isin(fmt, ["standard", "match_tiebreak"])
    known &= np.isfinite(pa) & np.isfinite(pb) & np.isin(rule, list(M.SET_RULES))
    out = np.full(pa.shape, np.nan)
    out[known] = M.match_win_by(pa[known], pb[known], bo[known], rule[known])
    mt = known & (fmt == "match_tiebreak")
    if mt.any():
        s, f = M.set_win(pa[mt], pb[mt]), M.tiebreak(pa[mt], pb[mt], 10)
        out[mt] = np.where(bo[mt] == 5, s ** 3 + 3 * s ** 3 * (1 - s) + 6 * s ** 2 * (1 - s) ** 2 * f,
                           s ** 2 + 2 * s * (1 - s) * f)
    return out


def scheduled_iid_prob(pa, pb, rows: pd.DataFrame) -> np.ndarray:
    """Convert prematch serve rates for one row per match (or player) using schedule rules."""
    schedule = scheduled_format(rows)
    bo5 = np.where(schedule["supported"], schedule["best_of"].eq(5).astype(float), np.nan)
    # Only recognised scheduled Slams require the lookup; unmapped events remain
    # missing rather than making the anatomy rule reader reject an entire batch.
    level = rows["level"].where(schedule["supported"], "unknown")
    rule = M.deciding_set_rule(level, rows["tournament_name"], rows["year"], rows["qualifying"])
    return iid_prob(pa, pb, bo5, rule.to_numpy(), schedule["format"].to_numpy())


def serve_rate_for_hold(h: np.ndarray) -> np.ndarray:
    """The serve-point rate whose hold rate under the iid model is h (stage2_iid.game inverted, by bisection)."""
    h = np.clip(np.asarray(h, dtype="float64"), 1e-9, 1 - 1e-9)
    lo, hi = np.full(h.shape, 1e-6), np.full(h.shape, 1 - 1e-6)
    for _ in range(60):
        mid = (lo + hi) / 2
        below = M.game(mid) < h
        lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
    return (lo + hi) / 2


# ------------------------------------------------------------------------------------------------
# The previous row under the time rule

def prev_visible(rows: pd.DataFrame, mask: np.ndarray, key: np.ndarray | None = None) -> np.ndarray:
    """For every row: the latest row in ``mask`` with the same key (default: the player) that the row may see, or -1.
    An earlier round of the same event comes first; otherwise the last such row of an earlier tournament week. Never
    the row itself, another match of the same round (a round robin) or another event of the same week. Rows outside
    ``mask`` get a value too (stage4_candidates.previous_row gives one only to rows inside it)."""
    n = len(rows)
    key = rows["pcode"].to_numpy() if key is None else np.asarray(key)
    d, e = rows["day"].to_numpy(), rows["ev"].to_numpy()
    r, o = rows["round_order"].to_numpy(), rows["order"].to_numpy()
    idx = np.lexsort((o, r, e, d, key))
    ks, ds, es, rs = key[idx], d[idx], e[idx], r[idx]
    pos = np.arange(n)
    cm = np.maximum.accumulate(np.where(np.asarray(mask, dtype=bool)[idx], pos, -1))
    new_day = np.r_[True, (ks[1:] != ks[:-1]) | (ds[1:] != ds[:-1])]
    start_day = np.maximum.accumulate(np.where(new_day, pos, 0))
    cand_b = np.where(start_day > 0, cm[np.maximum(start_day - 1, 0)], -1)
    ok_b = (cand_b >= 0) & (ks[np.maximum(cand_b, 0)] == ks)
    new_round = np.r_[True, (ks[1:] != ks[:-1]) | (ds[1:] != ds[:-1]) | (es[1:] != es[:-1]) | (rs[1:] != rs[:-1])]
    start_round = np.maximum.accumulate(np.where(new_round, pos, 0))
    cand_a = np.where(start_round > 0, cm[np.maximum(start_round - 1, 0)], -1)
    ca = np.maximum(cand_a, 0)
    ok_a = (cand_a >= 0) & (ks[ca] == ks) & (ds[ca] == ds) & (es[ca] == es)
    prev_sorted = np.where(ok_a, cand_a, np.where(ok_b, cand_b, -1))
    out = np.full(n, -1, dtype="int64")
    out[idx] = np.where(prev_sorted >= 0, idx[np.maximum(prev_sorted, 0)], -1)
    return out


def at(values: np.ndarray, src: np.ndarray, fill=0.0) -> np.ndarray:
    """values[src], with ``fill`` where src is -1 (no earlier row)."""
    v = np.asarray(values)
    out = v[np.maximum(src, 0)]
    if out.ndim == 1:
        return np.where(src >= 0, out, fill)
    return np.where((src >= 0)[:, None], out, fill)


# ------------------------------------------------------------------------------------------------
# Per-match statistics: count x and units d of every row that enters a history

def stat_xd(rows: pd.DataFrame) -> dict:
    """Per statistic: (x, d, ok) for every row, with x = d = 0 where the row does not enter that history. Box-score and
    score statistics: completed matches in the standard format (Stage 3's rule); match wins: completed or retired;
    deciding sets: completed matches that reached one. The units follow stage4_candidates.history_units exactly."""
    out = {}
    box = rows["box_hist"].to_numpy()
    played = rows["played"].to_numpy()

    def num(c):
        return rows[c].to_numpy(dtype="float64")
    for s in C.RATES:
        n, d = num(f"{s}_n"), num(f"{s}_d")
        ok = box & ~np.isnan(n) & ~np.isnan(d)
        out[s] = (np.where(ok, n, 0.0), np.where(ok, d, 0.0), ok)
    for s, src in (("rpw_first", "first_won"), ("rpw_second", "second_won")):
        n, d = opp(num(f"{src}_n")), opp(num(f"{src}_d"))
        ok = box & ~np.isnan(n) & ~np.isnan(d)
        out[s] = (np.where(ok, d - n, 0.0), np.where(ok, d, 0.0), ok)
    # break points won above what the match's own serve rates predict (Stage 2's measure, both ways), per break point
    bps, bpc = out["bp_saved"][1], out["bp_conv"][1]
    sv_n, sv_d = num("spw_n"), num("spw_d")
    pa = sv_n / np.where(sv_d > 0, sv_d, np.nan)
    sav, fac = num("bp_saved_n"), num("bp_saved_d")
    x_bp = (sav - fac * pa) - (opp(sav) - opp(fac) * opp(pa))
    ok = ((bps + bpc) > 0) & box & ~np.isnan(sv_d) & ~np.isnan(opp(sv_d)) & rows["bp_saved_d"].notna().to_numpy() \
        & rows["bp_conv_d"].notna().to_numpy() & np.isfinite(x_bp)
    out["bp_over"] = (np.where(ok, x_bp, 0.0), np.where(ok, bps + bpc, 0.0), ok)
    won = rows["won"].to_numpy().astype("float64")
    out["win"] = (np.where(played, won, 0.0), played.astype("float64"), played.copy())
    dec = P.deciding_set(rows) & (rows["status"].to_numpy() == "completed")
    out["deciding"] = (np.where(dec, won, 0.0), dec.astype("float64"), dec)
    return out


# ------------------------------------------------------------------------------------------------
# Constants: surface averages, shrinkage constants, the opponent adjustment

def pooled_means(rows: pd.DataFrame, x: np.ndarray, d: np.ndarray, ok: np.ndarray, pop: np.ndarray) -> dict:
    """Stage 3's surface averages (stage3_traits.surface_means): per tour, the pooled rate over the population; a
    surface with under 300 player-matches takes the tour's. Keys (tour, surface or 'all')."""
    out = {}
    tours, surfs = rows["tour"].to_numpy(), rows["surface"].to_numpy()
    sel = ok & pop
    for tour in C.TOURS:
        t = sel & (tours == tour)
        mu_all = float(x[t].sum() / d[t].sum())
        out[(tour, "all")] = mu_all
        for s in SURF:
            ts = t & (surfs == s)
            out[(tour, s)] = float(x[ts].sum() / d[ts].sum()) if ts.sum() >= 300 else mu_all
    return out


def mu_of_rows(rows: pd.DataFrame, means: dict) -> np.ndarray:
    """Each row's tour average on its own surface (the tour's over all surfaces where the surface is unknown)."""
    tours, surf = rows["tour"].to_numpy(), rows["surf"].to_numpy()
    out = np.empty(len(rows))
    for tour in C.TOURS:
        for code in (0, 1, 2, 3, 4):
            m = (tours == tour) & (surf == code)
            out[m] = means[(tour, SURF_NAME[code] if code else "all")]
    return out


def eb_constant(rows: pd.DataFrame, x, d, ok, pop, tour: str, surface: str, means: dict, rng) -> dict:
    """Stage 3's shrinkage constant (stage3_traits.shrinkage) for one statistic, tour and surface: player-windows (a
    season; three seasons on grass), each match against its surface's average when all surfaces are pooled, the
    measured chance variation over the true spread (stage3_traits.eb_constants), and a bootstrap over players."""
    sel = ok & pop & (rows["tour"].to_numpy() == tour)
    if surface != "all":
        sel &= rows["surface"].to_numpy() == surface
    g = rows.loc[sel, ["pcode", "year", "surf"]]
    xs, ds = x[sel], d[sel]
    if surface == "all":
        xs = xs - ds * (mu_of_rows(rows.loc[sel], means) - means[(tour, "all")])
    unit, uniq = pd.factorize(pd.Series(g["pcode"].to_numpy() * 100 + T.windows(g, surface)))
    s = T.unit_sums(unit, xs, ds)
    est = T.eb_constants(s["D"], s["X"], s["W"], s["m"])
    pu = pd.factorize(pd.Series(np.asarray(uniq) // 100))[0]
    P_ = int(pu.max()) + 1
    Ks = []
    for _ in range(BOOT // 50):
        draws = rng.integers(0, P_, size=(50, P_))
        copies = np.stack([np.bincount(row, minlength=P_) for row in draws])[:, pu].astype("float64")
        Ks.append(T.eb_constants(s["D"], s["X"], s["W"], s["m"], weight=copies)["K"])
    Ks = np.concatenate(Ks)
    per_match = float(ds.sum() / max(len(ds), 1))
    return {"K_units": float(est["K"]), "K_lo": float(np.percentile(Ks, 2.5, method="nearest")),
            "K_hi": float(np.percentile(Ks, 97.5, method="nearest")), "K_matches": float(est["K"]) / per_match,
            "mean": float(est["mu"]), "player_windows": int((s["D"] > 0).sum()), "player_matches": int(sel.sum())}


def seeded(*parts) -> np.random.Generator:
    return np.random.default_rng([SEED] + [zlib.crc32(str(p).encode("utf-8")) for p in parts])


def opponent_z(rows: pd.DataFrame, stat: str, typical: dict) -> np.ndarray:
    """The opponent's pre-match Stage 3 rating that the statistic faces, minus a typical opponent's: the return rating
    for serve-side statistics, the serve rating for return-side ones, their sum for whole-match ones."""
    tours = rows["tour"].to_numpy()
    s_typ = np.where(tours == "atp", typical["atp"]["serve"], typical["wta"]["serve"])
    r_typ = np.where(tours == "atp", typical["atp"]["return"], typical["wta"]["return"])
    so, ro = rows["serve_opp"].to_numpy(), rows["return_opp"].to_numpy()
    if stat in SERVE_SIDE:
        return ro - r_typ
    if stat in RETURN_SIDE:
        return so - s_typ
    return (so + ro) - (s_typ + r_typ)


def rate_scale(stat: str, x: np.ndarray, d: np.ndarray) -> np.ndarray:
    """A match's rate on the scale the adjustment moves it: log-odds of (x + 1/2) / (d + 1); the log of the same for a
    count per game; the rate itself for a statistic centred on zero."""
    with np.errstate(divide="ignore", invalid="ignore"):
        if stat in LINEAR:
            return x / np.where(d > 0, d, np.nan)
        r = (x + 0.5) / (d + 1.0)
        return np.log(r) if stat in POISSON else np.log(r / (1 - r))


def from_scale(stat: str, y: np.ndarray, d: np.ndarray) -> np.ndarray:
    """A rate on the adjustment's scale turned back into a count of the same d units."""
    if stat in LINEAR:
        return d * y
    return d * (np.exp(y) if stat in POISSON else expit(y))


def fit_slope(y: np.ndarray, z: np.ndarray, w: np.ndarray, surf: np.ndarray) -> dict:
    """Weighted least squares of y on z with an intercept per surface (weights: the units)."""
    levels = np.unique(surf)
    X = np.column_stack([z] + [(surf == s).astype("float64") for s in levels])
    XtW = X.T * w
    beta = np.linalg.solve(XtW @ X, XtW @ y)
    resid = y - X @ beta
    sigma2 = float((w * resid ** 2).sum() / (len(y) - X.shape[1]))
    cov = sigma2 * np.linalg.inv(XtW @ X)
    return {"slope": float(beta[0]), "slope_se": float(np.sqrt(cov[0, 0])), "n": int(len(y))}


def constants(rows: pd.DataFrame, xd: dict, typical: dict, pbp: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Every constant the features need: Stage 3's (read as they are) and those the plan sets in Stage 4."""
    s3 = json.loads(STAGE3.read_text(encoding="utf-8"))
    shr = pd.read_csv(SHRINKAGE)
    means = {}
    for r in s3["surface_means"]:
        means.setdefault(r["stat"], {})[(r["tour"], r["surface"])] = float(r["mean"])
    K = {}
    for stat in list(C.RATES) + list(STAGE3_ADJ.values()):
        years = "2013-2018" if stat in STAGE3_ADJ.values() else "2010-2018"
        g = shr[(shr["stat"] == stat) & (shr["years"] == years)]
        for r in g.itertuples(index=False):
            K[(stat, r.tour, r.surface)] = float(r.K_units)
    recs = []
    year = rows["year"].to_numpy()
    eval_lvl = rows["eval_level"].to_numpy()
    pop_k = eval_lvl & np.isin(year, list(K_YEARS))
    # the new statistics' surface averages and constants, by Stage 3's method on 2010-2018
    for stat in NEW_STATS:
        x, d, ok = xd[stat]
        means[stat] = pooled_means(rows, x, d, ok, pop_k)
        for tour in C.TOURS:
            for surface in ("all", "Hard", "Clay", "Grass"):
                e = eb_constant(rows, x, d, ok, pop_k, tour, surface, means[stat], seeded("K", stat, tour, surface))
                K[(stat, tour, surface)] = e["K_units"]
                recs.append({"kind": "shrinkage K", "stat": stat, "tour": tour, "surface": surface,
                             "years": "2010-2018", "value": e["K_units"], "lo": e["K_lo"], "hi": e["K_hi"],
                             "K_matches": e["K_matches"], "mean": means[stat][(tour, surface)],
                             "n": e["player_matches"], "player_windows": e["player_windows"]})
        log(f"  constant {stat}")
    # the opponent adjustment's slopes (2013-2018), and the surface averages of the adjusted rates
    pop_b = eval_lvl & np.isin(year, list(BETA_YEARS))
    slopes = {}
    adj = {}
    for stat in HIST:
        x, d, ok = xd[stat]
        z = opponent_z(rows, stat, typical)
        y = rate_scale(stat, x, d)
        for tour in C.TOURS:
            sel = ok & pop_b & (d > 0) & (rows["tour"].to_numpy() == tour) & np.isfinite(y) & np.isfinite(z)
            f = fit_slope(y[sel], z[sel], d[sel], rows["surf"].to_numpy()[sel])
            slopes[(stat, tour)] = f["slope"]
            recs.append({"kind": "adjustment beta" if stat not in STAGE3_ADJ else "adjustment beta, reference (not used)",
                         "stat": stat, "tour": tour, "surface": "all", "years": "2013-2018",
                         "value": -f["slope"], "lo": -f["slope"] - 1.96 * f["slope_se"], "hi": -f["slope"] + 1.96 * f["slope_se"],
                         "n": f["n"], "note": ("beta = minus the slope of the match's rate (log-odds; log for a count per game; "
                                               "the rate itself for break points above expectation) on the opponent's rating, "
                                               "with an intercept per surface") if stat not in STAGE3_ADJ else
                         "the same fit for serve or return points won; Stage 3's adjusted rates (beta = 1 by its model) are used"})
        if stat in STAGE3_ADJ:
            adj[stat] = np.where(ok, rows[f"{STAGE3_ADJ[stat]}_n"].to_numpy(dtype="float64"), 0.0)
            continue
        slope_row = np.where(rows["tour"].to_numpy() == "atp", slopes[(stat, "atp")], slopes[(stat, "wta")])
        ya = y - slope_row * z
        adj[stat] = np.where(ok & (d > 0) & np.isfinite(ya), from_scale(stat, ya, d), 0.0)
    for stat in HIST:
        x, d, ok = xd[stat]
        key = f"{stat}_adj"
        if stat in STAGE3_ADJ:
            means[key] = means[STAGE3_ADJ[stat]]
            for tour in C.TOURS:
                for surface in ("all", "Hard", "Clay", "Grass"):
                    K[(key, tour, surface)] = K[(STAGE3_ADJ[stat], tour, surface)]
        else:
            means[key] = pooled_means(rows, adj[stat], d, ok, pop_b)
            for tour in C.TOURS:
                for surface in ("all", "Hard", "Clay", "Grass"):
                    K[(key, tour, surface)] = K[(stat, tour, surface)]
    for stat in HIST:
        for tour in C.TOURS:
            for surface in ["all"] + list(SURF):
                recs.append({"kind": "surface average", "stat": stat, "tour": tour, "surface": surface,
                             "years": "2010-2018", "value": means[stat][(tour, surface)],
                             "note": "Stage 3's" if stat in C.RATES else "set in Stage 4 by Stage 3's pooling"})
                recs.append({"kind": "surface average, adjusted", "stat": stat, "tour": tour, "surface": surface,
                             "years": "2013-2018", "value": means[f"{stat}_adj"][(tour, surface)],
                             "note": "Stage 3's" if stat in STAGE3_ADJ else "set in Stage 4 by Stage 3's pooling"})
    # big-point play on return: Grand Slam point-by-point seasons 2011-2018
    bp_k = {}
    for tour in C.TOURS:
        g = pbp[(pbp["tour"] == tour) & pbp["year"].isin(list(PBP_K_YEARS))]
        unit, uniq = pd.factorize(pd.Series(g["pcode"].to_numpy() * 100 + (g["year"].to_numpy() - 2010)))
        s = T.unit_sums(unit, g["value"].to_numpy(), np.ones(len(g)))
        est = T.eb_constants(s["D"], s["X"], s["W"], s["m"])
        rng = seeded("K", "bigpoint", tour)
        pu = pd.factorize(pd.Series(np.asarray(uniq) // 100))[0]
        P_ = int(pu.max()) + 1
        Ks = np.concatenate([T.eb_constants(s["D"], s["X"], s["W"], s["m"], weight=np.stack(
            [np.bincount(row, minlength=P_) for row in rng.integers(0, P_, size=(50, P_))])[:, pu].astype("float64"))["K"]
            for _ in range(BOOT // 50)])
        bp_k[tour] = {"K": float(est["K"]), "mean": float(est["mu"])}
        recs.append({"kind": "shrinkage K", "stat": "bigpoint_return", "tour": tour, "surface": "all",
                     "years": "2011-2018", "value": float(est["K"]), "lo": float(np.percentile(Ks, 2.5, method="nearest")),
                     "hi": float(np.percentile(Ks, 97.5, method="nearest")), "K_matches": float(est["K"]),
                     "mean": float(est["mu"]), "n": int(len(g)), "player_windows": int((s["D"] > 0).sum()),
                     "note": "units are matches: the mean of the per-match measure, shrunk"})
    scales, elo_recs = elo_scales(rows)
    ctx = {"means": means, "K": K, "adjusted_x": adj, "slopes": slopes, "bigpoint": bp_k, "typical": typical,
           "elo_scale": scales}
    return ctx, pd.DataFrame(recs + elo_recs)


def k_for(ctx: dict, stat: str, tour: np.ndarray, surface: str = "all") -> np.ndarray:
    """The constant per row's tour; a surface's (carpet: all surfaces); infinite where no spread was found."""
    s = "all" if surface in ("Carpet", None) else surface
    return np.where(tour == "atp", ctx["K"][(stat, "atp", s)], ctx["K"][(stat, "wta", s)])


# ------------------------------------------------------------------------------------------------
# History sums: the one chronological pass

def history_sums(rows: pd.DataFrame, xd: dict, ctx: dict) -> dict:
    """Per row and statistic, the sums the forms read (every earlier match centred on its own surface's average):
    career (x, d), the adjusted career (x), decayed (x, d), the part older than 52 weeks (x, d) and the same surface
    (x, d). One call of the as-of helper per block of columns."""
    st = {}
    cols, names = [], []
    for s in HIST:
        x, d, ok = xd[s]
        x, d = _LLE.points_counts(rows, s, x, d, ok)   # level layer (LLE_LAYER)
        mu = mu_of_rows(rows, ctx["means"][s])
        mua = mu_of_rows(rows, ctx["means"][f"{s}_adj"])
        xc = np.where(ok, x - d * mu, 0.0)
        xac = np.where(ok, ctx["adjusted_x"][s] - d * mua, 0.0)
        cols += [xc, d, xac]
        names += [(s, "xc"), (s, "d"), (s, "xac")]
    V = np.column_stack(cols)
    del cols
    for lo in range(0, V.shape[1], 24):
        block = V[:, lo:lo + 24]
        car, dec = T.lookback_sums(rows, block, (HALF_LIFE,))
        bef = T.sums_before(rows["pcode"].to_numpy(), rows["day"].to_numpy(), block, rows["pcode"].to_numpy(),
                            rows["day"].to_numpy() - WEEK52)
        key = rows["pcode"].to_numpy() * 8 + rows["surf"].to_numpy()
        tmp = rows[["tournament_date", "tournament_id", "round_order"]].copy()
        tmp["_k"] = key
        for j in range(block.shape[1]):
            tmp[f"_v{j}"] = block[:, j]
        sur = C.asof_sums(tmp, [f"_v{j}" for j in range(block.shape[1])], player="_k").to_numpy()
        for j in range(block.shape[1]):
            s, what = names[lo + j]
            st[("car", s, what)] = car[:, j]
            st[("dec", s, what)] = dec[HALF_LIFE][:, j]
            st[("b52", s, what)] = bef[:, j]
            st[("sur", s, what)] = sur[:, j]
        log(f"  history sums: columns {lo}-{min(lo + 24, V.shape[1])} of {V.shape[1]}")
    return st


def h2h_sums(rows: pd.DataFrame, p_iid_own: np.ndarray) -> dict:
    """Earlier meetings of the player with this opponent (completed or retired): won, played, and won minus the iid
    model's chance from that meeting's pre-match Stage 3 ratings. Career, decayed, older than 52 weeks, same surface."""
    played = rows["played"].to_numpy()
    won = rows["won"].to_numpy()
    V = np.column_stack([np.where(played, won, 0.0), played.astype("float64"),
                         np.where(played & np.isfinite(p_iid_own), won - p_iid_own, 0.0)])
    pair = rows["pcode"].to_numpy().astype("int64") * 1_000_000 + rows["opp_pcode"].to_numpy().astype("int64")
    tmp = rows[["tournament_date", "tournament_id", "round_order", "day"]].copy()
    tmp["player_id"] = pair
    car, dec = T.lookback_sums(tmp, V, (HALF_LIFE,))
    bef = T.sums_before(pair, rows["day"].to_numpy(), V, pair, rows["day"].to_numpy() - WEEK52)
    tmp["_k"] = pair * 8 + rows["surf"].to_numpy()
    for j in range(3):
        tmp[f"_v{j}"] = V[:, j]
    sur = C.asof_sums(tmp, ["_v0", "_v1", "_v2"], player="_k").to_numpy()
    return {"car": car, "dec": dec[HALF_LIFE], "b52": bef, "sur": sur, "pair": pair}


# ------------------------------------------------------------------------------------------------
# Elo variants (Stage 1's pass with each update weighted)

def weighted_elo_pass(week, event, rnd, a, b, a_won, surf, upd, weight, n_players: int, k0: float, offset: float,
                      shape: float) -> np.ndarray:
    """stage1_baselines.elo_pass with each update multiplied by the match's weight (the margin-aware Elo of Angelini,
    Candila and De Angelis, 2022). With every weight 1 it is Stage 1's pass exactly (a test shows it)."""
    R = [B.START] * n_players
    N = [0] * n_players
    RS = [[B.START] * n_players for _ in B.SURFACES]
    NS = [[0] * n_players for _ in B.SURFACES]
    out = np.full((len(week), 8), np.nan)
    lo: dict = {}
    ls: dict = {}
    cur = None
    for i in range(len(week)):
        if week[i] != cur:
            for (p, _), st in lo.items():
                R[p] += st[0] + st[3]
                N[p] += st[1] + st[4]
            for (p, _, s), st in ls.items():
                RS[s][p] += st[0] + st[3]
                NS[s][p] += st[1] + st[4]
            lo.clear()
            ls.clear()
            cur = week[i]
        e, r, s, pa, pb = event[i], rnd[i], surf[i], a[i], b[i]
        xa = lo.get((pa, e))
        if xa is None:
            xa = lo[(pa, e)] = [0.0, 0, r, 0.0, 0]
        elif xa[2] < r:
            xa[0] += xa[3]; xa[1] += xa[4]; xa[2] = r; xa[3] = 0.0; xa[4] = 0
        xb = lo.get((pb, e))
        if xb is None:
            xb = lo[(pb, e)] = [0.0, 0, r, 0.0, 0]
        elif xb[2] < r:
            xb[0] += xb[3]; xb[1] += xb[4]; xb[2] = r; xb[3] = 0.0; xb[4] = 0
        ra, rb, na, nb = R[pa] + xa[0], R[pb] + xb[0], N[pa] + xa[1], N[pb] + xb[1]
        out[i, 0], out[i, 1], out[i, 2], out[i, 3] = ra, rb, na, nb
        do_s = s >= 0
        if do_s:
            ya = ls.get((pa, e, s))
            if ya is None:
                ya = ls[(pa, e, s)] = [0.0, 0, r, 0.0, 0]
            elif ya[2] < r:
                ya[0] += ya[3]; ya[1] += ya[4]; ya[2] = r; ya[3] = 0.0; ya[4] = 0
            yb = ls.get((pb, e, s))
            if yb is None:
                yb = ls[(pb, e, s)] = [0.0, 0, r, 0.0, 0]
            elif yb[2] < r:
                yb[0] += yb[3]; yb[1] += yb[4]; yb[2] = r; yb[3] = 0.0; yb[4] = 0
            sa, sb, nsa, nsb = RS[s][pa] + ya[0], RS[s][pb] + yb[0], NS[s][pa] + ya[1], NS[s][pb] + yb[1]
            out[i, 4], out[i, 5], out[i, 6], out[i, 7] = sa, sb, nsa, nsb
        if upd[i]:
            wgt = upd[i] * weight[i]   # level layer (LLE_LAYER): upd[i] True or w
            res = 1.0 if a_won[i] else 0.0
            surprise = res - 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            xa[3] += wgt * k0 / (na + offset) ** shape * surprise
            xb[3] -= wgt * k0 / (nb + offset) ** shape * surprise
            xa[4] += upd[i]   # level layer (LLE_LAYER)
            xb[4] += upd[i]
            if do_s:
                surprise = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))
                ya[3] += wgt * k0 / (nsa + offset) ** shape * surprise
                yb[3] -= wgt * k0 / (nsb + offset) ** shape * surprise
                ya[4] += upd[i]   # level layer (LLE_LAYER)
                yb[4] += upd[i]
    return out


def winner_shares(rows: pd.DataFrame) -> dict:
    """Per match: the winner's share of the games (from the score) and of the points (from the box score; the games'
    share where there is none). Missing where the score has no games."""
    a = rows.iloc[0::2]
    won_a = a["won"].to_numpy()
    g_a = a["games_won_n"].to_numpy(dtype="float64")
    g_d = a["games_won_d"].to_numpy(dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        ga = np.where(g_d > 0, g_a / g_d, np.nan)
        games = np.where(won_a, ga, 1 - ga)
        p_a = a["tpw_n"].to_numpy(dtype="float64") / np.where(a["tpw_d"].to_numpy(dtype="float64") > 0,
                                                              a["tpw_d"].to_numpy(dtype="float64"), np.nan)
        pts = np.where(np.isfinite(p_a), np.where(won_a, p_a, 1 - p_a), games)
    return {"games": games, "points": pts}


def elo_scales(rows: pd.DataFrame) -> tuple[dict, list]:
    """The weighted Elos' scale: the mean winner's share (games; points) over the rated matches of 2010-2018, per
    tour, so that the weights average one there."""
    shares = winner_shares(rows)
    a = rows.iloc[0::2]
    upd = a["status"].isin(B.UPDATES["ret"]).to_numpy()
    yrs = a["year"].isin(list(K_YEARS)).to_numpy()
    out, recs = {}, []
    for kind, sh in shares.items():
        for tour in C.TOURS:
            base = upd & yrs & np.isfinite(sh) & (a["tour"].to_numpy() == tour)
            out[(kind, tour)] = float(sh[base].mean())
            recs.append({"kind": "weighted Elo scale", "stat": f"elo_{kind}", "tour": tour, "surface": "all",
                         "years": "2010-2018", "value": out[(kind, tour)], "n": int(base.sum()),
                         "note": "the mean winner's share over the rated matches; a match's weight is its share over it "
                                 "(1 where the score has no games)"})
    return out, recs


def elo_variants(rows: pd.DataFrame, scales: dict) -> dict:
    """The games- and points-weighted surface Elo: Stage 1's frozen constants (retirements counted), each update
    multiplied by the winner's share over the scale (elo_scales, from the full history). Returns per match each
    player's pre-match overall and surface ratings (stage1_baselines.elo_pass's columns) and the surface weight."""
    summ = json.loads(BASE_SUMMARY.read_text(encoding="utf-8"))
    chosen = {(c["tour"], c["rule"]): c for c in summ["chosen"]}
    shares = winner_shares(rows)
    a = rows.iloc[0::2].reset_index(drop=True)
    upd = a["status"].isin(B.UPDATES["ret"]).to_numpy()
    out = {}
    for kind, share in shares.items():
        block = np.full((len(a), 8), np.nan)
        for tour in C.TOURS:
            idx = np.flatnonzero(a["tour"].eq(tour).to_numpy())
            if not len(idx):
                continue
            t = a.iloc[idx].reset_index(drop=True)
            k = chosen[(tour, "ret")]
            sh = share[idx]
            wgt = np.where(np.isfinite(sh), sh / scales[(kind, tour)], 1.0)
            h = elo_inputs(t)
            block[idx] = weighted_elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"],
                                           _LLE.elo_weights(t, upd[idx].tolist()), wgt.tolist(), h["n_players"], k["k0"], k["offset"], k["shape"])   # level layer (LLE_LAYER)
            out[(kind, tour, "w")] = k["w"]
        out[kind] = block
    return out


def elo_inputs(t: pd.DataFrame) -> dict:
    """stage1_baselines.history_arrays from one tour's rows of side A (player ids from A's and B's rows)."""
    m = pd.DataFrame({"tournament_date": t["tournament_date"], "tournament_id": t["tournament_id"],
                      "round_order": t["round_order"], "player_a_id": t["player_id"], "player_b_id": t["opponent_id"],
                      "a_won": t["won"], "surface": t["surface"]})
    return B.history_arrays(m)


# ------------------------------------------------------------------------------------------------
# Big-point play on return (Grand Slam point by point)

def pbp_history(rows: pd.DataFrame) -> pd.DataFrame:
    """Stage 2's per-match big-point measure on return (importance-weighted minus plain return points won), each file
    player linked to a Stage 0 id within the same Slam's main draw (stage4_candidates.link_in_event, the plan's link)."""
    p = pd.read_parquet(PBP_PLAYERS, columns=["match_id", "tour", "player", "r_n", "r_won", "r_w", "r_wwon"])
    p["year"] = p["match_id"].str.slice(0, 4).astype(int)
    slam = {"ausopen": "australian open", "frenchopen": "roland garros", "wimbledon": "wimbledon", "usopen": "us open"}
    p["slam"] = p["match_id"].str.split("-").str[1].map(slam)
    gs = rows[rows["level"].eq("GS") & ~rows["qualifying"].astype(bool)][["tour", "year", "tournament_name", "day",
                                                                          "player_id", "pcode"]]
    gs = gs.assign(slam=gs["tournament_name"].str.lower())
    names = C.load_match_players(["match_id", "player_id", "player_name"], with_order=False).drop_duplicates("player_id").set_index("player_id")["player_name"]
    gs = gs.assign(player_name=gs["player_id"].map(names))
    days = gs.drop_duplicates(["tour", "year", "slam"])[["tour", "year", "slam", "day"]]
    p = p.merge(days, on=["tour", "year", "slam"], how="left")
    draw = {k: [(pid, P.name_parts(nm)[0]) for pid, nm in g[["player_id", "player_name"]].drop_duplicates().itertuples(index=False)]
            for k, g in gs.groupby(["tour", "year", "slam"])}
    p["player_id"] = [P.link_in_event(nm, draw.get((t, y, s), [])) for nm, t, y, s in
                      p[["player", "tour", "year", "slam"]].itertuples(index=False)]
    p = p[p["player_id"].notna() & p["day"].notna() & (p["r_w"] > 0) & (p["r_n"] > 0)].copy()
    pc = pd.Series(rows["pcode"].to_numpy(), index=rows["player_id"].to_numpy())
    pc = pc[~pc.index.duplicated()]
    p["pcode"] = pc.reindex(p["player_id"]).to_numpy().astype("int64")
    p["value"] = p["r_wwon"] / p["r_w"] - p["r_won"] / p["r_n"]
    p["day"] = p["day"].astype("int64")
    return p[["tour", "year", "day", "pcode", "player_id", "value"]].reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# The state every feature reads, per row

def state(rows: pd.DataFrame, ctx: dict, xd: dict, pbp: pd.DataFrame, elo_w: dict) -> dict:
    """Everything per row that a feature reads from the past: history sums, meetings, the previous match, activity and
    load, Elo's change, and the big-point sums. One pass of each kind over the whole history."""
    n = len(rows)
    S: dict = {"hist": history_sums(rows, xd, ctx)}
    log("  history sums done")
    played = rows["played"].to_numpy()
    day, pcode = rows["day"].to_numpy(), rows["pcode"].to_numpy()
    rules = deciding_rules(rows)
    bo5 = best_of_five(rows, ctx.get("format_from", "scheduled"))
    S["bo5"], S["rule"] = bo5, rules
    S["format"] = scheduled_format(rows)["format"].to_numpy()
    # the iid model's chance from each match's pre-match Stage 3 ratings (the ratings feature; the adjusted h2h)
    ps_own = expit(rows["mu_logit"].to_numpy() + rows["serve_own"].to_numpy() - rows["return_opp"].to_numpy())
    ps_opp = expit(rows["mu_logit"].to_numpy() + rows["serve_opp"].to_numpy() - rows["return_own"].to_numpy())
    p_iid = np.empty(n)
    p_iid[0::2] = iid_prob(ps_own[0::2], ps_opp[0::2], bo5[0::2], rules[0::2], S["format"][0::2])
    p_iid[1::2] = 1 - p_iid[0::2]
    S["p_iid_own"] = p_iid
    S["h2h"] = h2h_sums(rows, p_iid)
    log("  meetings done")
    # record against the opponent's hand: total points won against players with that hand
    hand = rows["hand"].to_numpy(dtype=object)
    hcode = np.select([hand == "R", hand == "L"], [1, 2], 0)
    S["hcode"] = hcode
    x, d, ok = xd["tpw"]
    mu = mu_of_rows(rows, ctx["means"]["tpw"])
    tmp = rows[["tournament_date", "tournament_id", "round_order"]].copy()
    tmp["_k"] = pcode.astype("int64") * 3 + opp(hcode)
    tmp["_x"], tmp["_d"] = np.where(ok, x - d * mu, 0.0), d
    S["vs_hand"] = C.asof_sums(tmp, ["_x", "_d"], player="_k").to_numpy()
    # activity and load
    minutes = rows["minutes"].to_numpy(dtype="float64")
    sets_total = rows["sets_won_d"].to_numpy(dtype="float64")
    main = np.isin(rows["level"].to_numpy(), MAIN_TOUR) & ~rows["qualifying"].to_numpy(dtype=bool)
    V = np.column_stack([played.astype("float64"), (played & np.isnan(minutes)).astype("float64"),
                         np.where(played & ~np.isnan(minutes), minutes, 0.0),
                         (played & np.isnan(sets_total)).astype("float64"),
                         np.where(played & ~np.isnan(sets_total), sets_total, 0.0),
                         (played & main).astype("float64")])
    tmp = rows[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    for j in range(V.shape[1]):
        tmp[f"_v{j}"] = V[:, j]
    S["act_car"] = C.asof_sums(tmp, [f"_v{j}" for j in range(V.shape[1])]).to_numpy()
    for w in WINDOWS + (WEEK52,):
        S[f"act_bef{w}"] = T.sums_before(pcode, day, V, pcode, day - w)
    season_key = (pcode.astype("int64") * 20 + (rows["year"].to_numpy() - 2009)) * 8 + rows["surf"].to_numpy()
    tmp = rows[["tournament_date", "tournament_id", "round_order"]].copy()
    tmp["_k"], tmp["_v"] = season_key, played.astype("float64")
    S["season_surface_played"] = C.asof_sums(tmp, ["_v"], player="_k")["_v"].to_numpy()
    # the previous match: played (rest, fatigue) and scheduled (an early end)
    S["prev_played"] = prev_visible(rows, played)
    S["prev_sched"] = prev_visible(rows, np.ones(n, dtype=bool))
    # Elo's change: the first played match on or after 26 (52) weeks before this event
    o = np.lexsort((rows["order"].to_numpy(), day, pcode))
    o = o[played[o]]
    keys = pcode[o].astype("int64") * 1_000_000 + day[o]
    first_day = pd.Series(day[played]).groupby(pcode[played]).min()
    fday = first_day.reindex(pcode).to_numpy()
    for name, dd in ELO_CHANGE.items():
        pos = np.searchsorted(keys, pcode.astype("int64") * 1_000_000 + (day - dd), side="left")
        j = o[np.minimum(pos, len(o) - 1)]
        ok = (pos < len(o)) & (pcode[j] == pcode) & (fday <= day - dd)
        S[name] = np.where(ok, j, -1)
    # big-point play on return: earlier Grand Slams in the point-by-point files
    pv = pbp[["value"]].to_numpy()
    S["pbp"] = T.sums_before(pbp["pcode"].to_numpy(), pbp["day"].to_numpy(), np.column_stack([pv[:, 0], np.ones(len(pbp))]),
                             pcode, day)
    S["elo_w"] = elo_w
    return S


# ------------------------------------------------------------------------------------------------
# Lag: each history read as it stood at the player's previous match of that history

def lag_state(rows: pd.DataFrame, S: dict, xd: dict, only: set | None = None) -> dict:
    """The state one match later: every sum is read at the player's previous row of the same history (the previous
    match carrying the statistic; for the same-surface form, the previous one on this surface; for meetings, the
    previous meeting); the 52-week window keeps this match's dates; decayed sums are re-aged to this match's date."""
    L = dict(S)
    day, surf = rows["day"].to_numpy(), rows["surf"].to_numpy()
    pcode = rows["pcode"].to_numpy().astype("int64")
    need = None if only is None else only
    H = S["hist"]
    LH = {}
    for s in HIST:
        x, d, ok = xd[s]
        if need is not None and s not in need:
            for k in ("car", "dec", "b52", "sur"):
                for what in ("xc", "d", "xac"):
                    LH[(k, s, what)] = H[(k, s, what)]
            continue
        mask = ok & (d > 0)
        prev = prev_visible(rows, mask)
        prev_sur = prev_visible(rows, mask, pcode * 8 + surf)
        age = np.where(prev >= 0, day - day[np.maximum(prev, 0)], 0)
        inside = (prev >= 0) & (age <= WEEK52)
        for what in ("xc", "d", "xac"):
            car = H[("car", s, what)]
            LH[("car", s, what)] = at(car, prev)
            LH[("dec", s, what)] = at(H[("dec", s, what)], prev) * np.exp2(-age / (7.0 * HALF_LIFE))
            # the 52-week window of this match, with the history cut at the previous match: career at the previous
            # match less what lies before the window (all of it is earlier than that match when the match lies inside
            # the window); nothing when the previous match is older than the window
            LH[("b52", s, what)] = np.where(inside, H[("b52", s, what)], at(car, prev))
            LH[("sur", s, what)] = at(H[("sur", s, what)], prev_sur)
    L["hist"] = LH
    # meetings: the previous meeting with the same opponent (and on the same surface)
    h = S["h2h"]
    meet = rows["played"].to_numpy()
    pm = prev_visible(rows, meet, h["pair"])
    pms = prev_visible(rows, meet, h["pair"] * 8 + surf)
    agem = np.where(pm >= 0, day - day[np.maximum(pm, 0)], 0)
    L["h2h"] = {"car": at(h["car"], pm), "dec": at(h["dec"], pm) * np.exp2(-agem / (7.0 * HALF_LIFE))[:, None],
                "b52": np.where(((pm >= 0) & (agem <= WEEK52))[:, None], h["b52"], at(h["car"], pm)),
                "sur": at(h["sur"], pms), "pair": h["pair"]}
    # against the opponent's hand: the previous row against the same hand
    x, d, ok = xd["tpw"]
    pv = prev_visible(rows, ok & (d > 0), pcode * 3 + opp(S["hcode"]))
    L["vs_hand"] = at(S["vs_hand"], pv)
    # activity, load, the previous match, Elo's change: as at the previous match played
    pp = S["prev_played"]
    L["act_car"] = at(S["act_car"], pp)
    for w in WINDOWS + (WEEK52,):
        L[f"act_bef{w}"] = at(S[f"act_bef{w}"], pp)
    L["season_surface_played"] = at(S["season_surface_played"], prev_visible(rows, rows["played"].to_numpy(),
                                                                            (pcode * 20 + (rows["year"].to_numpy() - 2009)) * 8 + surf))
    L["prev_played"] = at(S["prev_played"], pp, -1).astype("int64")
    L["prev_sched"] = at(S["prev_sched"], S["prev_sched"], -1).astype("int64")
    for name in ELO_CHANGE:
        L[name] = at(S[name], pp, -1).astype("int64")
    L["lag_src"] = pp
    # big-point sums: as before the player's previous Grand Slam in the files
    L["pbp"] = S["pbp_lag"] if "pbp_lag" in S else S["pbp"]
    L["lagged"] = True
    return L


# ------------------------------------------------------------------------------------------------
# Assembly: the features of each pool match from the state

def form_value(rows: pd.DataFrame, S: dict, ctx: dict, stat: str, form: str) -> tuple[np.ndarray, np.ndarray]:
    """Per row: the player's value of ``stat`` in ``form`` (a shrunk share, a count per game or a rate around zero) and
    whether it exists (at least one earlier unit inside the form's window)."""
    H = S["hist"]
    tour = rows["tour"].to_numpy()
    surf_names = rows["surface"].to_numpy()
    if form == "adjusted":
        key = f"{stat}_adj"
        sx, sd = H[("car", stat, "xac")], H[("car", stat, "d")]
        mu = mu_of_rows(rows, ctx["means"][key])
        k = k_for(ctx, key, tour)
        exists = H[("car", stat, "d")] > 0
    elif form == "surface":
        sx, sd = H[("sur", stat, "xc")], H[("sur", stat, "d")]
        mu = mu_of_rows(rows, ctx["means"][stat])
        k = np.full(len(rows), np.inf)
        for s in SURF:
            m = surf_names == s
            k[m] = k_for(ctx, stat, tour[m], s)
        exists = (sd > 0) & (rows["surf"].to_numpy() > 0)
    else:
        if form == "career":
            sx, sd = H[("car", stat, "xc")], H[("car", stat, "d")]
            exists = sd > 0
        elif form == "52 weeks":
            sx = H[("car", stat, "xc")] - H[("b52", stat, "xc")]
            sd = H[("car", stat, "d")] - H[("b52", stat, "d")]
            exists = sd > 0.5
        elif form == "decayed":
            sx, sd = H[("dec", stat, "xc")], H[("dec", stat, "d")]
            exists = H[("car", stat, "d")] > 0
        else:
            raise ValueError(form)
        mu = mu_of_rows(rows, ctx["means"][stat])
        k = k_for(ctx, stat, tour)
    with np.errstate(invalid="ignore", divide="ignore"):
        kk = np.where(np.isfinite(k), k, 0.0)
        val = np.where(np.isfinite(k), mu + sx / (sd + kk), mu)
    return val, exists


def on_scale(stat: str, v: np.ndarray) -> np.ndarray:
    """A form value on the feature's scale: log-odds for a share, log for a count per game, itself around zero."""
    if stat in LINEAR:
        return v
    if stat in POISSON:
        return np.log(np.maximum(v, SHARE_CLIP))
    return safe_logit(v)


def build(rows: pd.DataFrame, ctx: dict, S: dict, pool: np.ndarray, cand: pd.DataFrame,
          only: set | None = None) -> dict:
    """Every candidate x form's inputs for the pool matches (A's row minus B's): {column: array over pool matches},
    missing where the feature does not exist. ``only``: candidate ids to build (the leak check builds a few)."""
    A = np.flatnonzero(pool) * 2          # A's row of each pool match
    Bi = A + 1
    tour_rows = rows["tour"].to_numpy()
    out = {}

    def want(cid):
        return only is None or cid in only

    def pair(v, e):
        return np.where(e[A] & e[Bi], v[A] - v[Bi], np.nan)

    lagged = S.get("lagged", False)
    # per-match statistics in five forms
    for c in cand[cand["group"].eq("statistic")].itertuples(index=False):
        if not want(c.id):
            continue
        for form in c.forms.split(";"):
            if c.id == "h2h":
                out[f"h2h|{form}"] = h2h_feature(rows, S, ctx, form, A)
                continue
            v, e = form_value(rows, S, ctx, c.id, form)
            out[f"{c.id}|{form}"] = pair(on_scale(c.id, v), e)
    # matchups
    for c in cand[cand["group"].eq("matchup")].itertuples(index=False):
        if not want(c.id):
            continue
        for form in c.forms.split(";"):
            out[f"{c.id}|{form}"] = matchup(rows, S, ctx, c.id, form, A, Bi)
    # single features
    singles = single_features(rows, S, ctx, A, Bi, want, lagged)
    out.update(singles)
    return out


def h2h_feature(rows: pd.DataFrame, S: dict, ctx: dict, form: str, A: np.ndarray) -> np.ndarray:
    """A's record against B: the log-odds of A's shrunk share of their earlier meetings (toward one half, with the
    match-win constant); adjusted: meetings won above the iid model's expectation, per meeting, shrunk."""
    h = S["h2h"]
    tour = rows["tour"].to_numpy()[A]
    surf_names = rows["surface"].to_numpy()[A]
    if form == "career":
        s = h["car"][A]
    elif form == "52 weeks":
        s = h["car"][A] - h["b52"][A]
    elif form == "decayed":
        s = h["dec"][A]
    elif form == "surface":
        s = h["sur"][A]
    else:
        s = h["car"][A]
    won, n, over = s[:, 0], s[:, 1], s[:, 2]
    if form == "surface":
        k = np.full(len(A), np.nan)
        for sname in SURF:
            m = surf_names == sname
            k[m] = k_for(ctx, "win", tour[m], sname)
        k = np.where(np.isfinite(k), k, 1e12)
        exists = (n > 0.5) & (rows["surf"].to_numpy()[A] > 0)
    else:
        k = k_for(ctx, "win", tour)
        exists = (n > 0.5) if form != "decayed" else (h["car"][A][:, 1] > 0.5)
    if form == "adjusted":
        return np.where(exists, over / (n + k), np.nan)
    return np.where(exists, safe_logit((won + 0.5 * k) / (n + k)), np.nan)


def matchup(rows: pd.DataFrame, S: dict, ctx: dict, cid: str, form: str, A: np.ndarray, Bi: np.ndarray) -> np.ndarray:
    """A's serve against B's return and the reverse, both statistics in the same form (candidates.md, section 2).
    Each pair is combined on the log-odds scale around the tour's average on the surface; points, games and the
    serve point from its parts then go through the iid model with the match's format (the feature: the log-odds of
    A's chance); break points are the log-odds sum."""
    stats = MATCHUPS[cid]
    val, ex = {}, {}
    for s in stats:
        v, e = form_value(rows, S, ctx, s, form)
        val[s], ex[s] = v, e
    exists = np.all([ex[s][A] & ex[s][Bi] for s in stats], axis=0)
    mkey = (lambda s: f"{s}_adj") if form == "adjusted" else (lambda s: s)

    def comb(srv_stat, ret_stat, srv_rows, ret_rows):
        """The server's expected rate against this returner: log-odds mu + (log-odds of the server's rate - log-odds mu)
        - (log-odds of the returner's rate - log-odds (1 - mu)), mu the tour's average of the serve statistic on the
        surface."""
        mu = np.clip(mu_of_rows(rows, ctx["means"][mkey(srv_stat)])[srv_rows], SHARE_CLIP, 1 - SHARE_CLIP)
        return expit(logit(mu) + (safe_logit(val[srv_stat][srv_rows]) - logit(mu))
                     - (safe_logit(val[ret_stat][ret_rows]) - logit(1 - mu)))
    bo5, rule, fmt = S["bo5"][A], S["rule"][A], S["format"][A]
    if cid == "mu_bp":
        f = (safe_logit(val["bp_saved"][A]) - safe_logit(val["bp_conv"][Bi])) - (safe_logit(val["bp_saved"][Bi]) - safe_logit(val["bp_conv"][A]))
        return np.where(exists, f, np.nan)
    if cid == "mu_points":
        pa, pb = comb("spw", "rpw", A, Bi), comb("spw", "rpw", Bi, A)
    elif cid == "mu_games":
        ha, hb = comb("hold", "brk", A, Bi), comb("hold", "brk", Bi, A)
        pa, pb = serve_rate_for_hold(ha), serve_rate_for_hold(hb)
    else:   # the serve point from its parts
        fi_a, fi_b = np.clip(val["first_in"][A], 0, 1), np.clip(val["first_in"][Bi], 0, 1)
        pa = fi_a * comb("first_won", "rpw_first", A, Bi) + (1 - fi_a) * comb("second_won", "rpw_second", A, Bi)
        pb = fi_b * comb("first_won", "rpw_first", Bi, A) + (1 - fi_b) * comb("second_won", "rpw_second", Bi, A)
    p = np.full(len(A), np.nan)
    ok = exists & np.isfinite(pa) & np.isfinite(pb)
    if ok.any():
        p[ok] = iid_prob(pa[ok], pb[ok], bo5[ok], rule[ok], fmt[ok])
    return np.where(ok, safe_logit(p), np.nan)


def single_features(rows: pd.DataFrame, S: dict, ctx: dict, A: np.ndarray, Bi: np.ndarray, want, lagged: bool) -> dict:
    """The features with one form (candidates.md, section 3.3)."""
    out = {}
    n = len(rows)
    tour = rows["tour"].to_numpy()
    day = rows["day"].to_numpy()
    src = S.get("lag_src") if lagged else None

    def lagv(v, fill=np.nan):
        """A per-row value as it stood at the player's previous match played (lag), or as it is."""
        return at(v, src, fill) if src is not None else v

    def diff(v, e=None):
        e = np.isfinite(v) if e is None else (e & np.isfinite(v))
        return np.where(e[A] & e[Bi], v[A] - v[Bi], np.nan)

    # rankings (as of the tournament's start; unranked as in Stage 1)
    if want("rank") or want("rank_points") or want("rank_elo_gap"):
        rk = filled_rank(rows)
        pts = np.clip(np.nan_to_num(rows["rank_points"].to_numpy(dtype="float64"), nan=0.0), 0, None)
        rk_l, pts_l = lagv(rk), lagv(pts)
        if want("rank"):
            out["rank|single"] = np.log(rk_l[Bi]) - np.log(rk_l[A])
        if want("rank_points"):
            out["rank_points|single"] = np.log1p(pts_l[A]) - np.log1p(pts_l[Bi])
        if want("rank_elo_gap"):
            gap = elo_rank_gap(rows, rk, S)
            out["rank_elo_gap|single"] = diff(lagv(gap))
    # Elo variants weighted by the margin
    for cid, kind in (("elo_games", "games"), ("elo_points", "points")):
        if not want(cid):
            continue
        blk = S["elo_w"][kind]
        w = np.where(tour[A] == "atp", S["elo_w"][(kind, "atp", "w")], S["elo_w"][(kind, "wta", "w")])
        ov = np.column_stack([blk[:, 0], blk[:, 1]]).reshape(-1)
        sv = np.column_stack([blk[:, 4], blk[:, 5]]).reshape(-1)
        if lagged:
            ov, sv = lag_elo(rows, ov, sv)
        sv = np.where(np.isnan(sv), ov, sv)
        ra = (1 - w) * ov[A] + w * sv[A]
        rb = (1 - w) * ov[Bi] + w * sv[Bi]
        out[f"{cid}|single"] = safe_logit(B.expected(ra, rb))
    # Stage 3's ratings
    if want("rating_serve") or want("rating_return") or want("rating_matchup"):
        so, ro = rows["serve_own"].to_numpy(), rows["return_own"].to_numpy()
        if lagged:
            upd_prev = prev_visible(rows, rows["rating_update"].to_numpy())
            # the ratings before the player's previous rating match: its pre-match values there
            so, ro = at(so, upd_prev, 0.0), at(ro, upd_prev, 0.0)
            so = np.where(upd_prev >= 0, so, rows["serve_own"].to_numpy())
            ro = np.where(upd_prev >= 0, ro, rows["return_own"].to_numpy())
        if want("rating_serve"):
            out["rating_serve|single"] = so[A] - so[Bi]
        if want("rating_return"):
            out["rating_return|single"] = ro[A] - ro[Bi]
        if want("rating_matchup"):
            mu = rows["mu_logit"].to_numpy()
            pa, pb = expit(mu[A] + so[A] - ro[Bi]), expit(mu[A] + so[Bi] - ro[A])
            out["rating_matchup|single"] = safe_logit(iid_prob(pa, pb, S["bo5"][A], S["rule"][A], S["format"][A]))
    # Elo's change over 6 and 12 months (overall Elo, retirements counted)
    for cid in ELO_CHANGE:
        if not want(cid):
            continue
        j = S[cid]
        now = rows["elo_own"].to_numpy(dtype="float64")
        if lagged:
            now = at(now, S["lag_src"], np.nan)
        then = at(rows["elo_own"].to_numpy(dtype="float64"), j, np.nan)
        out[f"{cid}|single"] = diff(np.where(j >= 0, now - then, np.nan))
    # the player
    if want("age"):
        age = lagv(rows["age"].to_numpy(dtype="float64"))
        ok = (age >= AGE_RANGE[0]) & (age <= AGE_RANGE[1])
        a1 = np.where(ok, age - AGE_CENTRE, np.nan)
        out["age|single"] = diff(a1)
        out["age|single|2"] = diff(a1 ** 2)
    if want("height"):
        out["height|single"] = diff(rows["height"].to_numpy(dtype="float64"))
    hand = rows["hand"].to_numpy(dtype=object)
    known = np.isin(hand, ["R", "L"])
    if want("lefty"):
        out["lefty|single"] = diff(np.where(known, (hand == "L").astype("float64"), np.nan))
    if want("vs_hand"):
        vs = S["vs_hand"]
        x, d, ok = None, None, None
        mu = mu_of_rows(rows, ctx["means"]["tpw"])
        k = k_for(ctx, "tpw", tour)
        H = S["hist"]
        car_x, car_d = H[("car", "tpw", "xc")], H[("car", "tpw", "d")]
        v_vs = mu + vs[:, 0] / (vs[:, 1] + k)
        v_all = mu + car_x / (car_d + k)
        e = known & opp(known) & (vs[:, 1] > 0)
        out["vs_hand|single"] = diff(safe_logit(v_vs) - safe_logit(v_all), e)
    # activity, rest and fatigue
    car = S["act_car"]
    if want("played_career"):
        out["played_career|single"] = diff(np.log1p(car[:, 0]))
    if want("played_52w"):
        out["played_52w|single"] = diff(np.log1p(car[:, 0] - S[f"act_bef{WEEK52}"][:, 0]))
    pp = S["prev_played"]
    if want("days_since"):
        gap = np.where(pp >= 0, (day - day[np.maximum(pp, 0)]).astype("float64"), np.nan)
        if lagged:
            gap = lag_prev_gap(rows, S)
        out["days_since|single"] = diff(np.log1p(gap))
    if want("last_early"):
        ps = S["prev_sched"]
        st = rows["status"].to_numpy()
        won = rows["won"].to_numpy()
        early = np.isin(st[np.maximum(ps, 0)], ["retired", "walkover"]) & (ps >= 0)
        own = np.where(ps >= 0, (early & ~won[np.maximum(ps, 0)]).astype("float64"), np.nan)
        theirs = np.where(ps >= 0, (early & won[np.maximum(ps, 0)]).astype("float64"), np.nan)
        out["last_early|single"] = diff(own)
        out["last_early|single|2"] = diff(theirs)
    minutes = rows["minutes"].to_numpy(dtype="float64")
    sets_total = rows["sets_won_d"].to_numpy(dtype="float64")
    if want("prev_minutes"):
        v = np.where(pp >= 0, minutes[np.maximum(pp, 0)], np.nan)
        out["prev_minutes|single"] = diff(np.log1p(v))
    if want("prev_sets"):
        v = np.where(pp >= 0, sets_total[np.maximum(pp, 0)], np.nan)
        out["prev_sets|single"] = diff(np.log1p(v))
    for w in WINDOWS:
        win = car - S[f"act_bef{w}"]
        if want(f"minutes_{w}d"):
            out[f"minutes_{w}d|single"] = diff(np.where(win[:, 1] < 0.5, np.log1p(np.maximum(win[:, 2], 0)), np.nan))
        if want(f"sets_{w}d"):
            out[f"sets_{w}d|single"] = diff(np.where(win[:, 3] < 0.5, np.log1p(np.maximum(win[:, 4], 0)), np.nan))
    if want("surface_first"):
        sf = (S["season_surface_played"] < SURFACE_FIRST).astype("float64")
        out["surface_first|single"] = diff(np.where(rows["surf"].to_numpy() > 0, sf, np.nan))
    if want("recent_level"):
        w52 = car - S[f"act_bef{WEEK52}"]
        share = (w52[:, 5] + 0.5) / (w52[:, 0] + 1.0)
        out["recent_level|single"] = diff(np.where(w52[:, 0] > 0.5, logit(share), np.nan))
    # place and entry
    if want("home"):
        ec = pd.Series(S["event_country"]).astype(object)
        pc = CTRY.player_country(rows["country"]).astype(object)
        ok = (ec.notna() & pc.notna()).to_numpy()
        same = (ec.fillna("?").to_numpy() == pc.fillna("!").to_numpy())
        out["home|single"] = diff(np.where(ok, same.astype("float64"), np.nan))
    for k_, codes in ENTRY_TYPES.items():
        cid = f"entry_{k_}"
        if not want(cid):
            continue
        rec = S[f"entry_ok_{k_}"]
        v = np.where(rec, np.isin(rows["entry"].fillna("").to_numpy(dtype=object), codes).astype("float64"), np.nan)
        out[f"{cid}|single"] = diff(v)
    # format and level
    if want("best_of_five"):
        out["best_of_five|single"] = np.where(tour[A] == "atp", S["bo5"][A].astype("float64"), np.nan)
    # big-point play on return
    if want("bigpoint_return"):
        sx = S["pbp"]
        kk = np.where(tour == "atp", ctx["bigpoint"]["atp"]["K"], ctx["bigpoint"]["wta"]["K"])
        mm = np.where(tour == "atp", ctx["bigpoint"]["atp"]["mean"], ctx["bigpoint"]["wta"]["mean"])
        v = (sx[:, 0] + kk * mm) / (sx[:, 1] + kk)
        out["bigpoint_return|single"] = diff(v, sx[:, 1] > 0.5)
    return out


def filled_rank(rows: pd.DataFrame) -> np.ndarray:
    """Each row's rank, an unranked player given the rank one below the lowest seen on the tour in earlier seasons
    (Stage 1's rule, stage1_baselines.unranked_rank)."""
    a = rows.iloc[0::2]
    m = pd.DataFrame({"match_id": a["match_id"].to_numpy(), "tour": a["tour"].to_numpy(), "year": a["year"].to_numpy()})
    r = pd.DataFrame({"rank_a": a["rank"].to_numpy(dtype="float64"), "rank_b": rows["rank"].to_numpy(dtype="float64")[1::2]})
    unr = B.unranked_rank(m, r)
    fill = np.array([unr[(t, int(y))] for t, y in zip(rows["tour"].to_numpy(), rows["year"].to_numpy())])
    rk = rows["rank"].to_numpy(dtype="float64")
    return np.where(np.isnan(rk), fill, rk)


def blended_rating(rows: pd.DataFrame, ov: np.ndarray, sv: np.ndarray) -> np.ndarray:
    summ = json.loads(BASE_SUMMARY.read_text(encoding="utf-8"))
    w = {c["tour"]: c["w"] for c in summ["chosen"] if c["rule"] == "ret"}
    ww = np.where(rows["tour"].to_numpy() == "atp", w["atp"], w["wta"])
    return (1 - ww) * ov + ww * np.where(np.isnan(sv), ov, sv)


def elo_rank_gap(rows: pd.DataFrame, rk: np.ndarray, S: dict) -> np.ndarray:
    """Each player's surface-blended Elo rating minus the rating their ranking implies: a line of the rating on
    log(rank) fitted per tour on the evaluation-level player rows of earlier seasons (ranked players; 2010, history
    only, on itself, as Stage 1's unranked rank), applied with the filled rank."""
    rating = blended_rating(rows, rows["elo_own"].to_numpy(dtype="float64"), rows["elo_surf_own"].to_numpy(dtype="float64"))
    S["blended_rating"] = rating
    lr = np.log(rk)
    year, tour = rows["year"].to_numpy(), rows["tour"].to_numpy()
    fit_rows = rows["eval_level"].to_numpy() & rows["played"].to_numpy() & rows["rank"].notna().to_numpy()
    out = np.full(len(rows), np.nan)
    for t in C.TOURS:
        for y in np.unique(year[tour == t]):
            sel = fit_rows & (tour == t) & (year < y)
            if sel.sum() < 2:                    # the first season of the history: fitted on itself
                sel = fit_rows & (tour == t) & (year == y)
            b1, b0 = np.polyfit(lr[sel], rating[sel], 1)
            m = (tour == t) & (year == y)
            out[m] = rating[m] - (b0 + b1 * lr[m])
    return out


def lag_elo(rows: pd.DataFrame, ov: np.ndarray, sv: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Elo ratings one rated match later: the overall rating before the player's previous rated match; the surface
    rating before their previous rated match on this surface."""
    rated = rows["played"].to_numpy()
    pcode = rows["pcode"].to_numpy().astype("int64")
    po = prev_visible(rows, rated)
    ps = prev_visible(rows, rated, pcode * 8 + rows["surf"].to_numpy())
    return np.where(po >= 0, ov[np.maximum(po, 0)], ov), np.where(ps >= 0, sv[np.maximum(ps, 0)], sv)


def lag_prev_gap(rows: pd.DataFrame, S: dict) -> np.ndarray:
    """Days between the previous match and the one before it (the rest feature one match later)."""
    day = rows["day"].to_numpy()
    p1 = S["prev_played"]                       # in a lagged state: the previous match's previous match
    p0 = S["lag_src"]                           # the previous match
    return np.where((p0 >= 0) & (p1 >= 0), (day[np.maximum(p0, 0)] - day[np.maximum(p1, 0)]).astype("float64"), np.nan)


def entry_masks(rows: pd.DataFrame) -> dict:
    """Where each entry type is scored (stage4_candidates.key_rows): an event whose main draw (qualifying) records
    entries, in a tour x level group x season cell where the type's code appears among such evaluation events; a
    qualifier or a lucky loser only in a main draw."""
    out = {}
    code = rows["entry"].notna().to_numpy()
    q = rows["qualifying"].to_numpy(dtype=bool)
    ev = pd.factorize(rows["tournament_id"].astype(str) + "|" + rows["tournament_date"].astype(str))[0]
    rec_main = pd.Series(code & ~q).groupby(ev).any().reindex(ev).to_numpy()
    rec_qual = pd.Series(code & q).groupby(ev).any().reindex(ev).to_numpy()
    rec = np.where(q, rec_qual, rec_main).astype(bool)
    entry = rows["entry"].fillna("").to_numpy(dtype=object)
    cell = (rows["tour"] + "|" + rows["group"] + "|" + rows["year"].astype(str)).to_numpy()
    evl = rows["evaluation"].to_numpy(dtype=bool)
    for k, codes in ENTRY_TYPES.items():
        has_code = np.isin(entry, codes)
        seen = pd.Series(has_code & rec & evl).groupby(cell).any()
        ok = seen.reindex(cell).fillna(False).to_numpy(dtype=bool)
        out[k] = rec & ok & (~q if k in ("q", "ll") else True)
    return out


# ------------------------------------------------------------------------------------------------
# Coverage reproduced against the plan's counts

def plan_key(c, form: str) -> str:
    w = P.FORM_WINDOW[form]
    if c.coverage == "hist":
        return f"hist:{c.stats}:{w}"
    if c.coverage == "h2h":
        return f"h2h:{w}"
    if c.coverage == "match":
        return f"match:{c.id}:{w}"
    return {"rank": "all", "always": "all", "ratings": "all", "home": "country_player", "entry": "entry_recorded",
            "pbp": "pbp", "hand": "hand"}.get(c.coverage, c.coverage)


def coverage_check(feat: pd.DataFrame, cand: pd.DataFrame) -> list:
    """Per candidate x form x tour: the evaluation matches on which the feature exists here, against the plan's count
    for the same key (stage4_candidates_coverage.csv, pooled over the scored years)."""
    cov = pd.read_csv(COVERAGE)
    ev = feat[feat["evaluation"]]
    out = []
    for c in cand.itertuples(index=False):
        for form in c.forms.split(";"):
            col = f"{c.id}|{form}"
            if col not in feat:
                continue
            key = plan_key(c, form)
            for tour in c.tours.split(";"):
                first = C.WTA_BOX_FROM if (tour == "wta" and c.wta_box_from_2019 == "yes") else C.EVAL_YEARS[0]
                e = ev[ev["tour"].eq(tour) & (ev["year"] >= first)]
                ex = e[col].notna()
                if f"{col}|2" in e:
                    ex &= e[f"{col}|2"].notna()
                t = cov[cov["key"].eq(key) & cov["tour"].eq(tour) & (cov["year"] >= first)]
                out.append({"id": c.id, "form": form, "tour": tour, "plan_key": key, "matches": int(len(e)),
                            "exists_here": int(ex.sum()), "plan_present": int(t["present"].sum()),
                            "plan_matches": int(t["matches"].sum())})
    return out


# ------------------------------------------------------------------------------------------------
# The probe cut by date, event and round

# what a match's play produces (perturbed for the cut's own round and everything after it) and what is known about a
# match before it starts (perturbed only for matches outside the protected set: the cut round's own pre-match values
# are inputs of its own features, as they should be)
OUTCOMES = ["won", "minutes", "spw_adj_n", "rpw_adj_n"] + [f"{r}_{x}" for r in C.RATES for x in ("n", "d")]
PRE_MATCH = ["rank", "rank_points", "age", "elo_own", "elo_surf_own", "serve_own", "return_own", "serve_opp", "return_opp"]
PROBE_ATOL = 1e-9      # as-of sums subtract a day's total from a running total, so a redrawn later value can move an
                       # earlier sum in its last bits; a leak moves a feature by orders of magnitude more


def probe(rows: pd.DataFrame, ctx: dict, cand: pd.DataFrame, pbp: pd.DataFrame, n_cuts: int = 4,
          seed: int = SEED) -> dict:
    """Black-box check of the time rule on a slice of real history, cut by date, event and round (as
    stage1_baselines.probe_by_round): at each cut match, what was played in every match the rule does not let it see
    (its own round and later rounds of its event, the week's other events, later weeks) is redrawn: results, box
    scores, scores, minutes, statuses, point-by-point values. The pre-match values (rankings, ages, pre-match ratings)
    of every match outside the protected set are redrawn too. Every feature is recomputed, the weighted Elos rerun on
    the redrawn results. The features of the matches of earlier weeks, and of the cut event's rounds up to and
    including the cut's, must not move."""
    rng = np.random.default_rng(seed)
    pool = pool_mask(rows)
    control = "leak_control|inclusive_wins"
    variants = {"plan": dict(ctx), "recorded_format": {**ctx, "format_from": "recorded"}}

    def leaky(r):
        """A positive control: career wins counted with the match itself (the commonest leak), A minus B."""
        tmp = r[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
        tmp["w"] = r["won"].to_numpy().astype("float64")
        s = C.asof_sums(tmp, ["w"])["w"].to_numpy() + tmp["w"].to_numpy()
        A = np.flatnonzero(pool) * 2
        return s[A] - s[A + 1]
    base = {}
    for vname, vctx in variants.items():
        b = build_all(rows, vctx, cand, pbp, pool)
        b[control] = leaky(rows)
        base[vname] = b
    names = sorted(base["plan"])
    real = np.array([k != control for k in names])
    week, ev, rnd = rows["day"].to_numpy()[0::2], rows["ev"].to_numpy()[0::2], rows["round_order"].to_numpy()[0::2]
    # cuts in the slice's last season: its first season fits the rank line and the unranked rank on itself (as Stage 1
    # does for 2010, history only), so a cut inside it would move them by design
    yr = rows["year"].to_numpy()[0::2]
    cand_idx = np.flatnonzero(pool & (yr == yr.max()))
    res = {"cuts": 0, "protected_checked": 0, "columns": int(real.sum()), "atol": PROBE_ATOL,
           "variants": {v: {"protected_changed": 0, "open_changed": 0, "control_protected_changed": 0,
                            "largest_protected_difference": 0.0, "changed_by_column": {}, "largest_by_column": {}}
                        for v in variants}}
    for c in rng.choice(cand_idx, size=min(n_cuts, len(cand_idx)), replace=False):
        later = (week > week[c]) | ((week == week[c]) & ((ev != ev[c]) | (rnd >= rnd[c])))
        keep = (week < week[c]) | ((week == week[c]) & (ev == ev[c]) & (rnd <= rnd[c]))
        pert = rows.copy()
        lr, after = np.repeat(later, 2), np.repeat(later & ~keep, 2)
        for cols, sel in ((OUTCOMES, lr), (PRE_MATCH, after)):
            for col in cols:
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
        redraw = np.repeat(lr[0::2] & (rng.random(len(later)) < 0.1), 2)
        st[redraw] = np.where(np.repeat(rng.random(len(later)) < 0.5, 2)[redraw], "retired", "completed")
        pert["status"] = st
        pert = prepare(pert)
        pbp_p = pbp.assign(value=np.where(pbp["day"].to_numpy() >= week[c], rng.normal(0, 0.05, len(pbp)), pbp["value"]))
        kp = keep[pool]
        res["cuts"] += 1
        res["protected_checked"] += int(kp.sum())
        for vname, vctx in variants.items():
            got = build_all(pert, vctx, cand, pbp_p, pool)
            got[control] = leaky(pert)
            B0 = np.column_stack([base[vname][k] for k in names])
            G = np.column_stack([got[k] for k in names])
            diff = ~np.isclose(G, B0, equal_nan=True, rtol=0, atol=PROBE_ATOL)
            gap = np.where(np.isfinite(G) & np.isfinite(B0) & kp[:, None], np.abs(G - B0), 0.0)
            r = res["variants"][vname]
            r["protected_changed"] += int((diff[:, real].any(axis=1) & kp).sum())
            r["open_changed"] += int((diff[:, real].any(axis=1) & ~kp).sum())
            r["control_protected_changed"] += int((diff[:, ~real].any(axis=1) & kp).sum())
            r["largest_protected_difference"] = max(r["largest_protected_difference"], float(gap[:, real].max()))
            for j, k in enumerate(names):
                ch = int((diff[:, j] & kp).sum())
                if real[j]:
                    r["largest_by_column"][k] = max(r["largest_by_column"].get(k, 0.0), float(gap[:, j].max()))
                    if ch:
                        r["changed_by_column"][k] = r["changed_by_column"].get(k, 0) + ch
            log(f"  probe cut {res['cuts']} ({vname}): protected changed {r['protected_changed']}, later changed "
                f"{r['open_changed']}, control caught at {r['control_protected_changed']}, largest protected difference "
                f"{r['largest_protected_difference']:.2e}")
    return res


# ------------------------------------------------------------------------------------------------

def pool_mask(rows: pd.DataFrame) -> np.ndarray:
    """Per match: an evaluation-level match of 2010 on, completed or retired (the walk-forward fits' pool). No last
    season since 10 Oct 2026 (it was 2026)."""
    a = rows.iloc[0::2]
    return (a["level"].isin(C.EVAL_LEVELS) & a["status"].isin(C.EVAL_STATUSES)
            & a["year"].ge(C.FIRST_YEAR)).to_numpy()


def build_all(rows: pd.DataFrame, ctx: dict, cand: pd.DataFrame, pbp: pd.DataFrame, pool: np.ndarray,
              lag: bool = False, only: set | None = None) -> dict:
    """State, then features (optionally one match later, and only for some candidates)."""
    xd = stat_xd(rows)
    ctx = dict(ctx)
    ctx["adjusted_x"] = adjusted_x(rows, xd, ctx)
    elo_w = elo_variants(rows, ctx["elo_scale"]) if (only is None or {"elo_games", "elo_points"} & set(only)) else {}
    S = state(rows, ctx, xd, pbp, elo_w)
    S["event_country"] = CTRY.event_country(rows[["tour", "year", "tournament_id", "tournament_name"]]).astype(object).to_numpy()
    em = entry_masks(rows)
    for k, v in em.items():
        S[f"entry_ok_{k}"] = v
    if lag:
        S["pbp_lag"] = pbp_lag(rows, pbp)
        S = lag_state(rows, S, xd, only=hist_needed(cand, only))
    return build(rows, ctx, S, pool, cand, only=only)


def hist_needed(cand: pd.DataFrame, only: set | None) -> set | None:
    if only is None:
        return None
    need = set()
    for c in cand.itertuples(index=False):
        if c.id in only and isinstance(c.stats, str):
            need |= set(c.stats.split(";"))
    need |= {"tpw"} if "vs_hand" in only else set()
    return need


def adjusted_x(rows: pd.DataFrame, xd: dict, ctx: dict) -> dict:
    """Each row's opponent-adjusted count of every statistic, with the slopes already fitted (constants())."""
    out = {}
    for stat in HIST:
        x, d, ok = xd[stat]
        if stat in STAGE3_ADJ:
            out[stat] = np.where(ok, rows[f"{STAGE3_ADJ[stat]}_n"].to_numpy(dtype="float64"), 0.0)
            continue
        z = opponent_z(rows, stat, ctx["typical"])
        y = rate_scale(stat, x, d)
        slope = np.where(rows["tour"].to_numpy() == "atp", ctx["slopes"][(stat, "atp")], ctx["slopes"][(stat, "wta")])
        ya = y - slope * z
        out[stat] = np.where(ok & (d > 0) & np.isfinite(ya), from_scale(stat, ya, d), 0.0)
    return out


def pbp_lag(rows: pd.DataFrame, pbp: pd.DataFrame) -> np.ndarray:
    """Big-point sums one Grand Slam later: the player's sums as they stood before their last Slam in the files."""
    pcode, day = rows["pcode"].to_numpy(), rows["day"].to_numpy()
    last = T.sums_before(pbp["pcode"].to_numpy(), pbp["day"].to_numpy(), pbp[["day"]].to_numpy(dtype="float64") * 0 + 1,
                         pcode, day)[:, 0]
    # the day of the player's last Slam before this match: the largest pbp day below this day
    o = np.lexsort((pbp["day"].to_numpy(), pbp["pcode"].to_numpy()))
    pk = pbp["pcode"].to_numpy()[o].astype("int64") * 1_000_000 + pbp["day"].to_numpy()[o]
    pos = np.searchsorted(pk, pcode.astype("int64") * 1_000_000 + day, side="left") - 1
    okp = (pos >= 0) & (pk[np.maximum(pos, 0)] // 1_000_000 == pcode) & (last > 0)
    lday = np.where(okp, pk[np.maximum(pos, 0)] % 1_000_000, day)
    vals = np.column_stack([pbp["value"].to_numpy(), np.ones(len(pbp))])
    return T.sums_before(pbp["pcode"].to_numpy(), pbp["day"].to_numpy(), vals, pcode, lday)


def run_probe(rows: pd.DataFrame, ctx: dict, cand: pd.DataFrame, pbp: pd.DataFrame) -> dict:
    """The probe on a slice: both tours from 2025 (history inside the slice only), cuts in 2026."""
    sl = rows["tournament_date"].ge(pd.Timestamp("2025-01-01")).to_numpy()
    sl_rows = prepare(rows[sl].reset_index(drop=True).drop(columns=["day", "pcode"]))
    sl_pbp = pbp.assign(pcode=pd.Series(sl_rows["pcode"].to_numpy(), index=sl_rows["player_id"].to_numpy())
                        .groupby(level=0).first().reindex(pbp["player_id"]).fillna(-1).to_numpy().astype("int64"))
    return probe(sl_rows, ctx, cand, sl_pbp)


def main() -> int:
    cand = pd.read_csv(CANDIDATES)
    plan_hash, cand_hash = sha256(PLAN), sha256(CANDIDATES)
    log(f"candidates.md sha256 {plan_hash}")
    rows, typical = load_rows()
    log(f"player-matches: {len(rows):,}")
    xd = stat_xd(rows)
    pbp = pbp_history(rows)
    log(f"point-by-point player-matches linked: {len(pbp):,}")
    ctx, consts = constants(rows, xd, typical, pbp)
    if "--probe-only" in sys.argv:          # rerun the probe alone and update the summary
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        assert summary["plan"]["sha256"] == plan_hash
        summary["probe"] = run_probe(rows, ctx, cand, pbp)
        SUMMARY.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
        log(f"probe rerun; wrote {SUMMARY.name}")
        return 0
    consts.to_csv(CONSTANTS, index=False)
    elo_w = elo_variants(rows, ctx["elo_scale"])
    log("weighted Elo passes done")
    S = state(rows, ctx, xd, pbp, elo_w)
    S["event_country"] = CTRY.event_country(rows[["tour", "year", "tournament_id", "tournament_name"]]).astype(object).to_numpy()
    for k, v in entry_masks(rows).items():
        S[f"entry_ok_{k}"] = v
    pool = pool_mask(rows)
    feats = build(rows, ctx, S, pool, cand)
    log(f"features built: {len(feats)} columns")
    a = rows.iloc[0::2][pool]
    frame = pd.DataFrame({"match_id": a["match_id"].to_numpy(), "tour": a["tour"].to_numpy(), "year": a["year"].to_numpy(),
                          "group": a["group"].to_numpy(), "evaluation": a["evaluation"].to_numpy(dtype=bool),
                          "status": a["status"].to_numpy(), "a_won": a["won"].to_numpy(dtype=bool),
                          "p_elo": a["p_elo_a"].to_numpy(), "p_mkt": a["p_mkt_a"].to_numpy(),
                          "order": a["order"].to_numpy()})
    frame["era"] = C.era_of(frame["year"]).astype("string")
    frame = pd.concat([frame, pd.DataFrame({k: np.asarray(v, dtype="float32") for k, v in feats.items()})], axis=1)
    frame.to_parquet(FEATURES, index=False, compression="zstd")
    log(f"wrote {FEATURES.name}: {len(frame):,} matches x {frame.shape[1]} columns")
    cov = coverage_check(frame, cand)
    log("coverage checked against the plan")
    pr = run_probe(rows, ctx, cand, pbp)
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "plan": {"file": "docs/studies/predictability_diagnostic/candidates.md", "sha256": plan_hash,
                        "candidate_table": "data/studies/predictability_diagnostic/stage4_candidates.csv",
                        "candidate_table_sha256": cand_hash},
               "settings": {"half_life_weeks": HALF_LIFE, "week52_days": WEEK52, "windows_days": list(WINDOWS),
                            "elo_change_days": ELO_CHANGE, "surface_first_below": SURFACE_FIRST, "age_range": list(AGE_RANGE),
                            "age_centre": AGE_CENTRE, "share_clip": SHARE_CLIP, "k_years": [K_YEARS[0], K_YEARS[-1]],
                            "beta_years": [BETA_YEARS[0], BETA_YEARS[-1]], "pbp_k_years": [PBP_K_YEARS[0], PBP_K_YEARS[-1]],
                            "boot": BOOT, "seed": SEED},
               "pool": {t: int((frame["tour"] == t).sum()) for t in C.TOURS},
               "pool_evaluation": {t: int(((frame["tour"] == t) & frame["evaluation"]).sum()) for t in C.TOURS},
               "pbp_linked_player_matches": int(len(pbp)), "typical_opponent": typical,
               "coverage_vs_plan": cov, "probe": pr, "seconds": round(time.time() - T0, 1)}
    SUMMARY.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    log(f"wrote {SUMMARY.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
