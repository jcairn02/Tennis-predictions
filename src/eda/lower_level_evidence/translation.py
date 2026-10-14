"""Level translation: what a lower-level match is worth as evidence about a player's main-tour performance
(the lower-level-evidence study, specialist 03).

The question, per statistic. By how much does a player's rate at a lower level (tour qualifying TQ, Slam qualifying
GSQ, Challenger / WTA 125 main draws CH, their qualifying CHQ; ITF and ITFQ once box scores exist) differ from the same
player's main-tour rate (the translation, delta_L)? How many lower-level units are worth one main-tour unit as evidence
(the exchange rate, lambda_L: 1 = equivalent, infinity = useless)? Does the project's opponent adjustment (the IOS
ridge ratings, solved over every level as if they were one) remove the level gap, or leave a bias that grows with a
player's lower-level share?

Steps (each writes small CSVs to <out>/<label>/):
    gaps         task 1. Same player, same season, at least 3 box scores at MAIN and at level L: the mean of
                 (rate at L - rate at MAIN) per statistic, with player-clustered intervals; and blend.level_shift's rule
                 re-run as a reproduction check.
    effects      task 2b. A batch opponent-adjusted fit per tour and serve statistic, on the IOS's per-match log-odds
                 scale: player-SEASON serve (O) and return (D) ratings, ridge kappa (the IOS's), plus level fixed
                 effects delta_L (MAIN = 0), unpenalised. Overall per window (2010-2018: the translation the arms use;
                 2019-2024; five 2-3 season eras), by surface, and by the two players' home tiers. Intervals cluster by
                 event.
    ios          tasks 2a and 3, opponent-adjusted. The IOS's form on a leak-proof weekly timeline (a result enters the
                 solve from the day after its latest possible finish; a match reads the last weekly solve on or before
                 its earliest possible start), per tour and serve statistic, in arms:
                     ios          every level as equivalent (the IOS as built)
                     main_only    lower-level rows left out (lambda = infinity)
                     translated   lower-level rows shifted by delta_L of the 2010-2018 batch fit (lambda = 1)
                     tr_lamX      translated, and each lower-level row's weight divided by X
                     lamX         weight divided by X, not translated
                     tier_prior   every level as equivalent, but the ridge shrinks each player towards his home
                                  tier's mean rating (from the fit window's batch fit) instead of the pool's zero
                     kappa_x5, tier_prior_x5, tp_tr_lam2   the shrinkage five times stronger (towards the zero or the
                                  tier's mean), and the tier prior with translation and a 2x discount
                 Scored by the binomial log loss per unit of main-tour rows (tune 2013-2018, validate 2019-2024),
                 overall and for low-exposure players (fewer than 10 main-tour matches in the previous 365 days). The
                 bias diagnostics: per arm, how much players whose year was mostly below the main tour are overrated
                 against main-tour-based players at the main tour (ios_arm_bias.csv); for the "ios" arm, main-tour
                 residuals by home tier and evidence (residual_by_evidence.csv) and against the lower-level share of
                 each rating's evidence, and same-player gaps (L - MAIN, selection-prone: see residual_gaps).
    credibility  task 3, raw rates. The precision-weighted estimate of a player's next main-tour match,
                     theta = (k mu + X_M + sum_L w_L (X_L - delta_L N_L)) / (k + N_M + sum_L w_L N_L),  w_L = 1/lambda_L,
                 from the player's own box scores of the previous 365 days (X numerators, N units, per level). Arms:
                 main_only (w = 0), pooled (w = 1, delta = 0: today's treatment of raw aggregates), translated (delta
                 fitted, w = 1), discounted (w fitted, delta = 0), translated_discounted (both fitted); k fitted in each.
                 Fitted on 2013-2018 targets, scored on 2019-2024.
    elo          task 4 (results channel, brief). A plain Elo over every level with a K multiplier for Challenger and ITF
                 results, scored on main-tour matches 2013-2024.
    itf          task 5. ITF box-score coverage (counts only; the holdout's included, no outcome read) and what the
                 results alone allow.

Simplifications against the IOS as built (all levels are treated alike by each, so the level comparisons stand): the
pooled IOS (no surface deviations), weekly snapshots and no incremental step (a match reads ratings up to a week older
than the IOS's), and Stage 3's surface averages recomputed from the Stage 0 read (checked against
stage4_constants.csv when it exists). h, kappa, tau and the typical units are the IOS constants registry's version
2026-10-08_reference, which the frozen reference was built with.

The holdout. Only matches of seasons up to --through (default 2024) and of events before 30 Dec 2024 are read: the
player rows and outcomes of other matches are never loaded (a filtered read), and common.assert_no_holdout_outcomes
guards each table with outcomes. Counting 2025-2026 matches and their box-score coverage (step itf) reads no outcome.

Lower levels without box scores in the read data are skipped by the box-score steps and enter by themselves once a
candidate Stage 0 carries them (--stage0-dir): every bucket with box scores gets its own delta and lambda.

Run: ./python.sh src/eda/lower_level_evidence/translation.py [--steps gaps,effects,ios,credibility,elo,itf]
     [--stage0-dir DIR] [--through 2024] [--label reference_2026-10-08] [--out DIR] [--workers 8] [--boot 30]
     [--fit-window 2010-2018] [--tune 2013-2018] [--validate 2019-2024]
About 4 minutes for effects and ios on 8 workers, 3 minutes for credibility with 30 bootstrap draws, 1 for the rest.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import scipy.sparse as sp
from scipy.optimize import minimize
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.ios_constants import registry as REG  # noqa: E402
from src.eda.lower_level_evidence import common as C  # noqa: E402

LABEL = "reference_2026-10-08"
OUT = C.OUT / "translation"
IOS_VERSION = "2026-10-08_reference"
TOURS = ("atp", "wta")
FIRST_YEAR = 2010
TUNE = (2013, 2018)
VALIDATE = (2019, 2024)
FIT_WINDOW = (2010, 2018)                     # the batch fit whose delta the translated arms use
ERAS = ((2010, 2012), (2013, 2015), (2016, 2018), (2019, 2021), (2022, 2024))
REF_DAY = int(np.datetime64("2018-01-01", "D").astype("int64"))       # the IOS's decay reference (stage3_traits)
ANCHOR = int(np.datetime64("2009-12-28", "D").astype("int64"))        # a Monday: the weekly snapshots' grid
STEP = 7
WINDOW_DAYS = 365
LOW_EXPOSURE = 10                             # fewer main-tour matches than this in the previous 365 days
MIN_BOX = 3
MIN_ROWS = 200                                # a level needs this many box-score rows in a fit to get its own delta
RTOL = 1e-7
MAX_ITER = 3000
LAMBDAS = (2.0, 4.0)                          # the weekly arms' discounts
SEED = 20261009

# The statistics as Stage 0 stores them (numerator / denominator per player row); higher is better for the player
# except double faults.
STATS = ("ace", "df", "first_in", "first_won", "second_won", "spw", "rpw", "tpw", "hold", "brk", "bp_saved", "bp_conv")
WORDS = {"ace": "aces per serve point", "df": "double faults per serve point", "first_in": "first serves in",
         "first_won": "first-serve points won", "second_won": "second-serve points won", "spw": "serve points won",
         "rpw": "return points won", "tpw": "total points won", "hold": "service games held",
         "brk": "return games won (breaks)", "bp_saved": "break points saved", "bp_conv": "break points converted"}
LOWER_IS_BETTER = {"df"}
# The IOS's eight serve-side systems (one row = one player's serve against the other's return) and the return-side
# measures read off them (the returner's share is one minus the server's).
SYSTEMS = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
RETURN_MEASURE = {"spw": "rpw", "hold": "brk", "bp_saved": "bp_conv"}
# Levels: the bucket codes used in the solves (MAIN must be 0)
LEVELS = ("MAIN", "TQ", "GSQ", "CH", "CHQ", "TEAM", "ITF", "ITFQ")
LEV_CODE = {b: i for i, b in enumerate(LEVELS)}
LOWER_CODES = [LEV_CODE[b] for b in C.LOWER]
TIER_OF = {"MAIN": "MT", "TQ": "Q", "GSQ": "Q", "CH": "CH", "CHQ": "CH", "ITF": "ITF", "ITFQ": "ITF", "TEAM": "TEAM"}
TIERS = ("MT", "Q", "CH", "ITF", "TEAM")      # ties in the home tier go to the higher (earlier) tier
TIER_CODES = {t: i for i, t in enumerate(TIERS + ("none",))}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def set_windows(fit: tuple[int, int], tune: tuple[int, int], validate: tuple[int, int]) -> None:
    """Set the study's windows (module-wide, in this process): the batch fit whose delta and home-tier means the
    weekly arms use, and the tune and validation seasons of every score. A candidate Stage 0 whose ITF box scores start
    in 2018 can then be run with, e.g., --fit-window 2018-2021 --tune 2019-2021 --validate 2022-2024."""
    global FIT_WINDOW, TUNE, VALIDATE
    FIT_WINDOW, TUNE, VALIDATE = tuple(fit), tuple(tune), tuple(validate)


def span(text: str) -> tuple[int, int]:
    lo, hi = (int(v) for v in text.split("-"))
    if hi < lo:
        raise ValueError(f"bad season span {text!r}")
    return lo, hi


# ------------------------------------------------------------------------------------------------
# Small statistics helpers

def cluster_se_mean(values: np.ndarray, clusters: np.ndarray) -> tuple[float, int]:
    """SE of a mean with a cluster sandwich and the G / (G - 1) factor."""
    v = np.asarray(values, float)
    _, ix = np.unique(np.asarray(clusters), return_inverse=True)
    G = int(ix.max()) + 1 if len(ix) else 0
    if G < 2:
        return np.nan, G
    infl = np.bincount(ix, weights=v - v.mean())
    return float(np.sqrt(G / (G - 1) * np.dot(infl, infl)) / len(v)), G


def cluster_se_ratio(num: np.ndarray, den: np.ndarray, clusters: np.ndarray) -> tuple[float, float, int]:
    """sum(num) / sum(den) and its cluster-sandwich SE (linearised)."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    r = num.sum() / den.sum()
    _, ix = np.unique(np.asarray(clusters), return_inverse=True)
    G = int(ix.max()) + 1 if len(ix) else 0
    if G < 2:
        return float(r), np.nan, G
    z = np.bincount(ix, weights=num - r * den)
    return float(r), float(np.sqrt(G / (G - 1) * np.dot(z, z)) / den.sum()), G


def binom_ll(x: np.ndarray, d: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Binomial log loss of x successes in d trials at probability p (the constant term left out)."""
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(x * np.log(p) + (d - x) * np.log1p(-p))


# ------------------------------------------------------------------------------------------------
# Data

MATCH_COLS = ["tour", "year", "map_level", "surface", "status", "format", "has_box", "tournament_date", "order",
              "tournament_id"]
PLAYER_COLS = ["match_id", "player_id", "opponent_id", "side", "won", "rank"] + \
    [f"{s}_{x}" for s in STATS for x in ("n", "d")]


def allowed_matches(stage0_dir: Path, through: int) -> pd.DataFrame:
    """Stage 0's matches of seasons up to `through` and of events before the holdout (no outcome column read)."""
    m = C.load_matches(stage0_dir, columns=MATCH_COLS)
    m["date"] = pd.to_datetime(m["tournament_date"])
    keep = (m["year"] <= through) & ~C.in_holdout(m["date"])
    return m[keep].reset_index(drop=True)


def load(stage0_dir: Path = C.STAGE0_DIR, through: int = 2024, timing: Path = C.TIMING) -> tuple[pd.DataFrame, dict]:
    """Player rows (two per match, A then B, in Stage 0's order) of the allowed matches, with the match columns, the
    match clock (es, lf, obs; a cautious window where the timeline lacks a match) and the box-score flags."""
    m = allowed_matches(stage0_dir, through)
    ids = pa.array(m["match_id"].to_numpy())
    tbl = pq.read_table(Path(stage0_dir) / "stage0_match_players.parquet", columns=PLAYER_COLS,
                        filters=pc.field("match_id").isin(ids))
    p = tbl.to_pandas()
    p = p.merge(m, on="match_id", how="inner", validate="many_to_one")
    C.assert_no_holdout_outcomes(p["date"], "translation.load: player rows")
    p = p.sort_values(["order", "side"], kind="mergesort").reset_index(drop=True)
    mid = p["match_id"].to_numpy()
    if len(p) % 2 or not (mid[0::2] == mid[1::2]).all():
        raise RuntimeError("player rows are not two per match in Stage 0's order")
    t = pd.read_parquet(timing, columns=["match_id", "es", "lf", "obs"]) if Path(timing).exists() else \
        pd.DataFrame(columns=["match_id", "es", "lf", "obs"])
    p = p.merge(t, on="match_id", how="left", validate="many_to_one")
    day = p["date"].to_numpy().astype("datetime64[D]").astype("int64")
    p["day"] = day
    miss = p["es"].isna() | p["lf"].isna() | p["obs"].isna()
    # a match the timeline lacks (a candidate's new rows): a cautious window, never a guessed day
    p.loc[miss, "es"] = day[miss.to_numpy()] - 7
    p.loc[miss, "lf"] = day[miss.to_numpy()] + 21
    p.loc[miss, "obs"] = day[miss.to_numpy()] + 3
    p["pcode"] = pd.factorize(p["tour"] + "|" + p["player_id"])[0]
    p["event"] = pd.factorize(p["tournament_id"].astype(str) + "|" + p["year"].astype(str))[0]
    p["box"] = p["status"].eq("completed").to_numpy() & p["format"].eq("standard").to_numpy() & \
        p["has_box"].fillna(False).astype(bool).to_numpy()
    p["played"] = p["status"].isin(["completed", "retired"])
    info = {"matches": int(len(p) // 2), "player_rows": int(len(p)), "timing_fallback_rows": int(miss.sum()),
            "years": [int(p["year"].min()), int(p["year"].max())], "last_event": str(p["date"].max().date()),
            "box_rows_by_tour_bucket": {f"{k[0]}|{k[1]}": int(v) for k, v in
                                        p[p["box"]].groupby(["tour", "bucket"]).size().items()}}
    return p, info


def stat_ok(p: pd.DataFrame, stat: str) -> np.ndarray:
    n, d = p[f"{stat}_n"].to_numpy(float), p[f"{stat}_d"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        return p["box"].to_numpy() & np.isfinite(n) & np.isfinite(d) & (d > 0) & (n >= 0) & (n <= d)


def player_sequence(p: pd.DataFrame, window: int = WINDOW_DAYS) -> tuple[np.ndarray, np.ndarray]:
    """Rows in each player's own order (player, then Stage 0's order), and for each position the first position of the
    same player's window (tournament date within `window` days): positions lo .. i-1 are the earlier matches of the
    window."""
    o = np.lexsort((p["order"].to_numpy(), p["pcode"].to_numpy()))
    code, day = p["pcode"].to_numpy()[o], p["day"].to_numpy()[o]
    same = np.diff(code) == 0
    if not (np.diff(day)[same] >= 0).all():
        raise RuntimeError("Stage 0's order does not follow the tournament date within a player")
    span = int(day.max() - day.min()) + 2 * window + 2
    comp = code.astype(np.int64) * span + (day - day.min() + window + 1)
    lo = np.searchsorted(comp, comp - window, side="left")
    return o, lo


def own_history(p: pd.DataFrame, window: int = WINDOW_DAYS) -> pd.DataFrame:
    """Per player row: the player's played matches (completed or retired) in the `window` days before, strictly earlier
    in Stage 0's order, by tier (every level, ITF's results included), the lower-level share (qualifying, Challenger
    and ITF tiers over all) and the home tier."""
    tier = p["bucket"].map(TIER_OF).to_numpy()
    played = p["played"].to_numpy()
    o, lo = player_sequence(p, window)
    idx = np.arange(len(o))
    out = pd.DataFrame(index=p.index)
    tot = np.zeros(len(p))
    counts = {}
    for t in TIERS:
        cs = np.concatenate([[0], np.cumsum(played[o] & (tier[o] == t))])
        c = cs[idx] - cs[lo]                       # rows lo .. idx-1: earlier rows of the window
        arr = np.empty(len(p))
        arr[o] = c
        counts[t] = arr
        out[f"n_{t}"] = arr.astype(np.int32)
        tot += arr
    out["n_all"] = tot.astype(np.int32)
    out["low_share"] = np.where(tot > 0, (tot - counts["MT"] - counts["TEAM"]) / np.maximum(tot, 1), np.nan)
    stack = np.column_stack([counts[t] for t in TIERS])
    home = np.array(TIERS)[np.argmax(stack, axis=1)]
    out["home"] = np.where(tot > 0, home, "none")
    out["low_exposure"] = counts["MT"] < LOW_EXPOSURE
    return out


# ------------------------------------------------------------------------------------------------
# Task 1: raw same-player gaps

def raw_gaps(p: pd.DataFrame, min_box: int = MIN_BOX, statuses=("completed",), standard_only: bool = True,
             pair_buckets: dict | None = None, years: tuple[int, int] | None = None) -> pd.DataFrame:
    """Same player, same season: rate at level L minus rate at MAIN (each a ratio of sums over the player-season's box
    scores at that level), for player-seasons with at least `min_box` box scores at both (seasons `years`, default the
    tune and validation seasons). pair_buckets maps a label to the buckets it pools (default: each lower bucket with box
    scores on its own). A statistic counts only where its numerator and denominator are both written."""
    years = years or (TUNE[0], VALIDATE[1])
    sel = p["status"].isin(statuses).to_numpy() & p["has_box"].fillna(False).astype(bool).to_numpy() & \
        p["year"].between(*years).to_numpy()
    if standard_only:
        sel &= p["format"].eq("standard").to_numpy()
    q = p[sel]
    present = [b for b in LEVELS[1:] if (q["bucket"] == b).sum() >= MIN_ROWS]
    pair_buckets = pair_buckets or {b: (b,) for b in present}
    agg = {}
    for s in STATS:
        ok = stat_ok(q.assign(box=True), s)
        agg[f"{s}_n"] = np.where(ok, q[f"{s}_n"].to_numpy(float), 0.0)
        agg[f"{s}_d"] = np.where(ok, q[f"{s}_d"].to_numpy(float), 0.0)
    a = pd.DataFrame(agg, index=q.index)
    a["box_matches"] = 1
    a["won"] = q["won"].astype(float).to_numpy()
    a["opp_rank"] = p["rank"].to_numpy(float)[np.arange(len(p)) ^ 1][sel]
    keys = [q["tour"], q["pcode"], q["year"]]
    rows = []
    main = a[q["bucket"].eq("MAIN").to_numpy()].groupby([k[q["bucket"].eq("MAIN").to_numpy()] for k in keys])
    gm = main.agg({**{c: "sum" for c in a.columns if c.endswith(("_n", "_d")) or c == "box_matches"},
                   "won": "mean", "opp_rank": "median"})
    gm.index.names = ["tour", "pcode", "year"]
    for label, bks in pair_buckets.items():
        mk = q["bucket"].isin(bks).to_numpy()
        gl = a[mk].groupby([k[mk] for k in keys]).agg(
            {**{c: "sum" for c in a.columns if c.endswith(("_n", "_d")) or c == "box_matches"},
             "won": "mean", "opp_rank": "median"})
        gl.index.names = ["tour", "pcode", "year"]
        both = gm.index.intersection(gl.index)
        A, B = gm.loc[both], gl.loc[both]
        ok = (A["box_matches"] >= min_box) & (B["box_matches"] >= min_box)
        A, B = A[ok], B[ok]
        for tour in TOURS:
            t = A.index.get_level_values("tour") == tour
            if t.sum() < 30:
                continue
            At, Bt = A[t], B[t]
            players = At.index.get_level_values("pcode").to_numpy()
            for s in STATS + ("won", "opp_rank"):
                if s in STATS:
                    with np.errstate(invalid="ignore", divide="ignore"):
                        va = (At[f"{s}_n"] / At[f"{s}_d"]).to_numpy(float)
                        vb = (Bt[f"{s}_n"] / Bt[f"{s}_d"]).to_numpy(float)
                else:
                    va, vb = At[s].to_numpy(float), Bt[s].to_numpy(float)
                dlt = vb - va
                okd = np.isfinite(dlt)
                se, G = cluster_se_mean(dlt[okd], players[okd])
                rec = {"tour": tour, "level": label, "stat": s, "player_seasons": int(okd.sum()), "players": G,
                       "mean_MAIN": float(np.mean(va[okd])), "mean_L": float(np.mean(vb[okd])),
                       "gap": float(dlt[okd].mean()), "se": se,
                       "lo": float(dlt[okd].mean() - 1.96 * se), "hi": float(dlt[okd].mean() + 1.96 * se)}
                if s in STATS:
                    # the same gap on the IOS's log-odds scale, from each player-season's pooled shares
                    with np.errstate(invalid="ignore", divide="ignore"):
                        la = logit((At[f"{s}_n"] + 0.5) / (At[f"{s}_d"] + 1.0)).to_numpy(float)
                        lb = logit((Bt[f"{s}_n"] + 0.5) / (Bt[f"{s}_d"] + 1.0)).to_numpy(float)
                    dl = (lb - la)[okd]
                    sel_ = np.isfinite(dl)
                    sel2, _ = cluster_se_mean(dl[sel_], players[okd][sel_])
                    rec.update({"gap_logit": float(dl[sel_].mean()), "se_logit": sel2,
                                "units_MAIN": float(At[f"{s}_d"].to_numpy(float)[okd].mean()),
                                "units_L": float(Bt[f"{s}_d"].to_numpy(float)[okd].mean())})
                rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# The opponent-adjusted system (the IOS's form)

def ios_constants(version: str = IOS_VERSION) -> tuple[dict, dict]:
    """(chosen[(tour, stat)] = {h, kappa, tau}, typ[(stat, tour)]) of the registry's version."""
    return REG.ios_constants(REG.load(version))


CENTRE_SURFACES = ("Hard", "Clay", "Grass", "Carpet")
ANALYSIS_BUCKETS = ("MAIN", "TQ", "GSQ", "CH", "CHQ")   # Stage 3's analysis levels (EVAL_LEVELS with qualifying)


def surface_means(p: pd.DataFrame, years=(2010, 2018)) -> dict:
    """Stage 3's surface averages (stage3_traits.surface_means): per tour and statistic, the pooled rate of the analysis
    matches (main tour, its qualifying, Challengers and theirs; completed, standard format) of 2010-2018, per surface
    with 300+ player-matches, else the tour's."""
    g = p[p["bucket"].isin(ANALYSIS_BUCKETS) & p["status"].eq("completed") & p["format"].eq("standard")
          & p["year"].between(*years)]
    out = {}
    for s in STATS:
        has = g[f"{s}_n"].notna() & g[f"{s}_d"].notna()
        gs = g[has]
        for tour in TOURS:
            t = gs[gs["tour"].eq(tour)]
            if not len(t):
                continue
            mu_all = float(t[f"{s}_n"].sum() / t[f"{s}_d"].sum())
            out[(tour, s, "all")] = mu_all
            for sf in CENTRE_SURFACES:
                ts = t[t["surface"].eq(sf)]
                out[(tour, s, sf)] = float(ts[f"{s}_n"].sum() / ts[f"{s}_d"].sum()) if len(ts) >= 300 else mu_all
    return out


def mu_rows(p: pd.DataFrame, stat: str, means: dict) -> np.ndarray:
    out = np.full(len(p), np.nan)
    tours, surf = p["tour"].to_numpy(), p["surface"].to_numpy()
    for tour in TOURS:
        if (tour, stat, "all") not in means:
            continue
        t = tours == tour
        out[t] = means[(tour, stat, "all")]
        for sf in CENTRE_SURFACES:
            out[t & (surf == sf)] = means[(tour, stat, sf)]
    return out


def compare_means(means: dict) -> dict:
    """The recomputed surface averages against Stage 3's stored ones (stage4_constants.csv), when present."""
    path = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"
    if not path.exists():
        return {"checked": False}
    k = pd.read_csv(path)
    k = k[k["kind"].eq("surface average")]
    diffs = []
    for r in k.itertuples(index=False):
        key = (r.tour, r.stat, r.surface)
        if key in means:
            diffs.append(abs(means[key] - float(r.value)))
    return {"checked": True, "cells": len(diffs), "max_abs_diff": float(max(diffs)) if diffs else None}


def system_arrays(p: pd.DataFrame, hist: pd.DataFrame, tour: str, stat: str, means: dict, typ: float, tau: int) -> dict:
    """One serve statistic's rows on one tour, as the IOS reads them: server = the row's player, returner = the
    opponent; y = logit((x + 1/2)/(d + 1)) - logit(mu) with mu the tour's surface average; base weight (d/typ)^tau."""
    ok = stat_ok(p, stat) & (p["tour"].to_numpy() == tour)
    r = np.flatnonzero(ok)
    opp = r ^ 1
    x = p[f"{stat}_n"].to_numpy(float)[r]
    d = p[f"{stat}_d"].to_numpy(float)[r]
    mu = mu_rows(p.iloc[r], stat, means)
    codes, uniq = pd.factorize(np.concatenate([p["pcode"].to_numpy()[r], p["pcode"].to_numpy()[opp]]))
    n = len(uniq)
    srv, ret = codes[:len(r)], codes[len(r):]
    y = logit((x + 0.5) / (d + 1.0)) - logit(mu)
    w0 = (d / typ) ** tau if tau else np.ones(len(r))
    return {"tour": tour, "stat": stat, "row": r, "srv": srv.astype(np.int64), "ret": ret.astype(np.int64), "n": n,
            "x": x, "d": d, "mu": mu, "y": y, "w0": w0,
            "obs": p["obs"].to_numpy(float)[r], "release": p["lf"].to_numpy(float)[r] + 1.0,
            "query": p["es"].to_numpy(float)[r],
            "lev": p["bucket"].map(LEV_CODE).to_numpy()[r].astype(np.int64),
            "year": p["year"].to_numpy()[r], "event": p["event"].to_numpy()[r],
            "surface": p["surface"].fillna("unknown").to_numpy()[r],
            "home_srv": hist["home"].to_numpy()[r], "home_ret": hist["home"].to_numpy()[opp],
            "tier_srv": hist["home"].map(TIER_CODES).to_numpy()[r].astype(np.int64),
            "tier_ret": hist["home"].map(TIER_CODES).to_numpy()[opp].astype(np.int64),
            "lowexp_srv": hist["low_exposure"].to_numpy()[r], "lowexp_ret": hist["low_exposure"].to_numpy()[opp]}


def pcg(matvec, diag: np.ndarray, b: np.ndarray, x0: np.ndarray, rtol: float = RTOL, max_iter: int = MAX_ITER):
    """Jacobi-preconditioned conjugate gradient (stageB_ios.pcg). Returns (x, iterations, converged)."""
    x = x0.copy()
    r = b - matvec(x)
    inv = 1.0 / diag
    z = r * inv
    p_ = z.copy()
    rz = float(r @ z)
    bn = float(np.linalg.norm(b))
    if bn == 0.0:
        return np.zeros_like(b), 0, True
    for it in range(max_iter):
        if float(np.linalg.norm(r)) <= rtol * bn:
            return x, it, True
        Ap = matvec(p_)
        den = float(p_ @ Ap)
        if den <= 0.0:
            break
        alpha = rz / den
        x = x + alpha * p_
        r = r - alpha * Ap
        z = r * inv
        rz_new = float(r @ z)
        if rz <= 0.0:
            break
        p_ = z + (rz_new / rz) * p_
        rz = rz_new
    return x, max_iter, bool(float(np.linalg.norm(r)) <= rtol * bn)


class Pattern:
    """The fixed server-by-returner sparsity of a set of rows (ios_time.TimedSystem's construction), its values set per
    solve."""

    def __init__(self, srv: np.ndarray, ret: np.ndarray, n: int):
        key = srv.astype(np.int64) * n + ret.astype(np.int64)
        uniq, self.pair = np.unique(key, return_inverse=True)
        ps, pr = uniq // n, uniq % n
        self.n_pairs, self.n = len(uniq), n
        indptr = np.r_[0, np.cumsum(np.bincount(ps, minlength=n))]
        self.W = sp.csr_matrix((np.zeros(len(uniq)), pr.astype(np.int32), indptr.astype(np.int64)), shape=(n, n))
        self.perm = np.lexsort((ps, pr))
        indptr_t = np.r_[0, np.cumsum(np.bincount(pr, minlength=n))]
        self.WT = sp.csr_matrix((np.zeros(len(uniq)), ps[self.perm].astype(np.int32), indptr_t.astype(np.int64)),
                                shape=(n, n))

    def set(self, pair_weights: np.ndarray) -> None:
        self.W.data[:] = pair_weights
        self.WT.data[:] = pair_weights[self.perm]

    def matvec(self, dO: np.ndarray, dD: np.ndarray):
        n, W, WT = self.n, self.W, self.WT

        def mv(v):
            o, d = v[:n], v[n:]
            return np.concatenate([dO * o - W @ d, dD * d - WT @ o])
        return mv


def weekly_solve(sd: dict, h: float, kappa: float, shift: np.ndarray, weight: np.ndarray,
                 rtol: float = RTOL, prior: tuple[np.ndarray, np.ndarray] | None = None) -> tuple[dict, dict]:
    """The IOS ridge solve on a leak-proof weekly timeline, for one system and one arm.

    A row enters the solve on its release day (latest possible finish + 1) with weight w0 * weight[level] *
    2^(-age/h) and value y - shift[level] (weight 0 leaves it out); every row reads the solve of the last weekly snapshot
    on or before its query day (earliest possible start), so no result reaches a match it could not precede. Returns,
    per row of sd: O of its server, D of its returner, their evidence weights (P serve, Q return) and the lower-level
    parts of those weights, and the snapshot day; plus solver statistics.

    prior = (mO, mD) per home-tier code (TIER_CODES): the ridge shrinks each player towards his home tier's mean instead
    of the pool's zero (the UFC pipeline's informative prior). A player's tier is his latest known one: from his rows
    as they are released and from the snapshot's own query rows (sd["tier_srv"], sd["tier_ret"]: the home tier from
    his own earlier matches, every level's results included)."""
    n, lev = sd["n"], sd["lev"]
    wl = weight[lev]
    k = np.flatnonzero((wl > 0) & np.isfinite(sd["release"]))
    k = k[np.argsort(sd["release"][k], kind="stable")]
    srv, ret = sd["srv"][k], sd["ret"][k]
    yv = (sd["y"] - shift[lev])[k]
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    ws = sd["w0"][k] * wl[k] * np.exp2((sd["obs"][k] - REF_DAY) * lam)
    low = np.isin(lev[k], LOWER_CODES).astype(float)      # qualifying, Challenger and ITF rows (not team events)
    rel = sd["release"][k]
    pat = Pattern(srv, ret, n)
    q = sd["query"]
    S = np.arange(ANCHOR, int(np.nanmax(q)) + STEP, STEP)
    j_of = np.searchsorted(S, q, side="right") - 1
    nr = len(q)
    out = {name: np.full(nr, np.nan) for name in ("O", "D", "P", "Q", "PL", "QL", "snap")}
    valid = j_of >= 0
    order = np.flatnonzero(valid)[np.argsort(j_of[valid], kind="stable")]
    js, starts = np.unique(j_of[order], return_index=True)
    ends = np.r_[starts[1:], len(order)]
    Pc, Qc, PLc, QLc, bOc, bDc = (np.zeros(n) for _ in range(6))
    PWc = np.zeros(pat.n_pairs)
    x = np.zeros(2 * n)
    ptr, its, nonconv = 0, [], 0
    if prior is not None:
        tier_now = np.full(n, TIER_CODES["none"])
        ts_k, tr_k = sd["tier_srv"][k], sd["tier_ret"][k]
    for j, a, b in zip(js, starts, ends):
        Sd = S[j]
        r = order[a:b]
        new = int(np.searchsorted(rel, Sd, side="right"))
        if new > ptr:
            sl = slice(ptr, new)
            w_, y_ = ws[sl], yv[sl]
            Pc += np.bincount(srv[sl], weights=w_, minlength=n)
            Qc += np.bincount(ret[sl], weights=w_, minlength=n)
            PLc += np.bincount(srv[sl], weights=w_ * low[sl], minlength=n)
            QLc += np.bincount(ret[sl], weights=w_ * low[sl], minlength=n)
            bOc += np.bincount(srv[sl], weights=w_ * y_, minlength=n)
            bDc -= np.bincount(ret[sl], weights=w_ * y_, minlength=n)
            PWc += np.bincount(pat.pair[sl], weights=w_, minlength=pat.n_pairs)
            if prior is not None:
                tier_now[srv[sl]] = ts_k[sl]
                tier_now[ret[sl]] = tr_k[sl]
            ptr = new
        g = np.exp2(-(Sd - REF_DAY) * lam)
        P, Q = Pc * g, Qc * g
        pat.set(PWc * g)
        dO, dD = P + kappa, Q + kappa
        bvec = np.concatenate([bOc * g, bDc * g])
        if prior is not None:
            tier_now[sd["srv"][r]] = sd["tier_srv"][r]
            tier_now[sd["ret"][r]] = sd["tier_ret"][r]
            bvec = bvec + kappa * np.concatenate([prior[0][tier_now], prior[1][tier_now]])
        x, it, conv = pcg(pat.matvec(dO, dD), np.concatenate([dO, dD]), bvec, x, rtol=rtol)
        its.append(it)
        nonconv += int(not conv)
        s_, t_ = sd["srv"][r], sd["ret"][r]
        out["O"][r], out["D"][r] = x[:n][s_], x[n:][t_]
        out["P"][r], out["Q"][r] = P[s_], Q[t_]
        out["PL"][r], out["QL"][r] = PLc[s_] * g, QLc[t_] * g
        out["snap"][r] = Sd
    stats = {"snapshots": int(len(js)), "rows_in_solve": int(len(k)), "pairs": int(pat.n_pairs), "players": int(n),
             "iterations_mean": float(np.mean(its)) if its else 0.0, "not_converged": int(nonconv)}
    return out, stats


def batch_fe(srv: np.ndarray, ret: np.ndarray, y: np.ndarray, w: np.ndarray, col: np.ndarray, n: int, n_cols: int,
             kappa: float, cluster: np.ndarray | None = None, eps: float = 1e-6, rtol: float = 1e-9) -> dict:
    """Weighted ridge fit of y ~ O[srv] - D[ret] + delta[col] (col -1: no effect; O, D penalised by kappa, delta by
    eps), solved exactly through the Schur complement of the O/D block: A u0 = b, A U = B, then
    (diag(S) - B'U) delta = b_delta - B'u0 and theta = u0 - U delta. The delta's SE is a cluster sandwich on the
    regressors with the ratings partialled out (clusters: `cluster`, e.g. the event)."""
    pat = Pattern(srv, ret, n)
    pat.set(np.bincount(pat.pair, weights=w, minlength=pat.n_pairs))
    P = np.bincount(srv, weights=w, minlength=n)
    Q = np.bincount(ret, weights=w, minlength=n)
    dO, dD = P + kappa, Q + kappa
    mv = pat.matvec(dO, dD)
    diag = np.concatenate([dO, dD])
    wy = w * y
    bth = np.concatenate([np.bincount(srv, weights=wy, minlength=n), -np.bincount(ret, weights=wy, minlength=n)])
    has = col >= 0
    B = np.zeros((2 * n, n_cols))
    for c in range(n_cols):
        m = col == c
        B[:n, c] = np.bincount(srv[m], weights=w[m], minlength=n)
        B[n:, c] = -np.bincount(ret[m], weights=w[m], minlength=n)
    Sw = np.bincount(col[has], weights=w[has], minlength=n_cols)
    bd = np.bincount(col[has], weights=wy[has], minlength=n_cols)
    u0, _, c0 = pcg(mv, diag, bth, np.zeros(2 * n), rtol=rtol)
    U = np.zeros((2 * n, n_cols))
    conv = [c0]
    for c in range(n_cols):
        if Sw[c] > 0:
            U[:, c], _, cc = pcg(mv, diag, B[:, c], np.zeros(2 * n), rtol=rtol)
            conv.append(cc)
    M = np.diag(Sw + eps) - B.T @ U
    delta = np.linalg.solve(M, bd - B.T @ u0) if n_cols else np.zeros(0)
    theta = u0 - U @ delta
    O, D = theta[:n], theta[n:]
    fit = O[srv] - D[ret] + (np.where(has, delta[np.maximum(col, 0)], 0.0) if n_cols else 0.0)
    res = y - fit
    out = {"delta": delta, "O": O, "D": D, "converged": bool(all(conv)), "S": Sw,
           "rows": np.bincount(col[has], minlength=n_cols)}
    if cluster is not None and n_cols:
        # partialled-out regressors z_k = e_col(k) - (U[srv_k] - U[n + ret_k])
        Z = -(U[srv] - U[n + ret])
        Z[np.flatnonzero(has), col[has]] += 1.0
        _, ix = np.unique(cluster, return_inverse=True)
        G = int(ix.max()) + 1
        sc = np.column_stack([np.bincount(ix, weights=w * res * Z[:, c], minlength=G) for c in range(n_cols)])
        Mi = np.linalg.inv(M)
        V = Mi @ (sc.T @ sc) @ Mi * G / max(G - 1, 1)
        out["se"] = np.sqrt(np.clip(np.diag(V), 0, None))
        out["clusters"] = G
    return out


# ------------------------------------------------------------------------------------------------
# Task 2b: level effects (batch fits) and tasks 2a/3: the weekly arms, per tour and system (one worker job each)

def home_group(h: np.ndarray) -> np.ndarray:
    return np.where(h == "MT", "MT", "low")


PRIOR_MIN_EVIDENCE = 5.0          # typical matches: the player-seasons whose ratings make a tier's prior mean


def tier_prior_means(sd: dict, res: dict, rk: np.ndarray, s_codes: np.ndarray, t_codes: np.ndarray,
                     n_ps: int) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Per home tier: the evidence-weighted mean serve rating (O) and return rating (D) of the batch fit's
    player-seasons with at least PRIOR_MIN_EVIDENCE typical matches of evidence; a player-season's tier is the most
    frequent home tier on its rows. A tier without such player-seasons keeps the pool's zero."""
    w = sd["w0"][rk]
    out = []
    means = []
    for side, codes, tiers, vals in (("O", s_codes, sd["tier_srv"][rk], res["O"]),
                                     ("D", t_codes, sd["tier_ret"][rk], res["D"])):
        ev = np.bincount(codes, weights=w, minlength=n_ps)
        M = np.zeros((n_ps, len(TIER_CODES)))
        np.add.at(M, (codes, tiers), 1.0)
        tier_ps = np.argmax(M, axis=1)
        m = np.zeros(len(TIER_CODES))
        for t, i in TIER_CODES.items():
            sel = (tier_ps == i) & (ev >= PRIOR_MIN_EVIDENCE)
            if sel.sum() >= 10:
                m[i] = float(np.average(vals[sel], weights=ev[sel]))
            out.append({"tour": sd["tour"], "stat": sd["stat"], "side": side, "tier": t, "player_seasons": int(sel.sum()),
                        "mean_rating": m[i]})
        means.append(m)
    return means[0], means[1], out


def effects_for_system(sd: dict, kappa: float, present: list[str]) -> tuple[list[dict], tuple | None, list[dict]]:
    """The batch fits of one system: delta_L per window, per era, by surface and by the players' home tiers; and the
    home-tier prior means from the fit window's fit."""
    rows = []
    tour, stat = sd["tour"], sd["stat"]
    prior, prior_rows = None, []

    def fit(mask, col, labels, variant, window, want=False):
        r = np.flatnonzero(mask)
        c = col[r]
        keep_cols = [i for i in range(len(labels)) if (c == i).sum() >= MIN_ROWS]
        if len(r) == 0 or not keep_cols:
            return None
        # player-SEASON ratings: the server's and the returner's (player, season) on each row
        srv_ps_key = sd["srv"].astype(np.int64)[r] * 10_000 + sd["year"][r]
        ret_ps_key = sd["ret"].astype(np.int64)[r] * 10_000 + sd["year"][r]
        codes, uniq = pd.factorize(np.concatenate([srv_ps_key, ret_ps_key]))
        s_, t_ = codes[:len(r)], codes[len(r):]
        remap = np.full(len(labels), -1)
        remap[keep_cols] = np.arange(len(keep_cols))
        # rows of a level whose cell is too thin are left out of the fit (never pooled into MAIN's reference)
        thin = (c >= 0) & (remap[np.maximum(c, 0)] < 0)
        keep = ~thin
        c2 = np.where(c >= 0, remap[np.maximum(c, 0)], -1)[keep]
        res = batch_fe(s_[keep], t_[keep], sd["y"][r][keep], sd["w0"][r][keep], c2, len(uniq), len(keep_cols), kappa,
                       cluster=sd["event"][r][keep])
        rk = r[keep]
        # the delta in points: the MAIN-surface average's share moved by delta, for the cell's own average mu
        for i, ci in enumerate(keep_cols):
            m = c2 == i
            mu_c = float(np.average(sd["mu"][rk][m], weights=sd["d"][rk][m]))
            rows.append({"tour": tour, "stat": stat, "variant": variant, "window": window, "cell": labels[ci],
                         "delta_logit": float(res["delta"][i]), "se": float(res["se"][i]),
                         "delta_points": float(expit(logit(mu_c) + res["delta"][i]) - mu_c),
                         "rows": int(m.sum()), "units": float(sd["d"][rk][m].sum()),
                         "servers": int(len(np.unique(sd["srv"][rk][m]))),
                         "clusters": int(res["clusters"]), "converged": res["converged"]})
        if want:
            return res, rk, s_[keep], t_[keep], len(uniq)
        return None

    lev = sd["lev"]
    yr = sd["year"]
    lower = [LEV_CODE[b] for b in present]
    col_level = np.where(lev == 0, -1, lev - 1)          # columns 0.. = LEVELS[1:]
    lev_names = np.array(LEVELS)
    labels_level = list(lev_names[1:])
    for lo, hi in (FIT_WINDOW, VALIDATE) + ERAS:
        got = fit((yr >= lo) & (yr <= hi), col_level, labels_level, "level", f"{lo}-{hi}",
                  want=(lo, hi) == FIT_WINDOW)
        if got is not None:
            mO, mD, prior_rows = tier_prior_means(sd, *got)
            prior = (mO, mD)
    # by surface (2010-2024): level x surface cells
    surf = np.array([s if s in ("Hard", "Clay", "Grass") else "other" for s in sd["surface"]])
    s_code = {"Hard": 0, "Clay": 1, "Grass": 2, "other": 3}
    sc = np.vectorize(s_code.get)(surf)
    col_s = np.where(lev == 0, -1, (lev - 1) * 4 + sc)
    labels_s = [f"{b}|{s}" for b in LEVELS[1:] for s in s_code]
    fit(np.isin(lev, [0] + lower) & (yr >= FIT_WINDOW[0]) & (yr <= VALIDATE[1]), col_s, labels_s, "level x surface",
        f"{FIT_WINDOW[0]}-{VALIDATE[1]}")
    # by the server's and returner's home tiers (MT or lower), 2010-2024
    hs, hr = home_group(sd["home_srv"]), home_group(sd["home_ret"])
    cell = (hs == "low").astype(int) * 2 + (hr == "low").astype(int)
    col_h = np.where(lev == 0, -1, (lev - 1) * 4 + cell)
    names = ["srvMT_retMT", "srvMT_retLow", "srvLow_retMT", "srvLow_retLow"]
    labels_h = [f"{b}|{c}" for b in LEVELS[1:] for c in names]
    fit((yr >= FIT_WINDOW[0]) & (yr <= VALIDATE[1]), col_h, labels_h, "level x home tiers",
        f"{FIT_WINDOW[0]}-{VALIDATE[1]}")
    return rows, prior, prior_rows


PRIOR_MULT = 5.0                  # the stronger home-tier prior: ridge kappa x 5 towards the tier's mean


def arms(present: list[str], delta: dict) -> dict:
    """The weekly arms: name -> (shift per level code, weight per level code, use the home-tier prior, kappa
    multiplier)."""
    zero = np.zeros(len(LEVELS))
    one = np.ones(len(LEVELS))
    sh = zero.copy()
    for b in present:
        sh[LEV_CODE[b]] = delta.get(b, 0.0)
    out = {"ios": (zero, one, False, 1.0)}
    mo = one.copy()
    mo[1:] = 0.0
    out["main_only"] = (zero, mo, False, 1.0)
    out["translated"] = (sh, one, False, 1.0)
    for lam in LAMBDAS:
        w = one.copy()
        w[1:] = 1.0 / lam
        out[f"tr_lam{lam:g}"] = (sh, w, False, 1.0)
        out[f"lam{lam:g}"] = (zero, w, False, 1.0)
    out["tier_prior"] = (zero, one, True, 1.0)
    out[f"kappa_x{PRIOR_MULT:g}"] = (zero, one, False, PRIOR_MULT)
    out[f"tier_prior_x{PRIOR_MULT:g}"] = (zero, one, True, PRIOR_MULT)
    w = one.copy()
    w[1:] = 1.0 / LAMBDAS[0]
    out[f"tp_tr_lam{LAMBDAS[0]:g}"] = (sh, w, True, 1.0)
    return out


def run_system(job: dict) -> dict:
    """One worker job: one tour and serve statistic. The batch fits, then the weekly arms (translation and home-tier
    prior means from the fit window's batch fit), then per-row predictions of the 'ios' arm and per-arm scores of
    main-tour rows."""
    sd, h, kappa, present = job["sd"], job["h"], job["kappa"], job["present"]
    if "windows" in job:                      # a worker process starts from the module's defaults
        set_windows(*job["windows"])
    t0 = time.time()
    eff, prior, prior_rows = effects_for_system(sd, kappa, present)
    delta = {}
    for r in eff:
        if r["variant"] == "level" and r["window"] == f"{FIT_WINDOW[0]}-{FIT_WINDOW[1]}" and r["cell"] in present:
            delta[r["cell"]] = r["delta_logit"]
    t1 = time.time()
    res = {"tour": sd["tour"], "stat": sd["stat"], "effects": eff, "delta_used": delta, "arms": {}, "solver": {},
           "prior_means": prior_rows}
    lmu = logit(sd["mu"])
    for name, (shift, weight, use_prior, kmult) in arms(present, delta).items():
        if job.get("arms") and name not in job["arms"]:
            continue
        if use_prior and prior is None:
            continue
        o, st = weekly_solve(sd, h, kappa * kmult, shift, weight, prior=prior if use_prior else None)
        pred = expit(lmu + np.nan_to_num(o["O"]) - np.nan_to_num(o["D"]) + shift[sd["lev"]])
        ll = binom_ll(sd["x"], sd["d"], pred)
        res["arms"][name] = {"ll": ll.astype(np.float32), "p": pred.astype(np.float32)}
        res["solver"][name] = st
        if name == "ios":
            res["ios_state"] = {k: o[k].astype(np.float32) for k in ("O", "D", "P", "Q", "PL", "QL")}
    res["ll0"] = binom_ll(sd["x"], sd["d"], sd["mu"]).astype(np.float32)
    res["seconds"] = {"effects": round(t1 - t0, 1), "weekly": round(time.time() - t1, 1)}
    return res


# ------------------------------------------------------------------------------------------------
# Scoring the weekly arms and the residual diagnostics

def score_arms(sd: dict, res: dict) -> pd.DataFrame:
    """Per arm: log loss per unit of the main-tour rows (tune / validate), its gain over the 'ios' arm (milli per unit,
    + = the arm better) with a 28-day-block interval, overall, for low-exposure rows (server or returner under 10
    main-tour matches in the last year) and for rows whose server's evidence is mostly lower-level."""
    lev, yr, d = sd["lev"], sd["year"], sd["d"]
    block = (sd["query"] - ANCHOR) // 28
    st = res["ios_state"]
    with np.errstate(invalid="ignore", divide="ignore"):
        share = np.where(st["P"] > 0, st["PL"] / st["P"], np.nan)
    groups = {"all": np.ones(len(d), bool),
              "low_exposure": sd["lowexp_srv"] | sd["lowexp_ret"],
              "server_mostly_lower": share > 0.5}
    base = res["arms"]["ios"]["ll"].astype(float)
    ll0 = res["ll0"].astype(float)
    rows = []
    for period, (lo, hi) in (("tune", TUNE), ("validate", VALIDATE)):
        main = (lev == 0) & (yr >= lo) & (yr <= hi)
        for gname, gm in groups.items():
            m = main & gm
            if m.sum() < 50:
                continue
            U = d[m].sum()
            for arm, a in res["arms"].items():
                ll = a["ll"].astype(float)
                gain, se, G = cluster_se_ratio(1000 * (base[m] - ll[m]), d[m], block[m])
                rows.append({"tour": sd["tour"], "stat": sd["stat"], "period": period, "group": gname, "arm": arm,
                             "rows": int(m.sum()), "units": float(U), "ll_per_unit": float(ll[m].sum() / U),
                             "gain_vs_avg_milli": float(1000 * (ll0[m].sum() - ll[m].sum()) / U),
                             "gain_vs_ios_milli": gain, "se": se, "lo": gain - 1.96 * se, "hi": gain + 1.96 * se,
                             "blocks": G})
    return pd.DataFrame(rows)


def arm_bias(p: pd.DataFrame, sd: dict, res: dict) -> pd.DataFrame:
    """Per arm, main-tour rows: the residual (actual - expected, per 100 units) by the two players' home tiers (MT: most
    of the last 365 days on the main tour; low: otherwise), and the asymmetry (MT server vs lower-based returner minus
    lower-based server vs MT returner, halved): how much the arm still overrates lower-based players against main-tour
    ones (0 = no such bias). Player-clustered intervals."""
    hs, hr = home_group(sd["home_srv"]), home_group(sd["home_ret"])
    pl = p["pcode"].to_numpy()[sd["row"]]
    rows = []
    for period, (lo, hi) in (("tune", TUNE), ("validate", VALIDATE), ("all", (TUNE[0], VALIDATE[1]))):
        main = (sd["lev"] == 0) & (sd["year"] >= lo) & (sd["year"] <= hi)
        a_ = main & (hs == "MT") & (hr == "low")
        b_ = main & (hs == "low") & (hr == "MT")
        for arm, a in res["arms"].items():
            e = sd["x"] - sd["d"] * a["p"].astype(float)
            rec = {"tour": sd["tour"], "stat": sd["stat"], "period": period, "arm": arm}
            for name, m in (("MT_vs_low", a_), ("low_vs_MT", b_),
                            ("MT_vs_MT", main & (hs == "MT") & (hr == "MT")),
                            ("low_vs_low", main & (hs == "low") & (hr == "low"))):
                r, se, _ = cluster_se_ratio(e[m], sd["d"][m], pl[m])
                rec[f"{name}_per_100"], rec[f"{name}_se"] = 100 * r, 100 * se
            # the asymmetry: one statistic over both mixed cells, clustered by the lower-based player
            m = a_ | b_
            sign = np.where(a_, 1.0, -1.0)[m]
            low_player = np.where(a_, p["pcode"].to_numpy()[sd["row"] ^ 1], pl)[m]
            r, se, _ = cluster_se_ratio(sign * e[m], sd["d"][m], low_player)
            rec["asymmetry_per_100"], rec["asymmetry_se"] = 100 * r, 100 * se
            rows.append(rec)
    return pd.DataFrame(rows)


def residual_rows(p: pd.DataFrame, sd: dict, res: dict) -> pd.DataFrame:
    """Per row of the 'ios' arm: the residual (actual - expected count) for the server's measure, the returner's
    (the negative, in the opponent's units) and the evidence shares."""
    pred = res["arms"]["ios"]["p"].astype(float)
    e = sd["x"] - sd["d"] * pred
    st = res["ios_state"]
    with np.errstate(invalid="ignore", divide="ignore"):
        sh_s = np.where(st["P"] > 0, st["PL"] / st["P"], np.nan)
        sh_r = np.where(st["Q"] > 0, st["QL"] / st["Q"], np.nan)
    return pd.DataFrame({"row": sd["row"], "e": e, "d": sd["d"], "lev": sd["lev"], "year": sd["year"],
                         "share_srv": sh_s, "share_ret": sh_r, "P": st["P"], "Q": st["Q"],
                         "lowexp_srv": sd["lowexp_srv"], "lowexp_ret": sd["lowexp_ret"],
                         "home_srv": sd["home_srv"], "home_ret": sd["home_ret"], "event": sd["event"],
                         "query": sd["query"]})


def residual_gaps(p: pd.DataFrame, rr: dict, years: tuple[int, int] | None = None,
                  min_box: int = MIN_BOX) -> pd.DataFrame:
    """Same player, same season, at least `min_box` rows at MAIN and at L: the residual rate (sum of residuals over
    units) at L minus at MAIN, per measure. Serve measures: the player serving; return measures (rpw, brk, bp_conv): the
    player returning, residual = -(server's); tpw: serve and return residuals over all points.

    Caution: membership (a season with matches at both levels) depends on that season's results (players drop after
    losing and climb after winning), so the gap carries a selection effect; residual_by_share and arm_bias condition
    on prior information only."""
    years = years or (TUNE[0], VALIDATE[1])
    pc_ = p["pcode"].to_numpy()
    out = []
    measures = {}
    for (tour, stat), r in rr.items():
        r = r[(r["year"] >= years[0]) & (r["year"] <= years[1])]
        rows = r["row"].to_numpy()
        measures[(tour, stat)] = pd.DataFrame({"tour": tour, "player": pc_[rows], "year": r["year"].to_numpy(),
                                               "lev": r["lev"].to_numpy(), "e": r["e"].to_numpy(),
                                               "d": r["d"].to_numpy()})
        if stat in RETURN_MEASURE:
            measures[(tour, RETURN_MEASURE[stat])] = pd.DataFrame(
                {"tour": tour, "player": pc_[rows ^ 1], "year": r["year"].to_numpy(), "lev": r["lev"].to_numpy(),
                 "e": -r["e"].to_numpy(), "d": r["d"].to_numpy()})
        if stat == "spw":
            # total points: each player-row's serve residual plus its return residual (the opponent's row, negated)
            e_by = pd.Series(r["e"].to_numpy(), index=rows)
            d_by = pd.Series(r["d"].to_numpy(), index=rows)
            both = np.intersect1d(rows, rows ^ 1)
            measures[(tour, "tpw")] = pd.DataFrame(
                {"tour": tour, "player": pc_[both], "year": p["year"].to_numpy()[both],
                 "lev": p["bucket"].map(LEV_CODE).to_numpy()[both],
                 "e": e_by.loc[both].to_numpy() - e_by.loc[both ^ 1].to_numpy(),
                 "d": d_by.loc[both].to_numpy() + d_by.loc[both ^ 1].to_numpy()})
    for (tour, meas), f in measures.items():
        g = f.groupby(["player", "year", "lev"]).agg(E=("e", "sum"), D=("d", "sum"), n=("e", "size")).reset_index()
        main = g[g["lev"] == 0].set_index(["player", "year"])
        for lv in sorted(set(g["lev"]) - {0}):
            low = g[g["lev"] == lv].set_index(["player", "year"])
            both = main.index.intersection(low.index)
            A, B = main.loc[both], low.loc[both]
            ok = (A["n"] >= min_box) & (B["n"] >= min_box)
            A, B = A[ok], B[ok]
            if len(A) < 30:
                continue
            gap = (B["E"] / B["D"] - A["E"] / A["D"]).to_numpy()
            players = A.index.get_level_values("player").to_numpy()
            se, G = cluster_se_mean(gap, players)
            se_m, _ = cluster_se_mean((A["E"] / A["D"]).to_numpy(), players)
            se_l, _ = cluster_se_mean((B["E"] / B["D"]).to_numpy(), players)
            out.append({"tour": tour, "measure": meas, "level": LEVELS[lv], "player_seasons": int(len(gap)),
                        "players": G, "resid_MAIN": float((A["E"] / A["D"]).mean()), "se_MAIN": se_m,
                        "resid_L": float((B["E"] / B["D"]).mean()), "se_L": se_l, "gap": float(gap.mean()), "se": se,
                        "lo": float(gap.mean() - 1.96 * se), "hi": float(gap.mean() + 1.96 * se)})
    return pd.DataFrame(out)


SHARE_BINS = (0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0001)


def residual_by_share(p: pd.DataFrame, rr: dict, years: tuple[int, int] | None = None
                      ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Main-tour rows only: the residual rate by the lower-level share of the server's serve evidence (serve measures)
    and of the returner's return evidence (return measures), in bins; and the weighted slope of the per-row residual
    rate on both shares together, with player-clustered SEs."""
    years = years or (TUNE[0], VALIDATE[1])
    pc_ = p["pcode"].to_numpy()
    bins, slopes = [], []
    for (tour, stat), r in rr.items():
        r = r[(r["lev"] == 0) & (r["year"] >= years[0]) & (r["year"] <= years[1])
              & np.isfinite(r["share_srv"]) & np.isfinite(r["share_ret"])]
        rows = r["row"].to_numpy()
        e, d = r["e"].to_numpy(), r["d"].to_numpy()
        for side, share, sign, who in (("serve", r["share_srv"].to_numpy(), 1.0, rows),
                                       ("return", r["share_ret"].to_numpy(), -1.0, rows ^ 1)):
            if side == "return" and stat not in RETURN_MEASURE:
                continue
            meas = stat if side == "serve" else RETURN_MEASURE[stat]
            b = np.digitize(share, SHARE_BINS[1:-1])
            for i in range(len(SHARE_BINS) - 1):
                m = b == i
                if m.sum() < 30:
                    continue
                rate, se, G = cluster_se_ratio(sign * e[m], d[m], pc_[who][m])
                bins.append({"tour": tour, "measure": meas, "side": side,
                             "share_bin": f"{SHARE_BINS[i]:.1f}-{min(SHARE_BINS[i + 1], 1.0):.1f}", "rows": int(m.sum()),
                             "units": float(d[m].sum()), "resid_per_100": 100 * rate, "se_per_100": 100 * se,
                             "players": G})
        # both shares at once: the serve-side measure's residual rate on the server's and returner's shares
        y = e / d
        X = np.column_stack([np.ones(len(y)), r["share_srv"].to_numpy(), r["share_ret"].to_numpy()])
        XtW = X.T * d
        A = XtW @ X
        beta = np.linalg.solve(A, XtW @ y)
        res_ = y - X @ beta
        _, ix = np.unique(pc_[rows], return_inverse=True)
        G = int(ix.max()) + 1
        sc = np.column_stack([np.bincount(ix, weights=d * res_ * X[:, j]) for j in range(3)])
        Ai = np.linalg.inv(A)
        V = Ai @ (sc.T @ sc) @ Ai * G / (G - 1)
        se = np.sqrt(np.diag(V))
        slopes.append({"tour": tour, "stat": stat, "rows": int(len(y)),
                       "server_share_slope_per_100": 100 * beta[1], "server_share_se": 100 * se[1],
                       "returner_share_slope_per_100": 100 * beta[2], "returner_share_se": 100 * se[2],
                       "intercept_per_100": 100 * beta[0], "clusters": G})
    return pd.DataFrame(bins), pd.DataFrame(slopes)


EVIDENCE_BINS = (5.0, 20.0)       # typical matches of the rating's own (decayed, weighted) evidence


def residual_by_evidence(p: pd.DataFrame, rr: dict, years: tuple[int, int] | None = None) -> pd.DataFrame:
    """Main-tour rows: the residual per 100 units by the player's home tier (MT or lower) and by how much evidence his
    rating holds (P serving, Q returning; under 5, 5-20, 20+ typical matches), for the server (his serve measure) and
    the returner (his return measure, the negative of the server's). Player-clustered intervals. A negative value means
    the IOS-form rating overrates that group."""
    years = years or (TUNE[0], VALIDATE[1])
    pc_ = p["pcode"].to_numpy()
    out = []
    for (tour, stat), r in rr.items():
        r = r[(r["lev"] == 0) & (r["year"] >= years[0]) & (r["year"] <= years[1])]
        rows = r["row"].to_numpy()
        e, d = r["e"].to_numpy(), r["d"].to_numpy()
        for side, home, ev, sign, who in (("server", r["home_srv"].to_numpy(), r["P"].to_numpy(), 1.0, pc_[rows]),
                                          ("returner", r["home_ret"].to_numpy(), r["Q"].to_numpy(), -1.0,
                                           pc_[rows ^ 1])):
            hg = home_group(home)
            b = np.digitize(np.nan_to_num(ev), EVIDENCE_BINS)
            names = (f"<{EVIDENCE_BINS[0]:g}", f"{EVIDENCE_BINS[0]:g}-{EVIDENCE_BINS[1]:g}", f"{EVIDENCE_BINS[1]:g}+")
            for h in ("MT", "low"):
                for i, name in enumerate(names):
                    m = (hg == h) & (b == i)
                    if m.sum() < 100:
                        continue
                    rate, se, G = cluster_se_ratio(sign * e[m], d[m], who[m])
                    out.append({"tour": tour, "stat": stat, "side": side, "home": h, "evidence": name,
                                "rows": int(m.sum()), "resid_per_100": 100 * rate, "se_per_100": 100 * se,
                                "players": G})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------
# Task 3, raw rates: the credibility estimator

def own_prior_sums(p: pd.DataFrame, stat: str, levels: list[str], window: int = WINDOW_DAYS) -> dict:
    """For every player row: the player's own box-score sums of `stat` (numerator X, units N) per level over his
    strictly earlier matches (Stage 0's order) of the previous `window` days."""
    ok = stat_ok(p, stat)
    o, lo = player_sequence(p, window)
    idx = np.arange(len(o))
    lev = p["bucket"].to_numpy()[o]
    xs = np.where(ok, p[f"{stat}_n"].to_numpy(float), 0.0)[o]
    ds = np.where(ok, p[f"{stat}_d"].to_numpy(float), 0.0)[o]
    out = {}
    for b in levels:
        m = lev == b
        for name, v in (("X", xs), ("N", ds)):
            cs = np.concatenate([[0.0], np.cumsum(np.where(m, v, 0.0))])
            arr = np.empty(len(p))
            arr[o] = cs[idx] - cs[lo]
            out[f"{name}_{b}"] = arr
    return out


def cred_theta(par: dict, D: dict, lower: list[str]) -> np.ndarray:
    k = par["k"]
    num = k * D["mu"] + D["X_MAIN"]
    den = k + D["N_MAIN"]
    for b in lower:
        w = par["w"].get(b, 0.0)
        if w:
            num = num + w * (D[f"X_{b}"] - par["delta"].get(b, 0.0) * D[f"N_{b}"])
            den = den + w * D[f"N_{b}"]
    return np.clip(num / den, 1e-4, 1 - 1e-4)


CRED_ARMS = ("main_only", "pooled", "translated", "discounted", "translated_discounted")


def cred_unpack(arm: str, v: np.ndarray, lower: list[str]) -> dict:
    """Parameter vector -> {k, delta{}, w{}} for an arm: [log k] + deltas (if fitted) + weights (if fitted)."""
    par = {"k": float(np.exp(v[0])), "delta": {}, "w": {}}
    i = 1
    if arm in ("translated", "translated_discounted"):
        for b in lower:
            par["delta"][b] = float(v[i])
            i += 1
    if arm in ("discounted", "translated_discounted"):
        for b in lower:
            par["w"][b] = float(v[i])
            i += 1
    elif arm in ("pooled", "translated"):
        par["w"] = {b: 1.0 for b in lower}
    return par


def cred_fit(D: dict, lower: list[str], arm: str, start: dict | None = None, single_start: bool = False) -> dict:
    """Maximum likelihood of the arm's parameters (binomial, per unit) with the analytic gradient. Two starts for a
    discounted arm (its weights from the start values and from 0.3), one when `single_start` (a bootstrap draw warm
    started at the full sample's fit)."""
    nd = len(lower) if arm in ("translated", "translated_discounted") else 0
    nw = len(lower) if arm in ("discounted", "translated_discounted") else 0
    v0 = [np.log(start["k"]) if start else np.log(50.0)]
    v0 += [start["delta"].get(b, 0.0) if start else 0.0 for b in lower][:nd]
    v0 += [start["w"].get(b, 0.5) if start else 0.5 for b in lower][:nw]
    bounds = [(-3.0, 12.0)] + [(-0.3, 0.3)] * nd + [(0.0, 3.0)] * nw
    U = D["d"].sum()
    scale = 1e5            # the per-unit loss moves by ~1e-6 per step: scaled so the optimiser's tolerances bite
    x, d, mu = D["x"], D["d"], D["mu"]

    def f(v):
        par = cred_unpack(arm, v, lower)
        k = par["k"]
        num = k * mu + D["X_MAIN"]
        den = k + D["N_MAIN"]
        for b in lower:
            w = par["w"].get(b, 0.0)
            if w:
                num = num + w * (D[f"X_{b}"] - par["delta"].get(b, 0.0) * D[f"N_{b}"])
                den = den + w * D[f"N_{b}"]
        raw = num / den
        th = np.clip(raw, 1e-4, 1 - 1e-4)
        ll = binom_ll(x, d, th).sum()
        g_th = np.where(raw == th, (d * th - x) / (th * (1 - th)), 0.0) / den      # dLL/dtheta x dtheta/d(num, den)
        grad = np.zeros(len(v))
        grad[0] = k * float(g_th @ (mu - th))
        i = 1
        if nd:
            for b in lower:
                grad[i] = -par["w"].get(b, 0.0) * float(g_th @ D[f"N_{b}"])
                i += 1
        if nw:
            for b in lower:
                grad[i] = float(g_th @ (D[f"X_{b}"] - par["delta"].get(b, 0.0) * D[f"N_{b}"] - th * D[f"N_{b}"]))
                i += 1
        return scale * float(ll / U), scale * grad / U
    starts = [np.array(v0, float)]
    if nw and not single_start:
        starts.append(np.r_[v0[:1 + nd], np.full(nw, 0.3)])
    best = None
    for start_v in starts:
        r = minimize(f, start_v, jac=True, method="L-BFGS-B", bounds=bounds,
                     options={"maxiter": 3000, "ftol": 1e-15, "gtol": 1e-8})
        if best is None or r.fun < best.fun:
            best = r
    par = cred_unpack(arm, best.x, lower)
    par["ll_per_unit"] = float(best.fun / scale)
    par["converged"] = bool(best.success)
    return par


def credibility(p: pd.DataFrame, hist: pd.DataFrame, means_main: dict, present: list[str], boot: int = 0,
                seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per tour and statistic: each arm fitted on the 2013-2018 main-tour targets and scored on 2019-2024 (and on its
    own window), gains (milli per unit, + = better) against 'pooled' and 'main_only' with player-clustered intervals,
    overall and for low-exposure targets; optional player bootstrap of the full arm's parameters."""
    params, scores = [], []
    rng = np.random.default_rng(seed)
    for stat in STATS:
        sums = own_prior_sums(p, stat, ["MAIN"] + present)
        ok = stat_ok(p, stat) & p["bucket"].eq("MAIN").to_numpy()
        mu = mu_rows(p, stat, means_main)
        for tour in TOURS:
            base = ok & (p["tour"].to_numpy() == tour)
            fits = {}
            data = {}
            for period, (lo, hi) in (("tune", TUNE), ("validate", VALIDATE)):
                m = base & p["year"].between(lo, hi).to_numpy()
                r = np.flatnonzero(m)
                Dd = {"x": p[f"{stat}_n"].to_numpy(float)[r], "d": p[f"{stat}_d"].to_numpy(float)[r], "mu": mu[r],
                      "player": p["pcode"].to_numpy()[r], "lowexp": hist["low_exposure"].to_numpy()[r]}
                for k_, v in sums.items():
                    Dd[k_] = v[r]
                data[period] = Dd
            lower = [b for b in present if data["tune"][f"N_{b}"].sum() > 0]
            for arm in CRED_ARMS:
                fits[arm] = cred_fit(data["tune"], lower, arm,
                                     start=fits.get("translated") if arm == "translated_discounted" else None)
                par = fits[arm]
                rec = {"tour": tour, "stat": stat, "arm": arm, "k": par["k"], "ll_tune": par["ll_per_unit"],
                       "converged": par["converged"]}
                for b in lower:
                    rec[f"delta_{b}"] = par["delta"].get(b, 0.0)
                    rec[f"w_{b}"] = par["w"].get(b, 0.0)
                params.append(rec)
            if boot and stat in ("spw", "rpw", "tpw", "hold", "brk", "first_won", "second_won", "ace"):
                players = np.unique(data["tune"]["player"])
                pos = pd.Series(np.arange(len(data["tune"]["player"]))).groupby(data["tune"]["player"]).apply(
                    lambda s: s.to_numpy())
                for bi in range(boot):
                    draw = rng.choice(players, size=len(players), replace=True)
                    idx = np.concatenate([pos[pl] for pl in draw])
                    Db = {k_: v[idx] for k_, v in data["tune"].items()}
                    par = cred_fit(Db, lower, "translated_discounted", start=fits["translated_discounted"],
                                   single_start=True)
                    rec = {"tour": tour, "stat": stat, "arm": f"boot{bi}", "k": par["k"], "ll_tune": par["ll_per_unit"],
                           "converged": par["converged"]}
                    for b in lower:
                        rec[f"delta_{b}"] = par["delta"].get(b, 0.0)
                        rec[f"w_{b}"] = par["w"].get(b, 0.0)
                    params.append(rec)
            for period in ("tune", "validate"):
                Dd = data[period]
                lls = {arm: binom_ll(Dd["x"], Dd["d"], cred_theta(fits[arm], Dd, lower)) for arm in CRED_ARMS}
                for gname, gm in (("all", np.ones(len(Dd["x"]), bool)), ("low_exposure", Dd["lowexp"]),
                                  ("has_lower", sum(Dd[f"N_{b}"] for b in lower) > 0)):
                    if gm.sum() < 50:
                        continue
                    for arm in CRED_ARMS:
                        for ref in ("pooled", "main_only"):
                            if arm == ref:
                                continue
                            gain, se, G = cluster_se_ratio(1000 * (lls[ref][gm] - lls[arm][gm]), Dd["d"][gm],
                                                           Dd["player"][gm])
                            scores.append({"tour": tour, "stat": stat, "period": period, "group": gname, "arm": arm,
                                           "vs": ref, "targets": int(gm.sum()),
                                           "ll_per_unit": float(lls[arm][gm].sum() / Dd["d"][gm].sum()),
                                           "gain_milli": gain, "se": se, "lo": gain - 1.96 * se,
                                           "hi": gain + 1.96 * se, "players": G})
        log(f"  credibility {stat} done")
    return pd.DataFrame(params), pd.DataFrame(scores)


def units_per_match(p: pd.DataFrame, present: list[str]) -> pd.DataFrame:
    """Mean units per box-score match of each statistic, per tour and level (2013-2024): the conversion from a
    per-unit exchange rate to matches."""
    rows = []
    for s in STATS:
        ok = stat_ok(p, s) & p["year"].between(TUNE[0], VALIDATE[1]).to_numpy()
        for tour in TOURS:
            for b in ["MAIN"] + present:
                m = ok & (p["tour"].to_numpy() == tour) & (p["bucket"].to_numpy() == b)
                if m.sum():
                    rows.append({"tour": tour, "stat": s, "level": b,
                                 "units_per_match": float(p[f"{s}_d"].to_numpy(float)[m].mean()),
                                 "matches": int(m.sum())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# Task 4: the results channel, a plain Elo with a K multiplier for Challenger and ITF results

def elo_matches(stage0_dir: Path, through: int) -> pd.DataFrame:
    m = allowed_matches(stage0_dir, through)
    m = m[m["status"].isin(["completed", "retired"])]
    ids = pa.array(m["match_id"].to_numpy())
    won = pq.read_table(Path(stage0_dir) / "stage0_matches.parquet", columns=["match_id", "a_won", "player_a_id",
                                                                               "player_b_id"],
                        filters=pc.field("match_id").isin(ids)).to_pandas()
    m = m.merge(won, on="match_id", how="inner", validate="one_to_one")
    C.assert_no_holdout_outcomes(m["date"], "translation.elo: match results")
    return m.sort_values("order").reset_index(drop=True)


def elo_run(a: np.ndarray, b: np.ndarray, y: np.ndarray, mult: np.ndarray) -> np.ndarray:
    """Plain Elo (FiveThirtyEight's K = 250 / (n + 5)^0.4), every match in order, each update multiplied by `mult`.
    Returns the pre-match probability that A wins."""
    n_pl = int(max(a.max(), b.max())) + 1
    R = [1500.0] * n_pl
    N = [0] * n_pl
    out = np.empty(len(a))
    al, bl, yl, ml = a.tolist(), b.tolist(), y.tolist(), mult.tolist()
    for i in range(len(al)):
        ia, ib = al[i], bl[i]
        pa_ = 1.0 / (1.0 + 10.0 ** ((R[ib] - R[ia]) / 400.0))
        out[i] = pa_
        if ml[i]:
            delta = yl[i] - pa_
            R[ia] += 250.0 / (N[ia] + 5) ** 0.4 * ml[i] * delta
            R[ib] -= 250.0 / (N[ib] + 5) ** 0.4 * ml[i] * delta
        N[ia] += 1
        N[ib] += 1
    return out


ELO_GRID = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25)


def elo_k(m: pd.DataFrame) -> pd.DataFrame:
    """K multipliers for Challenger-tier (CH, CHQ) and ITF-tier (ITF, ITFQ) results: one varied with the other at 1,
    and both together. Scored on main-tour matches 2013-2024 (raw Elo log loss), and with a per-tour slope fitted on
    2013-2018 applied to 2019-2024."""
    rows = []
    for tour in TOURS:
        t = m[m["tour"].eq(tour)].reset_index(drop=True)
        codes, _ = pd.factorize(np.concatenate([t["player_a_id"].to_numpy(), t["player_b_id"].to_numpy()]))
        a, b = codes[:len(t)], codes[len(t):]
        y = t["a_won"].astype(float).to_numpy()
        tier = t["bucket"].map(TIER_OF).to_numpy()
        is_ch, is_itf = tier == "CH", tier == "ITF"
        main = (t["bucket"].eq("MAIN") & t["year"].between(TUNE[0], VALIDATE[1])).to_numpy()
        tune = main & t["year"].between(*TUNE).to_numpy()
        val = main & t["year"].between(*VALIDATE).to_numpy()
        block = ((t["date"].to_numpy().astype("datetime64[D]").astype("int64") - ANCHOR) // 28)
        combos = sorted({(c, 1.0) for c in ELO_GRID} | {(1.0, i) for i in ELO_GRID} | {(g, g) for g in ELO_GRID})
        ref_ll = None
        lls = {}
        for mc, mi in combos:
            mult = np.where(is_ch, mc, np.where(is_itf, mi, 1.0))
            pa_ = elo_run(a, b, y, mult)
            lo = logit(np.clip(pa_, 1e-6, 1 - 1e-6))
            ll = -(y * np.log(np.clip(pa_, 1e-9, 1)) + (1 - y) * np.log(np.clip(1 - pa_, 1e-9, 1)))
            # slope on the tune seasons, applied to the validation seasons
            beta = 1.0
            for _ in range(30):
                pp = expit(beta * lo[tune])
                g_ = np.sum((y[tune] - pp) * lo[tune])
                h_ = np.sum(pp * (1 - pp) * lo[tune] ** 2)
                beta += g_ / h_
            pv = expit(beta * lo[val])
            llc = -(y[val] * np.log(pv) + (1 - y[val]) * np.log(1 - pv))
            lls[(mc, mi)] = (ll, llc, beta)
            if (mc, mi) == (1.0, 1.0):
                ref_ll = (ll, llc)
        for (mc, mi), (ll, llc, beta) in lls.items():
            for period, msk in (("2013-2024 raw", main), ("2019-2024 raw", val)):
                g, se, G = cluster_se_ratio(1000 * (ref_ll[0][msk] - ll[msk]), np.ones(msk.sum()), block[msk])
                rows.append({"tour": tour, "mult_CH": mc, "mult_ITF": mi, "score": period, "matches": int(msk.sum()),
                             "logloss": float(ll[msk].mean()), "gain_vs_1_mLL": g, "se": se,
                             "lo": g - 1.96 * se, "hi": g + 1.96 * se})
            g, se, G = cluster_se_ratio(1000 * (ref_ll[1] - llc), np.ones(len(llc)), block[val])
            rows.append({"tour": tour, "mult_CH": mc, "mult_ITF": mi, "score": "2019-2024 slope-calibrated",
                         "matches": int(val.sum()), "logloss": float(llc.mean()), "gain_vs_1_mLL": g, "se": se,
                         "lo": g - 1.96 * se, "hi": g + 1.96 * se, "slope_tune": beta})
        log(f"  elo {tour} done")
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# Task 5: ITF coverage (counts only)

def itf_coverage(stage0_dir: Path) -> pd.DataFrame:
    """Box-score coverage of ITF and ITFQ (and the other levels) by tour and year, every season including the
    holdout's: has_box counts only, no outcome read."""
    m = C.load_matches(stage0_dir, columns=["tour", "year", "map_level", "has_box", "status"])
    g = m.groupby(["tour", "bucket", "year"]).agg(matches=("has_box", "size"),
                                                   with_box=("has_box", lambda s: int(s.fillna(False).sum())))
    g["box_share"] = g["with_box"] / g["matches"]
    return g.reset_index()


# ------------------------------------------------------------------------------------------------
# Orchestration

def present_levels(p: pd.DataFrame) -> list[str]:
    """The lower levels with box scores in the read data (each gets its own delta and lambda)."""
    return [b for b in LEVELS[1:] if int((p["box"] & p["bucket"].eq(b)).sum()) >= MIN_ROWS]


def main_surface_means(p: pd.DataFrame, years: tuple[int, int] | None = None) -> dict:
    """Per tour and statistic: the main tour's own surface averages over the fit window (the raw estimator's prior
    mean)."""
    years = years or FIT_WINDOW
    g = p[p["bucket"].eq("MAIN") & p["box"] & p["year"].between(*years)]
    out = {}
    for s in STATS:
        ok = stat_ok(g, s)
        gs = g[ok]
        for tour in TOURS:
            t = gs[gs["tour"].eq(tour)]
            if not len(t):
                continue
            mu_all = float(t[f"{s}_n"].sum() / t[f"{s}_d"].sum())
            out[(tour, s, "all")] = mu_all
            for sf in CENTRE_SURFACES:
                ts = t[t["surface"].eq(sf)]
                out[(tour, s, sf)] = float(ts[f"{s}_n"].sum() / ts[f"{s}_d"].sum()) if len(ts) >= 300 else mu_all
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0-dir", default=str(C.STAGE0_DIR))
    ap.add_argument("--timing", default=str(C.TIMING))
    ap.add_argument("--through", type=int, default=2024)
    ap.add_argument("--label", default=LABEL)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--steps", default="gaps,effects,ios,credibility,elo,itf")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--systems", default=",".join(SYSTEMS), help="serve statistics for the effects/ios steps")
    ap.add_argument("--boot", type=int, default=0, help="player-bootstrap draws of the credibility parameters")
    ap.add_argument("--fit-window", default=f"{FIT_WINDOW[0]}-{FIT_WINDOW[1]}",
                    help="seasons of the batch fit whose delta and home-tier means the weekly arms use")
    ap.add_argument("--tune", default=f"{TUNE[0]}-{TUNE[1]}", help="seasons the credibility arms are fitted on")
    ap.add_argument("--validate", default=f"{VALIDATE[0]}-{VALIDATE[1]}", help="seasons every arm is scored on")
    a = ap.parse_args(argv)
    if a.through >= 2025:
        raise SystemExit("--through 2025 or later would read holdout outcomes")
    set_windows(span(a.fit_window), span(a.tune), span(a.validate))
    if VALIDATE[1] > a.through or TUNE[1] >= VALIDATE[0] or FIT_WINDOW[1] >= VALIDATE[0]:
        raise SystemExit("the fit window and tune seasons must end before the validation seasons, which must end by "
                         "--through")
    steps = set(a.steps.split(","))
    out = Path(a.out) / a.label
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    summary["run"] = {"stage0_dir": str(a.stage0_dir), "timing": str(a.timing), "through": a.through,
                      "label": a.label, "steps": sorted(steps), "ios_constants": IOS_VERSION,
                      "fit_window": list(FIT_WINDOW), "tune": list(TUNE), "validate": list(VALIDATE),
                      "boot": a.boot, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    p, info = load(Path(a.stage0_dir), a.through, Path(a.timing))
    summary["data"] = info
    log(f"loaded {info['player_rows']:,} player rows ({info['matches']:,} matches)")
    hist = own_history(p)
    present = present_levels(p)
    summary["levels_with_box_scores"] = present
    log(f"lower levels with box scores: {present}")

    if "gaps" in steps:
        g = raw_gaps(p)
        g.to_csv(out / "raw_gaps.csv", index=False)
        # the event-levels study's rule (completed and retired, any format; CH pooled with CHQ? no: CH vs MT and
        # TQ+GSQ vs MT) as a reproduction check of blend/level_shift.csv
        chk = raw_gaps(p, statuses=("completed", "retired"), standard_only=False,
                       pair_buckets={"CH": ("CH",), "Q": ("TQ", "GSQ")})
        chk.to_csv(out / "raw_gaps_blend_rule.csv", index=False)
        log("gaps done")

    if {"effects", "ios"} & steps:
        chosen, typ = ios_constants()
        means = surface_means(p)
        summary["surface_means_check"] = compare_means(means)
        systems = [s for s in a.systems.split(",") if s]
        jobs = []
        for tour in TOURS:
            for stat in systems:
                c = chosen[(tour, stat)]
                sd = system_arrays(p, hist, tour, stat, means, typ[(stat, tour)], c["tau"])
                jobs.append({"sd": sd, "h": c["h"], "kappa": c["kappa"], "present": present,
                             "windows": (FIT_WINDOW, TUNE, VALIDATE)})
        log(f"{len(jobs)} system jobs on {a.workers} workers")
        results = []
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for res in ex.map(run_system, jobs):
                results.append(res)
                log(f"  {res['tour']} {res['stat']}: effects {res['seconds']['effects']} s, "
                    f"weekly {res['seconds']['weekly']} s")
        eff = pd.DataFrame([r for res in results for r in res["effects"]])
        eff.to_csv(out / "level_effects.csv", index=False)
        pd.DataFrame([r for res in results for r in res["prior_means"]]).to_csv(out / "tier_prior_means.csv",
                                                                                index=False)
        summary["delta_used"] = {f"{r['tour']}|{r['stat']}": r["delta_used"] for r in results}
        summary["solver"] = {f"{r['tour']}|{r['stat']}": r["solver"] for r in results}
        if "ios" in steps:
            sc = pd.concat([score_arms(j["sd"], r) for j, r in zip(jobs, results)], ignore_index=True)
            sc.to_csv(out / "ios_arms.csv", index=False)
            pd.concat([arm_bias(p, j["sd"], r) for j, r in zip(jobs, results)], ignore_index=True).to_csv(
                out / "ios_arm_bias.csv", index=False)
            rr = {(r["tour"], r["stat"]): residual_rows(p, j["sd"], r) for j, r in zip(jobs, results)}
            residual_gaps(p, rr).to_csv(out / "residual_gaps.csv", index=False)
            residual_by_evidence(p, rr).to_csv(out / "residual_by_evidence.csv", index=False)
            b, s = residual_by_share(p, rr)
            b.to_csv(out / "residual_by_share.csv", index=False)
            s.to_csv(out / "residual_share_slopes.csv", index=False)
            # the evidence shares of main-tour rows (how much of each rating comes from lower levels)
            sh = []
            for (tour, stat), r in rr.items():
                mm = r[(r["lev"] == 0) & r["year"].between(TUNE[0], VALIDATE[1])]
                for side, col in (("serve", "share_srv"), ("return", "share_ret")):
                    v = mm[col].to_numpy()
                    v = v[np.isfinite(v)]
                    sh.append({"tour": tour, "stat": stat, "side": side, "rows": int(len(v)),
                               "mean_share": float(v.mean()), "median_share": float(np.median(v)),
                               "share_over_half": float((v > 0.5).mean())})
            pd.DataFrame(sh).to_csv(out / "evidence_shares.csv", index=False)
        log("effects / ios done")

    if "credibility" in steps:
        mm = main_surface_means(p)
        par, sc = credibility(p, hist, mm, present, boot=a.boot)
        par.to_csv(out / "credibility_params.csv", index=False)
        sc.to_csv(out / "credibility_scores.csv", index=False)
        units_per_match(p, present).to_csv(out / "units_per_match.csv", index=False)
        log("credibility done")

    if "elo" in steps:
        em = elo_matches(Path(a.stage0_dir), a.through)
        elo_k(em).to_csv(out / "elo_k.csv", index=False)
        log("elo done")

    if "itf" in steps:
        cov = itf_coverage(Path(a.stage0_dir))
        cov.to_csv(out / "coverage_by_level_year.csv", index=False)
        log("itf coverage done")

    summary["run"]["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    summary_path.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
