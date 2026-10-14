"""Stage 2 of the predictability diagnostic: anatomy of a win.

What decides a match, read from each match's own statistics. None of this is a pre-match forecast: every
number here uses the match's own box score, so it says how matches are won, not how to predict them.

    a  points to wins      the chance of winning against the share of all points won; how often the player
                           with fewer points won; by tour, best of, surface, level and era
    b  beyond points       break points and tiebreaks won above what the match's own point rates predict
                           (the iid model, stage2_iid.py), and the log loss they add to a logistic regression
                           on the points share
    c  randomness floor    the iid model's chance that A wins from the two players' serve-point rates in the
                           match: its log loss is a rough, optimistic floor, compared with Elo and the closing
                           odds of stage1_baselines; a simulation sizes the optimism
    d  persistence         each player's matches split into two random halves: do break-point and tiebreak
                           over-performance carry from one half to the other, as serve points won do?
    e  components          the points edge split exactly into aces, first serves in play, first serves in,
                           second serves in play, double faults and serve-point count; by tour and surface
    f  match impact        for every per-match rate of stage0_match_players, the log-loss improvement over a
                           coin of a one-input logistic regression on its A - B difference in the same match

The pure-luck twin. Every analysed match is replayed point by point under the iid model (stage2_iid.simulate)
with the same players, format and deciding-set rule, at "true" serve rates drawn from what the measured rates
allow (measured rates carry binomial noise; denoised_rates()). The replay's box scores go through the same
analyses, so each result has a benchmark: what pure scoring luck, with no skill on big points and no
streaks, would show. The twin also gives the floor that the plug-in one approximates: the log loss of a
forecaster who knew each player's true rates for the day (the entropy of the iid chance at the true rates).

The population (counted step by step in stage2_results.json): evaluation matches, WTA from 2019 (the Brief's
rule for box scores), completed, with a box score, in the standard format, and with a complete score. The
best of three or five is read from the score (the source mislabels Wimbledon's best-of-five final qualifying
round in several years). Retirements are set aside and reported apart: their box scores cover part of a
match decided by something else.

Writes, in data/studies/predictability_diagnostic/:
    stage2_matches.parquet        one row per analysed match: rates, the iid probability, over-performance,
                                  the points-edge components, the Stage 1 baselines, the twin's rates and result
    stage2_slam_rules_check.csv   each Grand Slam, draw and year: the deciding-set rule against its scores
    stage2_points_curve.csv       (a) share of player-matches won by points-share bin
    stage2_fewer_points.csv       (a) share of matches won with fewer points, by group
    stage2_beyond_points.csv      (b) log loss of the logistic regressions, by tour and best of, real and twin
    stage2_floor_cells.csv        (c) the floors against Elo and the market, by tour, window, best of and level
    stage2_floor_calibration.csv  (c) the plug-in floor's calibration
    stage2_persistence.csv        (d) split-half correlations, real and twin
    stage2_components.csv         (e) the points edge by component, tour and surface
    stage2_match_impact.csv       (f) every rate's match impact
    stage2_results.json           everything stage2.md and the report quote

Shared helper kept here rather than in common.py (Stage 3 may run beside this stage): oof_logit(), the
out-of-fold logistic regression without an intercept.

Run: ./python.sh src/eda/predictability_diagnostic/stage2_anatomy.py
"""
from __future__ import annotations

import itertools
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402
from src.eda.predictability_diagnostic.stage0_build import is_tiebreak, tokens_of  # noqa: E402

TABLE = C.OUT / "stage2_matches.parquet"
RULES_CHECK = C.OUT / "stage2_slam_rules_check.csv"
CURVE = C.OUT / "stage2_points_curve.csv"
FEWER = C.OUT / "stage2_fewer_points.csv"
BEYOND = C.OUT / "stage2_beyond_points.csv"
FLOOR_CELLS = C.OUT / "stage2_floor_cells.csv"
FLOOR_CAL = C.OUT / "stage2_floor_calibration.csv"
PERSIST = C.OUT / "stage2_persistence.csv"
COMPONENTS = C.OUT / "stage2_components.csv"
IMPACT = C.OUT / "stage2_match_impact.csv"
RESULTS = C.OUT / "stage2_results.json"

SEED = 20260930
EPS = 1e-12
FOLDS = 5
SPLITS = 50                              # random half-splits per tour in (d)
TWIN_REPLAYS = 5                         # pure-luck replays for (d)'s benchmark
TWIN_SPLITS = 20                         # random half-splits per replay
MIN_N = C.DIRECTIONAL_ONLY_BELOW
LEVEL_GROUPS = [("GS", "Grand Slams"), ("FIN", "Tour Finals"), ("T1000", "1000s"), ("T500", "500s"), ("T250", "250s"),
                ("GSQ", "Grand Slam qualifying"), ("TQ", "Tour qualifying"), ("CH", "Challenger / WTA 125"),
                ("CHQ", "Challenger / 125 qualifying")]
FORMATS = [("atp", 3, "ATP, best of 3"), ("atp", 5, "ATP, best of 5"), ("wta", 3, "WTA, best of 3")]
FIRST_YEAR = {"atp": 2013, "wta": C.WTA_BOX_FROM}
HEADLINE = (2022, 2026)
ELO = "p_elo_surf_ret"                   # Stage 1's charted rating: surface Elo, retirements counted
COMPONENT_NAMES = {"ace": "Aces", "first_play": "First serves in play", "first_in": "First serves in",
                   "second_play": "Second serves in play", "double_faults": "Double faults",
                   "serve_count": "Serve-point count"}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records"))


def window_name(tour: str) -> str:
    return f"{FIRST_YEAR[tour]}-2026"


# ------------------------------------------------------------------------------------------------
# Small statistics

def logloss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype="float64"), EPS, 1 - EPS)
    return np.where(np.asarray(y, dtype=bool), -np.log(p), -np.log(1 - p))


def gap(a: np.ndarray, b: np.ndarray) -> dict:
    """Mean of a - b in milli-log-loss (per-match losses on the same matches), with a 95% interval."""
    d = np.asarray(a) - np.asarray(b)
    n = len(d)
    if n < 2:
        return {"n": int(n)}
    mean, se = 1000 * d.mean(), 1000 * d.std(ddof=1) / np.sqrt(n)
    return {"n": int(n), "milli": round(float(mean), 2), "lo": round(float(mean - 1.96 * se), 2),
            "hi": round(float(mean + 1.96 * se), 2), "directional_only": bool(n < MIN_N)}


def oof_logit(X: np.ndarray, y: np.ndarray, seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    """Out-of-fold probabilities (5 folds) of a logistic regression without an intercept, and the coefficients
    fitted on all rows. No intercept: side A is random, so the chance is one half when the inputs are level."""
    X = np.asarray(X, dtype="float64").reshape(len(y), -1)
    y = np.asarray(y, dtype=bool)
    p = np.empty(len(y))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for tr, te in KFold(FOLDS, shuffle=True, random_state=seed).split(X):
            lr = LogisticRegression(fit_intercept=False, C=np.inf, max_iter=5000).fit(X[tr], y[tr])
            p[te] = lr.predict_proba(X[te])[:, 1]
        full = LogisticRegression(fit_intercept=False, C=np.inf, max_iter=5000).fit(X, y)
    return p, full.coef_[0]


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype="float64"), 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def fisher_ci(r: float, n: int) -> tuple[float, float]:
    if n < 4 or not np.isfinite(r):
        return np.nan, np.nan
    z, se = np.arctanh(np.clip(r, -0.999999, 0.999999)), 1 / np.sqrt(n - 3)
    return float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))


# ------------------------------------------------------------------------------------------------
# The analysis table

MATCH_COLS = ["match_id", "tour", "year", "era", "level", "map_level", "qualifying", "evaluation", "round", "surface",
              "best_of", "tournament_name", "tournament_date", "status", "score", "score_flag", "format", "has_box",
              "a_won", "player_a_id", "player_b_id"]
BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]


def score_info(scores: pd.Series) -> pd.DataFrame:
    """From each score: the number of sets written, and the last set's games and tiebreak."""
    info = {}
    for s in scores.unique():
        sets, _ = tokens_of(s)
        if sets:
            a, b, tb, br = sets[-1]
            info[s] = (len(sets), bool(is_tiebreak(a, b, tb, br, False)), max(a, b), min(a, b), tb, br)
        else:
            info[s] = (0, False, -1, -1, -1, False)
    cols = ["n_sets_written", "last_set_tb", "last_hi", "last_lo", "last_tb_points", "last_bracket"]
    return pd.DataFrame([info[s] for s in scores], columns=cols, index=scores.index)


def player_sides() -> pd.DataFrame:
    """One row per match: the A and B players' box counts and stored rates, suffixed _a and _b."""
    rate_cols = [f"{r}_{x}" for r in C.RATES for x in ("n", "d")]
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "player_id"] + BOX + rate_cols)
    a = mp[mp["side"].eq("A")].drop(columns="side").set_index("match_id").add_suffix("_a")
    b = mp[mp["side"].eq("B")].drop(columns="side").set_index("match_id").add_suffix("_b")
    return a.join(b, how="inner")


def build_table() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """The analysed matches (one row each, side A and B columns), the retirements set aside, and the counts."""
    m = C.load_matches(MATCH_COLS)
    sides = player_sides()
    steps = []

    def count(label, frame):
        steps.append({"step": label, **{t: int((frame["tour"] == t).sum()) for t in C.TOURS}})

    ev = m[m["evaluation"]]
    count("evaluation matches (Stage 0)", ev)
    ev = ev[ev["tour"].eq("atp") | (ev["year"] >= C.WTA_BOX_FROM)]
    count(f"WTA from {C.WTA_BOX_FROM} (the Brief's window for box-score evaluation)", ev)
    retired = ev[ev["status"].eq("retired")].join(sides, on="match_id")
    ev = ev[ev["status"].eq("completed")]
    count("completed (retirements set aside and reported apart)", ev)
    ev = ev[ev["has_box"]]
    count("with a box score that passed Stage 0's checks", ev)
    ev = ev[ev["format"].eq("standard")]
    count("standard format (Next Gen short sets and match tiebreaks left out)", ev)
    t = ev.join(sides, on="match_id").join(score_info(ev["score"]))
    won = t["a_won"].to_numpy()
    t["sets_w"] = np.where(won, t["sets_won_n_a"], t["sets_won_n_b"])
    t["sets_l"] = np.where(won, t["sets_won_n_b"], t["sets_won_n_a"])
    t["best_of_score"] = 2 * t["sets_w"] - 1
    complete = (t["best_of_score"].isin([3, 5]) & (t["sets_l"] < t["sets_w"])
                & (t["n_sets_written"] == t["sets_w"] + t["sets_l"]) & (t["svpt_a"] > 0) & (t["svpt_b"] > 0))
    t = t[complete].copy()
    count("a complete score (the winner took 2 of 3 or 3 of 5 sets, every set written)", t)
    # Stage 0 keeps a box score whose counts are all written; a count written as text that is not a number
    # (one Tennis My Life match) then reads as blank
    counts8 = [f"{b}_{s}" for b in BOX if b != "sv_gms" for s in ("a", "b")]
    t = t[t[counts8].notna().all(axis=1)].copy()
    count("every point and break-point count readable", t)
    kept = m[m["has_box"]].join(sides, on="match_id")
    blank = kept[kept[counts8].isna().any(axis=1)]
    stage0_blank = {"matches": int(len(blank)), "evaluation": int(blank["evaluation"].sum()),
                    "examples": blank["match_id"].head(5).tolist()}
    t["best_of_recorded"] = t["best_of"]
    t["best_of"] = t["best_of_score"].astype("int64")
    disagree = t[t["best_of"].ne(t["best_of_recorded"])]
    best_of_note = {"matches": int(len(disagree)),
                    "by_event": records(disagree.groupby(["tour", "tournament_name", "qualifying", "round", "year"]).size()
                                        .rename("matches").reset_index())}
    t["rule"] = M.deciding_set_rule(t["level"], t["tournament_name"], t["year"], t["qualifying"])
    t["deciding_played"] = t["sets_w"] + t["sets_l"] == t["best_of"]
    t["deciding_tb"] = t["deciding_played"] & t["last_set_tb"]
    t["level_group"] = t["map_level"]
    t["surface"] = t["surface"].fillna("unknown")
    return t.reset_index(drop=True), retired, {"steps": steps, "best_of_from_score": best_of_note,
                                               "stage0_kept_box_with_a_blank_count": stage0_blank}


def add_model_columns(t: pd.DataFrame) -> pd.DataFrame:
    """The match's own point rates, the iid model's chances, and over-performance against them."""
    pa = (t["spw_n_a"] / t["spw_d_a"]).to_numpy(dtype="float64")
    pb = (t["spw_n_b"] / t["spw_d_b"]).to_numpy(dtype="float64")
    t["pa"], t["pb"] = pa, pb
    t["tpw_a"] = t["tpw_n_a"] / t["tpw_d_a"]
    t["edge_a"] = t["tpw_a"] - 0.5
    t["p_floor"] = M.match_win_by(pa, pb, t["best_of"].to_numpy(), t["rule"].to_numpy())
    t["p_tb7"] = M.tiebreak(pa, pb, 7)
    target = M.tiebreak_target(t["rule"].to_numpy())
    p_dec = np.where(target == 10, M.tiebreak(pa, pb, 10), t["p_tb7"].to_numpy())
    t["n_tb"] = t["tb_won_d_a"].fillna(0).astype("int64")
    t["tb_won_a"] = t["tb_won_n_a"].fillna(0)
    dec = t["deciding_tb"].to_numpy().astype("float64")
    t["tb_exp_a"] = (t["n_tb"] - dec) * t["p_tb7"] + dec * p_dec
    t["tb_over_a"] = t["tb_won_a"] - t["tb_exp_a"]
    # break points: a break point is a serve point, won by the server with the match's serve rate under the iid
    # model; saved minus what that rate predicts. A's conversions over-perform by exactly what B's saves under-perform.
    t["bp_exp_saved_a"] = t["bp_faced_a"] * pa
    t["bp_exp_saved_b"] = t["bp_faced_b"] * pb
    t["bp_save_over_a"] = t["bp_saved_a"] - t["bp_exp_saved_a"]
    t["bp_save_over_b"] = t["bp_saved_b"] - t["bp_exp_saved_b"]
    t["bp_net_a"] = t["bp_save_over_a"] - t["bp_save_over_b"]
    return t


def add_components(t: pd.DataFrame) -> pd.DataFrame:
    """The points edge, tpw_A - 1/2, split exactly into six parts (A - B, midpoint rule).

    Per player, serve points won = fi * fw + (1 - fi) * sw, with first serves in fi, first-serve points won
    fw = ar + (1 - ar) * fwr (aces per first serve in, then first serves in play won) and second-serve points won
    sw = (1 - dr) * swi (double faults per second serve, then second serves in play won). The source does not say
    which serve an ace came on; every ace is counted against first serves (about 4% come on second serves in the
    Grand Slam point-by-point files). For a difference of products the midpoint rule is exact:
    d(xy) = mean(x) d(y) + mean(y) d(x). With w the player's share of the match's serve points,
    tpw_A - 1/2 = 1/2 (spw_A - spw_B) + (w_A - w_B) (mean(spw) - 1/2)."""
    def rates(s):
        F, P = t[f"first_in_{s}"], t[f"svpt_{s}"]
        S = P - F
        return {"fi": F / P, "ar": t[f"ace_{s}"] / F, "fwr": (t[f"first_won_{s}"] - t[f"ace_{s}"]) / (F - t[f"ace_{s}"]),
                "dr": t[f"df_{s}"] / S.where(S > 0), "swi": t[f"second_won_{s}"] / (S - t[f"df_{s}"]).where(S - t[f"df_{s}"] > 0),
                "fw": t[f"first_won_{s}"] / F, "sw": t[f"second_won_{s}"] / S.where(S > 0)}
    A, B = rates("a"), rates("b")
    mean = {k: (A[k] + B[k]) / 2 for k in A}
    d = {k: A[k] - B[k] for k in A}
    w_a = t["svpt_a"] / (t["svpt_a"] + t["svpt_b"])
    t["c_ace"] = 0.5 * mean["fi"] * (1 - mean["fwr"]) * d["ar"]
    t["c_first_play"] = 0.5 * mean["fi"] * (1 - mean["ar"]) * d["fwr"]
    t["c_first_in"] = 0.5 * d["fi"] * (mean["fw"] - mean["sw"])
    t["c_second_play"] = 0.5 * (1 - mean["fi"]) * (1 - mean["dr"]) * d["swi"]
    t["c_double_faults"] = -0.5 * (1 - mean["fi"]) * mean["swi"] * d["dr"]
    t["c_serve_count"] = (2 * w_a - 1) * ((t["pa"] + t["pb"]) / 2 - 0.5)
    for k in ("fi", "ar", "fwr", "dr", "swi"):
        t[f"d_{k}"] = d[k]
    return t


def attach_baselines(t: pd.DataFrame) -> pd.DataFrame:
    b = pd.read_parquet(C.OUT / "stage1_baselines.parquet", columns=["match_id", ELO, "p_market"])
    return t.merge(b, on="match_id", how="left", validate="one_to_one")


# ------------------------------------------------------------------------------------------------
# The Grand Slams' deciding-set rules against their scores

def rules_check() -> tuple[pd.DataFrame, dict]:
    """Every completed Grand Slam match whose score is complete and went to a deciding set, 2010 on: per Slam,
    draw and year, how its deciding sets ended, set against the rule in stage2_slam_final_set_rules.csv."""
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "tournament_name", "status", "score"])
    gs = m[m["level"].eq("GS") & m["status"].eq("completed")]
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "won", "sets_won_n"])
    w = mp[mp["won"]].set_index("match_id")["sets_won_n"]
    lo = mp[~mp["won"]].set_index("match_id")["sets_won_n"]
    gs = gs.assign(sets_w=gs["match_id"].map(w), sets_l=gs["match_id"].map(lo)).join(score_info(gs["score"]))
    gs = gs[gs["sets_w"].isin([2, 3]) & (gs["sets_l"] == gs["sets_w"] - 1) & (gs["n_sets_written"] == 2 * gs["sets_w"] - 1)]
    gs = gs.assign(slam=gs["tournament_name"].map(M.slam_of), draw=np.where(gs["qualifying"], "qualifying", "main"),
                   rule=M.deciding_set_rule(gs["level"], gs["tournament_name"], gs["year"], gs["qualifying"]))
    gs["kind"] = np.select([(gs["last_hi"] == 13) & (gs["last_lo"] == 12), gs["last_hi"] > 7,
                            (gs["last_hi"] == 7) & (gs["last_lo"] == 6)], ["13-12", "long", "7-6"], "6-x or 7-5")
    rows = []
    for (slam, draw, year, rule), g in gs.groupby(["slam", "draw", "year", "rule"]):
        k = g["kind"].value_counts()
        tbp = g.loc[g["last_set_tb"] & (g["last_tb_points"] >= 0), "last_tb_points"]
        long_, t1312, t76 = int(k.get("long", 0)), int(k.get("13-12", 0)), int(k.get("7-6", 0))
        ok = {"ADV": t76 == 0 and t1312 == 0, "TB7@12": t76 == 0 and int(g["last_hi"].max()) <= 13,
              "TB7@6": long_ == 0 and t1312 == 0, "TB10@6": long_ == 0 and t1312 == 0}[rule]
        rows.append({"slam": slam, "draw": draw, "year": int(year), "rule": rule, "deciding_sets": int(len(g)),
                     "longer_than_7_games": long_, "ended_13_12": t1312, "ended_7_6": t76,
                     "most_games_won_in_it": int(g["last_hi"].max()),
                     "tiebreak_loser_points_mean": round(float(tbp.mean()), 2) if len(tbp) else None,
                     "consistent_with_rule": bool(ok)})
    out = pd.DataFrame(rows)
    out.to_csv(RULES_CHECK, index=False)
    by_rule = gs.groupby("rule")["last_tb_points"].apply(lambda s: round(float(s[s >= 0].mean()), 2) if (s >= 0).any() else None)
    return out, {"cells": int(len(out)), "inconsistent": records(out[~out["consistent_with_rule"]]),
                 "tiebreak_loser_points_mean_by_rule": by_rule.to_dict()}


# ------------------------------------------------------------------------------------------------
# The pure-luck twin: the same matches replayed as if every point were an independent draw

def denoised_rates(t: pd.DataFrame, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, list]:
    """A 'true' serve rate for each player in each match, drawn from what the measured rate allows.

    A rate measured on n serve points carries binomial noise of variance p(1 - p) / n, so measured rates are
    more spread out than true ones. Per tour and surface, the variance of true rates is that of measured rates
    less the average noise; each measured rate is shrunk toward the group's mean by the share of its variance
    that is true, and a true rate is drawn from the normal posterior around it (empirical Bayes). Surfaces
    with under 400 player-matches in a tour use the tour's mean and spread."""
    n = len(t)
    P = np.concatenate([t["pa"].to_numpy(), t["pb"].to_numpy()])
    N = np.concatenate([t["svpt_a"].to_numpy(), t["svpt_b"].to_numpy()]).astype("float64")
    tour = np.concatenate([t["tour"].to_numpy()] * 2).astype(str)
    surf = np.concatenate([t["surface"].to_numpy()] * 2).astype(str)
    noise = P * (1 - P) / N

    def prior(mask):
        mu, var = float(P[mask].mean()), float(P[mask].var())
        return mu, max(var - float(noise[mask].mean()), 1e-6), var

    draw, rows = np.empty_like(P), []
    for tr in np.unique(tour):
        whole = prior(tour == tr)
        for sf in np.unique(surf[tour == tr]):
            m = (tour == tr) & (surf == sf)
            mu, vt, var = prior(m) if m.sum() >= 400 else whole
            shrink = vt / (vt + noise[m])
            draw[m] = rng.normal(mu + shrink * (P[m] - mu), np.sqrt(shrink * noise[m]))
            rows.append({"tour": tr, "surface": sf, "player_matches": int(m.sum()), "own_prior": bool(m.sum() >= 400),
                         "mean": round(mu, 4), "measured_var": round(var, 6), "true_var": round(vt, 6),
                         "true_share_of_var": round(vt / var, 3), "mean_shrink": round(float(shrink.mean()), 3)})
    draw = np.clip(draw, 0.02, 0.98)
    return draw[:n], draw[n:], rows


def twin(t: pd.DataFrame, seed: int, denoise: bool = True) -> tuple[pd.DataFrame, list]:
    """Replay every analysed match point by point under the iid model (same players, format and deciding-set
    rule), at de-noised rates (or, with ``denoise=False``, at the measured rates), and build the box score the
    replay shows, with the same columns the analyses read."""
    rng = np.random.default_rng(seed)
    if denoise:
        pa, pb, prior = denoised_rates(t, rng)
    else:
        pa, pb, prior = t["pa"].to_numpy(), t["pb"].to_numpy(), []
    sim = M.simulate(pa, pb, t["best_of"].to_numpy(), t["rule"].to_numpy(), seed=seed + 1)
    tw = t[["match_id", "tour", "year", "era", "level_group", "surface", "best_of", "rule", "player_id_a", "player_id_b"]].copy()
    tw["a_won"] = sim["a_won"]
    for j, s in enumerate(("a", "b")):
        o = 1 - j
        tw[f"svpt_{s}"] = sim["served"][:, j]
        tw[f"spw_n_{s}"], tw[f"spw_d_{s}"] = sim["won"][:, j], sim["served"][:, j]
        tw[f"rpw_n_{s}"], tw[f"rpw_d_{s}"] = sim["served"][:, o] - sim["won"][:, o], sim["served"][:, o]
        tw[f"bp_faced_{s}"], tw[f"bp_saved_{s}"] = sim["bp_faced"][:, j], sim["bp_saved"][:, j]
    tw["tpw_n_a"], tw["tpw_n_b"] = tw["spw_n_a"] + tw["rpw_n_a"], tw["spw_n_b"] + tw["rpw_n_b"]
    tw["tpw_d_a"] = tw["svpt_a"] + tw["svpt_b"]
    tw["tb_won_d_a"], tw["tb_won_n_a"] = sim["tiebreaks"], sim["tb_won"][:, 0]
    tw["deciding_tb"] = sim["deciding_tb"]
    tw = add_model_columns(tw)
    tw["pa_true"], tw["pb_true"] = pa, pb
    tw["p_true"] = M.match_win_by(pa, pb, t["best_of"].to_numpy(), t["rule"].to_numpy())
    return tw, prior


def entropy(p: np.ndarray) -> np.ndarray:
    """The expected log loss of a forecaster who gives p and is right about it: -(p ln p + (1-p) ln(1-p))."""
    p = np.clip(np.asarray(p, dtype="float64"), EPS, 1 - EPS)
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def fit_summary(t: pd.DataFrame) -> dict:
    """How a world looks, for setting a replay beside the real matches: per tour, the plug-in floor's log loss,
    the spread of points shares, matches won with fewer points, tiebreaks per match, and break points saved
    against the match's own serve rate."""
    out = {}
    for tour in C.TOURS:
        g = t[t["tour"].eq(tour)]
        fewer = g["tpw_n_a"].lt(g["tpw_n_b"]).where(g["a_won"], g["tpw_n_b"].lt(g["tpw_n_a"]))
        faced = g["bp_faced_a"].sum() + g["bp_faced_b"].sum()
        out[tour] = {"matches": int(len(g)), "plug_in_floor_logloss": float(logloss(g["p_floor"], g["a_won"]).mean()),
                     "points_share_sd_points": round(100 * float(g["tpw_a"].std()), 3),
                     "serve_rate_sd_points": round(100 * float(np.concatenate([g["pa"], g["pb"]]).std()), 3),
                     "won_with_fewer_points_pct": round(100 * float(fewer.mean()), 2),
                     "tiebreaks_per_match": round(float(g["n_tb"].mean()), 4),
                     "matches_with_tiebreak_pct": round(100 * float((g["n_tb"] > 0).mean()), 2),
                     "bp_saved_pct": round(100 * float((g["bp_saved_a"].sum() + g["bp_saved_b"].sum()) / faced), 3),
                     "bp_expected_saved_pct": round(100 * float((g["bp_exp_saved_a"].sum() + g["bp_exp_saved_b"].sum()) / faced), 3),
                     "break_points_per_match": round(float(faced / len(g)), 3)}
    return out


def format_fits(t: pd.DataFrame) -> list:
    """Per tour and best of: the logistic regression of the result on the points share (in points above 50%),
    and how often the player with fewer points won."""
    fits = []
    for tour, bo, label in FORMATS:
        g = t[t["tour"].eq(tour) & t["best_of"].eq(bo)]
        x = 100 * g["edge_a"].to_numpy()
        p, coef = oof_logit(x, g["a_won"].to_numpy())
        beta = float(coef[0])
        fewer = g["tpw_n_a"].lt(g["tpw_n_b"]).where(g["a_won"], g["tpw_n_b"].lt(g["tpw_n_a"]))
        fits.append({"tour": tour, "best_of": bo, "label": label, "matches": int(len(g)), "slope_per_point": round(beta, 4),
                     "odds_per_point": round(float(np.exp(beta)), 3),
                     "share_for_75pct": round(50 + np.log(3) / beta, 2), "share_for_90pct": round(50 + np.log(9) / beta, 2),
                     "cv_logloss": float(logloss(p, g["a_won"]).mean()),
                     "won_with_fewer_points_pct": round(100 * float(fewer.mean()), 2),
                     "mean_winner_share": round(float(np.where(g["a_won"], g["tpw_a"], 1 - g["tpw_a"]).mean() * 100), 2)})
    return fits


# ------------------------------------------------------------------------------------------------
# (a) points to wins

def points_curve(t: pd.DataFrame) -> pd.DataFrame:
    """Share of player-matches won, by the share of all points the player won (bins one point wide, centred on
    whole percentages). Both players of each match are counted, so the curve is symmetric about 50%."""
    rows = []
    for tour, bo, label in FORMATS:
        g = t[t["tour"].eq(tour) & t["best_of"].eq(bo)]
        x = np.concatenate([g["tpw_a"].to_numpy(), 1 - g["tpw_a"].to_numpy()])
        y = np.concatenate([g["a_won"].to_numpy(), ~g["a_won"].to_numpy()])
        b = np.round(100 * x).astype(int)
        d = pd.DataFrame({"bin": b, "won": y}).groupby("bin")["won"].agg(["size", "mean"]).reset_index()
        for r in d.itertuples():
            rows.append({"tour": tour, "best_of": bo, "label": label, "points_share_pct": int(r.bin),
                         "player_matches": int(r.size), "won_pct": round(100 * float(r.mean), 2)})
    return pd.DataFrame(rows)


def points_to_wins(t: pd.DataFrame, retired: pd.DataFrame, tw: pd.DataFrame) -> dict:
    curve = pd.concat([points_curve(t).assign(world="real"), points_curve(tw).assign(world="pure luck")], ignore_index=True)
    curve.to_csv(CURVE, index=False)

    t = t.assign(fewer=t["tpw_n_a"].lt(t["tpw_n_b"]).where(t["a_won"], t["tpw_n_b"].lt(t["tpw_n_a"])),
                 equal=t["tpw_n_a"].eq(t["tpw_n_b"]),
                 window=np.where(t["year"] >= HEADLINE[0], "2022-2026", "earlier"))
    dims = {"all": [], "best_of": ["best_of"], "surface": ["surface"], "level": ["level_group"], "era": ["era"],
            "window": ["window"], "best_of_surface": ["best_of", "surface"], "best_of_level": ["best_of", "level_group"]}
    fewer = []
    for dim, keys in dims.items():
        for key, g in t.groupby(["tour"] + keys, observed=True):
            key = key if isinstance(key, tuple) else (key,)
            fewer.append({"dim": dim, "tour": key[0], **{k: v for k, v in zip(keys, key[1:])}, "matches": int(len(g)),
                          "won_with_fewer_points_pct": round(100 * float(g["fewer"].mean()), 2),
                          "equal_points_pct": round(100 * float(g["equal"].mean()), 2),
                          "directional_only": bool(len(g) < MIN_N)})
    fewer = pd.DataFrame(fewer)
    for c in ("best_of", "surface", "level_group", "era", "window"):
        if c not in fewer:
            fewer[c] = None
    fewer.to_csv(FEWER, index=False)

    fits = format_fits(t)
    rb = retired[retired["has_box"] & (retired["svpt_a"] > 0) & (retired["svpt_b"] > 0)]
    rb_w = np.where(rb["a_won"], rb["tpw_n_a"], rb["tpw_n_b"])
    rb_l = np.where(rb["a_won"], rb["tpw_n_b"], rb["tpw_n_a"])
    ret = [{"tour": tour, "matches": int((rb["tour"] == tour).sum()),
            "advanced_with_fewer_points_pct": round(100 * float((rb_w < rb_l)[rb["tour"].to_numpy() == tour].mean()), 2)}
           for tour in C.TOURS]
    return {"fits": fits, "fits_pure_luck": format_fits(tw), "fewer_rows": records(fewer), "retirements": ret,
            "curve": records(curve), "curve_min_rows_to_show": 100}


# ------------------------------------------------------------------------------------------------
# (b) beyond points: break points and tiebreaks

def beyond_points(t: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Logistic regressions of the result on the points share (or the iid model's chance), with and without
    break-point and tiebreak over-performance; and break points and tiebreaks against expectation."""
    out_rows, desc = [], []
    groups = [(tour, None, f"{tour.upper()}, all") for tour in C.TOURS] + FORMATS[:2]
    for tour, bo, label in groups:
        g = t[t["tour"].eq(tour) & (t["best_of"].eq(bo) if bo else True)]
        y = g["a_won"].to_numpy()
        base_pts = 100 * g["edge_a"].to_numpy()
        base_iid = logit(g["p_floor"].to_numpy())
        bp, tb = g["bp_net_a"].to_numpy(), g["tb_over_a"].to_numpy()
        specs = {"points": [base_pts], "points + break points": [base_pts, bp], "points + tiebreaks": [base_pts, tb],
                 "points + both": [base_pts, bp, tb], "iid model": [base_iid], "iid model + break points": [base_iid, bp],
                 "iid model + tiebreaks": [base_iid, tb], "iid model + both": [base_iid, bp, tb]}
        ll, coefs = {}, {}
        for name, cols in specs.items():
            p, coef = oof_logit(np.column_stack(cols), y)
            ll[name], coefs[name] = logloss(p, y), [round(float(c), 5) for c in coef]
        coin = np.log(2)
        for name in specs:
            base = "points" if name.startswith("points") else "iid model"
            out_rows.append({"tour": tour, "best_of": bo or "all", "label": label, "model": name, "matches": int(len(g)),
                             "cv_logloss": float(ll[name].mean()), "better_than_coin_milli": 1000 * (coin - float(ll[name].mean())),
                             "gain_over_base_milli": gap(ll[base], ll[name]), "coefficients": coefs[name]})
        # descriptive: break points and tiebreaks against expectation, all players and by result
        rows = pd.concat([pd.DataFrame({"won": g["a_won"].to_numpy(), "faced": g["bp_faced_a"], "saved": g["bp_saved_a"],
                                        "exp": g["bp_exp_saved_a"], "tb": g["tb_won_a"], "tb_exp": g["tb_exp_a"], "n_tb": g["n_tb"]}),
                          pd.DataFrame({"won": ~g["a_won"].to_numpy(), "faced": g["bp_faced_b"], "saved": g["bp_saved_b"],
                                        "exp": g["bp_exp_saved_b"], "tb": g["n_tb"] - g["tb_won_a"],
                                        "tb_exp": g["n_tb"] - g["tb_exp_a"], "n_tb": g["n_tb"]})], ignore_index=True)

        def bp_line(r):
            return {"break_points_faced": int(r["faced"].sum()), "saved_pct": round(100 * float(r["saved"].sum() / r["faced"].sum()), 2),
                    "expected_saved_pct": round(100 * float(r["exp"].sum() / r["faced"].sum()), 2),
                    "tiebreaks": int(r["n_tb"].sum()),
                    "tiebreaks_won_pct": round(100 * float(r["tb"].sum() / max(r["n_tb"].sum(), 1)), 2),
                    "tiebreaks_expected_pct": round(100 * float(r["tb_exp"].sum() / max(r["n_tb"].sum(), 1)), 2)}
        fewer = g["tpw_n_a"].lt(g["tpw_n_b"]).where(g["a_won"], g["tpw_n_b"].lt(g["tpw_n_a"]))
        sign = np.where(g["a_won"], 1.0, -1.0)
        wbp, wtb = sign * g["bp_net_a"].to_numpy(), sign * g["tb_over_a"].to_numpy()
        f = fewer.to_numpy()
        desc.append({"tour": tour, "best_of": bo or "all", "label": label, "matches": int(len(g)),
                     "all_players": bp_line(rows), "winners": bp_line(rows[rows["won"]]), "losers": bp_line(rows[~rows["won"]]),
                     "bp_net_sd": round(float(g["bp_net_a"].std()), 3),
                     "winner_bp_net_mean": round(float(wbp.mean()), 3), "winner_tb_over_mean": round(float(wtb.mean()), 3),
                     "matches_with_tiebreak_pct": round(100 * float((g["n_tb"] > 0).mean()), 2),
                     "won_with_fewer_points": int(f.sum()),
                     "of_those_ahead_on_break_points_pct": round(100 * float((wbp[f] > 0).mean()), 2) if f.any() else None,
                     "of_those_ahead_on_tiebreaks_pct": round(100 * float((wtb[f] > 0).mean()), 2) if f.any() else None,
                     "of_those_ahead_on_either_pct": round(100 * float(((wbp[f] > 0) | (wtb[f] > 0)).mean()), 2) if f.any() else None})
    return pd.DataFrame(out_rows), desc


# ------------------------------------------------------------------------------------------------
# (c) the randomness floor

def floor(t: pd.DataFrame, tw: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """The plug-in floor (the iid model's chance from the rates measured in the match) against Elo and the market;
    and, from the pure-luck twin, the log loss of a forecaster who knew each player's true rates for the day (the
    entropy of the twin's chance at its true rates) and the plug-in floor the twin itself shows (a check that the
    twin looks like the real matches)."""
    t = t.assign(ll_floor=logloss(t["p_floor"], t["a_won"]), ll_elo=logloss(t[ELO], t["a_won"]),
                 ll_market=logloss(t["p_market"].fillna(0.5), t["a_won"]),
                 luck=entropy(tw["p_true"].to_numpy()), measured_entropy=entropy(t["p_floor"].to_numpy()),
                 twin_plugin=logloss(tw["p_floor"].to_numpy(), tw["a_won"].to_numpy()))

    def cell(g, odds_only):
        g = g[g["p_market"].notna()] if odds_only else g
        if len(g) == 0:
            return None
        o = {"matches": int(len(g)), "floor": float(g["ll_floor"].mean()), "elo": float(g["ll_elo"].mean()),
             "luck": float(g["luck"].mean()), "twin_plugin": float(g["twin_plugin"].mean()),
             "measured_entropy": float(g["measured_entropy"].mean()),
             "elo_minus_floor": gap(g["ll_elo"], g["ll_floor"]), "elo_minus_luck": gap(g["ll_elo"], g["luck"]),
             "directional_only": bool(len(g) < MIN_N)}
        if odds_only:
            o["market"] = float(g["ll_market"].mean())
            o["market_minus_floor"] = gap(g["ll_market"], g["ll_floor"])
            o["market_minus_luck"] = gap(g["ll_market"], g["luck"])
        return o

    rows = []
    for tour in C.TOURS:
        for win, years in ((window_name(tour), (FIRST_YEAR[tour], 2026)), ("2022-2026", HEADLINE)):
            base = t[t["tour"].eq(tour) & t["year"].between(*years)]
            splits = [("all", None, base)] + [("best_of", bo, base[base["best_of"].eq(bo)]) for bo in (3, 5)] \
                + [("level", lg, base[base["level_group"].eq(lg)]) for lg, _ in LEVEL_GROUPS]
            for dim, val, g in splits:
                if len(g) == 0:
                    continue
                for odds_only in (False, True):
                    c = cell(g, odds_only)
                    if c:
                        rows.append({"tour": tour, "window": win, "dim": dim, "value": val, "odds_only": odds_only, **c})
    cells = pd.DataFrame(rows)
    flat = cells.copy()
    for col in ("elo_minus_floor", "elo_minus_luck", "market_minus_floor", "market_minus_luck"):
        flat[col] = flat[col].map(lambda d: d.get("milli") if isinstance(d, dict) else None)
    flat.to_csv(FLOOR_CELLS, index=False)

    # calibration of the floor, and a refit of its slope (1 = calibrated, below 1 = too sure)
    cal, slope = [], []
    edges = np.round(np.arange(0.5, 1.0001, 0.05), 2)
    for tour in C.TOURS:
        g = t[t["tour"].eq(tour)]
        p, y = g["p_floor"].to_numpy(), g["a_won"].to_numpy()
        fav, fav_won = np.maximum(p, 1 - p), np.where(p >= 0.5, y, ~y)
        b = np.clip(np.digitize(fav, edges[1:-1]), 0, len(edges) - 2)
        for i in range(len(edges) - 1):
            s = b == i
            cal.append({"tour": tour, "bin": f"{edges[i]:.2f}-{edges[i + 1]:.2f}", "matches": int(s.sum()),
                        "mean_p": float(fav[s].mean()) if s.any() else None, "won": float(fav_won[s].mean()) if s.any() else None})
        po, coef = oof_logit(logit(p), y)
        gt = tw[tw["tour"].eq(tour)]
        _, coef_tw = oof_logit(logit(gt["p_floor"].to_numpy()), gt["a_won"].to_numpy())
        slope.append({"tour": tour, "slope": round(float(coef[0]), 4), "refit_logloss": float(logloss(po, y).mean()),
                      "floor_logloss": float(logloss(p, y).mean()), "twin_slope": round(float(coef_tw[0]), 4)})
    pd.DataFrame(cal).to_csv(FLOOR_CAL, index=False)
    return {"cells": json.loads(cells.to_json(orient="records")), "calibration": cal, "slope": slope}, t


# ------------------------------------------------------------------------------------------------
# (d) persistence

def persistence(t: pd.DataFrame, splits: int = SPLITS) -> pd.DataFrame:
    """Split each player's matches into two random halves; correlate, across players, a measure in one half
    with the same measure in the other (the mean over ``splits`` random splits). Serve and return points won
    are the yardsticks of a stable trait."""
    def side(s, o):
        won = t["a_won"] if s == "a" else ~t["a_won"]
        return pd.DataFrame({
            "tour": t["tour"], "player": t[f"player_id_{s}"], "won": won,
            "bp_faced": t[f"bp_faced_{s}"], "bp_saved": t[f"bp_saved_{s}"], "bp_exp_saved": t[f"bp_exp_saved_{s}"],
            "bp_chances": t[f"bp_faced_{o}"], "bp_conv": t[f"bp_faced_{o}"] - t[f"bp_saved_{o}"],
            "bp_exp_conv": t[f"bp_faced_{o}"] - t[f"bp_exp_saved_{o}"],
            "tb": t["n_tb"], "tb_won": t["tb_won_a"] if s == "a" else t["n_tb"] - t["tb_won_a"],
            "tb_exp": t["tb_exp_a"] if s == "a" else t["n_tb"] - t["tb_exp_a"],
            "sv": t[f"spw_d_{s}"], "sv_won": t[f"spw_n_{s}"], "rt": t[f"rpw_d_{s}"], "rt_won": t[f"rpw_n_{s}"]})
    rows = pd.concat([side("a", "b"), side("b", "a")], ignore_index=True)
    sums = ["bp_faced", "bp_saved", "bp_exp_saved", "bp_chances", "bp_conv", "bp_exp_conv", "tb", "tb_won", "tb_exp",
            "sv", "sv_won", "rt", "rt_won"]
    measures = {
        "bp_saved_over": ("Break points saved above the serve rate", lambda h: (h["bp_saved"] - h["bp_exp_saved"]) / h["bp_faced"], "bp_faced", 20),
        "bp_converted_over": ("Break points converted above the return rate", lambda h: (h["bp_conv"] - h["bp_exp_conv"]) / h["bp_chances"], "bp_chances", 20),
        "bp_both_over": ("Break points won above expectation, serving and returning",
                         lambda h: (h["bp_saved"] - h["bp_exp_saved"] + h["bp_conv"] - h["bp_exp_conv"]) / (h["bp_faced"] + h["bp_chances"]),
                         "bp_both", 40),
        "tb_over": ("Tiebreaks won above the point rates", lambda h: (h["tb_won"] - h["tb_exp"]) / h["tb"], "tb", 5),
        "spw": ("Serve points won (yardstick)", lambda h: h["sv_won"] / h["sv"], "sv", 0),
        "rpw": ("Return points won (yardstick)", lambda h: h["rt_won"] / h["rt"], "rt", 0),
    }
    rng = np.random.default_rng(SEED)
    out = []
    for tour in C.TOURS:
        r = rows[rows["tour"].eq(tour)].reset_index(drop=True)
        n_matches = r.groupby("player").size()
        for min_half in (10, 25, 50):
            keep = n_matches.index[n_matches >= 2 * min_half]
            rr = r[r["player"].isin(keep)].reset_index(drop=True)
            res = {k: [] for k in measures}
            npl = {k: [] for k in measures}
            for _ in range(splits):
                key = rng.random(len(rr))
                half = rr.assign(k=key).groupby("player")["k"].rank(method="first").astype(int) % 2
                h = rr[sums].groupby([rr["player"], half]).sum()
                h["bp_both"] = h["bp_faced"] + h["bp_chances"]
                for name, (_, fn, denom, min_den) in measures.items():
                    v = fn(h).unstack()
                    den = h[denom].unstack()
                    ok = (den >= max(min_den, 1)).all(axis=1) & v.notna().all(axis=1)
                    v = v[ok]
                    res[name].append(float(np.corrcoef(v[0], v[1])[0, 1]) if len(v) > 3 else np.nan)
                    npl[name].append(int(len(v)))
            for name, (label, _, denom, min_den) in measures.items():
                rs = np.array(res[name])
                n = int(np.median(npl[name]))
                mean_r = float(np.nanmean(rs))
                lo, hi = fisher_ci(mean_r, n)
                out.append({"tour": tour, "min_matches_per_half": min_half, "measure": name, "label": label,
                            "min_per_half": f"{min_den} {denom}" if min_den else "", "players": n,
                            "r_mean": round(mean_r, 4), "r_split_p2_5": round(float(np.nanpercentile(rs, 2.5)), 4),
                            "r_split_p97_5": round(float(np.nanpercentile(rs, 97.5)), 4),
                            "r_ci_lo": round(lo, 4), "r_ci_hi": round(hi, 4),
                            "full_reliability": round(2 * mean_r / (1 + mean_r), 4) if mean_r > -1 else None})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------
# (e) components of the points edge

def components(t: pd.DataFrame) -> dict:
    parts = [f"c_{k}" for k in COMPONENT_NAMES]
    # a rate must exist (a player with no second serve has none) and lie in [0, 1]: in a few box scores more
    # second-serve points were won than second serves were in play, which cannot happen
    in_range = pd.Series(True, index=t.index)
    for s in ("a", "b"):
        S, F = t[f"svpt_{s}"] - t[f"first_in_{s}"], t[f"first_in_{s}"]
        in_range &= (t[f"second_won_{s}"] <= S - t[f"df_{s}"]) & (t[f"first_won_{s}"] - t[f"ace_{s}"] <= F - t[f"ace_{s}"])
    ok = t[parts].notna().all(axis=1) & in_range
    g_all = t[ok]
    resid = (g_all[parts].sum(axis=1) - g_all["edge_a"]).abs().max()
    rows = []
    for tour in C.TOURS:
        for surf in ("all", "Hard", "Clay", "Grass", "Carpet"):
            g = g_all[g_all["tour"].eq(tour) & (g_all["surface"].eq(surf) if surf != "all" else True)]
            if len(g) == 0:
                continue
            e = g["edge_a"].to_numpy()
            sign = np.where(g["a_won"], 1.0, -1.0)
            row = {"tour": tour, "surface": surf, "matches": int(len(g)), "directional_only": bool(len(g) < MIN_N),
                   "winner_edge_points": round(100 * float((sign * e).mean()), 3)}
            for k in COMPONENT_NAMES:
                c = g[f"c_{k}"].to_numpy()
                row[f"winner_{k}_points"] = round(100 * float((sign * c).mean()), 3)
                row[f"variance_share_{k}_pct"] = round(100 * float((c * e).sum() / (e * e).sum()), 2)
            # the same split as a regression of the points edge on the six differences, with Shapley shares of R^2
            X = np.column_stack([g["d_fi"], g["d_ar"], g["d_fwr"], g["d_dr"], g["d_swi"], (2 * g["svpt_a"] / (g["svpt_a"] + g["svpt_b"]) - 1)])
            r2, shap = shapley_r2(X, e)
            row["regression_r2"] = round(r2, 5)
            for k, s in zip(["first_in", "ace", "first_play", "double_faults", "second_play", "serve_count"], shap):
                row[f"shapley_{k}_pct"] = round(100 * s / r2, 2)
            rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(COMPONENTS, index=False)
    return {"rows": records(out), "left_out": int((~ok).sum()),
            "left_out_no_second_serve_in_play": int(t[parts].isna().any(axis=1).sum()),
            "left_out_impossible_counts": int((~in_range).sum()), "max_abs_residual": float(resid),
            "names": COMPONENT_NAMES}


def shapley_r2(X: np.ndarray, y: np.ndarray) -> tuple[float, list]:
    """R^2 of an ordinary least-squares fit (with an intercept) and each input's Shapley share of it: its
    average gain in R^2 over every order of entering the inputs."""
    k = X.shape[1]
    y = y - y.mean()
    tss = float(y @ y)
    cache = {(): 0.0}

    def r2(cols):
        if cols in cache:
            return cache[cols]
        Z = X[:, cols] - X[:, cols].mean(axis=0)
        beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
        res = y - Z @ beta
        cache[cols] = 1 - float(res @ res) / tss
        return cache[cols]
    full = r2(tuple(range(k)))
    shap = []
    from math import factorial
    for j in range(k):
        others = [i for i in range(k) if i != j]
        s = 0.0
        for size in range(k):
            for sub in itertools.combinations(others, size):
                wgt = factorial(size) * factorial(k - size - 1) / factorial(k)
                s += wgt * (r2(tuple(sorted(sub + (j,)))) - r2(tuple(sorted(sub))))
        shap.append(s)
    return full, shap


# ------------------------------------------------------------------------------------------------
# (f) match impact of every rate

MIRROR = {"rpw": "spw", "brk": "hold", "bp_conv": "bp_saved"}   # A's return points won are B's serve points lost, and so on


def match_impact(t: pd.DataFrame) -> dict:
    """Per rate: a one-input logistic regression of the result on the A - B difference (5-fold), scored on every
    match with a missing difference read as no difference ("all"), and on the matches where the rate exists for
    both players ("defined"). A rate and its mirror (``same_as``) give the same difference in every match."""
    rows = []
    for tour in C.TOURS:
        for bo in ("all", 3, 5):
            g = t[t["tour"].eq(tour) & (t["best_of"].eq(bo) if bo != "all" else True)]
            if len(g) == 0:
                continue
            y = g["a_won"].to_numpy()
            for rate, words in C.RATES.items():
                ra = g[f"{rate}_n_a"] / g[f"{rate}_d_a"].where(g[f"{rate}_d_a"] > 0)
                rb = g[f"{rate}_n_b"] / g[f"{rate}_d_b"].where(g[f"{rate}_d_b"] > 0)
                d = (ra - rb).to_numpy(dtype="float64")
                defined = np.isfinite(d)
                row = {"tour": tour, "best_of": bo, "rate": rate, "words": words, "same_as": MIRROR.get(rate, ""),
                       "matches": int(len(g)), "defined": int(defined.sum()), "defined_pct": round(100 * float(defined.mean()), 2)}
                for scope, mask, x in (("all", np.ones(len(g), bool), np.where(defined, d, 0.0)), ("defined", defined, d)):
                    if mask.sum() < 10:
                        continue
                    xx, yy = x[mask], y[mask]
                    separates = bool(((xx > 0) == yy).all() and (xx != 0).all())
                    if separates:     # the difference decides the match by definition (sets won)
                        ll, coef = 0.0, np.nan
                    else:
                        p, c = oof_logit(xx, yy)
                        ll, coef = float(logloss(p, yy).mean()), float(c[0])
                    row[f"{scope}_logloss"] = ll
                    row[f"{scope}_impact_milli"] = round(1000 * (np.log(2) - ll), 2)
                    row[f"{scope}_coef"] = coef
                    row[f"{scope}_separates"] = separates
                rows.append(row)
            # the iid floor, for reference on the same matches
            p_ref = g["p_floor"].to_numpy()
            rows.append({"tour": tour, "best_of": bo, "rate": "iid_floor", "words": "the iid model's chance from both serve rates (reference)",
                         "matches": int(len(g)), "defined": int(len(g)), "defined_pct": 100.0,
                         "all_logloss": float(logloss(p_ref, y).mean()), "all_impact_milli": round(1000 * (np.log(2) - float(logloss(p_ref, y).mean())), 2)})
        log(f"  match impact {tour} done")
    out = pd.DataFrame(rows)
    out.to_csv(IMPACT, index=False)
    return {"rows": records(out)}


# ------------------------------------------------------------------------------------------------

def main() -> int:
    t, retired, counts = build_table()
    log(f"analysis table: {len(t):,} matches ({', '.join(f'{k} {v:,}' for k, v in t['tour'].value_counts().items())})")
    t = add_model_columns(t)
    t = add_components(t)
    t = attach_baselines(t)
    res = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "population": counts,
           "first_year": FIRST_YEAR, "headline": list(HEADLINE), "directional_only_below": MIN_N, "coin": float(np.log(2)),
           "level_groups": LEVEL_GROUPS, "formats": FORMATS, "seed": SEED, "folds": FOLDS}
    res["population"]["final_by_tour_best_of"] = records(t.groupby(["tour", "best_of"]).size().rename("matches").reset_index())
    res["population"]["deciding_rules"] = records(t.groupby(["tour", "rule"]).size().rename("matches").reset_index())
    res["population"]["retired_set_aside"] = {k: int(v) for k, v in retired["tour"].value_counts().items()}
    rc, rc_summary = rules_check()
    res["rules_check"] = rc_summary
    log(f"rules check: {rc_summary['cells']} cells, {len(rc_summary['inconsistent'])} inconsistent")
    # the pure-luck twin (de-noised rates), and a replay at the measured rates to show why the de-noising is needed
    tw, prior = twin(t, SEED)
    tw_raw, _ = twin(t, SEED + 10, denoise=False)
    res["twin"] = {"prior": prior, "fit": {"real": fit_summary(t), "twin": fit_summary(tw),
                                           "replay_at_measured_rates": fit_summary(tw_raw)}}
    log("pure-luck twin built")
    res["a_points_to_wins"] = points_to_wins(t, retired, tw)
    log("a done")
    b_real, b_desc = beyond_points(t)
    b_twin, b_twin_desc = beyond_points(tw)
    b = pd.concat([b_real.assign(world="real"), b_twin.assign(world="pure luck")], ignore_index=True)
    b.assign(gain_over_base_milli=b["gain_over_base_milli"].map(json.dumps),
             coefficients=b["coefficients"].map(json.dumps)).to_csv(BEYOND, index=False)
    res["b_beyond_points"] = {"models": records(b), "descriptive": b_desc, "pure_luck_descriptive": b_twin_desc}
    log("b done")
    res["c_floor"], t = floor(t, tw)
    log("c done")
    # pure luck's correlations, from several replays (one replay's correlations wobble by sampling alone)
    parts = [persistence(t).assign(world="real", replay=0)]
    for k in range(TWIN_REPLAYS):
        twk = tw if k == 0 else twin(t, SEED + 100 * k)[0]
        parts.append(persistence(twk, splits=TWIN_SPLITS).assign(world="pure luck", replay=k + 1))
        log(f"  persistence, pure-luck replay {k + 1} of {TWIN_REPLAYS}")
    d = pd.concat(parts, ignore_index=True)
    d.to_csv(PERSIST, index=False)
    luck = d[d["world"].eq("pure luck")].groupby(["tour", "min_matches_per_half", "measure"])["r_mean"]
    real = d[d["world"].eq("real")].set_index(["tour", "min_matches_per_half", "measure"])
    summary = real.assign(luck_r_mean=luck.mean(), luck_r_min=luck.min(), luck_r_max=luck.max()).reset_index()
    res["d_persistence"] = {"rows": records(summary), "splits": SPLITS, "twin_replays": TWIN_REPLAYS,
                            "twin_splits": TWIN_SPLITS}
    log("d done")
    res["e_components"] = components(t)
    log("e done")
    res["f_match_impact"] = match_impact(t)
    log("f done")
    keep = ["match_id", "tour", "year", "era", "level_group", "qualifying", "round", "surface", "best_of", "rule",
            "tournament_name", "tournament_date", "a_won", "player_id_a", "player_id_b", "pa", "pb", "tpw_a", "edge_a",
            "p_floor", "n_tb", "deciding_tb", "tb_won_a", "tb_exp_a", "tb_over_a", "bp_faced_a", "bp_saved_a",
            "bp_faced_b", "bp_saved_b", "bp_save_over_a", "bp_save_over_b", "bp_net_a"] + \
        [f"c_{k}" for k in COMPONENT_NAMES] + [ELO, "p_market", "ll_floor", "luck"]
    out = t[keep].copy()
    out["twin_pa_true"], out["twin_pb_true"], out["twin_p_true"] = tw["pa_true"], tw["pb_true"], tw["p_true"]
    out["twin_a_won"], out["twin_p_floor"] = tw["a_won"].to_numpy(), tw["p_floor"].to_numpy()
    out.to_parquet(TABLE, index=False)
    RESULTS.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    log(f"wrote {TABLE.name} and {RESULTS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
