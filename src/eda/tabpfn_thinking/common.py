"""Shared definitions for the study "one TabPFN-3.5-Thinking fit on the promising features" (src/eda/tabpfn_thinking/).

The question: given the features the predictability diagnostic, the UFC-ideas study and the feature-alpha audit found
promising, does a non-linear tabular foundation model (TabPFN-3.5-Thinking, Prior Labs' hosted API) extract more than
the logistic regressions those studies used, and does what it extracts reach beyond the bookmakers' closing odds?

The design (fixed before any paid call; the paid call is made once):

    population   main-tour singles (Grand Slams, Tour Finals, 1000s, 500s, 250s), completed or retired, both tours
                 pooled with a tour column; the audit's events without a supported pre-match format are left out
                 (Next Gen Finals, the three Melbourne 2021 WTA events)
    training     seasons 2013-2021 (the warm-up seasons 2010-2012, when every rating is still settling, are left out)
    test         seasons 2022-2026 (the studies' headline window)
    inputs       FEATURES below: A - B differences (side A is random) plus six match-context columns
    the paid fit TabPFN gets the closing odds' log-odds as an input as well (TABPFN_NAMES), and is trained and scored
                 on the matches with odds: it models P(A wins | odds, features), so what it adds is measured directly
                 against the odds. (A first plan kept the odds out and stacked the forecast with them afterwards; the
                 scorer's dry run on the free models, before any paid call, showed that stacking cannot recover the
                 profile's small market-orthogonal signal: +0.10 milli-log-loss stacked against +0.79 used directly.)
                 The free models answer the no-odds question (beyond Elo) on every test match.
    symmetry     side A is random, so every model is made antisymmetric: a forecast is the mean of P(A wins | x) and
                 1 - P(A wins | x with A and B swapped) (FLIP); the logistic regressions are antisymmetric already
    scoring      log loss; differences in milli-log-loss (positive = better); 95% intervals are paired cluster t
                 intervals over contiguous four-week blocks of tournament dates (the corrected harness's method,
                 src/eda/predictability_diagnostic/stage4_rundown.paired_interval, re-implemented here so this study
                 does not import a module that is being edited), calendar weeks as a sensitivity

Every number in the write-up is read from data/studies/tabpfn_thinking/ (written by this study's scripts).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "tabpfn_thinking"
DOCS = ROOT / "docs" / "studies" / "tabpfn_thinking"
UPLOAD = OUT / "upload"            # the exact frames the API receives (features only) and their labels
THINKING = OUT / "thinking"        # receipts, the saved fitted-model record and the returned probabilities

UFC_OUT = ROOT / "data" / "studies" / "ufc_ideas"
PD_OUT = ROOT / "data" / "studies" / "predictability_diagnostic"
SOURCES = {                        # every input table, hashed into the manifest at build time
    "stage4": PD_OUT / "stage4_features.parquet",
    "stage0_matches": PD_OUT / "stage0_matches.parquet",
    "stageD": UFC_OUT / "stageD_features.parquet",
    "stageD_profile": UFC_OUT / "stageD_profile_features.parquet",
}

TOURS = ("atp", "wta")
MAIN_GROUPS = ("GS", "FIN", "T1000", "T500", "T250")
TRAIN_YEARS = (2013, 2021)
TEST_YEARS = (2022, 2026)
EPS = 1e-9
LN2 = float(np.log(2))
BLOCK_ORIGIN = np.datetime64("2010-01-04")     # a Monday: the corrected harness's origin for weeks and 4-week blocks

# ------------------------------------------------------------------------------------------------
# The inputs. Each: (name sent to the model, source table, source column, group, kind, description).
# kind "diff": an A - B difference (antisymmetric: negated when A and B are swapped); "context": a property of the
# match (unchanged by the swap). ios_points_short takes each tour's own Stage B memory (4 weeks men, 13 women).

PROFILE_STATS = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk",
                 "bp_conv", "rpw_first", "rpw_second"]
ADJDEF_STATS = ["ace", "df", "first_in", "bp_faced_pg"]
IOS_STATS = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"]

FEATURES: list[dict] = [
    {"name": "elo_logit", "src": "pool", "col": "p_elo", "group": "elo", "kind": "diff",
     "desc": "surface Elo's log-odds that A wins (Stage 1)"},
    {"name": "ratings_iid", "src": "stageD", "col": "rating_matchup|single", "group": "ratings", "kind": "diff",
     "desc": "serve and return strength ratings through the iid point model, log-odds (Stage 3)"},
    {"name": "elo_games", "src": "stageD", "col": "elo_games|single", "group": "ratings", "kind": "diff",
     "desc": "games-weighted Elo difference (Stage 4)"},
    {"name": "adjperf_tpw_2w", "src": "stageD", "col": "adjperf_tpw|decayed", "group": "points", "kind": "diff",
     "desc": "opponent-adjusted total points won, 2-week half-life (Stage B)"},
    {"name": "ios_points_short", "src": "stageD", "col": {"atp": "ios_matchup_points|diagnostic: h 4 weeks",
                                                         "wta": "ios_matchup_points|diagnostic: h 13 weeks"},
     "group": "points", "kind": "diff",
     "desc": "IOS points matchup with a short memory (4 weeks men, 13 women), log-odds (Stage B)"},
    {"name": "points_52w", "src": "stageD", "col": "mu_points|52 weeks", "group": "points", "kind": "diff",
     "desc": "points-won matchup over the last 52 weeks (Stage 4)"},
    {"name": "sets_14d", "src": "stageD", "col": "sets_14d|single", "group": "player", "kind": "diff",
     "desc": "sets played in the last 14 days (Stage 4)"},
    {"name": "surface_first", "src": "stageD", "col": "surface_first|single", "group": "player", "kind": "diff",
     "desc": "first matches on this surface this season (Stage 4)"},
    {"name": "age", "src": "stageD", "col": "age|single", "group": "player", "kind": "diff",
     "desc": "age difference (Stage 4)"},
    {"name": "age_sq", "src": "stageD", "col": "age|single|2", "group": "player", "kind": "diff",
     "desc": "difference of squared ages around 25 (Stage 4)"},
]
FEATURES += [{"name": f"form_{s}", "src": "stageD_profile", "col": f"adjperf_{s}|decayed", "group": "profile_form",
              "kind": "diff", "desc": f"adjperf of {s}, 2-week half-life (Stage B; the Stage D profile)"}
             for s in PROFILE_STATS]
FEATURES += [{"name": f"formdef_{s}", "src": "stageD_profile", "col": f"adjdef_{s}|decayed", "group": "profile_form",
              "kind": "diff", "desc": f"adjdef of {s}, 2-week half-life (Stage B; the Stage D profile)"}
             for s in ADJDEF_STATS]
FEATURES += [{"name": f"ios{side}_{s}", "src": "stageD_profile", "col": f"ios_{side}_{s}|single",
              "group": "profile_traits", "kind": "diff",
              "desc": f"IOS {'offence' if side == 'O' else 'defence'} rating of {s}, long memory (Stage B)"}
             for s in IOS_STATS for side in ("O", "D")]
FEATURES += [{"name": f"prod_{s}", "src": "stageD_profile", "col": f"prod_{s}|single", "group": "profile_traits",
              "kind": "diff", "desc": f"IOS matchup product of {s}: A's offence x B's lack of defence minus the "
                                      f"reverse (Stage D)"} for s in IOS_STATS]
FEATURES += [
    {"name": "tour", "src": "match", "col": "tour", "group": "context", "kind": "context",
     "desc": "0 men (ATP), 1 women (WTA); categorical"},
    {"name": "surface", "src": "match", "col": "surface", "group": "context", "kind": "context",
     "desc": "0 hard, 1 clay, 2 grass, 3 carpet; categorical"},
    {"name": "level", "src": "match", "col": "group", "group": "context", "kind": "context",
     "desc": "0 Grand Slam, 1 Tour Finals, 2 1000, 3 500, 4 250; categorical"},
    {"name": "indoor", "src": "match", "col": "indoor", "group": "context", "kind": "context",
     "desc": "1 indoor, 0 outdoor (Stage 0's event metadata; the men only, missing for every women's match)"},
    {"name": "best_of", "src": "match", "col": "best_of", "group": "context", "kind": "context",
     "desc": "scheduled best of 3 or 5 (the audit's pre-match rule, not the score)"},
    {"name": "round", "src": "match", "col": "round_order", "group": "context", "kind": "context",
     "desc": "round order within the event (Stage 0's round_order)"},
]
NAMES = [f["name"] for f in FEATURES]
DIFF = [f["name"] for f in FEATURES if f["kind"] == "diff"]
CONTEXT = [f["name"] for f in FEATURES if f["kind"] == "context"]
ODDS = {"name": "odds_logit", "src": "pool", "col": "p_mkt", "group": "odds", "kind": "diff",
        "desc": "the closing odds' log-odds that A wins (the average of the books in tennis-data.co.uk, de-vigged; "
                "Stage 1's market probability)"}
TABPFN_NAMES = [ODDS["name"]] + NAMES          # the paid fit's inputs, in this order
ANTISYMMETRIC = set(DIFF) | {ODDS["name"]}
CATEGORICAL = ["tour", "surface", "level"]
GROUPS = {g: [f["name"] for f in FEATURES if f["group"] == g]
          for g in dict.fromkeys(f["group"] for f in FEATURES)}
GROUP_LABELS = {"odds": "Closing odds", "elo": "Surface Elo", "ratings": "Serve/return ratings and games-weighted Elo",
                "points": "Points-won aggregates", "player": "Load, surface familiarity, age",
                "profile_form": "Two-week statistics profile (16)", "profile_traits": "IOS offence/defence profile and products (21)",
                "context": "Match context"}
# The Stage D "everything" inputs that survive the audit's priorities (no BT, schedule or revaluation): the linear
# reference model "everything" below. Its earlier walk-forward result is not comparable (different design).
EVERYTHING = ["elo_logit", "ratings_iid", "elo_games", "adjperf_tpw_2w", "ios_points_short", "sets_14d",
              "surface_first", "age", "age_sq"]
PROFILE16 = GROUPS["profile_form"]
CODES = {"tour": {"atp": 0, "wta": 1}, "surface": {"Hard": 0, "Clay": 1, "Grass": 2, "Carpet": 3},
         "level": {"GS": 0, "FIN": 1, "T1000": 2, "T500": 3, "T250": 4}}

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def fingerprint(X_train: pd.DataFrame, y_train: np.ndarray, X_query: pd.DataFrame) -> str:
    """A hash of the exact values the API receives: column names and order, shapes, every value as little-endian
    float64 (NaN canonical) and the binary labels. Independent of the pandas version (the frames are built in the
    `tennis` env and sent from `tennis-tabpfn`)."""
    h = hashlib.sha256(b"tabpfn_thinking/v1")
    for name, frame in (("train", X_train), ("query", X_query)):
        h.update(json.dumps({"name": name, "shape": list(frame.shape), "columns": list(map(str, frame.columns))},
                            sort_keys=True).encode())
        v = np.ascontiguousarray(frame.to_numpy(dtype="float64"))
        v = np.where(np.isnan(v), np.nan, v).astype("<f8")          # one NaN bit pattern
        h.update(v.tobytes())
    y = np.asarray(y_train)
    if not np.isin(y, [0, 1]).all():
        raise ValueError("labels must be 0/1")
    h.update(y.astype("<i8").tobytes())
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=_json_default), encoding="utf-8")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    if isinstance(o, (pd.Timestamp, np.datetime64)):
        return str(o)
    raise TypeError(type(o))


# ------------------------------------------------------------------------------------------------
# Symmetry

def flip(X: pd.DataFrame) -> pd.DataFrame:
    """The same matches with A and B swapped: every A - B difference (and the odds' log-odds) negated, the match
    context unchanged."""
    out = X.copy()
    diff = [c for c in X.columns if c in ANTISYMMETRIC]
    out[diff] = -X[diff]
    return out


def symmetrize(p_orig: np.ndarray, p_flip: np.ndarray) -> np.ndarray:
    """P(A wins) from a forecast of each orientation: the mean of P(A | x) and 1 - P(A | swapped x)."""
    return 0.5 * (np.asarray(p_orig, dtype=float) + 1.0 - np.asarray(p_flip, dtype=float))


# ------------------------------------------------------------------------------------------------
# Scoring

def ll(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per-match log loss of a forecast that A wins."""
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.where(np.asarray(y, dtype=bool), -np.log(p), -np.log(1 - p))


def blocks(dates: np.ndarray, width_days: int) -> np.ndarray:
    """Contiguous blocks of ``width_days`` from a Monday origin (7: calendar weeks; 28: four-week blocks)."""
    days = (np.asarray(dates, dtype="datetime64[D]") - BLOCK_ORIGIN).astype(int)
    return days // width_days


def paired_interval(values: np.ndarray, clusters: np.ndarray) -> dict:
    """Paired mean gain with a cluster-sandwich SE and a t reference on G - 1 degrees of freedom (the corrected
    harness's stage4_rundown.paired_interval, same formula). Returns milli-log-loss bounds."""
    values = np.asarray(values, dtype=float)
    labels, ix = np.unique(clusters, return_inverse=True)
    n, count = len(values), len(labels)
    mean = float(values.mean()) if n else np.nan
    influence = np.bincount(ix, weights=values - mean)
    se = np.sqrt(count / (count - 1) * np.dot(influence, influence)) / n if count > 1 else np.nan
    radius = student_t.ppf(0.975, count - 1) * se if count > 1 else np.nan
    return {"clusters": int(count), "lo": float(1000 * (mean - radius)), "hi": float(1000 * (mean + radius))}


def compare(ll_base: np.ndarray, ll_model: np.ndarray, dates: np.ndarray) -> dict:
    """The model's gain over the base in milli-log-loss (positive = the model is better) on the same matches, with
    the four-week-block interval (primary) and the calendar-week interval (sensitivity)."""
    d = np.asarray(ll_base, dtype=float) - np.asarray(ll_model, dtype=float)
    ok = np.isfinite(d)
    d, dates = d[ok], np.asarray(dates)[ok]
    n = int(len(d))
    if n == 0:
        return {"n": 0, "gain": np.nan}
    four, week = paired_interval(d, blocks(dates, 28)), paired_interval(d, blocks(dates, 7))
    return {"n": n, "gain": float(1000 * d.mean()), "lo": four["lo"], "hi": four["hi"], "blocks": four["clusters"],
            "week_lo": week["lo"], "week_hi": week["hi"], "weeks": week["clusters"]}


def fit_logistic(Z: np.ndarray, y: np.ndarray, max_iter: int = 100, tol: float = 1e-10, ridge: float = 1e-8):
    """Maximum-likelihood logistic regression without an intercept (Newton steps, a step longer than 4 cut back, a
    tiny ridge against a singular Hessian), as the earlier harness fits it. Returns (coefficients, standard errors)."""
    from scipy.special import expit
    Z = np.asarray(Z, dtype=float)
    y = np.asarray(y, dtype=float)
    beta = np.zeros(Z.shape[1])
    eye = np.eye(Z.shape[1]) * ridge
    for _ in range(max_iter):
        p = expit(Z @ beta)
        g = Z.T @ (y - p) - ridge * beta
        H = (Z.T * (p * (1 - p))) @ Z + eye
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        beta += step
        if np.abs(step).max() < tol:
            break
    p = expit(Z @ beta)
    cov = np.linalg.pinv((Z.T * (p * (1 - p))) @ Z)
    return beta, np.sqrt(np.maximum(np.diag(cov), 0))


def share_of_gap(ll_model: float, ll_market: float) -> float:
    """The earlier summaries' ladder: (coin - model) / (coin - market) on the same matches."""
    return (LN2 - ll_model) / (LN2 - ll_market)
