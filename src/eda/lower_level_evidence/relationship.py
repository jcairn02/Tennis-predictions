"""The relationship's numbers (role B of the level-evidence system, SPEC section 3 and 6.2).

The question. What does a lower-level match (tour qualifying TQ, Slam qualifying GSQ, Challenger / WTA 125 main draws
CH, their qualifying CHQ; ITF and ITFQ once their box scores can be fitted) tell us about a player's main-tour level,
statistic by statistic? Three parts, per statistic s, tour g and level L, all fitted walk-forward on the match clock:
    translation   a lower-level observation's logit rate is shifted by T = gamma_s,g * (opponent's Elo - E_ref) +
                  delta_s,g,L (gamma: the statistic's opponent dependence inside the main tour, role A's; delta: the
                  residual level effect);
    exchange rate a translated lower-level observation counts w_s,g,L times a main-tour observation;
    prior         a player's prior mean is the average main-tour newcomer of his home tier (kept only if it predicts
                  better).

The predictor (the statistic-level testbed). For a player's main-tour match (the target), his statistic is predicted
from his own earlier box scores within WINDOW_DAYS, every level, as a recency-weighted credibility average on the logit
scale:
    eta_t = s[surf_t] + gamma * (E_opp,t - E_ref)
            + [k mu_tier(t) + sum_main v_i (y_i - s[surf_i] - gamma g_i)
               + sum_L w_L sum_{i in L} v_i (y_i - s[surf_i] - T_i)] / [k + sum_main v_i + sum_L w_L sum_{i in L} v_i]
with y_i = logit((x_i + 1/2) / (d_i + 1)) (log((x_i + 1/2)/(d_i + 1/2)) for a count per game), v_i = d_i *
2^(-(obs_t - obs_i) / h), g_i = E_opp,i - E_ref, s the main tour's surface offsets. The target's binomial (or Poisson)
log-likelihood per opportunity scores it. Everything that is a sum over a player's history is a set of per-target
sufficient statistics, so every fit is a few-parameter optimisation over arrays (seconds, not minutes).

The formulations (scored on main-tour matches, both players, walk-forward):
    F0   lower rows pooled as equivalent: raw (today)
    F1   main tour only (w = 0)
    F2   constant same-season level offsets (role 08's rule, refitted walk-forward)
    F2b  constant level offsets fitted by maximum likelihood (no opponent gap)
    F3g  opponent-gap translation only (delta = 0)
    F3   opponent-gap translation plus a residual delta_L
    F4   F3 plus the exchange rate w (per statistic, shrunk across statistics within a level)
    F5   F4 plus the newcomer prior (mu by home tier)
    F6   the formulation chosen on 2015-2018 walk-forward scores, with the recency half-life chosen per season on the
         fit window
Every formulation shares the main-tour treatment: main rows and the target opponent-adjusted by gamma, surface-centred.

Walk-forward. Parameters for season Y use only main-tour targets with lf + 1 <= the season's first es (the match
clock), in the trailing FIT_SEASONS seasons (from 2011), and only histories before those targets. A level enters a
season's fit only when the fit window holds at least MIN_LEVEL_SEASONS seasons with MIN_SEASON_MATCHES box-score
matches at that level (ITF and ITFQ: none before 2025 in the frozen tables, so w = 0).

The holdout. Seasons up to 2024 are read with common.assert_no_holdout_outcomes. The rows for seasons 2025 and 2026
are produced only by `--mechanical`, which refuses to run unless this file's sha256 equals the frozen hash in
method_freeze.json, writes parameter rows only, and prints no diagnostic.

Results channel. The reference's Elo (stage1_baselines.elo_pass, its K schedule per tour, retirements counted) with K
multiplied by w_results for lower-level results (counts advance by w_results), scored on main-tour results.

Run (from the repository root):
    ./python.sh src/eda/lower_level_evidence/relationship.py --steps dev          # formulations, dose, era, h grid
    ./python.sh src/eda/lower_level_evidence/relationship.py --steps elo
    ./python.sh src/eda/lower_level_evidence/relationship.py --steps params       # 2013-2024 rows + bootstrap
    ./python.sh src/eda/lower_level_evidence/relationship.py --freeze             # hash the code and the rows
    ./python.sh src/eda/lower_level_evidence/relationship.py --mechanical         # 2025, 2026 rows (frozen code)
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):     # single-threaded BLAS: the machine is
    os.environ.setdefault(_v, "1")                                          # shared, and small matvecs thrash

import argparse
import hashlib
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
from scipy.optimize import minimize
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as C  # noqa: E402

METHOD_VERSION = "B-relationship-2026-10-09"
OUT = C.OUT / "system" / "relationship"
CLASSES_DIR = C.OUT / "system" / "classes"
STAGE1 = CLASSES_DIR / "strength_elo.parquet"      # role A's checked copy of Stage 1's pre-match Elo (strength_elo.json)
STAGE1_SANDBOX = Path("C:/Users/zerom/tnr_lle/data/studies/predictability_diagnostic/stage1_baselines.parquet")
FREEZE = OUT / "method_freeze.json"
TOURS = ("atp", "wta")
FIRST_TARGET_YEAR = 2011          # targets need a history: Stage 0 starts in 2010
FIT_SEASONS = 6                   # trailing seasons of targets in a fit (fixed before any score was read)
WINDOW_DAYS = 730                 # a target reads its player's box scores of the previous two years
DEFAULT_H_WEEKS = 52.0            # recency half-life of F0-F5 (F6 tunes it)
H_GRID_WEEKS = (26.0, 52.0, 104.0, 208.0)    # the IOS registry's range; 2 years uniform (inf) lost in a first test
LOW_EXPOSURE = 10                 # fewer main-tour results than this in the previous 365 days
MIN_SEASON_MATCHES = 100          # a season "has box scores" at a level with this many box-score matches
MIN_LEVEL_SEASONS = 2             # a level is fitted only with this many such seasons in the fit window
MIN_OFFSET_PLAYER_SEASONS = 100   # role 08's rule: a cell under this takes the both-tours value, then 0
DOSE_GRID = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25)
W_BOUNDS = (0.0, 3.0)
DELTA_BOUNDS = (-1.5, 1.5)
DELTA_RIDGE_SD = 0.5              # weak N(0, 0.5^2) prior on delta (logit): inert unless a cell is degenerate
SEED = 20261009
T0 = time.time()

LEVELS = ("MAIN", "TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")   # MAIN holds team events too (the layer leaves them)
LOWER = LEVELS[1:]
LEVEL_OF_BUCKET = {"MAIN": "MAIN", "TEAM": "MAIN", "TQ": "TQ", "GSQ": "GSQ", "CH": "CH", "CHQ": "CHQ", "ITF": "ITF",
                   "ITFQ": "ITFQ"}
TIER_OF_BUCKET = {"MAIN": "MT", "TEAM": "MT", "TQ": "Q", "GSQ": "Q", "CH": "CH", "CHQ": "CH", "ITF": "ITF",
                  "ITFQ": "ITF"}
TIER_OF_LEVEL = {"MAIN": "MT", "TQ": "Q", "GSQ": "Q", "CH": "CH", "CHQ": "CH", "ITF": "ITF", "ITFQ": "ITF"}
TIERS = ("MT", "Q", "CH", "ITF", "none")       # home tier: most played matches of the previous 365 days
SURFACES = ("Hard", "Clay", "Grass", "Carpet", "other")


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The statistics: one (numerator, denominator) per player row, from his own serve, his return or the opponent's
# serve against him ("defence"). Family binomial (a rate per opportunity) or poisson (a count per game).

STATS = {
    # name: (side, family, how)
    "ace": ("serve", "binomial", ("own", "ace")),
    "df": ("serve", "binomial", ("own", "df")),
    "first_in": ("serve", "binomial", ("own", "first_in")),
    "first_won": ("serve", "binomial", ("own", "first_won")),
    "second_won": ("serve", "binomial", ("own", "second_won")),
    "spw": ("serve", "binomial", ("own", "spw")),
    "hold": ("serve", "binomial", ("own", "hold")),
    "bp_saved": ("serve", "binomial", ("own", "bp_saved")),
    "bp_faced_pg": ("serve", "poisson", ("own", "bp_faced_pg")),
    "rpw": ("return", "binomial", ("own", "rpw")),
    "brk": ("return", "binomial", ("own", "brk")),
    "bp_conv": ("return", "binomial", ("own", "bp_conv")),
    "rpw_first": ("return", "binomial", ("opp_lost", "first_won")),
    "rpw_second": ("return", "binomial", ("opp_lost", "second_won")),
    "def_ace": ("defence", "binomial", ("opp", "ace")),
    "def_df": ("defence", "binomial", ("opp", "df")),
    "def_first_in": ("defence", "binomial", ("opp", "first_in")),
    "def_bp_faced_pg": ("defence", "poisson", ("opp", "bp_faced_pg")),
    "tpw": ("both", "binomial", ("own", "tpw")),
}
GROUPS = {"serve points": ("spw", "first_won", "second_won"),
          "serve games": ("hold", "bp_saved", "bp_faced_pg"),
          "serve style": ("ace", "df", "first_in"),
          "return": ("rpw", "brk", "bp_conv", "rpw_first", "rpw_second"),
          "defence": ("def_ace", "def_df", "def_first_in", "def_bp_faced_pg"),
          "total points": ("tpw",)}
BASE_COLS = sorted({h[1] for _, _, h in STATS.values()})


# ------------------------------------------------------------------------------------------------
# Data

MATCH_COLS = ["tour", "year", "map_level", "surface", "status", "format", "has_box", "tournament_date", "order",
              "tournament_id", "player_a_id", "player_b_id"]


def season_first_es(stage0_dir: Path = C.STAGE0_DIR, timing: Path = C.TIMING) -> dict:
    """Each season's cutoff on the match clock: the earliest possible start (es) of its first main-tour match, both
    tours (role A's classify.season_cutoff, recomputed here and checked equal). A fit for season Y reads only results
    with lf + 1 <= this day. Reads no outcome."""
    m = C.load_matches(stage0_dir, columns=["year", "map_level"])
    t = pd.read_parquet(timing, columns=["match_id", "es"])
    m = m.merge(t, on="match_id", how="left")
    m = m[m["bucket"].eq("MAIN")]
    return {int(y): float(v) for y, v in m.groupby("year")["es"].min().items()}


def load(stage0_dir: Path = C.STAGE0_DIR, through: int = 2024, timing: Path = C.TIMING, stage1: Path = STAGE1,
         mechanical: bool = False) -> pd.DataFrame:
    """Player rows (two per match, in Stage 0's order) of seasons up to `through`, with the match columns, the clock
    (es, lf, obs), each side's pre-match Elo (the reference's Stage 1, retirements counted), the bucket, level and tier.

    Seasons after 2024 are read only in the mechanical mode (frozen code; parameter rows only)."""
    if through >= 2025 and not mechanical:
        raise SystemExit("seasons after 2024 hold holdout outcomes: only --mechanical (frozen code) may read them")
    m = C.load_matches(stage0_dir, columns=MATCH_COLS)
    m["date"] = pd.to_datetime(m["tournament_date"])
    keep = m["year"] <= through
    if through <= 2024:
        keep &= ~C.in_holdout(m["date"])
    m = m[keep].reset_index(drop=True)
    ids = pa.array(m["match_id"].to_numpy())
    pcols = ["match_id", "player_id", "opponent_id", "side", "won"] + \
        [f"{s}_{x}" for s in BASE_COLS for x in ("n", "d")]
    tbl = pq.read_table(Path(stage0_dir) / "stage0_match_players.parquet", columns=pcols,
                        filters=pc.field("match_id").isin(ids))
    p = tbl.to_pandas().merge(m, on="match_id", how="inner", validate="many_to_one")
    if through <= 2024:
        C.assert_no_holdout_outcomes(p["date"], "relationship.load: player rows")
    p = p.sort_values(["order", "side"], kind="mergesort").reset_index(drop=True)
    mid = p["match_id"].to_numpy()
    if len(p) % 2 or not (mid[0::2] == mid[1::2]).all():
        raise RuntimeError("player rows are not two per match in Stage 0's order")
    if not (p["side"].to_numpy()[0::2] == "A").all() or \
            not (p["player_id"].to_numpy()[0::2] == p["player_a_id"].to_numpy()[0::2]).all():
        raise RuntimeError("side A is not player_a_id")
    t = pd.read_parquet(timing, columns=["match_id", "es", "lf", "obs"])
    p = p.merge(t, on="match_id", how="left", validate="many_to_one")
    day = p["date"].to_numpy().astype("datetime64[D]").astype("int64")
    p["day"] = day
    miss = (p["es"].isna() | p["lf"].isna() | p["obs"].isna()).to_numpy()
    # a match the timeline lacks (a candidate's new rows): a cautious window, never a guessed day
    p.loc[miss, "es"] = day[miss] - 7
    p.loc[miss, "lf"] = day[miss] + 21
    p.loc[miss, "obs"] = day[miss] + 3
    e = pq.read_table(stage1, columns=["match_id", "elo_a_ret", "elo_b_ret"],
                      filters=pc.field("match_id").isin(ids)).to_pandas()
    e = e.set_index("match_id")
    ea = p["match_id"].map(e["elo_a_ret"]).to_numpy(float)
    eb = p["match_id"].map(e["elo_b_ret"]).to_numpy(float)
    is_a = p["side"].to_numpy() == "A"
    p["elo_own"] = np.where(is_a, ea, eb)
    p["elo_opp"] = np.where(is_a, eb, ea)
    p["level"] = p["bucket"].map(LEVEL_OF_BUCKET)
    p["tier_row"] = p["bucket"].map(TIER_OF_BUCKET)
    p["pcode"] = pd.factorize(p["tour"] + "|" + p["player_id"])[0]
    p["box"] = p["status"].eq("completed").to_numpy() & p["format"].eq("standard").to_numpy() & \
        p["has_box"].fillna(False).astype(bool).to_numpy()
    p["played"] = p["status"].isin(["completed", "retired"])
    p["surf"] = p["surface"].where(p["surface"].isin(SURFACES[:4]), "other")
    p.attrs["timing_fallback_rows"] = int(miss.sum())
    p.attrs["elo_missing_rows"] = int(np.isnan(p["elo_opp"].to_numpy()).sum())
    return p


def stat_nd(p: pd.DataFrame, stat: str) -> tuple[np.ndarray, np.ndarray]:
    """(numerator, denominator) of a statistic per player row; NaN where the row is not a usable box score."""
    side, family, (who, base) = STATS[stat]
    n, d = p[f"{base}_n"].to_numpy(float), p[f"{base}_d"].to_numpy(float)
    opp = np.arange(len(p)) ^ 1
    if who == "opp":
        n, d = n[opp], d[opp]
    elif who == "opp_lost":
        n, d = d[opp] - n[opp], d[opp]
    box = p["box"].to_numpy()
    with np.errstate(invalid="ignore"):
        ok = box & np.isfinite(n) & np.isfinite(d) & (d > 0) & (n >= 0)
        if family == "binomial":
            ok &= n <= d
    return np.where(ok, n, np.nan), np.where(ok, d, np.nan)


def player_sequence(code: np.ndarray, order: np.ndarray, day: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Rows in each player's own order (player, then Stage 0's order), and for each position the first position of the
    same player's window (tournament date within `window` days before): positions lo .. i-1 are the earlier rows of
    the window (copied from translation.player_sequence)."""
    o = np.lexsort((order, code))
    c, dd = code[o], day[o]
    same = np.diff(c) == 0
    if not (np.diff(dd)[same] >= 0).all():
        raise RuntimeError("Stage 0's order does not follow the tournament date within a player")
    span = int(dd.max() - dd.min()) + 2 * window + 2
    comp = c.astype(np.int64) * span + (dd - dd.min() + window + 1)
    lo = np.searchsorted(comp, comp - window, side="left")
    return o, lo


def own_history(p: pd.DataFrame, window: int = 365) -> pd.DataFrame:
    """Per player row, from his strictly earlier played matches (completed or retired) of the previous `window` days,
    every level (ITF results included): the count by tier, the home tier (most matches; ties to the higher tier) and
    the low-exposure flag (fewer than LOW_EXPOSURE main-tour results). Copied from translation.own_history with team
    events counted as main tour."""
    tier = p["tier_row"].to_numpy()
    played = p["played"].to_numpy()
    o, lo = player_sequence(p["pcode"].to_numpy(), p["order"].to_numpy(), p["day"].to_numpy(), window)
    idx = np.arange(len(o))
    counts = {}
    for t in TIERS[:-1]:
        cs = np.concatenate([[0], np.cumsum(played[o] & (tier[o] == t))])
        arr = np.empty(len(p))
        arr[o] = cs[idx] - cs[lo]
        counts[t] = arr
    stack = np.column_stack([counts[t] for t in TIERS[:-1]])
    tot = stack.sum(axis=1)
    home = np.array(TIERS[:-1])[np.argmax(stack, axis=1)]
    out = pd.DataFrame(index=p.index)
    out["n_MT"] = counts["MT"].astype(np.int32)
    out["home"] = np.where(tot > 0, home, "none")
    out["low_exposure"] = counts["MT"] < LOW_EXPOSURE
    return out


# ------------------------------------------------------------------------------------------------
# Per (tour, statistic): the valid rows in each player's order, the targets and their sufficient statistics

def observation(n: np.ndarray, d: np.ndarray, family: str) -> np.ndarray:
    """A row's observation on the link scale: logit((x + 1/2) / (d + 1)), or log((x + 1/2) / (d + 1/2)) for a count
    per game."""
    if family == "binomial":
        r = (n + 0.5) / (d + 1.0)
        return np.log(r) - np.log1p(-r)
    return np.log((n + 0.5) / (d + 0.5))


class TourStat:
    """One tour's valid rows of one statistic (box scores with a usable numerator and denominator) in each player's
    own order, and the main-tour targets among them (main draws of the 250+ levels; team events are history only).

    `sums(h_weeks)` returns per target, per level group (LEVELS) the decayed window sums over the player's strictly
    earlier rows of the previous WINDOW_DAYS: V = sum v, Y = sum v y, E = sum v E_opp, VS[surface] = sum v on that
    surface, NR = rows; v = d * 2^(-(obs_t - obs_i) / h)."""

    def __init__(self, p: pd.DataFrame, hist: pd.DataFrame, tour: str, stat: str):
        self.tour, self.stat = tour, stat
        self.family = STATS[stat][1]
        n, d = stat_nd(p, stat)
        ok = np.isfinite(n) & (p["tour"].to_numpy() == tour) & np.isfinite(p["elo_opp"].to_numpy())
        r = np.flatnonzero(ok)
        o, lo = player_sequence(p["pcode"].to_numpy()[r], p["order"].to_numpy()[r], p["day"].to_numpy()[r],
                                WINDOW_DAYS)
        r = r[o]                                   # valid rows in each player's own order
        self.rows, self.lo = r, lo
        self.n, self.d = n[r], d[r]
        self.y = observation(self.n, self.d, self.family)
        self.code = p["pcode"].to_numpy()[r]
        self.obs = p["obs"].to_numpy(float)[r]
        self.lev = pd.Categorical(p["level"].to_numpy()[r], categories=LEVELS).codes.astype(np.int64)
        self.surf = pd.Categorical(p["surf"].to_numpy()[r], categories=SURFACES).codes.astype(np.int64)
        self.eopp = p["elo_opp"].to_numpy(float)[r]
        self.year = p["year"].to_numpy()[r]
        self.lf_row = p["lf"].to_numpy(float)[r]
        bucket = p["bucket"].to_numpy()[r]
        self.pos = np.flatnonzero(bucket == "MAIN")          # target positions
        tp = r[self.pos]
        self.t = {"x": self.n[self.pos], "d": self.d[self.pos], "eopp": self.eopp[self.pos],
                  "surf": self.surf[self.pos], "year": self.year[self.pos],
                  "es": p["es"].to_numpy(float)[tp], "lf": p["lf"].to_numpy(float)[tp],
                  "obs": self.obs[self.pos], "player": self.code[self.pos],
                  "tier": pd.Categorical(hist["home"].to_numpy()[tp], categories=TIERS).codes.astype(np.int64),
                  "low_exposure": hist["low_exposure"].to_numpy()[tp], "n_MT": hist["n_MT"].to_numpy()[tp],
                  "match_row": tp}
        # each player's first observation day: the decay's reference keeps the exponents small
        first = np.r_[0, np.flatnonzero(np.diff(self.code) != 0) + 1]
        cnt = np.diff(np.r_[first, len(self.code)])
        self.t0 = np.repeat(self.obs[first], cnt)
        # per row, the bucket (for role 08's rule) and the year
        self.bucket = bucket

    def sums(self, h_weeks: float) -> dict:
        h = h_weeks * 7.0
        pos, lo = self.pos, self.lo[self.pos]
        if np.isfinite(h):
            g = np.exp2((self.obs - self.t0) / h)
            back = np.exp2(-(self.obs[pos] - self.t0[pos]) / h)
        else:
            g = np.ones(len(self.obs))
            back = np.ones(len(pos))
        v = self.d * g
        cols = [v, v * self.y, v * self.eopp] + [v * (self.surf == s) for s in range(len(SURFACES))] + \
            [np.ones(len(v))]
        nl = len(LEVELS)
        T = len(pos)
        out = {"V": np.zeros((T, nl)), "Y": np.zeros((T, nl)), "E": np.zeros((T, nl)),
               "VS": np.zeros((T, nl, len(SURFACES))), "NR": np.zeros((T, nl))}
        for li in range(nl):
            m = self.lev == li
            if not m.any():
                continue
            a = np.column_stack([np.where(m, c, 0.0) for c in cols])
            cs = np.vstack([np.zeros((1, a.shape[1])), np.cumsum(a, axis=0)])
            s = cs[pos] - cs[lo]                         # rows lo .. pos-1: the earlier rows of the window
            out["V"][:, li] = s[:, 0] * back
            out["Y"][:, li] = s[:, 1] * back
            out["E"][:, li] = s[:, 2] * back
            out["VS"][:, li, :] = s[:, 3:3 + len(SURFACES)] * back[:, None]
            out["NR"][:, li] = s[:, -1]                  # rows, undecayed (the ones column carries no decay)
        return out


# ------------------------------------------------------------------------------------------------
# Season constants: everything a season's fit uses comes from results with lf + 1 <= the season's first es

def fit_years(season: int) -> tuple[int, int]:
    return max(FIRST_TARGET_YEAR, season - FIT_SEASONS), season - 1


def fit_mask(ts: TourStat, season: int, first_es: dict) -> np.ndarray:
    """The targets a season's fit may use: the trailing FIT_SEASONS seasons, every one surely finished before the
    season's first match could start (lf + 1 <= first es)."""
    lo, hi = fit_years(season)
    t = ts.t
    return (t["year"] >= lo) & (t["year"] <= hi) & (t["lf"] + 1.0 <= first_es[season])


def strength_ref(p: pd.DataFrame, tour: str, season: int, first_es: dict) -> float:
    """The main-tour reference opponent's strength: the mean pre-match Elo of the opponents in main-tour box-score rows
    of the 365 days before the season (lf + 1 <= its first es)."""
    s = first_es[season]
    m = (p["tour"].to_numpy() == tour) & (p["bucket"].to_numpy() == "MAIN") & p["box"].to_numpy() & \
        (p["lf"].to_numpy() + 1.0 <= s) & (p["es"].to_numpy() >= s - 365.0)
    e = p["elo_opp"].to_numpy(float)[m]
    e = e[np.isfinite(e)]
    if len(e) < 100:                               # the first seasons: the whole available main tour
        m = (p["tour"].to_numpy() == tour) & (p["bucket"].to_numpy() == "MAIN") & p["box"].to_numpy() & \
            (p["lf"].to_numpy() + 1.0 <= s)
        e = p["elo_opp"].to_numpy(float)[m]
        e = e[np.isfinite(e)]
    return float(e.mean())


def surface_offsets(ts: TourStat, fm: np.ndarray) -> np.ndarray:
    """The main tour's surface offsets on the link scale, from the fit's targets: link(rate on the surface) -
    link(rate overall); 0 for a surface with under 300 targets."""
    x, d, sf = ts.t["x"][fm], ts.t["d"][fm], ts.t["surf"][fm]
    out = np.zeros(len(SURFACES))
    if d.sum() <= 0:
        return out

    def link(r):
        return np.log(r) - np.log1p(-r) if ts.family == "binomial" else np.log(r)
    base = link(x.sum() / d.sum())
    for s in range(len(SURFACES)):
        m = sf == s
        if m.sum() >= 300 and x[m].sum() > 0:
            out[s] = link(x[m].sum() / d[m].sum()) - base
    return out


def level_seasons(ts: TourStat, season: int, first_es: dict) -> dict:
    """Per lower level: the seasons of the fit window holding at least MIN_SEASON_MATCHES box-score matches of it
    (2 rows a match), counted only on rows surely finished before the season."""
    lo, hi = fit_years(season)
    out = {}
    for li, L in enumerate(LEVELS):
        if L == "MAIN":
            continue
        m = (ts.lev == li) & (ts.year >= lo - 2) & (ts.year <= hi) & (ts.lf_row + 1.0 <= first_es[season])
        if not m.any():
            out[L] = []
            continue
        yrs, cnt = np.unique(ts.year[m], return_counts=True)
        out[L] = [int(y) for y, c in zip(yrs, cnt) if c >= 2 * MIN_SEASON_MATCHES]
    return out


def fitted_levels(ts: TourStat, S: dict, fm: np.ndarray, season: int, first_es: dict) -> list[str]:
    """The lower levels a season's fit estimates: at least MIN_LEVEL_SEASONS seasons with box scores, and at least 30
    fit targets (players' rows) with some history at the level. Others get w = 0 (ITF and ITFQ in the frozen tables)."""
    ls = level_seasons(ts, season, first_es)
    out = []
    for li, L in enumerate(LEVELS):
        if L == "MAIN":
            continue
        if len(ls.get(L, [])) >= MIN_LEVEL_SEASONS and int((S["V"][fm, li] > 0).sum()) >= 30:
            out.append(L)
    return out


def role08_offsets(tss: dict, season: int, first_es: dict, s_off: dict) -> dict:
    """Role 08's rule, refitted walk-forward on the predictor's scale: per tour and level, the mean over player-seasons
    of the fit window with at least 3 box scores at the main tour (main draws) and 3 at the level of (his d-weighted
    mean surface-centred observation at the level - at the main tour). A cell under MIN_OFFSET_PLAYER_SEASONS
    player-seasons takes the both-tours value, then 0. Returns {(tour, level): (offset, player_seasons)}."""
    lo, hi = fit_years(season)
    per = {}
    for tour, ts in tss.items():
        so = s_off[tour]
        ok = (ts.year >= lo) & (ts.year <= hi) & (ts.lf_row + 1.0 <= first_es[season])   # the match clock
        yc = ts.year[ok]
        z = ts.y[ok] - so[ts.surf[ok]]
        d = ts.d[ok]
        key = pd.DataFrame({"code": ts.code[ok], "year": yc, "lev": ts.lev[ok],
                            "main": ts.bucket[ok] == "MAIN", "dz": d * z, "d": d})
        key = key[key["main"] | (key["lev"] > 0)]
        key["cell"] = np.where(key["main"], 0, key["lev"])
        g = key.groupby(["code", "year", "cell"]).agg(dz=("dz", "sum"), d=("d", "sum"), n=("d", "size"))
        g["m"] = g["dz"] / g["d"]
        g = g.reset_index()
        mm = g[g["cell"] == 0].set_index(["code", "year"])
        for li, L in enumerate(LEVELS):
            if L == "MAIN":
                continue
            ll = g[g["cell"] == li].set_index(["code", "year"])
            both = mm.index.intersection(ll.index)
            A, B = mm.loc[both], ll.loc[both]
            q = (A["n"] >= 3) & (B["n"] >= 3)
            diff = (B["m"] - A["m"])[q].to_numpy()
            per[(tour, L)] = diff
    out = {}
    for (tour, L), diff in per.items():
        if len(diff) >= MIN_OFFSET_PLAYER_SEASONS:
            out[(tour, L)] = (float(diff.mean()), len(diff))
        else:
            pooled = np.concatenate([per.get((t2, L), np.zeros(0)) for t2 in tss])
            if len(pooled) >= MIN_OFFSET_PLAYER_SEASONS:
                out[(tour, L)] = (float(pooled.mean()), len(pooled))
            else:
                out[(tour, L)] = (0.0, len(diff))
    return out


# ------------------------------------------------------------------------------------------------
# The predictor: design arrays for a set of targets, the loss with its analytic gradient, the fit

def design(ts: TourStat, S: dict, ix: np.ndarray, eref: float, soff: np.ndarray, lower: list[str],
           mode: str, c_const: dict | None = None, case_w: np.ndarray | None = None) -> dict:
    """The arrays the predictor reads for targets `ix`. Lower rows are surface-centred and then, by `mode`:
    'raw' (nothing more: pooled as equivalent), 'const' (minus a constant offset c_L per unit: role 08's rule) or
    'gap' (minus gamma * (E_opp - E_ref) per row: the opponent-gap translation). Main rows and the target are always
    surface-centred and opponent-adjusted by gamma (inside the model)."""
    V, Y, E, VS = S["V"][ix], S["Y"][ix], S["E"][ix], S["VS"][ix]
    cen = Y - np.einsum("tls,s->tl", VS, soff)
    gap = E - eref * V
    li = [LEVELS.index(L) for L in lower]
    t = ts.t
    out = {"x": t["x"][ix], "d": t["d"][ix], "bS": soff[t["surf"][ix]], "eg": t["eopp"][ix] - eref,
           "CM": cen[:, 0], "GM": gap[:, 0], "VM": V[:, 0], "CL": cen[:, li], "GL": gap[:, li], "VL": V[:, li],
           "mode": mode, "lower": list(lower), "tier": t["tier"][ix], "player": t["player"][ix],
           "low_exposure": t["low_exposure"][ix], "year": t["year"][ix], "obs": t["obs"][ix], "family": ts.family,
           "NRL": S["NR"][ix][:, li]}
    out["cL"] = np.array([(c_const or {}).get(L, 0.0) for L in lower])
    out["cw"] = np.ones(len(ix)) if case_w is None else case_w
    return out


def n_mu(spec: dict) -> int:
    """Free prior means: one per home tier ('tier', fitted), one ('pool'), none ('tierfixed': the newcomer means)."""
    return {"tier": len(TIERS), "pool": 1, "tierfixed": 0}[spec["prior"]]


def unpack(theta: np.ndarray, spec: dict, nL: int) -> dict:
    """Parameter vector -> {logk, mu (1, or one per home tier), delta (per lower level), w (per lower level), gamma}."""
    out = {"logk": theta[0]}
    i = 1
    nmu = n_mu(spec)
    out["mu"] = np.asarray(spec["mu_fix"], float) if spec["prior"] == "tierfixed" else theta[i:i + nmu]
    i += nmu
    if spec["delta"]:
        out["delta"] = theta[i:i + nL]
        i += nL
    else:
        out["delta"] = np.zeros(nL)
    if spec["w"] == "free":
        out["w"] = theta[i:i + nL]
        i += nL
    else:
        out["w"] = np.asarray(spec["wfix"], float) if nL else np.zeros(0)
    if spec.get("gamma_free"):
        out["gamma"] = theta[i]
        i += 1
    else:
        out["gamma"] = float(spec.get("gamma", 0.0))
    return out


def _core(theta: np.ndarray, D: dict, spec: dict):
    nL = D["VL"].shape[1]
    q_ = unpack(theta, spec, nL)
    k = np.exp(q_["logk"])
    g = q_["gamma"]
    mu_t = q_["mu"][D["tier"]] if spec["prior"] in ("tier", "tierfixed") else np.full(len(D["x"]), q_["mu"][0])
    ck = ("_cache", g)                      # the gamma-shifted sums are constant while gamma is
    if D.get("_ckey") != ck:
        if D["mode"] == "gap":
            AL = D["CL"] - g * D["GL"]
        elif D["mode"] == "const":
            AL = D["CL"] - D["cL"][None, :] * D["VL"]
        else:
            AL = D["CL"]
        D["_AL"], D["_AM"], D["_ckey"] = AL, D["CM"] - g * D["GM"], ck
    AL, AM = D["_AL"], D["_AM"]
    numL = AL - q_["delta"][None, :] * D["VL"]
    w = q_["w"]
    N = k * mu_t + AM + (numL @ w if nL else 0.0)
    Dn = k + D["VM"] + (D["VL"] @ w if nL else 0.0)
    q = N / Dn
    eta = D["bS"] + g * D["eg"] + q
    return q_, k, mu_t, numL, w, N, Dn, q, eta


def loglik_rows(eta: np.ndarray, x: np.ndarray, d: np.ndarray, family: str) -> tuple[np.ndarray, np.ndarray]:
    """Per-row log-likelihood (no constant) and its derivative in eta."""
    if family == "binomial":
        ll = x * eta - d * np.logaddexp(0.0, eta)
        return ll, x - d * expit(eta)
    lam = np.exp(np.clip(eta, -30, 30))
    return x * eta - d * lam, x - d * lam


def eta_grad_matrix(theta: np.ndarray, D: dict, spec: dict) -> tuple[np.ndarray, np.ndarray]:
    """eta per target and d eta / d theta (T x p)."""
    nL = D["VL"].shape[1]
    q_, k, mu_t, numL, w, N, Dn, q, eta = _core(theta, D, spec)
    cols = [k * (mu_t - q) / Dn]
    if spec["prior"] == "tier":
        for j in range(len(TIERS)):
            cols.append(np.where(D["tier"] == j, k / Dn, 0.0))
    elif spec["prior"] == "pool":
        cols.append(k / Dn)
    if spec["delta"]:
        for L in range(nL):
            cols.append(-w[L] * D["VL"][:, L] / Dn)
    if spec["w"] == "free":
        for L in range(nL):
            cols.append((numL[:, L] - q * D["VL"][:, L]) / Dn)
    if spec.get("gamma_free"):
        gl = (D["GL"] @ w) if (nL and D["mode"] == "gap") else 0.0
        cols.append(D["eg"] - (D["GM"] + gl) / Dn)
    return eta, np.column_stack(cols)


def penalty(theta: np.ndarray, spec: dict, nL: int) -> tuple[float, np.ndarray]:
    """Log-prior terms: delta ~ N(0, DELTA_RIDGE_SD^2); w ~ N(wbar_L, tau2_L) when a w prior is given (the
    hierarchical shrinkage across statistics); tier means ~ N(mu_MT, 1) (weak)."""
    q_ = unpack(theta, spec, nL)
    pen, grad = 0.0, np.zeros(len(theta))
    i = 1
    nmu = n_mu(spec)
    if spec["prior"] == "tier":
        mu = q_["mu"]
        for j in range(1, nmu):
            pen -= 0.5 * (mu[j] - mu[0]) ** 2
            grad[i + j] -= (mu[j] - mu[0])
            grad[i] += (mu[j] - mu[0])
    i += nmu
    if spec["delta"]:
        dl = q_["delta"]
        pen -= 0.5 * float(np.sum(dl ** 2)) / DELTA_RIDGE_SD ** 2
        grad[i:i + nL] -= dl / DELTA_RIDGE_SD ** 2
        i += nL
    if spec["w"] == "free" and spec.get("wprior") is not None:
        wbar, tau2 = spec["wprior"]
        wv = q_["w"]
        pen -= 0.5 * float(np.sum((wv - wbar) ** 2 / tau2))
        grad[i:i + nL] -= (wv - wbar) / tau2
    return pen, grad


SCALE = 1e4


def objective(theta: np.ndarray, D: dict, spec: dict) -> tuple[float, np.ndarray]:
    """The penalised negative log-likelihood per unit (scaled) and its analytic gradient, computed as dot products
    (the same derivatives as eta_grad_matrix, without building the Jacobian)."""
    nL = D["VL"].shape[1]
    q_, k, mu_t, numL, w, N, Dn, q, eta = _core(theta, D, spec)
    ll, r = loglik_rows(eta, D["x"], D["d"], D["family"])
    cw = D["cw"]
    rw = cw * r
    rD = rw / Dn
    g = [k * float(np.dot(rD, mu_t - q))]
    if spec["prior"] == "tier":
        g.extend(k * np.bincount(D["tier"], weights=rD, minlength=len(TIERS)))
    elif spec["prior"] == "pool":
        g.append(k * float(rD.sum()))
    if nL:
        rDV = rD @ D["VL"]
        if spec["delta"]:
            g.extend(-w * rDV)
        if spec["w"] == "free":
            g.extend(rD @ numL - (rD * q) @ D["VL"])
    if spec.get("gamma_free"):
        gl = (D["GL"] @ w) if (nL and D["mode"] == "gap") else 0.0
        g.append(float(np.dot(rw, D["eg"])) - float(np.dot(rD, D["GM"] + gl)))
    U = float(np.sum(cw * D["d"]))
    pen, gpen = penalty(theta, spec, nL)
    f = -(float(np.sum(cw * ll)) + pen) / U
    grad = -(np.asarray(g, float) + gpen) / U
    return SCALE * f, SCALE * grad


def bounds(spec: dict, nL: int) -> list:
    b = [(-3.0, 13.0)]
    b += [(-8.0, 8.0)] * n_mu(spec)
    if spec["delta"]:
        allowed = spec.get("delta_allowed")
        allowed = np.ones(nL, bool) if allowed is None else np.asarray(allowed, bool)
        b += [DELTA_BOUNDS if a else (0.0, 0.0) for a in allowed]     # delta held at 0 where the class bars it
    if spec["w"] == "free":
        b += [W_BOUNDS] * nL
    if spec.get("gamma_free"):
        b += [(-0.05, 0.05)]
    return b


def start_values(D: dict, spec: dict, prev: dict | None = None) -> np.ndarray:
    nL = D["VL"].shape[1]
    x, d = D["x"], D["d"]
    rate = x.sum() / d.sum()
    mu0 = (np.log(rate) - np.log1p(-rate)) if D["family"] == "binomial" else np.log(rate)
    mu0 -= float(np.average(D["bS"], weights=d))
    v = [np.log(10.0 * float(np.median(d)))]
    v += [mu0] * n_mu(spec)
    if spec["delta"]:
        v += [0.0] * nL
    if spec["w"] == "free":
        v += [1.0] * nL
    if spec.get("gamma_free"):
        v += [0.0]
    v = np.array(v, float)
    if prev is not None and len(prev.get("theta", [])) == len(v):     # warm start from a fit of the same shape
        v = np.array(prev["theta"], float)
    return v


def fit(D: dict, spec: dict, prev: dict | None = None, maxiter: int = 2000) -> dict:
    """Maximum (penalised) likelihood of a formulation's free parameters. A cold fit tries two starts (the prior worth
    ten typical matches, and worth one) and keeps the better: a start with the prior far too strong can stall in a
    poor optimum (seen once in five planted worlds with 2,000-unit targets; on real data 89 of 90 sampled fits were
    identical from five starts, the 90th 1e-6 per unit worse: scratch check of 9 Oct). A warm start (prev) is used
    alone."""
    nL = D["VL"].shape[1]
    b = bounds(spec, nL)
    v_first = start_values(D, spec, prev)
    starts = [v_first]
    if prev is None or len(prev.get("theta", [])) != len(v_first):
        v_alt = v_first.copy()
        v_alt[0] = np.log(float(np.median(D["d"])))
        starts.append(v_alt)
    best = None
    for v0 in starts:
        v0 = np.array([min(max(a, lo), hi) for a, (lo, hi) in zip(v0, b)])
        # tolerances: the comparisons need the loss to about 1e-9 per unit (f is scaled by 1e4, about 5e3 in all)
        r_ = minimize(objective, v0, args=(D, spec), jac=True, method="L-BFGS-B", bounds=b,
                      options={"maxiter": maxiter, "ftol": 1e-12, "gtol": 1e-6})
        if best is None or r_.fun < best.fun - 1e-12:
            best = r_
    r = best
    q_ = unpack(r.x, spec, nL)
    return {"theta": r.x, "k": float(np.exp(q_["logk"])), "mu": np.array(q_["mu"], float),
            "delta": np.array(q_["delta"], float), "w": np.asarray(q_["w"], float).copy(),
            "gamma": float(q_["gamma"]), "f": float(r.fun / SCALE), "converged": bool(r.success),
            "nit": int(r.nit), "lower": list(D["lower"])}


def predict_ll(theta: np.ndarray, D: dict, spec: dict) -> np.ndarray:
    """Per-target log-likelihood (no constant) of a fitted formulation."""
    eta, _ = eta_grad_matrix(theta, D, spec)
    return loglik_rows(eta, D["x"], D["d"], D["family"])[0]


def _llgrad(theta: np.ndarray, D: dict, spec: dict) -> np.ndarray:
    eta, J = eta_grad_matrix(theta, D, spec)
    _, r = loglik_rows(eta, D["x"], D["d"], D["family"])
    return (D["cw"] * r) @ J


def sandwich(theta: np.ndarray, D: dict, spec: dict) -> np.ndarray:
    """Player-clustered sandwich covariance of the free parameters (penalties left out; numerical Hessian of the
    analytic gradient)."""
    eta, J = eta_grad_matrix(theta, D, spec)
    _, r = loglik_rows(eta, D["x"], D["d"], D["family"])
    sc = (D["cw"] * r)[:, None] * J
    _, ix = np.unique(D["player"], return_inverse=True)
    G = int(ix.max()) + 1
    Sg = np.zeros((G, J.shape[1]))
    np.add.at(Sg, ix, sc)
    meat = Sg.T @ Sg * G / max(G - 1, 1)
    p = len(theta)
    H = np.zeros((p, p))
    for j in range(p):
        h = 1e-5 * max(1.0, abs(theta[j]))
        tp, tm = theta.copy(), theta.copy()
        tp[j] += h
        tm[j] -= h
        H[:, j] = (_llgrad(tp, D, spec) - _llgrad(tm, D, spec)) / (2 * h)
    H = 0.5 * (H + H.T)
    try:
        Hi = np.linalg.inv(-H)
    except np.linalg.LinAlgError:
        Hi = np.linalg.pinv(-H)
    return Hi @ meat @ Hi


# ------------------------------------------------------------------------------------------------
# Role A's classes and gamma; the newcomer prior; the formulations

def load_classes(path: Path = CLASSES_DIR / "classes.csv") -> dict:
    """{(tour, stat): {"class": "OPP" | "ENV", "delta_levels": [levels where delta is real]}} from role A's table."""
    c = pd.read_csv(path)
    c = c[c["kind"].eq("stat") & c["name"].isin(list(STATS))]
    out = {}
    for r in c.to_dict("records"):
        lv = str(r.get("delta_levels") or "none")
        out[(r["tour"], r["name"])] = {"class": r["class"],
                                       "delta_levels": [] if lv in ("none", "nan", "") else
                                       [x.strip() for x in lv.split(",") if x.strip()]}
    return out


def gamma_by_season(seasons, first_es: dict, mechanical: bool = False, stage0_dir: Path = C.STAGE0_DIR,
                    timing: Path = C.TIMING, strength: Path = STAGE1) -> pd.DataFrame:
    """Role A's walk-forward gamma per (season, tour, stat): classify.gamma(through = the season's cutoff), in logit
    (log) per 100 Elo. Seasons after 2025 read 2025 outcomes, so only the mechanical mode may ask for them."""
    from src.eda.lower_level_evidence import classify as A
    rows = []
    for Y in seasons:
        g = A.gamma(first_es[Y], stage0_dir=stage0_dir, timing=timing, strength_path=strength,
                    allow_holdout=bool(mechanical and Y >= 2026))
        g["season"] = Y
        rows.append(g[["season", "tour", "stat", "gamma", "gamma_lo", "gamma_hi", "gamma_unit", "n_rows",
                       "last_result_day", "method_version"]])
    return pd.concat(rows, ignore_index=True)


NEWCOMER_MAX_MAIN = 5             # a newcomer: fewer main-tour box scores than this in the previous two years
NEWCOMER_MIN_TARGETS = 50


def ml_constant(x: np.ndarray, d: np.ndarray, off: np.ndarray, family: str) -> float:
    """Maximum-likelihood constant mu of eta = off + mu (binomial or Poisson), by Newton's method."""
    r = x.sum() / d.sum()
    mu = (np.log(r) - np.log1p(-r) if family == "binomial" else np.log(r)) - float(np.average(off, weights=d))
    for _ in range(50):
        eta = off + mu
        if family == "binomial":
            p = expit(eta)
            g, h = float(np.sum(x - d * p)), -float(np.sum(d * p * (1 - p)))
        else:
            lam = np.exp(eta)
            g, h = float(np.sum(x - d * lam)), -float(np.sum(d * lam))
        step = g / h
        mu -= step
        if abs(step) < 1e-10:
            break
    return float(mu)


def newcomer_means(ts: TourStat, S: dict, fm: np.ndarray, soff: np.ndarray, eref: float, gamma: float
                   ) -> tuple[np.ndarray, dict]:
    """The owner's UFC prior made literal: per home tier, the average main-tour newcomer's level (opponent-adjusted
    and surface-centred, link scale) over the fit's targets whose player had fewer than NEWCOMER_MAX_MAIN main-tour box
    scores in the previous two years. A tier under NEWCOMER_MIN_TARGETS such targets takes the pooled newcomer mean
    (NaN when even that is thin: the caller then uses the fitted pool mean)."""
    t = ts.t
    nc = fm & (S["NR"][:, 0] < NEWCOMER_MAX_MAIN)
    off = soff[t["surf"]] + gamma * (t["eopp"] - eref)
    pooled = ml_constant(t["x"][nc], t["d"][nc], off[nc], ts.family) if nc.sum() >= NEWCOMER_MIN_TARGETS else np.nan
    mus = np.full(len(TIERS), pooled)
    counts = {}
    for j, tier in enumerate(TIERS):
        m = nc & (t["tier"] == j)
        counts[tier] = int(m.sum())
        if m.sum() >= NEWCOMER_MIN_TARGETS:
            mus[j] = ml_constant(t["x"][m], t["d"][m], off[m], ts.family)
    return mus, {"pooled": pooled, "counts": counts}


# The formulations: (lower-row mode, delta, w, prior, uses classes). "cls" mode = A's class: 'gap' for OPP, 'raw'
# (delta only) for ENV; "nc" = no classes: every statistic 'gap' with delta at every level.
FORMULATIONS = {
    "F0": ("raw", False, "one", "pool", False),
    "F1": (None, False, "zero", "pool", False),
    "F2": ("const", False, "one", "pool", False),
    "F2b": ("raw", True, "one", "pool", False),
    "F3g": ("cls", False, "one", "pool", True),
    "F3": ("cls", True, "one", "pool", True),
    "F4free": ("cls", True, "free", "pool", True),
    "F4": ("cls", True, "shrunk", "pool", True),
    "F5ml": ("cls", True, "free", "tier", True),
    "F5free": ("cls", True, "free", "tierfixed", True),
    "F5": ("cls", True, "shrunk", "tierfixed", True),
    "F3nc": ("gap", True, "one", "pool", False),
    "F4ncfree": ("gap", True, "free", "pool", False),
    "F4nc": ("gap", True, "shrunk", "pool", False),
    "F5ncfree": ("gap", True, "free", "tierfixed", False),
    "F5nc": ("gap", True, "shrunk", "tierfixed", False),
}
PASS1 = ("F4free", "F5free", "F4ncfree", "F5ncfree")      # their per-statistic w feed the shrinkage across statistics
SHRUNK_OF = {"F4": "F4free", "F5": "F5free", "F4nc": "F4ncfree", "F5nc": "F5ncfree"}


class Season:
    """Everything one season's fit and scores of one (tour, statistic) read, all from results in by the season's
    cutoff: the fit and score targets, E_ref, the surface offsets, the fitted lower levels, role 08's offsets, gamma,
    the class and the newcomer means."""

    def __init__(self, ts: TourStat, S: dict, Y: int, first_es: dict, eref: float, gamma_pt: float, cls: dict,
                 c08: dict | None = None, score: bool = True):
        self.ts, self.S, self.Y = ts, S, Y
        fm = fit_mask(ts, Y, first_es)
        self.fm = fm
        self.fi = np.flatnonzero(fm)
        self.si = np.flatnonzero(ts.t["year"] == Y) if score else np.zeros(0, np.int64)
        self.eref = eref
        self.soff = surface_offsets(ts, fm)
        self.lower = fitted_levels(ts, S, fm, Y, first_es)
        self.gamma = 0.0 if not np.isfinite(gamma_pt) else float(gamma_pt)
        self.cls = cls or {"class": "OPP", "delta_levels": list(LOWER)}
        self.c08 = c08 or {}
        self.mus, self.mus_info = newcomer_means(ts, S, fm, self.soff, eref, self.gamma)

    def setup(self, name: str, wprior: dict | None = None, wfix: float | None = None,
              case_w: np.ndarray | None = None) -> tuple[dict, dict, dict]:
        """(fit design, score design, spec) of a formulation. wprior: {level: (wbar, tau2)}; wfix: a uniform w (the
        dose curve) replacing the formulation's weights."""
        mode, has_delta, wmode, prior, uses_cls = FORMULATIONS[name]
        lower = [] if wmode == "zero" else list(self.lower)
        if mode == "cls":
            mode = "gap" if self.cls["class"] == "OPP" else "raw"
        mode = mode or "gap"
        allowed = [L in self.cls["delta_levels"] for L in lower] if uses_cls else [True] * len(lower)
        spec = {"prior": prior, "delta": has_delta, "gamma": self.gamma, "delta_allowed": allowed}
        if wfix is not None:
            spec.update({"w": "fixed", "wfix": [float(wfix)] * len(lower)})
        elif wmode in ("one", "zero"):
            spec.update({"w": "fixed", "wfix": [1.0] * len(lower)})
        else:
            spec["w"] = "free"
            if wmode == "shrunk" and wprior is not None:
                wb = np.array([wprior.get(L, (1.0, 1e6))[0] for L in lower])
                t2 = np.array([max(wprior.get(L, (1.0, 1e6))[1], 1e-4) for L in lower])
                spec["wprior"] = (wb, t2)
        if prior == "tierfixed":
            mus = self.mus.copy()
            if not np.all(np.isfinite(mus)):
                mus[~np.isfinite(mus)] = np.nanmean(mus) if np.any(np.isfinite(mus)) else 0.0
            spec["mu_fix"] = mus
        c = {L: self.c08.get(L, 0.0) for L in lower}
        Df = design(self.ts, self.S, self.fi, self.eref, self.soff, lower, mode, c,
                    None if case_w is None else case_w[self.fi])
        Ds = design(self.ts, self.S, self.si, self.eref, self.soff, lower, mode, c) if len(self.si) else None
        return Df, Ds, spec


# ------------------------------------------------------------------------------------------------
# Jobs: one statistic, both tours, in a worker process that loads the data once

_DATA: dict = {}


def _data(ctx: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    key = (ctx["through"], ctx.get("mechanical", False), ctx["stage0_dir"], ctx["timing"])
    if key not in _DATA:
        _DATA.clear()
        p = load(Path(ctx["stage0_dir"]), ctx["through"], Path(ctx["timing"]), stage1=Path(ctx.get("strength", STAGE1)),
                 mechanical=ctx.get("mechanical", False))
        _DATA[key] = (p, own_history(p))
    return _DATA[key]


def _seasons_for(stat: str, tss: dict, Ss: dict, Y: int, ctx: dict, score: bool) -> dict:
    out = {}
    for tour in TOURS:
        out[tour] = Season(tss[tour], Ss[tour], Y, ctx["first_es"], ctx["eref"][(tour, Y)],
                           ctx["gamma"].get((Y, tour, stat), np.nan), ctx["classes"].get((tour, stat)), score=score)
    c08 = role08_offsets(tss, Y, ctx["first_es"], {t: out[t].soff for t in TOURS})
    for tour in TOURS:
        out[tour].c08 = {L: c08[(tour, L)][0] for L in LOWER if (tour, L) in c08}
        out[tour].c08_n = {L: c08[(tour, L)][1] for L in LOWER if (tour, L) in c08}
    return out


def w_index(spec: dict, nL: int) -> int:
    return 1 + n_mu(spec) + (nL if spec["delta"] else 0)


def job_pass1(stat: str, ctx: dict) -> list[dict]:
    """Per (tour, season, half-life) and pass-1 formulation: each lower level's free w with its player-clustered SE
    (the input of the shrinkage across statistics)."""
    p, hist = _data(ctx)
    tss = {tour: TourStat(p, hist, tour, stat) for tour in TOURS}
    out = []
    for h in ctx["h_grid"]:
        Ss = {tour: tss[tour].sums(h) for tour in TOURS}
        for Y in ctx["seasons"]:
            ssd = _seasons_for(stat, tss, Ss, Y, ctx, score=False)
            for tour in TOURS:
                ss = ssd[tour]
                if len(ss.fi) < 200 or not ss.lower:
                    continue
                nL = len(ss.lower)
                for name in ctx.get("pass1", PASS1):
                    if "nc" in name and h != DEFAULT_H_WEEKS:      # the no-class variants: default half-life only
                        continue
                    Df, _, spec = ss.setup(name)
                    f = fit(Df, spec)
                    try:
                        V = sandwich(f["theta"], Df, spec)
                        i0 = w_index(spec, nL)
                        se = np.sqrt(np.clip(np.diag(V)[i0:i0 + nL], 0, None))
                    except Exception:                               # noqa: BLE001 (a singular fit: no SE)
                        se = np.full(nL, np.nan)
                    for j, L in enumerate(ss.lower):
                        out.append({"stat": stat, "tour": tour, "season": Y, "h": h, "formulation": name, "level": L,
                                    "w": float(f["w"][j]), "se": float(se[j]), "delta": float(f["delta"][j]),
                                    "k": f["k"], "converged": f["converged"]})
    return out


def shrinkage(pass1: pd.DataFrame, min_stats: int = 3) -> dict:
    """The hierarchical shrinkage of w across statistics within a level (per tour, season, half-life, formulation):
    DerSimonian-Laird between-statistic variance tau2 and the precision-weighted level mean wbar, from each statistic's
    free w and its player-clustered SE (an SE under 0.02 or missing is floored at 0.02; a w at a bound keeps its SE).
    Returns {(tour, season, h, formulation, level): (wbar, tau2)}; levels with under `min_stats` statistics get no
    shrinkage (tau2 = 1e6)."""
    out = {}
    for key, g in pass1.groupby(["tour", "season", "h", "formulation", "level"]):
        w = g["w"].to_numpy(float)
        se = np.nan_to_num(g["se"].to_numpy(float), nan=1.0)
        se = np.maximum(se, 0.02)
        if len(w) < min_stats:
            out[key] = (float(np.mean(w)), 1e6)
            continue
        u = 1.0 / se ** 2
        wfe = float(np.sum(u * w) / np.sum(u))
        Q = float(np.sum(u * (w - wfe) ** 2))
        den = float(np.sum(u) - np.sum(u ** 2) / np.sum(u))
        tau2 = max(0.0, (Q - (len(w) - 1)) / den) if den > 0 else 0.0
        v = 1.0 / (se ** 2 + tau2)
        out[key] = (float(np.sum(v * w) / np.sum(v)), float(tau2))
    return out


DEV_FULL = ("F0", "F1", "F2", "F2b", "F3g", "F3", "F4free", "F4", "F5ml", "F5free", "F5", "F3nc", "F4ncfree", "F4nc",
            "F5ncfree", "F5nc")
DEV_HGRID = ("F3", "F4", "F5")                 # the no-class variants: default half-life only
DOSE_BASES = ("F4", "F5")


def job_pass2(stat: str, ctx: dict, shrink: dict, work: str) -> list[dict]:
    """Every formulation's fit for each (tour, season) and its per-target log-likelihood on the season's main-tour
    targets: the full set at the default half-life, the h-grid set at the others; F6 (per tour and season, the
    half-life whose fit-window log-likelihood is highest, for F4 and F5); the dose curve (uniform w) at the default
    half-life and at F6's. Per-target columns go to <work>/targets_<stat>.parquet; the fits are returned."""
    p, hist = _data(ctx)
    tss = {tour: TourStat(p, hist, tour, stat) for tour in TOURS}
    fits_out = []
    cols: dict = {}                 # (tour, Y) -> {column: array}
    train_ll: dict = {}             # (tour, Y, name, h) -> fit-window log-likelihood per unit (unpenalised)
    h_def = DEFAULT_H_WEEKS

    def run(ss, tour, Y, name, h, wfix=None, tag=None):
        wprior = None
        if name in SHRUNK_OF:
            wprior = {L: shrink.get((tour, Y, h, SHRUNK_OF[name], L), (1.0, 1e6)) for L in ss.lower}
        Df, Ds, spec = ss.setup(name, wprior=wprior, wfix=wfix)
        f = fit(Df, spec)
        tr = float(predict_ll(f["theta"], Df, spec).sum() / Df["d"].sum())
        col = tag or f"{name}@{h:g}"
        if Ds is not None and len(Ds["x"]):
            cols[(tour, Y)][col] = predict_ll(f["theta"], Ds, spec)
        train_ll[(tour, Y, col)] = tr
        rec = {"stat": stat, "tour": tour, "season": Y, "h": h, "column": col, "formulation": name,
               "wfix": wfix, "k": f["k"], "gamma": f["gamma"], "converged": f["converged"], "nit": f["nit"],
               "train_ll_per_unit": tr, "fit_targets": int(len(ss.fi)), "lower": ",".join(ss.lower),
               "mode": Df["mode"], "class": ss.cls["class"]}
        for j, L in enumerate(f["lower"]):
            rec[f"w_{L}"] = float(f["w"][j]) if len(f["w"]) else np.nan
            rec[f"delta_{L}"] = float(f["delta"][j])
            rec[f"c08_{L}"] = float(ss.c08.get(L, 0.0))
        for j, tier in enumerate(TIERS):
            rec[f"mu_{tier}"] = float(f["mu"][j]) if len(f["mu"]) > j else (float(f["mu"][0]) if len(f["mu"]) else np.nan)
            rec[f"newcomer_mu_{tier}"] = float(ss.mus[j])
        fits_out.append(rec)
        return f

    for h in ctx["h_grid"]:
        Ss = {tour: tss[tour].sums(h) for tour in TOURS}
        for Y in ctx["seasons"]:
            ssd = _seasons_for(stat, tss, Ss, Y, ctx, score=True)
            for tour in TOURS:
                ss = ssd[tour]
                if len(ss.fi) < 200 or len(ss.si) == 0:
                    continue
                if (tour, Y) not in cols:
                    t = tss[tour].t
                    si = ss.si
                    cols[(tour, Y)] = {"stat": np.array([stat] * len(si)), "tour": np.array([tour] * len(si)),
                                       "season": np.full(len(si), Y), "player": t["player"][si], "d": t["d"][si],
                                       "low_exposure": t["low_exposure"][si], "n_MT": t["n_MT"][si],
                                       "tier": t["tier"][si], "match_row": t["match_row"][si],
                                       "has_lower": (Ss[tour]["V"][si][:, 1:] > 0).any(axis=1)}
                names = DEV_FULL if h == h_def else DEV_HGRID
                for name in names:
                    run(ss, tour, Y, name, h)
                for base in DOSE_BASES:
                    if h == h_def:
                        for wv in DOSE_GRID:
                            run(ss, tour, Y, base, h, wfix=wv, tag=f"dose_{base}_{wv:g}@{h:g}")
    # F6: per (tour, season) and base, the half-life with the highest fit-window log-likelihood; then the dose there
    hs = list(ctx["h_grid"])
    for (tour, Y) in list(cols):
        for base in DEV_HGRID:
            tl = [train_ll.get((tour, Y, f"{base}@{h:g}"), -np.inf) for h in hs]
            hb = hs[int(np.argmax(tl))]
            cols[(tour, Y)][f"F6_{base}"] = cols[(tour, Y)][f"{base}@{hb:g}"]
            fits_out.append({"stat": stat, "tour": tour, "season": Y, "h": hb, "column": f"F6_{base}",
                             "formulation": f"F6_{base}", "train_ll_per_unit": max(tl)})
    if ctx.get("dose_at_f6", True):
        for (tour, Y) in list(cols):
            for base in DOSE_BASES:
                hb = [r["h"] for r in fits_out if r["column"] == f"F6_{base}" and r["tour"] == tour and r["season"] == Y][0]
                if hb == h_def:                      # F6 kept the default half-life: its dose is the default's
                    for wv in DOSE_GRID:
                        cols[(tour, Y)][f"dose_{base}_{wv:g}@F6"] = cols[(tour, Y)][f"dose_{base}_{wv:g}@{h_def:g}"]
                    continue
                ss = Season(tss[tour], tss[tour].sums(hb), Y, ctx["first_es"], ctx["eref"][(tour, Y)],
                            ctx["gamma"].get((Y, tour, stat), np.nan), ctx["classes"].get((tour, stat)), score=True)
                for wv in DOSE_GRID:
                    run(ss, tour, Y, base, hb, wfix=wv, tag=f"dose_{base}_{wv:g}@F6")
    frames = []
    for (tour, Y), c in cols.items():
        df = pd.DataFrame({k: v for k, v in c.items() if not isinstance(v, np.ndarray) or v.ndim == 1})
        frames.append(df)
    if frames:
        out = pd.concat(frames, ignore_index=True)
        base_ll = out["F0@52"].to_numpy(float) if "F0@52" in out else None
        llc = [c for c in out.columns if "@" in c or c.startswith("F6_")]
        for c in llc:
            if c != "F0@52" and base_ll is not None:
                out[c] = (out[c].to_numpy(float) - base_ll).astype(np.float32)      # stored as the gain over F0
        Path(work).mkdir(parents=True, exist_ok=True)
        out.to_parquet(Path(work) / f"targets_{stat}.parquet", index=False)
    return fits_out


# ------------------------------------------------------------------------------------------------
# Aggregation: gains over F0 per statistic and per group, player-clustered; the dose curve; the F6 choice

def verdict(est: float, se: float) -> tuple[float, str]:
    """P(better) = Phi(est / se) and the owner's label: better / worse when the 95% interval clears 0, else
    unresolved."""
    from scipy.stats import norm
    if not np.isfinite(se) or se <= 0:
        return np.nan, "unresolved"
    pb = float(norm.cdf(est / se))
    lo, hi = est - 1.96 * se, est + 1.96 * se
    return pb, ("better" if lo > 0 else "worse" if hi < 0 else "unresolved")


def player_influence(dll: np.ndarray, d: np.ndarray, player: np.ndarray, players: np.ndarray) -> tuple[float, np.ndarray]:
    """gain = sum(dll) / sum(d) (per unit) and each player's linearised influence on it (indexed like `players`)."""
    U = float(d.sum())
    g = float(dll.sum()) / U
    ix = np.searchsorted(players, player)
    z = np.bincount(ix, weights=dll - g * d, minlength=len(players)) / U
    return g, z


def summarise(tg: pd.DataFrame, columns: list[str], periods: dict, groups_of_stats: dict) -> pd.DataFrame:
    """Gains over F0 (milli per unit; + = better) per tour, statistic or statistic group, period, exposure group and
    column, with player-clustered 95% intervals and P(better). A statistic group's gain is the mean of its statistics'
    gains, its interval from the summed player influences."""
    rows = []
    for tour in TOURS:
        t = tg[tg["tour"].eq(tour)]
        players = np.unique(t["player"].to_numpy())
        G = len(players)
        for pname, (lo, hi) in periods.items():
            tp = t[t["season"].between(lo, hi)]
            for ex_name, ex in (("all", None), ("low_exposure", True)):
                te = tp if ex is None else tp[tp["low_exposure"].to_numpy()]
                for col in columns:
                    if col not in te.columns:
                        continue
                    per_stat = {}
                    for stat, ts_ in te.groupby("stat"):
                        v = ts_[col].to_numpy(float)
                        ok = np.isfinite(v)
                        if ok.sum() < 30:
                            continue
                        g, z = player_influence(v[ok], ts_["d"].to_numpy(float)[ok], ts_["player"].to_numpy()[ok],
                                                players)
                        per_stat[stat] = (g, z, int(ok.sum()))
                    for gname, members in groups_of_stats.items():
                        mem = [s for s in members if s in per_stat]
                        if not mem:
                            continue
                        g = float(np.mean([per_stat[s][0] for s in mem]))
                        z = np.mean([per_stat[s][1] for s in mem], axis=0)
                        se = float(np.sqrt(G / max(G - 1, 1) * np.dot(z, z)))
                        pb, lab = verdict(g, se)
                        rows.append({"tour": tour, "period": pname, "exposure": ex_name, "column": col,
                                     "stat_group": gname, "n_stats": len(mem),
                                     "targets": int(sum(per_stat[s][2] for s in mem)),
                                     "gain_milli": 1000 * g, "se": 1000 * se, "lo": 1000 * (g - 1.96 * se),
                                     "hi": 1000 * (g + 1.96 * se), "p_better": pb, "reading": lab})
    return pd.DataFrame(rows)


SELECT_PERIOD = (2015, 2018)      # the F6 choice and every method choice before the dev report
DEV_PERIOD = (2019, 2024)
F6_CANDIDATES = ("F3", "F4", "F5")


def choose_f6(summary: pd.DataFrame) -> dict:
    """The pre-registered F6 rule (written before any score was read): per tour, among F3, F4 and F5 at the default
    half-life, the one with the highest mean gain over F0 across all statistics in 2015-2018 (all targets); F6 is that
    formulation with the half-life chosen per season on its fit window."""
    out = {}
    s = summary[(summary["period"] == f"{SELECT_PERIOD[0]}-{SELECT_PERIOD[1]}") & (summary["exposure"] == "all")
                & (summary["stat_group"] == "all statistics")]
    for tour in TOURS:
        cand = s[(s["tour"] == tour) & s["column"].isin([f"{c}@{DEFAULT_H_WEEKS:g}" for c in F6_CANDIDATES])]
        if len(cand):
            best = cand.loc[cand["gain_milli"].idxmax(), "column"].split("@")[0]
            out[tour] = best
    return out


# ------------------------------------------------------------------------------------------------
# Step dev: the formulations, the half-life grid and the dose curve, walk-forward 2013-2024

def build_ctx(p: pd.DataFrame, first_es: dict, seasons, through: int, stage0_dir: Path, timing: Path,
              mechanical: bool = False, classes_path: Path = CLASSES_DIR / "classes.csv",
              h_grid=H_GRID_WEEKS, strength: Path = STAGE1) -> tuple[dict, pd.DataFrame]:
    eref = {(tour, Y): strength_ref(p, tour, Y, first_es) for tour in TOURS for Y in seasons}
    gam = gamma_by_season(seasons, first_es, mechanical, stage0_dir, timing, strength)
    gamma = {(int(r["season"]), r["tour"], r["stat"]): (r["gamma"] / 100.0 if np.isfinite(r["gamma"]) else np.nan)
             for r in gam.to_dict("records")}
    ctx = {"seasons": list(seasons), "first_es": first_es, "eref": eref, "gamma": gamma,
           "classes": load_classes(classes_path), "h_grid": list(h_grid), "through": through,
           "mechanical": mechanical, "stage0_dir": str(stage0_dir), "timing": str(timing), "strength": str(strength)}
    return ctx, gam


def check_cutoffs(first_es: dict, seasons) -> dict:
    """Role A's classify.season_cutoff against this module's (both: the first main-tour match's es)."""
    from src.eda.lower_level_evidence import classify as A
    out = {}
    for Y in seasons:
        a = int((A.season_cutoff(Y) - pd.Timestamp("1970-01-01")).days)
        out[str(Y)] = {"B": int(first_es[Y]), "A": a, "equal": a == int(first_es[Y])}
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def periods_dict(lo: int = 2013, hi: int = 2024) -> dict:
    out = {f"{SELECT_PERIOD[0]}-{SELECT_PERIOD[1]}": SELECT_PERIOD, f"{DEV_PERIOD[0]}-{DEV_PERIOD[1]}": DEV_PERIOD}
    for y in range(lo, hi + 1):
        out[str(y)] = (y, y)
    return out


def stat_groups() -> dict:
    g = {"all statistics": tuple(STATS)}
    g.update(GROUPS)
    g.update({s: (s,) for s in STATS})
    return g


def step_dev(a) -> None:
    seasons = list(range(a.first_season, a.last_season + 1))
    first_es = season_first_es(Path(a.stage0_dir), Path(a.timing))
    p = load(Path(a.stage0_dir), a.through, Path(a.timing), stage1=Path(a.strength))
    log(f"loaded {len(p):,} player rows; timing fallbacks {p.attrs['timing_fallback_rows']}, "
        f"Elo missing {p.attrs['elo_missing_rows']}")
    h_grid = tuple(float(x) for x in a.h_grid.split(",")) if a.h_grid else H_GRID_WEEKS
    ctx, gam = build_ctx(p, first_es, seasons, a.through, Path(a.stage0_dir), Path(a.timing), h_grid=h_grid,
                         strength=Path(a.strength))
    del p
    stats = a.stats.split(",") if a.stats else list(STATS)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(a.work)
    checks = {"cutoffs": check_cutoffs(first_es, seasons + [s for s in (2025, 2026) if s in first_es])}
    gam.to_csv(out / "dev_gamma_used.csv", index=False)
    log(f"pass 1: {len(stats)} statistics on {a.workers} workers")
    with ProcessPoolExecutor(max_workers=a.workers) as ex:          # one pool: each worker loads the data once
        p1 = [r for res in ex.map(job_pass1, stats, [ctx] * len(stats)) for r in res]
        pass1 = pd.DataFrame(p1)
        pass1.to_parquet(out / "dev_pass1.parquet", index=False)
        shrink = shrinkage(pass1)
        log("pass 2")
        fits = [r for res in ex.map(job_pass2, stats, [ctx] * len(stats), [shrink] * len(stats),
                                    [str(work)] * len(stats)) for r in res]
    fits = pd.DataFrame(fits)
    fits.to_parquet(out / "dev_fits.parquet", index=False)
    tg = pd.concat([pd.read_parquet(work / f"targets_{s}.parquet") for s in stats
                    if (work / f"targets_{s}.parquet").exists()], ignore_index=True)
    cols = [c for c in tg.columns if ("@" in c or c.startswith("F6_")) and c != "F0@52"]
    log(f"summarising {len(cols)} columns over {len(tg):,} targets")
    summ = summarise(tg, cols, periods_dict(seasons[0], seasons[-1]), stat_groups())
    summ.to_csv(out / "formulations.csv", index=False)
    f6 = choose_f6(summ)
    checks["f6_choice"] = f6
    checks["shrinkage_cells"] = len(shrink)
    checks["fits_not_converged"] = int((~fits["converged"].fillna(True).astype(bool)).sum())
    checks["fits"] = int(len(fits))
    checks["classes_sha256"] = sha256_file(CLASSES_DIR / "classes.csv")
    checks["gamma_method"] = sorted(set(gam["method_version"].astype(str)))
    checks["h_grid"] = list(h_grid)
    (out / "dev_checks.json").write_text(json.dumps(checks, indent=1, default=str), encoding="utf-8")
    log(f"F6 choice (2015-2018): {f6}; wrote {out}")



# ------------------------------------------------------------------------------------------------
# The results channel: the reference's Elo (stage1_baselines.elo_pass, retirements counted, its K schedule per tour)
# with K multiplied by w_results for lower-level results

ELO_K = {"atp": {"k0": 600.0, "offset": 2.0, "shape": 0.6},      # stage1_baselines_summary.json, "chosen", rule "ret"
         "wta": {"k0": 600.0, "offset": 1.0, "shape": 0.6}}
ELO_START = 1500.0
ELO_GRID = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25)
ELO_LEVELS = ("TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")         # team events stay at 1 (the layer leaves them)
ELO_SUMMARY = Path("C:/Users/zerom/tnr_lle/data/studies/predictability_diagnostic/stage1_baselines_summary.json")


def elo_k_schedule() -> dict:
    """The reference's K constants, checked against Stage 1's summary when it is readable."""
    if ELO_SUMMARY.exists():
        js = json.loads(ELO_SUMMARY.read_text(encoding="utf-8"))
        for c in js["chosen"]:
            if c["rule"] == "ret":
                k = ELO_K[c["tour"]]
                if (k["k0"], k["offset"], k["shape"]) != (c["k0"], c["offset"], c["shape"]):
                    raise RuntimeError(f"Stage 1's K schedule for {c['tour']} is not the one this module copies")
    return ELO_K


def elo_pass_w(week, event, rnd, a, b, a_won, upd, mult, n_players: int, k0: float, offset: float, shape: float,
               count_w: bool = True) -> np.ndarray:
    """stage1_baselines.elo_pass (its time rule: a round's updates reach the next round of the event, an event's reach
    other events after the week), overall rating only, with each update's K multiplied by mult[i]. A player's
    rated-match count advances by mult[i] (count_w) or by 1. With mult = 1 it is the reference's pass. Returns A's and
    B's pre-match ratings."""
    R = [ELO_START] * n_players
    N = [0.0] * n_players
    out = np.full((len(week), 2), np.nan)
    lo: dict = {}
    cur = None
    for i in range(len(week)):
        if week[i] != cur:
            for (p_, _), st in lo.items():
                R[p_] += st[0] + st[3]
                N[p_] += st[1] + st[4]
            lo.clear()
            cur = week[i]
        e, r, pa, pb = event[i], rnd[i], a[i], b[i]
        xa = lo.get((pa, e))
        if xa is None:
            xa = lo[(pa, e)] = [0.0, 0.0, r, 0.0, 0.0]
        elif xa[2] < r:
            xa[0] += xa[3]; xa[1] += xa[4]; xa[2] = r; xa[3] = 0.0; xa[4] = 0.0
        xb = lo.get((pb, e))
        if xb is None:
            xb = lo[(pb, e)] = [0.0, 0.0, r, 0.0, 0.0]
        elif xb[2] < r:
            xb[0] += xb[3]; xb[1] += xb[4]; xb[2] = r; xb[3] = 0.0; xb[4] = 0.0
        ra, rb, na, nb = R[pa] + xa[0], R[pb] + xb[0], N[pa] + xa[1], N[pb] + xb[1]
        out[i, 0], out[i, 1] = ra, rb
        if upd[i]:
            m = mult[i]
            res = 1.0 if a_won[i] else 0.0
            surprise = res - 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            if m:
                xa[3] += m * k0 / (na + offset) ** shape * surprise
                xb[3] -= m * k0 / (nb + offset) ** shape * surprise
            inc = m if count_w else 1.0
            xa[4] += inc
            xb[4] += inc
    return out


def elo_history(stage0_dir: Path, through: int, timing: Path, mechanical: bool = False) -> dict:
    """Per tour: every match of seasons up to `through` in Stage 0's order, as elo_pass reads them, with the bucket, the
    clock and the main-tour flag. Outcomes of seasons after 2024 only in the mechanical mode."""
    if through >= 2025 and not mechanical:
        raise SystemExit("Elo through 2025 or later reads holdout outcomes: only --mechanical may")
    m = C.load_matches(stage0_dir, columns=["tour", "year", "map_level", "status", "tournament_id", "tournament_date",
                                            "round_order", "player_a_id", "player_b_id", "a_won", "order"])
    m["date"] = pd.to_datetime(m["tournament_date"])
    keep = m["year"] <= through
    if through <= 2024:
        keep &= ~C.in_holdout(m["date"])
    m = m[keep].sort_values("order", kind="mergesort").reset_index(drop=True)
    if through <= 2024:
        C.assert_no_holdout_outcomes(m["date"], "relationship.elo_history: results")
    t = pd.read_parquet(timing, columns=["match_id", "es", "lf"])
    m = m.merge(t, on="match_id", how="left")
    out = {}
    for tour in TOURS:
        x = m[m["tour"].eq(tour)].reset_index(drop=True)
        players, codes = np.unique(np.concatenate([x["player_a_id"].to_numpy(), x["player_b_id"].to_numpy()]),
                                   return_inverse=True)
        out[tour] = {"week": x["date"].to_numpy().astype("datetime64[D]").astype("int64").tolist(),
                     "event": pd.factorize(x["tournament_date"].astype(str) + "|" + x["tournament_id"])[0].tolist(),
                     "rnd": x["round_order"].astype(int).tolist(),
                     "a": codes[:len(x)].tolist(), "b": codes[len(x):].tolist(),
                     "a_won": x["a_won"].fillna(False).astype(bool).tolist(),
                     "upd": x["status"].isin(["completed", "retired"]).tolist(), "n_players": int(len(players)),
                     "bucket": x["bucket"].to_numpy(), "year": x["year"].to_numpy(), "match_id": x["match_id"].to_numpy(),
                     "y": x["a_won"].astype(float).to_numpy(), "lf": x["lf"].to_numpy(float),
                     "es": x["es"].to_numpy(float), "main": (x["bucket"].eq("MAIN") & x["status"].isin(
                         ["completed", "retired"])).to_numpy()}
    return out


def elo_run(h: dict, tour: str, mult_by_level: dict, count_w: bool = True) -> np.ndarray:
    """P(A wins) before each match, the K of each lower-level result multiplied by its level's w_results."""
    k = elo_k_schedule()[tour]
    mult = np.ones(len(h["week"]))
    for L, v in mult_by_level.items():
        mult[h["bucket"] == L] = v
    r = elo_pass_w(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["upd"], mult.tolist(),
                   h["n_players"], k["k0"], k["offset"], k["shape"], count_w=count_w)
    return 1.0 / (1.0 + 10.0 ** ((r[:, 1] - r[:, 0]) / 400.0)), r


def _elo_job(args) -> tuple:
    tour, setting, count_w, ctx = args
    if "_elo" not in _DATA:
        _DATA["_elo"] = elo_history(Path(ctx["stage0_dir"]), ctx["through"], Path(ctx["timing"]),
                                    mechanical=ctx.get("mechanical", False))
    h = _DATA["_elo"][tour]
    p_, _ = elo_run(h, tour, dict(setting), count_w=count_w)
    y = h["y"]
    pc_ = np.clip(p_, 1e-9, 1 - 1e-9)
    ll = np.where(h["main"], y * np.log(pc_) + (1 - y) * np.log(1 - pc_), np.nan)
    return tour, setting, count_w, ll.astype(np.float64)


ANCHOR = int(np.datetime64("2009-12-28", "D").astype("int64"))       # a Monday: the 4-week blocks' grid


def block_gain(diff: np.ndarray, block: np.ndarray) -> tuple[float, float]:
    """Mean of a per-match difference (mLL) and its 4-week-block SE."""
    g = float(diff.mean())
    _, ix = np.unique(block, return_inverse=True)
    G = int(ix.max()) + 1
    z = np.bincount(ix, weights=diff - g)
    return 1000 * g, 1000 * float(np.sqrt(G / max(G - 1, 1) * np.dot(z, z)) / len(diff))


def elo_select(ll: dict, h: dict, first_es: dict, seasons, levels) -> dict:
    """Walk-forward w_results per (season, level): on main-tour results of the trailing FIT_SEASONS seasons in by the
    season's cutoff, the grid value with the highest log-likelihood, each level with the others at 1."""
    out = {}
    for Y in seasons:
        lo_, hi_ = fit_years(Y)
        tr = h["main"] & (h["year"] >= lo_) & (h["year"] <= hi_) & (h["lf"] + 1.0 <= first_es[Y])
        base = float(np.nansum(ll[()][tr]))
        for L in levels:
            best_v, best = 1.0, base
            for v in ELO_GRID:
                if v == 1.0:
                    continue
                s = float(np.nansum(ll[((L, v),)][tr]))
                if s > best + 1e-9:
                    best_v, best = v, s
            out[(Y, L)] = (best_v, best - base, int(tr.sum()))
    return out


def step_elo(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    first_es = season_first_es(Path(a.stage0_dir), Path(a.timing))
    ctx = {"stage0_dir": a.stage0_dir, "timing": a.timing, "through": a.through, "mechanical": False}
    hist = elo_history(Path(a.stage0_dir), a.through, Path(a.timing))
    # the reproduction check: mult 1 must give the reference's pre-match Elo
    st = pd.read_parquet(Path(a.strength), columns=["match_id", "elo_a_ret", "elo_b_ret"]).set_index("match_id")
    checks = {}
    for tour in TOURS:
        h = hist[tour]
        _, r = elo_run(h, tour, {})
        ea = pd.Series(h["match_id"]).map(st["elo_a_ret"]).to_numpy(float)
        eb = pd.Series(h["match_id"]).map(st["elo_b_ret"]).to_numpy(float)
        checks[tour] = {"matches": int(len(r)), "max_abs_diff_A": float(np.nanmax(np.abs(r[:, 0] - ea))),
                        "max_abs_diff_B": float(np.nanmax(np.abs(r[:, 1] - eb)))}
        log(f"Elo reproduction {tour}: {checks[tour]}")
    levels = [L for L in ELO_LEVELS if any((hist[t]["bucket"] == L).any() for t in TOURS)]
    settings = [()] + [((L, v),) for L in levels for v in ELO_GRID if v != 1.0]
    jobs = [(tour, s, True, ctx) for tour in TOURS for s in settings]
    log(f"Elo grid: {len(jobs)} passes on {a.workers} workers")
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(_elo_job, jobs))
    ll = {tour: {} for tour in TOURS}
    for tour, s, cw, v in res:
        ll[tour][s] = v
    seasons = list(range(a.first_season, a.last_season + 1))
    rows_grid, rows_sel, rows_score = [], [], []
    joint = {}
    for tour in TOURS:
        h = hist[tour]
        block = (np.asarray(h["week"]) - ANCHOR) // 28
        dev = h["main"] & (h["year"] >= DEV_PERIOD[0]) & (h["year"] <= DEV_PERIOD[1])
        for s in settings[1:]:
            d_ = (ll[tour][s] - ll[tour][()])[dev]
            g, se = block_gain(d_, block[dev])
            pb, lab = verdict(g, se)
            (L, v), = s
            rows_grid.append({"tour": tour, "level": L, "w_results": v, "period": "2019-2024", "matches": int(dev.sum()),
                              "gain_vs_1_mLL": g, "se": se, "lo": g - 1.96 * se, "hi": g + 1.96 * se,
                              "p_better": pb, "reading": lab})
        sel = elo_select(ll[tour], h, first_es, seasons, levels)
        for (Y, L), (v, gain, n) in sel.items():
            rows_sel.append({"season_used": Y, "tour": tour, "level": L, "w_results": v,
                             "train_gain_total_ll": gain, "train_matches": n})
        for Y in seasons:
            joint[(tour, Y)] = tuple(sorted((L, sel[(Y, L)][0]) for L in levels if sel[(Y, L)][0] != 1.0))
    # the joint (per-level choices together) walk-forward score: one pass per distinct joint setting
    need = sorted({(tour, s) for (tour, Y), s in joint.items() if s and s not in ll[tour]})
    if need:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for tour, s, cw, v in ex.map(_elo_job, [(t, s, True, ctx) for t, s in need]):
                ll[tour][s] = v
    # the count rule: rated-match counts advancing by 1 instead of by w_results, at each joint setting
    need_c = sorted({(tour, s) for (tour, Y), s in joint.items() if s})
    llc = {}
    if need_c:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for tour, s, cw, v in ex.map(_elo_job, [(t, s, False, ctx) for t, s in need_c]):
                llc[(tour, s)] = v
    for tour in TOURS:
        h = hist[tour]
        block = (np.asarray(h["week"]) - ANCHOR) // 28
        diffs, blocks, diffs_c = [], [], []
        for Y in seasons:
            m = h["main"] & (h["year"] == Y)
            s = joint[(tour, Y)]
            d_ = (ll[tour][s] - ll[tour][()])[m] if s else np.zeros(int(m.sum()))
            dc = (llc[(tour, s)] - ll[tour][()])[m] if s else np.zeros(int(m.sum()))
            g, se = block_gain(d_, block[m])
            rows_score.append({"tour": tour, "season": Y, "joint_setting": str(dict(s)), "matches": int(m.sum()),
                               "gain_vs_1_mLL": g, "se": se, "count_rule": "w"})
            if DEV_PERIOD[0] <= Y <= DEV_PERIOD[1]:
                diffs.append(d_)
                diffs_c.append(dc)
                blocks.append(block[m])
        if diffs:
            d_, b_ = np.concatenate(diffs), np.concatenate(blocks)
            for name, dd in (("w", d_), ("one", np.concatenate(diffs_c))):
                g, se = block_gain(dd, b_)
                pb, lab = verdict(g, se)
                rows_score.append({"tour": tour, "season": "2019-2024", "joint_setting": "walk-forward choices",
                                   "matches": int(len(dd)), "gain_vs_1_mLL": g, "se": se, "lo": g - 1.96 * se,
                                   "hi": g + 1.96 * se, "p_better": pb, "reading": lab, "count_rule": name})
    pd.DataFrame(rows_grid).to_csv(out / "elo_grid.csv", index=False)
    pd.DataFrame(rows_sel).to_csv(out / "elo_w_results.csv", index=False)
    pd.DataFrame(rows_score).to_csv(out / "elo_scores.csv", index=False)
    checks["k_schedule"] = elo_k_schedule()
    checks["levels"] = levels
    (out / "elo_checks.json").write_text(json.dumps(checks, indent=1, default=str), encoding="utf-8")
    log(f"wrote the results channel to {out}")



# ------------------------------------------------------------------------------------------------
# Step params: the parameter tables (SPEC 6.2), one code path for every season (2025-2026 only in the mechanical mode)

def boot_weights(n_codes: int, season: int, tour: str, b: int) -> np.ndarray:
    """The player-block bootstrap's multipliers (Poisson(1) per player), identical in every worker and statistic for
    a (season, tour, draw), so the draws stay aligned across statistics."""
    rng = np.random.default_rng([SEED, season, TOURS.index(tour), b])
    return rng.poisson(1.0, size=n_codes).astype(float)


def _tour_stats(stat: str, ctx: dict) -> tuple[dict, int]:
    p, hist = _data(ctx)
    return {tour: TourStat(p, hist, tour, stat) for tour in TOURS}, int(p["pcode"].max()) + 1


def method_names(method: str) -> tuple[str, str, str, str]:
    """(SYS free, SYS shrunk, NOCLASS free, NOCLASS shrunk) of a method (F4 or F5)."""
    return {"F4": ("F4free", "F4", "F4ncfree", "F4nc"), "F5": ("F5free", "F5", "F5ncfree", "F5nc")}[method]


def _w_se(f: dict, Df: dict, spec: dict) -> np.ndarray:
    nL = len(f["lower"])
    try:
        V = sandwich(f["theta"], Df, spec)
        i0 = w_index(spec, nL)
        return np.sqrt(np.clip(np.diag(V)[i0:i0 + nL], 0, None))
    except Exception:                                   # noqa: BLE001 (a singular fit: no SE)
        return np.full(nL, np.nan)


def job_params_p1(stat: str, ctx: dict) -> list[dict]:
    """Round 1: the method's free fit at every half-life (SYS) and at the default (NOCLASS), with SEs."""
    tss, _ = _tour_stats(stat, ctx)
    out = []
    for h in ctx["h_grid"]:
        Ss = {t: tss[t].sums(h) for t in TOURS}
        for Y in ctx["seasons"]:
            for tour in TOURS:
                ss = Season(tss[tour], Ss[tour], Y, ctx["first_es"], ctx["eref"][(tour, Y)],
                            ctx["gamma"].get((Y, tour, stat), np.nan), ctx["classes"].get((tour, stat)), score=False)
                if len(ss.fi) < 200 or not ss.lower:
                    continue
                sys_free, _, nc_free, _ = method_names(ctx["method"][tour])
                for name in (sys_free,) + ((nc_free,) if h == DEFAULT_H_WEEKS else ()):
                    Df, _, spec = ss.setup(name)
                    f = fit(Df, spec)
                    se = _w_se(f, Df, spec)
                    for j, L in enumerate(f["lower"]):
                        out.append({"stat": stat, "tour": tour, "season": Y, "h": h, "formulation": name,
                                    "level": L, "w": float(f["w"][j]), "se": float(se[j])})
    return out


def _season_point(ss: Season, tour: str, Y: int, name: str, h: float, shrink: dict, case_w=None, prev=None):
    wprior = {L: shrink.get((tour, Y, h, SHRUNK_OF[name], L), (1.0, 1e6)) for L in ss.lower} \
        if name in SHRUNK_OF else None
    Df, _, spec = ss.setup(name, wprior=wprior, case_w=case_w)
    f = fit(Df, spec, prev=prev)
    return f, Df, spec


def job_params_p2(stat: str, ctx: dict, shrink: dict) -> dict:
    """Round 2: the shrunk fits at every half-life; h* per (tour, season) by the fit-window log-likelihood; at h*:
    the point estimates (SYS), NOCLASS at the default half-life, the units per match, and the bootstrap's free fits
    (round A of the draws)."""
    tss, n_codes = _tour_stats(stat, ctx)
    Ss = {h: {t: tss[t].sums(h) for t in TOURS} for h in ctx["h_grid"]}
    points, boot_a = [], []
    for Y in ctx["seasons"]:
        for tour in TOURS:
            sys_free, sys_shr, nc_free, nc_shr = method_names(ctx["method"][tour])
            best = None
            for h in ctx["h_grid"]:
                ss = Season(tss[tour], Ss[h][tour], Y, ctx["first_es"], ctx["eref"][(tour, Y)],
                            ctx["gamma"].get((Y, tour, stat), np.nan), ctx["classes"].get((tour, stat)), score=False)
                if len(ss.fi) < 200:
                    break
                f, Df, spec = _season_point(ss, tour, Y, sys_shr, h, shrink)
                tr = float(predict_ll(f["theta"], Df, spec).sum() / Df["d"].sum())
                if best is None or tr > best[0]:
                    best = (tr, h, ss, f, Df, spec)
            if best is None:
                continue
            tr, h, ss, f, Df, spec = best
            fnc, Dnc, snc = None, None, None
            ssd = Season(tss[tour], Ss[DEFAULT_H_WEEKS][tour], Y, ctx["first_es"], ctx["eref"][(tour, Y)],
                         ctx["gamma"].get((Y, tour, stat), np.nan), ctx["classes"].get((tour, stat)), score=False)
            fnc, Dnc, snc = _season_point(ssd, tour, Y, nc_shr, DEFAULT_H_WEEKS, shrink)
            ts = tss[tour]
            fm = ss.fm
            lo_, hi_ = fit_years(Y)
            win = (ts.year >= lo_ - 2) & (ts.year <= hi_) & (ts.lf_row + 1.0 <= ctx["first_es"][Y])
            upm = {}
            for li, L in enumerate(LEVELS):
                m = win & (ts.lev == li) & ((ts.bucket == "MAIN") if L == "MAIN" else True)
                upm[L] = float(ts.d[m].mean()) if m.any() else np.nan
            npl = {"MAIN": int(len(np.unique(ts.t["player"][fm])))}
            for li, L in enumerate(LEVELS):
                if L != "MAIN":
                    npl[L] = int(len(np.unique(ts.t["player"][fm][ss.S["V"][fm, li] > 0])))
            free_ref = fit(*ss.setup(sys_free)[::2])        # the unshrunk w at h*
            points.append({"stat": stat, "tour": tour, "season": Y, "h": h, "train_ll": tr,
                           "lower": list(f["lower"]), "w": f["w"].tolist(), "delta": f["delta"].tolist(),
                           "w_free": free_ref["w"].tolist(), "k": f["k"], "mu": f["mu"].tolist(),
                           "newcomer_mu": ss.mus.tolist(), "newcomer_info": ss.mus_info, "gamma_pt": ss.gamma,
                           "class": ss.cls["class"], "delta_levels": ss.cls["delta_levels"], "mode": Df["mode"],
                           "converged": f["converged"], "fit_targets": int(len(ss.fi)),
                           "fit_through": float(ts.t["lf"][fm].max()), "units_per_match": upm, "n_players": npl,
                           "nc_lower": list(fnc["lower"]), "nc_w": fnc["w"].tolist(), "nc_delta": fnc["delta"].tolist(),
                           "nc_k": fnc["k"], "eref": ss.eref})
            # bootstrap round A: the free fit on each draw (warm-started at the full sample's free fit)
            for b in range(ctx["boot"]):
                cw = boot_weights(n_codes, Y, tour, b)[ts.t["player"]]
                Df_b, _, spec_b = ss.setup(sys_free, case_w=cw)
                fb = fit(Df_b, spec_b, prev=free_ref)
                for j, L in enumerate(fb["lower"]):
                    boot_a.append({"stat": stat, "tour": tour, "season": Y, "h": h, "b": b, "level": L,
                                   "w": float(fb["w"][j]), "formulation": sys_free})
    return {"points": points, "boot_a": boot_a}


def job_params_p3(stat: str, ctx: dict, points: list, shrink_pt: dict, shrink_b: dict) -> dict:
    """Round 3: the final point estimate at each statistic's h*, shrunk with the level means and spreads of the
    statistics' free fits at their own h* (the same construction as every bootstrap draw); then bootstrap round B: on
    each draw, the shrunk refit with that draw's level means and spreads."""
    tss, n_codes = _tour_stats(stat, ctx)
    out, finals = [], []
    cache = {}
    for pt in points:
        if pt["stat"] != stat:
            continue
        Y, tour, h = pt["season"], pt["tour"], pt["h"]
        if (tour, h) not in cache:
            cache[(tour, h)] = tss[tour].sums(h)
        ss = Season(tss[tour], cache[(tour, h)], Y, ctx["first_es"], ctx["eref"][(tour, Y)],
                    ctx["gamma"].get((Y, tour, stat), np.nan), ctx["classes"].get((tour, stat)), score=False)
        _, sys_shr, _, _ = method_names(ctx["method"][tour])
        wprior = {L: shrink_pt.get((tour, Y, L), (1.0, 1e6)) for L in ss.lower}
        Df, _, spec = ss.setup(sys_shr, wprior=wprior)
        f = fit(Df, spec)
        fin = dict(pt)
        fin.update({"w": f["w"].tolist(), "delta": f["delta"].tolist(), "k": f["k"], "mu": f["mu"].tolist(),
                    "lower": list(f["lower"]), "converged": f["converged"],
                    "train_ll": float(predict_ll(f["theta"], Df, spec).sum() / Df["d"].sum()),
                    "wbar": [float(wprior[L][0]) for L in f["lower"]], "tau2": [float(wprior[L][1]) for L in f["lower"]]})
        finals.append(fin)
        prev = f
        for b in range(ctx["boot"]):
            cw = boot_weights(n_codes, Y, tour, b)[tss[tour].t["player"]]
            wprior = {L: shrink_b.get((tour, Y, b, L), (1.0, 1e6)) for L in ss.lower}
            Df, _, spec = ss.setup(sys_shr, wprior=wprior, case_w=cw)
            f = fit(Df, spec, prev=prev)
            prev = f
            for j, L in enumerate(f["lower"]):
                out.append({"stat": stat, "tour": tour, "season": Y, "b": b, "level": L, "w": float(f["w"][j]),
                            "delta": float(f["delta"][j])})
    return {"points": finals, "draws": out}


def shrink_point(p1: pd.DataFrame, h_star: dict) -> dict:
    """The full sample's shrinkage across statistics from each statistic's free w at its own h* (the construction
    every bootstrap draw repeats). Returns {(tour, season, level): (wbar, tau2)}."""
    r = p1[~p1["formulation"].astype(str).str.endswith("ncfree")].copy()
    keep = [h_star.get((a_, b_, c_)) == h for a_, b_, c_, h in zip(r["stat"], r["tour"], r["season"], r["h"])]
    r = r[np.asarray(keep, bool)].copy()
    r["h"] = 0.0
    r["formulation"] = "point"
    sh = shrinkage(r)
    return {(t, Y, L): v for (t, Y, h, f_, L), v in sh.items()}


def shrink_draws(boot_a: pd.DataFrame, p1: pd.DataFrame, h_star: dict) -> dict:
    """Per draw: the shrinkage across statistics recomputed from the draw's free w, with each statistic's SE fixed at
    its full-sample value (round 1, at the statistic's h*). Returns {(tour, season, b, level): (wbar, tau2)}."""
    se = {(r["stat"], r["tour"], r["season"], r["h"], r["level"]): r["se"]
          for r in p1.to_dict("records") if not str(r["formulation"]).endswith("ncfree")}
    rows = []
    for r in boot_a.to_dict("records"):
        rows.append({"tour": r["tour"], "season": r["b"] * 10000 + r["season"], "h": 0.0,
                     "formulation": "draw", "level": r["level"], "w": r["w"],
                     "se": se.get((r["stat"], r["tour"], r["season"], h_star[(r["stat"], r["tour"], r["season"])],
                                   r["level"]), np.nan)})
    sh = shrinkage(pd.DataFrame(rows))
    return {(t, s % 10000, s // 10000, L): v for (t, s, h, f, L), v in sh.items()}


def params_rows(points: list, boot_b: pd.DataFrame, gam: pd.DataFrame, ctx: dict, code_sha: str) -> pd.DataFrame:
    """The SPEC 6.2 table: one row per (season_used, tour, stat, level)."""
    g = gam.set_index(["season", "tour", "stat"])
    q = boot_b.groupby(["stat", "tour", "season", "level"]).agg(
        w_lo=("w", lambda v: float(np.quantile(v, 0.025))), w_hi=("w", lambda v: float(np.quantile(v, 0.975))),
        delta_lo=("delta", lambda v: float(np.quantile(v, 0.025))),
        delta_hi=("delta", lambda v: float(np.quantile(v, 0.975))), boot_draws=("w", "size")) \
        if len(boot_b) else pd.DataFrame()
    rows = []
    for pt in points:
        Y, tour, stat = pt["season"], pt["tour"], pt["stat"]
        gr = g.loc[(Y, tour, stat)] if (Y, tour, stat) in g.index else None
        method = ctx["method"][tour]
        mu_pool = pt["mu"][0] if len(pt["mu"]) == 1 else np.nan
        for L in LEVELS:
            fitted = L == "MAIN" or L in pt["lower"]
            j = pt["lower"].index(L) if L in pt["lower"] else None
            jn = pt["nc_lower"].index(L) if L in pt["nc_lower"] else None
            tier = TIER_OF_LEVEL[L]
            rec = {"season_used": Y, "tour": tour, "stat": stat, "level": L,
                   "gamma": float(gr["gamma"]) if gr is not None else np.nan,
                   "gamma_unit": (str(gr["gamma_unit"]) + " per 100 Elo") if gr is not None else None,
                   "delta": 0.0 if j is None else float(pt["delta"][j]),
                   "w": 1.0 if L == "MAIN" else (0.0 if j is None else float(pt["w"][j])),
                   "n_players": pt["n_players"].get(L, 0), "strength_ref": pt["eref"],
                   "prior_mu": float(pt["newcomer_mu"][TIERS.index(tier)]) if method == "F5" else mu_pool,
                   "prior_k": pt["k"], "fit_through": str(np.datetime64(int(pt["fit_through"]), "D")),
                   "method_version": f"{METHOD_VERSION}|{method}|h*|{'classes' if True else ''}",
                   # beyond SPEC 6.2
                   "class": pt["class"], "translate_mode": pt["mode"], "fitted": bool(fitted),
                   "delta_allowed": L in pt["delta_levels"], "h_weeks": pt["h"],
                   "w_free": np.nan if j is None else float(pt["w_free"][j]),
                   "w_level_mean": np.nan if j is None else float(pt["wbar"][j]),
                   "w_tau2": np.nan if j is None else float(pt["tau2"][j]),
                   "prior_tier": tier, "prior_mu_newcomer": float(pt["newcomer_mu"][TIERS.index(tier)]),
                   "prior_mu_pool_fit": mu_pool, "prior_kind": "newcomer" if method == "F5" else "pool",
                   "units_per_match": pt["units_per_match"].get(L, np.nan),
                   "units_per_match_main": pt["units_per_match"].get("MAIN", np.nan),
                   "gamma_noclass": float(gr["gamma"]) if gr is not None else np.nan,
                   "delta_noclass": 0.0 if jn is None else float(pt["nc_delta"][jn]),
                   "w_noclass": 1.0 if L == "MAIN" else (0.0 if jn is None else float(pt["nc_w"][jn])),
                   "prior_k_noclass": pt["nc_k"], "fit_targets": pt["fit_targets"],
                   "converged": pt["converged"], "code_sha256": code_sha}
            rec["w_per_match"] = rec["w"] * rec["units_per_match"] / rec["units_per_match_main"] \
                if np.isfinite(rec["units_per_match"]) and rec["units_per_match_main"] else np.nan
            if L == "MAIN":
                rec.update({"w_lo": 1.0, "w_hi": 1.0, "delta_lo": 0.0, "delta_hi": 0.0, "boot_draws": 0})
            elif len(q) and (stat, tour, Y, L) in q.index:
                rec.update(q.loc[(stat, tour, Y, L)].to_dict())
            else:
                rec.update({"w_lo": 0.0 if j is None else np.nan, "w_hi": 0.0 if j is None else np.nan,
                            "delta_lo": 0.0 if j is None else np.nan, "delta_hi": 0.0 if j is None else np.nan,
                            "boot_draws": 0})
            rows.append(rec)
    return pd.DataFrame(rows)


JOINT_PAIRS = {"spw": "rpw", "hold": "brk", "bp_saved": "bp_conv", "ace": "def_ace", "df": "def_df",
               "first_in": "def_first_in", "first_won": "rpw_first", "second_won": "rpw_second",
               "bp_faced_pg": "def_bp_faced_pg", "tpw": "tpw"}


def add_joint_w(rows: pd.DataFrame) -> pd.DataFrame:
    """w_joint: the weight of one joint-solve observation (a serve statistic and its receiving side): the mean of the
    two sides' w, on both statistics' rows."""
    rows = rows.copy()
    key = rows.set_index(["season_used", "tour", "stat", "level"])["w"]
    mate = {**JOINT_PAIRS, **{v: k for k, v in JOINT_PAIRS.items()}}
    wj = []
    for r in rows[["season_used", "tour", "stat", "level", "w"]].itertuples(index=False):
        m = mate.get(r.stat)
        k2 = (r.season_used, r.tour, m, r.level)
        wj.append(0.5 * (r.w + key[k2]) if m is not None and k2 in key.index else np.nan)
    rows["w_joint"] = wj
    return rows


def results_rows(sel: pd.DataFrame, seasons, code_sha: str) -> pd.DataFrame:
    """Rows with stat = 'results': w_results per (season_used, tour, level), from the Elo grid's walk-forward choice."""
    rows = []
    for r in sel.to_dict("records"):
        if r["season_used"] not in seasons:
            continue
        rows.append({"season_used": r["season_used"], "tour": r["tour"], "stat": "results", "level": r["level"],
                     "gamma": np.nan, "delta": 0.0, "w": r["w_results"], "w_lo": np.nan, "w_hi": np.nan,
                     "delta_lo": np.nan, "delta_hi": np.nan, "n_players": np.nan, "strength_ref": np.nan,
                     "prior_mu": np.nan, "prior_k": np.nan, "fit_through": None,
                     "method_version": f"{METHOD_VERSION}|elo-grid", "class": "RES",
                     "train_gain_total_ll": r["train_gain_total_ll"], "train_matches": r["train_matches"],
                     "code_sha256": code_sha})
    return pd.DataFrame(rows)


def run_params(a, seasons, through: int, mechanical: bool) -> tuple[pd.DataFrame, dict]:
    first_es = season_first_es(Path(a.stage0_dir), Path(a.timing))
    p = load(Path(a.stage0_dir), through, Path(a.timing), stage1=Path(a.strength), mechanical=mechanical)
    h_grid = tuple(float(x) for x in a.h_grid.split(",")) if a.h_grid else H_GRID_WEEKS
    ctx, gam = build_ctx(p, first_es, seasons, through, Path(a.stage0_dir), Path(a.timing), mechanical=mechanical,
                         h_grid=h_grid, strength=Path(a.strength))
    del p
    ctx["method"] = parse_method(a.method)
    ctx["boot"] = a.boot
    stats = a.stats.split(",") if a.stats else list(STATS)
    code_sha = sha256_file(Path(__file__))
    quiet = mechanical
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        p1 = pd.DataFrame([r for res in ex.map(job_params_p1, stats, [ctx] * len(stats)) for r in res])
        shrink = shrinkage(p1)
        if not quiet:
            log("params round 2")
        r2 = list(ex.map(job_params_p2, stats, [ctx] * len(stats), [shrink] * len(stats)))
        points = [pt for r in r2 for pt in r["points"]]
        boot_a = pd.DataFrame([x for r in r2 for x in r["boot_a"]])
        h_star = {(pt["stat"], pt["tour"], pt["season"]): pt["h"] for pt in points}
        shrink_pt = shrink_point(p1, h_star)
        shrink_b = shrink_draws(boot_a, p1, h_star) if len(boot_a) else {}
        if not quiet:
            log("params round 3 (final points; bootstrap round B)")
        r3 = list(ex.map(job_params_p3, stats, [ctx] * len(stats), [points] * len(stats), [shrink_pt] * len(stats),
                         [shrink_b] * len(stats)))
    points = [pt for r in r3 for pt in r["points"]]
    boot_b = pd.DataFrame([x for r in r3 for x in r["draws"]])
    rows = add_joint_w(params_rows(points, boot_b, gam, ctx, code_sha))
    extra = {"p1": p1, "boot_a": boot_a, "boot_b": boot_b, "points": points, "gamma": gam, "ctx": ctx,
             "first_es": first_es}
    return rows, extra


def parse_method(text: str) -> dict:
    """'F5' or 'atp=F5,wta=F4' -> {tour: method}."""
    if "=" not in text:
        return {t: text for t in TOURS}
    out = dict(kv.split("=") for kv in text.split(","))
    return {t: out[t] for t in TOURS}


def step_params(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seasons = list(range(a.first_season, a.last_season + 1))
    if max(seasons) > 2024:
        raise SystemExit("seasons after 2024 are produced only by --mechanical")
    rows, extra = run_params(a, seasons, a.through, mechanical=False)
    sel = pd.read_csv(out / "elo_w_results.csv") if (out / "elo_w_results.csv").exists() else pd.DataFrame()
    if len(sel):
        rows = pd.concat([rows, results_rows(sel, seasons, rows["code_sha256"].iloc[0])], ignore_index=True)
    rows.to_parquet(out / "params_dev.parquet", index=False)
    extra["boot_b"].to_parquet(out / "bootstrap_draws.parquet", index=False)
    extra["p1"].to_parquet(out / "params_round1.parquet", index=False)
    pts = pd.DataFrame([{k: (json.dumps(v, default=str) if isinstance(v, (list, dict)) else v) for k, v in pt.items()}
                        for pt in extra["points"]])
    pts.to_parquet(out / "params_points.parquet", index=False)
    log(f"wrote {len(rows)} parameter rows for {seasons[0]}-{seasons[-1]} to {out / 'params_dev.parquet'}")


# ------------------------------------------------------------------------------------------------
# Freeze and the mechanical rows of 2025 and 2026

def frozen_inputs(strength: Path = STAGE1) -> dict:
    """The files whose content fixes the 2025-2026 rows besides the data: this module, role A's classify.py, the class
    table, the strength the run reads (--strength; since 10 Oct 2026 the one actually used, P7_plan.md section 10 #3)."""
    from src.eda.lower_level_evidence import classify as A
    return {"relationship_sha256": sha256_file(Path(__file__)), "classify_sha256": sha256_file(Path(A.__file__)),
            "common_sha256": sha256_file(Path(C.__file__)),
            "classes_sha256": sha256_file(CLASSES_DIR / "classes.csv"), "strength_sha256": sha256_file(strength)}


def freeze_path(out) -> Path:
    """A run's freeze record: inside its own --out (since 10 Oct 2026; P7_plan.md section 10 #3). With the default
    --out it is the study's own method_freeze.json, which --freeze never overwrites (below)."""
    return Path(out) / "method_freeze.json"


def verify_frozen(freeze: Path = FREEZE, strength: Path = STAGE1) -> dict:
    """Refuses (SystemExit) unless every frozen input's sha256 equals the freeze record."""
    if not Path(freeze).exists():
        raise SystemExit(f"no freeze record at {freeze}: run --freeze first")
    rec = json.loads(Path(freeze).read_text(encoding="utf-8"))
    now = frozen_inputs(strength)
    bad = [k for k, v in rec.items() if k.endswith("_sha256") and k in now and now[k] != v]
    if bad or "relationship_sha256" not in rec:
        raise SystemExit(f"the code or inputs differ from the frozen record ({bad}): the 2025-2026 rows may only come "
                         "from the frozen code")
    return rec


def step_freeze(a) -> int:
    out = Path(a.out)
    dev = out / "params_dev.parquet"
    if not dev.exists():
        raise SystemExit("no params_dev.parquet: run --steps params first")
    freeze = freeze_path(out)
    if freeze.exists():                    # a freeze is written once per folder: the study's (B's) is never replaced
        raise SystemExit(f"{freeze} exists: a refit freezes into a new --out folder")
    rec = {"written_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "method_version": METHOD_VERSION,
           "method": parse_method(a.method), "h_grid": [float(x) for x in (a.h_grid.split(",") if a.h_grid
                                                                           else H_GRID_WEEKS)],
           "boot": a.boot, "params_dev_sha256": sha256_file(dev),
           "elo_w_results_sha256": sha256_file(out / "elo_w_results.csv") if (out / "elo_w_results.csv").exists()
           else None}
    rec.update(frozen_inputs(Path(a.strength)))
    rec["strength_path"] = str(Path(a.strength))
    freeze.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    log(f"froze {freeze}: relationship.py {rec['relationship_sha256'][:12]}..., params_dev {rec['params_dev_sha256'][:12]}...")
    return 0


def step_mechanical(a) -> int:
    """The rows of seasons 2025 and 2026 from the frozen code (fits on <= 2024 and <= 2025, on the match clock). Prints
    nothing about them: their diagnostics stay unread until the holdout readout. Reads the freeze record of its own
    --out (freeze_path)."""
    rec = verify_frozen(freeze_path(a.out), Path(a.strength))
    a.method = ",".join(f"{t}={m}" for t, m in rec["method"].items())
    a.boot = int(rec["boot"])
    a.h_grid = ",".join(str(h) for h in rec["h_grid"])
    out = Path(a.out)
    seasons = [2025, 2026]
    rows, extra = run_params(a, seasons, 2025, mechanical=True)
    # results channel: the same walk-forward grid, through 2025 (mechanical)
    sel = elo_select_mechanical(a, seasons)
    rows = pd.concat([rows, results_rows(sel, seasons, rows["code_sha256"].iloc[0])], ignore_index=True)
    sealed = out / "holdout_sealed"
    sealed.mkdir(exist_ok=True)
    rows.to_parquet(sealed / "params_2025_2026.parquet", index=False)
    extra["boot_b"].to_parquet(sealed / "bootstrap_draws_2025_2026.parquet", index=False)
    dev = pd.read_parquet(out / "params_dev.parquet")
    if sha256_file(out / "params_dev.parquet") != rec["params_dev_sha256"]:
        raise SystemExit("params_dev.parquet differs from the frozen one")
    allp = pd.concat([dev, rows], ignore_index=True)
    allp.to_parquet(out / "params.parquet", index=False)
    (out / "params.sha256").write_text(f"{sha256_file(out / 'params.parquet')}  params.parquet\n", encoding="utf-8")
    print(f"mechanical rows written: {len(rows)} (seasons 2025-2026, unread); params.parquet {len(allp)} rows")
    return 0


def elo_select_mechanical(a, seasons) -> pd.DataFrame:
    """w_results for the holdout seasons: the Elo grid through 2025 (mechanical), the same walk-forward choice."""
    first_es = season_first_es(Path(a.stage0_dir), Path(a.timing))
    ctx = {"stage0_dir": a.stage0_dir, "timing": a.timing, "through": 2025, "mechanical": True}
    hist = elo_history(Path(a.stage0_dir), 2025, Path(a.timing), mechanical=True)
    levels = [L for L in ELO_LEVELS if any((hist[t]["bucket"] == L).any() for t in TOURS)]
    settings = [()] + [((L, v),) for L in levels for v in ELO_GRID if v != 1.0]
    jobs = [(tour, s, True, ctx) for tour in TOURS for s in settings]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(_elo_job, jobs))
    ll = {t: {} for t in TOURS}
    for tour, s, cw, v in res:
        ll[tour][s] = v
    rows = []
    for tour in TOURS:
        sel = elo_select(ll[tour], hist[tour], first_es, seasons, levels)
        for (Y, L), (v, gain, n) in sel.items():
            rows.append({"season_used": Y, "tour": tour, "level": L, "w_results": v, "train_gain_total_ll": gain,
                         "train_matches": n})
    return pd.DataFrame(rows)



# ------------------------------------------------------------------------------------------------
# Step tables: the paired contrasts behind the report (from the dev step's per-target files)

CONTRASTS = {
    # name: (first column, second column); + = the first predicts better
    "F1 vs F0 (main tour only)": ("F1@52", None),
    "F2 vs F0 (constant same-season offsets)": ("F2@52", None),
    "F3 vs F0 (gap translation + delta)": ("F3@52", None),
    "F4 vs F0 (+ exchange rate)": ("F4@52", None),
    "F5 vs F0 (+ newcomer prior)": ("F5@52", None),
    "F6 vs F0 (chosen formulation, half-life tuned)": ("F6", None),
    "F3 vs F2 (per-match gap vs constant offsets)": ("F3@52", "F2@52"),
    "F3 vs F2b (per-match gap vs fitted constant offsets)": ("F3@52", "F2b@52"),
    "F3 vs F3g (the residual delta)": ("F3@52", "F3g@52"),
    "F4 vs F3 (the exchange rate)": ("F4@52", "F3@52"),
    "F4 vs F4free (the shrinkage across statistics)": ("F4@52", "F4free@52"),
    "F5 vs F4 (the newcomer prior)": ("F5@52", "F4@52"),
    "F5ml vs F4 (tier means fitted for prediction)": ("F5ml@52", "F4@52"),
    "F4 vs F4nc (the classes)": ("F4@52", "F4nc@52"),
    "F5 vs F5nc (the classes)": ("F5@52", "F5nc@52"),
    "F4 vs F1 (lower levels translated and weighted vs ignored)": ("F4@52", "F1@52"),
    "F5 vs F1": ("F5@52", "F1@52"),
    "F6 vs its base at 52 weeks (the half-life tuning)": ("F6", "F6base@52"),
    # the frozen method (F4, w shrunk, half-life chosen per season), both tours
    "METHOD vs F0 (pooled as equivalent)": ("F6_F4", None),
    "METHOD vs F1 (main tour only)": ("F6_F4", "F1@52"),
    "METHOD vs F2 (constant same-season offsets)": ("F6_F4", "F2@52"),
    "METHOD vs F3 (no exchange rate)": ("F6_F4", "F3@52"),
}


def step_tables(a) -> None:
    out = Path(a.out)
    work = Path(a.work)
    chk = json.loads((out / "dev_checks.json").read_text(encoding="utf-8"))
    f6 = chk["f6_choice"]
    stats = a.stats.split(",") if a.stats else list(STATS)
    tg = pd.concat([pd.read_parquet(work / f"targets_{s}.parquet") for s in stats
                    if (work / f"targets_{s}.parquet").exists()], ignore_index=True)
    # gains are stored over F0; F0's own column holds its log-likelihood (kept as ll_F0), its gain is 0
    tg["ll_F0"] = tg["F0@52"].to_numpy(float)
    tg["F0@52"] = 0.0
    tg["F6"] = np.nan
    tg["F6base@52"] = np.nan
    for tour, base in f6.items():
        m = tg["tour"].eq(tour).to_numpy()
        tg.loc[m, "F6"] = tg.loc[m, f"F6_{base}"]
        tg.loc[m, "F6base@52"] = tg.loc[m, f"{base}@52"]
    cols = {}
    for name, (c1, c2) in CONTRASTS.items():
        cols[name] = tg[c1].to_numpy(float) - (tg[c2].to_numpy(float) if c2 else 0.0)
    # the dose curve: each uniform w against w = 1 and against F0, at 52 weeks and at F6's half-life
    for base in DOSE_BASES:
        for at in ("52", "F6"):
            one = tg[f"dose_{base}_1@{at}"].to_numpy(float)
            for wv in DOSE_GRID:
                v = tg[f"dose_{base}_{wv:g}@{at}"].to_numpy(float)
                cols[f"dose {base}@{at} w={wv:g} vs F0"] = v
                cols[f"dose {base}@{at} w={wv:g} vs w=1"] = v - one
            fitted = tg[f"{base}@52" if at == "52" else f"F6_{base}"].to_numpy(float)
            cols[f"dose {base}@{at} fitted w vs w=1"] = fitted - one
    keep = ["stat", "tour", "season", "player", "d", "low_exposure"]
    cg = pd.concat([tg[keep], pd.DataFrame(cols, index=tg.index)], axis=1)
    summ = summarise(cg, list(cols), {f"{SELECT_PERIOD[0]}-{SELECT_PERIOD[1]}": SELECT_PERIOD,
                                      f"{DEV_PERIOD[0]}-{DEV_PERIOD[1]}": DEV_PERIOD}, stat_groups())
    summ = summ.rename(columns={"column": "contrast"})
    summ[~summ["contrast"].str.startswith("dose")].to_csv(out / "contrasts.csv", index=False)
    dose = summ[summ["contrast"].str.startswith("dose")].copy()
    dose.to_csv(out / "dose_curve.csv", index=False)
    # the per-target file kept for audit (key columns only)
    audit = tg[keep + ["ll_F0", "F1@52", "F2@52", "F3@52", "F4@52", "F5@52", "F6"]].copy()
    audit.to_parquet(out / "targets_dev_key.parquet", index=False)
    log(f"wrote contrasts.csv, dose_curve.csv, targets_dev_key.parquet to {out}")


# ------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", default="dev")
    ap.add_argument("--stage0-dir", default=str(C.STAGE0_DIR))
    ap.add_argument("--timing", default=str(C.TIMING))
    ap.add_argument("--strength", default=str(STAGE1), help="pre-match Elo per match (a P7 candidate: its own copy)")
    ap.add_argument("--through", type=int, default=2024)
    ap.add_argument("--first-season", type=int, default=2013)
    ap.add_argument("--last-season", type=int, default=2024)
    ap.add_argument("--stats", default="")
    ap.add_argument("--h-grid", default="")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--boot", type=int, default=100)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--work", default=str(OUT / "work"))
    ap.add_argument("--method", default="F5", help="the frozen method: F4 or F5, or per tour 'atp=F5,wta=F4'")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--mechanical", action="store_true")
    a = ap.parse_args(argv)
    if a.through >= 2025 and not a.mechanical:
        raise SystemExit("--through 2025 or later reads holdout outcomes: only --mechanical may")
    steps = set(a.steps.split(","))
    if a.mechanical:
        return step_mechanical(a)
    if a.freeze:
        return step_freeze(a)
    if "dev" in steps:
        step_dev(a)
    if "tables" in steps:
        step_tables(a)
    if "elo" in steps:
        step_elo(a)
    if "params" in steps:
        step_params(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
