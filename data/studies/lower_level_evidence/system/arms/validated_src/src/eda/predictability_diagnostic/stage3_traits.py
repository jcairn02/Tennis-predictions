"""Stage 3 of the predictability diagnostic, part 2: which statistics repeat.

For every per-match rate of the Stage 0 table, and for serve and return points won adjusted for the opponent
(from the ratings of stage3_ratings.py), by tour and surface:

    1 reliability   each player's matches in a window (a season; three seasons on grass, where a season is
                    thin): two random sets of n matches, the rate on each, correlated across players, averaged
                    over random draws, for several n. n is given in matches and in the rate's own units (serve
                    points, break points, tiebreaks...). The Spearman-Brown curve r = n / (n + k) is fitted;
                    k is the sample at which reliability reaches 0.5.
    2 shrinkage     how much of the tour average to mix into a player's rate: the shrunk rate is
                    (x + K mu) / (d + K), with K the chance variation per unit over the true between-player
                    variation (empirical Bayes, method of moments). The chance variation is measured two ways:
                    binomial chance alone (a beta-binomial's), and the match-to-match variation within a player's
                    window (binomial chance plus opponents, conditions and form). On 2010-2018, for Stage 4, and
                    on every year, to show how much it moves.
    3 carry-over    a player's shrunk rate one season against the next; one surface against another in the same
                    season. Each with the correlation a perfectly stable rate would give at those samples (the
                    noise ceiling), and the ratio of the two.
    4 forecast      the rate in a player's next match from their history: career to date, last 52 weeks and
                    exponentially decayed, each shrunk toward the tour's average on the next match's surface;
                    for serve, return and total points won also the serve and return ratings, which know the
                    opponent. Scored by log loss per opportunity (point, game, set...) against the tour average.
    5 adjustment    raw against opponent-adjusted serve and return points won, on reliability and carry-over.
    6 verdict       repeats, repeats weakly or mostly noise, from the reliability at a typical season's sample.

Populations. Items 1-3 use completed matches in the standard format at the evaluation levels (Grand Slams,
Finals, 1000s, 500s, 250s, Challenger / WTA 125, and their qualifying), where box scores are kept; reliability
and carry-over use the evaluation years 2013-2026. Item 4's history is every completed singles match from 2010
at every level (the Brief's history); its targets are evaluation matches, completed, the WTA's box-score rates
from 2019. Retirements are left out throughout: their statistics cover part of a match. A rate counts for a
match where its denominator is written (0 is a match without the chance, such as no tiebreak; missing is not
counted). "All surfaces" measures each match against the tour's average on its surface (2010-2018), so a
player's mix of surfaces is not counted as a trait.

Shared helpers kept here rather than in common.py (Stage 2 may run beside this stage): split_half(),
sb_fit(), eb_constants(), sums_before() and lookback_sums().

Writes, in data/studies/predictability_diagnostic/:
    stage3_reliability.csv     split-half correlations: tour, surface, statistic, n, players, the rate's units
    stage3_shrinkage.csv       the constants: statistic x tour x surface x years (Stage 4 uses 2010-2018)
    stage3_persistence.csv     reliability at a typical season's sample, the Spearman-Brown k, the year-to-year
                               carry-over and the verdict (the summary's chart)
    stage3_carryover.csv       year to year and surface to surface
    stage3_forecast.csv        the next-match forecasts' scores
    stage3_results.json        everything stage3.md and the report quote

Run after stage3_ratings.py: ./python.sh src/eda/predictability_diagnostic/stage3_traits.py   (about 2½ minutes)
"""
from __future__ import annotations

import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import gammaln

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

RATINGS = C.OUT / "stage3_ratings.parquet"
RATINGS_SUMMARY = C.OUT / "stage3_ratings_summary.json"
RELIABILITY = C.OUT / "stage3_reliability.csv"
SHRINKAGE = C.OUT / "stage3_shrinkage.csv"
PERSISTENCE = C.OUT / "stage3_persistence.csv"
CARRYOVER = C.OUT / "stage3_carryover.csv"
FORECAST = C.OUT / "stage3_forecast.csv"
RESULTS = C.OUT / "stage3_results.json"

SEED = 20261001
EPS = 1e-9
ADJ = {"spw_adj": "serve points won, adjusted for the returner: the rate against an average returner",
       "rpw_adj": "return points won, adjusted for the server: the rate against an average server"}
STATS = list(C.RATES) + list(ADJ)
SCORE_STATS = ("tb_won", "sets_won", "games_won")          # from the score: every completed match has them
POISSON = {"bp_faced_pg"}                                  # a count per game, not a share
UNITS = {"spw": "serve points", "rpw": "return points", "tpw": "points", "hold": "service games",
         "brk": "return games", "ace": "serve points", "df": "serve points", "first_in": "serve points",
         "first_won": "first serves in", "second_won": "second-serve points", "bp_saved": "break points faced",
         "bp_conv": "break-point chances", "bp_faced_pg": "service games", "tb_won": "tiebreaks",
         "sets_won": "sets", "games_won": "games", "spw_adj": "serve points", "rpw_adj": "return points"}
SURFACES = ["all", "Hard", "Clay", "Grass"]
CENTRE_SURFACES = ("Hard", "Clay", "Grass", "Carpet")
WINDOW_SEASONS = {"Grass": 3}                              # longer windows where a surface is thin
REL_YEARS = range(2013, 2027)                              # reliability and carry-over: the evaluation years
SHRINK_YEARS = {"2010-2018": range(2010, 2019), "2010-2026": range(2010, 2027)}
ADJ_SHRINK_YEARS = {"2013-2018": range(2013, 2019), "2013-2026": range(2013, 2027)}   # after the ratings' warm-up
STAGE4_YEARS = {"raw": "2010-2018", "adjusted": "2013-2018"}
N_GRID = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30]
DRAWS = 20                                                 # random draws per n
MIN_UNITS = 30                                             # fewest player-windows for a correlation
FIT_UNITS = C.DIRECTIONAL_ONLY_BELOW                       # Spearman-Brown fitted on n's with 300+ player-windows
FIXED_HALF = 15                                            # the fixed-population check: 2 x 15 matches or more
REGULAR = 20                                               # a regular plays 20+ such matches in a season
BOOT = 200                                                 # bootstrap resamples of players for K's range
HALF_LIVES = [13, 26, 52, 104, 208]                        # weeks, for the decayed history
HALF_LIFE_TUNE = ("atp", range(2013, 2019))                # chosen on the men's 2013-2018 targets
FORECAST_WINDOWS = {"2019-2026": range(2019, 2027), "2022-2026": range(2022, 2027)}
WEEK52 = 364                                               # days: the last 52 weeks
REF_DAY = int(np.datetime64("2018-01-01", "D").astype("int64"))
VERDICT = (0.5, 0.2)                                       # reliability at a typical season: repeats / weakly / noise
CEILING_MIN = 0.3                                          # carry-over over a ceiling below this is not read
NON_CHANCE_MIN = 0.05                                      # a forecast's share is not read when chance is 95%+
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records", double_precision=6))


def fisher_ci(r: float, n: int) -> tuple[float, float]:
    if n < 4 or not np.isfinite(r):
        return np.nan, np.nan
    z, se = np.arctanh(np.clip(r, -0.999999, 0.999999)), 1 / np.sqrt(n - 3)
    return float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))


# ------------------------------------------------------------------------------------------------
# Inputs

def load_rows() -> tuple[pd.DataFrame, dict]:
    """Every player-match (two rows per match): the match's keys, the 16 stored rates as numerator and denominator,
    and serve and return points won adjusted for the opponent's pre-match rating:
        spw_adj = 1 / (1 + exp(-(logit(serve share) + R_opponent - R_typical))), the share against a typical
                  returner;
        rpw_adj = 1 - 1 / (1 + exp(-(logit(opponent's serve share) - S_opponent + S_typical))), against a
                  typical server;
    with the shares read as (won + 1/2) / (played + 1) so that a perfect match keeps a finite log-odds. The
    typical opponent's ratings are the average of opponents' pre-match ratings in the tour's analysis matches of
    2013-2018, so an adjusted rate sits on the same scale as the raw one."""
    rate_cols = [f"{r}_{x}" for r in C.RATES for x in ("n", "d")]
    mp = C.load_match_players(["match_id", "player_id", "side"] + rate_cols,
                              match_columns=["tour", "year", "level", "qualifying", "evaluation", "status", "format",
                                             "surface", "tournament_id", "tournament_date", "round_order"])
    rt = pd.read_parquet(RATINGS, columns=["match_id", "serve_a", "serve_b", "return_a", "return_b", "p_serve_a",
                                           "p_serve_b"]).set_index("match_id")
    rt = rt.reindex(mp["match_id"])
    a = mp["side"].eq("A").to_numpy()
    s_opp = np.where(a, rt["serve_b"], rt["serve_a"]).astype("float64")
    r_opp = np.where(a, rt["return_b"], rt["return_a"]).astype("float64")
    ref = (mp["level"].isin(C.EVAL_LEVELS) & mp["status"].eq("completed") & mp["format"].eq("standard")
           & mp["year"].isin(list(ADJ_SHRINK_YEARS["2013-2018"])) & mp["spw_d"].notna()).to_numpy()
    tours = mp["tour"].to_numpy()
    s_typ, r_typ = np.zeros(len(mp)), np.zeros(len(mp))
    for tour in C.TOURS:
        m = tours == tour
        s_typ[m], r_typ[m] = s_opp[ref & m].mean(), r_opp[ref & m].mean()
    mp["p_serve_own"] = np.where(a, rt["p_serve_a"], rt["p_serve_b"])
    mp["p_serve_opp"] = np.where(a, rt["p_serve_b"], rt["p_serve_a"])
    n, w = mp["spw_d"].to_numpy(), mp["spw_n"].to_numpy()
    lo = np.log((w + 0.5) / (n - w + 0.5))
    mp["spw_adj_d"] = mp["spw_d"]
    mp["spw_adj_n"] = n / (1 + np.exp(-(lo + r_opp - r_typ)))
    n_o = mp["rpw_d"].to_numpy()
    w_o = n_o - mp["rpw_n"].to_numpy()                     # the opponent's serve points won
    lo_o = np.log((w_o + 0.5) / (n_o - w_o + 0.5))
    mp["rpw_adj_d"] = mp["rpw_d"]
    mp["rpw_adj_n"] = n_o * (1 - 1 / (1 + np.exp(-(lo_o - s_opp + s_typ))))
    typical = {t: {"serve": float(s_typ[tours == t][0]), "return": float(r_typ[tours == t][0])} for t in C.TOURS}
    mp["day"] = mp["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    mp["pcode"] = pd.factorize(mp["player_id"])[0]
    mp["box_stat_from"] = np.where(mp["tour"].eq("wta"), C.WTA_BOX_FROM, C.EVAL_YEARS[0])
    return mp, typical


def has(rows: pd.DataFrame, stat: str) -> pd.Series:
    """Whether a row carries ``stat``: numerator and denominator both written (a denominator of 0 is a match
    without the chance and counts; one Tennis My Life box score has a denominator but an unreadable count)."""
    return rows[f"{stat}_d"].notna() & rows[f"{stat}_n"].notna()


def seeded(*parts) -> np.random.Generator:
    """A generator seeded by the study's seed and stable labels, so each group's draws do not depend on others."""
    return np.random.default_rng([SEED] + [zlib.crc32(str(p).encode("utf-8")) for p in parts])


def surface_means(rows: pd.DataFrame) -> dict:
    """Per tour, statistic and surface: the pooled rate (sum of numerators over sum of denominators) on the
    analysis matches of 2010-2018 (the adjusted rates: 2013-2018), and the same over all surfaces. A surface with
    under 300 player-matches takes the tour's."""
    out = {}
    for stat in STATS:
        yrs = ADJ_SHRINK_YEARS["2013-2018"] if stat in ADJ else SHRINK_YEARS["2010-2018"]
        g = rows[rows["year"].isin(list(yrs)) & has(rows, stat)]
        for tour in C.TOURS:
            t = g[g["tour"].eq(tour)]
            mu_all = float(t[f"{stat}_n"].sum() / t[f"{stat}_d"].sum())
            out[(tour, stat, "all")] = mu_all
            for s in CENTRE_SURFACES:
                ts = t[t["surface"].eq(s)]
                out[(tour, stat, s)] = float(ts[f"{stat}_n"].sum() / ts[f"{stat}_d"].sum()) if len(ts) >= 300 else mu_all
    return out


def mu_column(rows: pd.DataFrame, stat: str, means: dict) -> np.ndarray:
    """The tour's average of ``stat`` on each row's surface (the tour's over all surfaces where unknown)."""
    out = np.empty(len(rows))
    tours, surfs = rows["tour"].to_numpy(), rows["surface"].to_numpy()
    for tour in np.unique(tours):
        for s in list(CENTRE_SURFACES) + [None]:
            mask = (tours == tour) & (np.isin(surfs, [s]) if s else ~np.isin(surfs, CENTRE_SURFACES))
            out[mask] = means[(tour, stat, s or "all")]
    return out


def centred(rows: pd.DataFrame, stat: str, means: dict, surface: str) -> tuple[np.ndarray, np.ndarray]:
    """Numerator and denominator of ``stat`` for each row: as stored on one surface; over all surfaces, the
    numerator measured against the surface's average and put back on the tour's overall average,
    x - d (mu_surface - mu_all)."""
    x = rows[f"{stat}_n"].to_numpy(dtype="float64")
    d = rows[f"{stat}_d"].to_numpy(dtype="float64")
    if surface == "all":
        x = x - d * (mu_column(rows, stat, means) - means[(rows["tour"].iloc[0], stat, "all")])
    return x, d


def windows(rows: pd.DataFrame, surface: str) -> np.ndarray:
    """The window of each row: its season, or blocks of seasons from 2010 where the surface is thin."""
    w = WINDOW_SEASONS.get(surface, 1)
    return ((rows["year"].to_numpy() - 2010) // w).astype("int64")


# ------------------------------------------------------------------------------------------------
# 1. Split-half reliability and the Spearman-Brown curve

def split_half(unit: np.ndarray, X: np.ndarray, D: np.ndarray, rng: np.random.Generator, n_grid=N_GRID,
               draws: int = DRAWS, fixed_min: int | None = None) -> list[dict]:
    """Split-half correlations for k statistics that share their rows.

    ``unit`` codes each row's player-window (0..U-1); X and D are (rows, k) numerators and denominators. For
    each n, every player-window with at least 2n rows (or, with ``fixed_min``, at least that many, for every n)
    gives two random sets of n rows; the correlation across player-windows of the rate on one set and on the
    other is averaged over ``draws`` draws. Player-windows whose either set has a zero denominator are left out
    of that draw. Returns one dict per (n, statistic index) with the mean correlation, the draws' spread, the
    player-windows used and the mean denominator of a set."""
    X = np.asarray(X, dtype="float64").reshape(len(unit), -1)
    D = np.asarray(D, dtype="float64").reshape(len(unit), -1)
    U = int(unit.max()) + 1
    count = np.bincount(unit, minlength=U)
    k = X.shape[1]
    acc = {(n, j): ([], [], []) for n in n_grid for j in range(k)}
    for _ in range(draws):
        o = np.lexsort((rng.random(len(unit)), unit))
        us = unit[o]
        rank = np.arange(len(us)) - np.searchsorted(us, us, side="left")
        for n in n_grid:
            need = fixed_min if fixed_min else 2 * n
            if need < 2 * n:
                continue
            ok = count >= need
            if ok.sum() < MIN_UNITS:
                continue
            sel = ok[us] & (rank < 2 * n)
            rows = o[sel]
            idx = us[sel] * 2 + (rank[sel] >= n)
            for j in range(k):
                sx = np.bincount(idx, weights=X[rows, j], minlength=2 * U).reshape(U, 2)
                sd = np.bincount(idx, weights=D[rows, j], minlength=2 * U).reshape(U, 2)
                good = ok & (sd[:, 0] > 0) & (sd[:, 1] > 0)
                if good.sum() < MIN_UNITS:
                    continue
                ra, rb = sx[good, 0] / sd[good, 0], sx[good, 1] / sd[good, 1]
                if ra.std() == 0 or rb.std() == 0:
                    continue
                acc[(n, j)][0].append(float(np.corrcoef(ra, rb)[0, 1]))
                acc[(n, j)][1].append(int(good.sum()))
                acc[(n, j)][2].append(float(sd[good].mean()))
    out = []
    for (n, j), (rs, us_, den) in acc.items():
        if not rs:
            continue
        r = float(np.mean(rs))
        units = int(np.median(us_))
        lo, hi = fisher_ci(r, units)
        out.append({"n": n, "stat_index": j, "r": r, "r_lo": lo, "r_hi": hi,
                    "r_draw_p2_5": float(np.percentile(rs, 2.5)), "r_draw_p97_5": float(np.percentile(rs, 97.5)),
                    "player_windows": units, "units_per_set": float(np.mean(den)), "draws": len(rs),
                    "k_from_this_n": float(n * (1 - r) / r) if r > 0 else np.inf,
                    "directional_only": bool(units < FIT_UNITS)})
    return out


def sb_fit(n, r, w) -> dict:
    """Least squares (weights ``w``) of r = n / (n + k) in k: the Spearman-Brown curve of a sample of n, where
    k = (1 - rho) / rho for the reliability rho of one unit. k is the sample at which reliability reaches 0.5.
    Searched on a log grid of k from 0.001 to 10 million and refined; k at the top of the grid means no signal."""
    n, r, w = (np.asarray(v, dtype="float64") for v in (n, r, w))
    ok = np.isfinite(n) & np.isfinite(r) & np.isfinite(w) & (w > 0)
    if ok.sum() < 1:
        return {"k": np.nan, "points": 0}
    n, r, w = n[ok], r[ok], w[ok]

    def loss(k):
        k = np.atleast_1d(k)[:, None]
        return (w * (r - n / (n + k)) ** 2).sum(axis=1)
    grid = np.exp(np.linspace(np.log(1e-3), np.log(1e7), 4001))
    i = int(np.argmin(loss(grid)))
    if i == len(grid) - 1:
        return {"k": np.inf, "points": int(ok.sum()), "max_abs_resid": float(np.abs(r).max()), "no_signal": True}
    a, b = np.log(grid[max(i - 1, 0)]), np.log(grid[min(i + 1, len(grid) - 1)])
    g = (np.sqrt(5) - 1) / 2
    for _ in range(80):                                     # golden-section search on log k
        c, d = b - g * (b - a), a + g * (b - a)
        if loss(np.exp(c))[0] < loss(np.exp(d))[0]:
            b = d
        else:
            a = c
    k = float(np.exp((a + b) / 2))
    resid = r - n / (n + k)
    return {"k": k, "points": int(ok.sum()), "max_abs_resid": float(np.abs(resid).max()),
            "rmse": float(np.sqrt(np.average(resid ** 2, weights=w))), "no_signal": False}


def reliability(rows: pd.DataFrame, means: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split-half correlations for every tour x surface x statistic (evaluation years, analysis matches), and the
    Spearman-Brown fits: on the n's with at least 300 player-windows, in matches and in the rate's units. For all
    surfaces, a second fit on a fixed population (player-windows with 2 x 15 matches or more) checks that the
    changing population across n does not drive the curve."""
    rel = rows[rows["year"].isin(list(REL_YEARS))]
    out, fits = [], []
    for tour in C.TOURS:
        for surface in SURFACES:
            g = rel[rel["tour"].eq(tour) & (rel["surface"].eq(surface) if surface != "all" else True)]
            # statistics that are written on exactly the same rows share one set of random draws (raw and
            # adjusted serve points won, for instance), so their comparison is paired
            groups: dict = {}
            for stat in STATS:
                mask = has(g, stat).to_numpy()
                groups.setdefault(mask.tobytes(), (mask, []))[1].append(stat)
            for mask, stats in groups.values():
                sub = g[mask]
                unit = pd.factorize(pd.Series(sub["pcode"].to_numpy() * 100 + windows(sub, surface)))[0]
                X, D = zip(*(centred(sub, s, means, surface) for s in stats))
                X, D = np.column_stack(X), np.column_stack(D)
                for pop, fixed in (("at least 2n matches", None), (f"fixed: at least {2 * FIXED_HALF} matches", 2 * FIXED_HALF)):
                    if fixed and surface != "all":
                        continue
                    grid = N_GRID if not fixed else [x for x in N_GRID if x <= FIXED_HALF]
                    rng = seeded("reliability", tour, surface, stats[0], pop)
                    for x in split_half(unit, X, D, rng, grid, fixed_min=fixed):
                        out.append({"tour": tour, "surface": surface, "stat": stats[x.pop("stat_index")],
                                    "population": pop, **x})
            log(f"  reliability {tour} {surface}")
    rel_df = pd.DataFrame(out)
    rel_df["unit"] = rel_df["stat"].map(UNITS)
    for (tour, surface, stat, pop), g in rel_df.groupby(["tour", "surface", "stat", "population"]):
        use = g[~g["directional_only"]]
        basis = "300+ player-windows"
        if len(use) < 2:
            use, basis = g[g["player_windows"] >= MIN_UNITS], "every n (under 300 player-windows: directional only)"
        fm = sb_fit(use["n"], use["r"], use["player_windows"])
        fu = sb_fit(use["units_per_set"], use["r"], use["player_windows"])
        fits.append({"tour": tour, "surface": surface, "stat": stat, "population": pop, "fit_on": basis,
                     "n_values": int(len(use)), "n_max": int(use["n"].max()),
                     "k_matches": fm["k"], "k_units": fu["k"], "fit_max_abs_resid": fm.get("max_abs_resid"),
                     "fit_rmse": fm.get("rmse"), "no_signal": bool(fm.get("no_signal", False)),
                     "units_per_match": float((use["units_per_set"] / use["n"]).mean())})
    return rel_df, pd.DataFrame(fits)


# ------------------------------------------------------------------------------------------------
# 2. Shrinkage: empirical Bayes

def unit_sums(unit: np.ndarray, x: np.ndarray, d: np.ndarray) -> dict:
    """Per player-window: the denominator D and numerator X summed, the within-window sum of squares
    W = sum_j d_j (r_j - X/D)^2 = sum_j x_j^2 / d_j - X^2 / D over matches with d_j > 0, and the count m of
    such matches."""
    U = int(unit.max()) + 1
    pos = d > 0
    D = np.bincount(unit, weights=d, minlength=U)
    X = np.bincount(unit, weights=x, minlength=U)
    Q = np.bincount(unit[pos], weights=x[pos] ** 2 / d[pos], minlength=U)
    m = np.bincount(unit[pos], minlength=U).astype("float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        W = np.where(D > 0, Q - X ** 2 / D, 0.0)
    return {"D": D, "X": X, "W": np.maximum(W, 0.0), "m": m}


def eb_constants(D, X, W, m, poisson: bool = False, weight=None) -> dict:
    """The empirical-Bayes split of a rate's variation across player-windows (method of moments).

    A window's rate r = X / D has mean mu (pooled), true spread tau^2 across windows, and chance variance s2 / D.
    s2, the chance variance per unit, is measured from the match-to-match variation within windows:
    s2 = sum W / sum (m - 1) (exact in expectation when a match's chance variance is s2 / d). Then
        tau^2 = (sum D (r - mu)^2 - s2 (N - 1)) / (sum D - sum D^2 / sum D),
    the unbalanced one-way analysis of variance, and the shrinkage constant is K = s2 / tau^2 (in units): the
    shrunk rate (X + K mu) / (D + K) gives a window its reliability D / (D + K). The binomial-chance version
    takes s2 = mu (1 - mu) (a Poisson count: s2 = mu), a beta-binomial's method-of-moments K.
    ``weight`` (a bootstrap's copies of each window) multiplies every sum; rows of a 2-D weight are resamples."""
    w = np.ones_like(D) if weight is None else weight
    keep = (D > 0).astype("float64")
    w = w * keep
    sD = (w * D).sum(axis=-1)
    mu = (w * X).sum(axis=-1) / sD
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(D > 0, X / np.where(D > 0, D, 1.0), 0.0)
    N = w.sum(axis=-1)
    dev = r - (mu[..., None] if np.ndim(mu) else mu)
    S = (w * D * dev ** 2).sum(axis=-1)
    denom = sD - (w * D ** 2).sum(axis=-1) / sD
    s2 = (w * W).sum(axis=-1) / (w * np.maximum(m - 1, 0)).sum(axis=-1)
    s2_bin = mu if poisson else mu * (1 - mu)
    tau2 = (S - s2 * (N - 1)) / denom
    tau2_bin = (S - s2_bin * (N - 1)) / denom
    with np.errstate(divide="ignore", invalid="ignore"):
        K = np.where(tau2 > 0, s2 / tau2, np.inf)
        K_bin = np.where(tau2_bin > 0, s2_bin / tau2_bin, np.inf)
    return {"mu": mu, "s2": s2, "s2_binomial": s2_bin, "tau2": tau2, "tau2_binomial": tau2_bin, "K": K, "K_binomial": K_bin}


def shrinkage(rows: pd.DataFrame, means: dict) -> pd.DataFrame:
    """The constants for every statistic x tour x surface x years, with a bootstrap range over players."""
    out = []
    for stat in STATS:
        for years_name, yrs in (ADJ_SHRINK_YEARS if stat in ADJ else SHRINK_YEARS).items():
            g0 = rows[rows["year"].isin(list(yrs)) & has(rows, stat)]
            for tour in C.TOURS:
                for surface in SURFACES:
                    g = g0[g0["tour"].eq(tour) & (g0["surface"].eq(surface) if surface != "all" else True)]
                    if len(g) == 0:
                        continue
                    rng = seeded("shrinkage", stat, years_name, tour, surface)
                    x, d = centred(g, stat, means, surface)
                    key = pd.Series(g["pcode"].to_numpy() * 100 + windows(g, surface))
                    unit, uniq = pd.factorize(key)
                    s = unit_sums(unit, x, d)
                    est = eb_constants(s["D"], s["X"], s["W"], s["m"], stat in POISSON)
                    # bootstrap: resample players, each bringing all their windows
                    player_of_unit = (uniq.to_numpy() // 100)
                    pu = pd.factorize(pd.Series(player_of_unit))[0]
                    P = int(pu.max()) + 1
                    Ks = []
                    for _ in range(BOOT // 50):
                        draws = rng.integers(0, P, size=(50, P))
                        copies = np.stack([np.bincount(row, minlength=P) for row in draws])[:, pu].astype("float64")
                        b = eb_constants(s["D"], s["X"], s["W"], s["m"], stat in POISSON, weight=copies)
                        Ks.append(b["K"])
                    Ks = np.concatenate(Ks)
                    per_match = float(d.sum() / len(d))
                    K, Kb = float(est["K"]), float(est["K_binomial"])
                    out.append({"stat": stat, "tour": tour, "surface": surface, "years": years_name,
                                "unit": UNITS[stat], "chance": "Poisson" if stat in POISSON else "binomial",
                                "mean": float(est["mu"]), "K_units": K, "K_matches": K / per_match,
                                "K_units_lo": float(np.percentile(Ks, 2.5, method="nearest")),
                                "K_units_hi": float(np.percentile(Ks, 97.5, method="nearest")),
                                "K_binomial_units": Kb, "K_binomial_matches": Kb / per_match,
                                "chance_var_per_unit": float(est["s2"]), "binomial_var_per_unit": float(est["s2_binomial"]),
                                "overdispersion": float(est["s2"] / est["s2_binomial"]),
                                "true_sd": float(np.sqrt(est["tau2"])) if est["tau2"] > 0 else 0.0,
                                "true_sd_binomial": float(np.sqrt(est["tau2_binomial"])) if est["tau2_binomial"] > 0 else 0.0,
                                "units_per_match": per_match, "player_windows": int((s["D"] > 0).sum()), "players": P,
                                "player_matches": int(len(g)),
                                "window_seasons": WINDOW_SEASONS.get(surface, 1)})
        log(f"  shrinkage {stat}")
    return pd.DataFrame(out)


def constants_for(shr: pd.DataFrame, stat: str, tour: str, surface: str, kind: str = "K_units") -> float:
    years = STAGE4_YEARS["adjusted" if stat in ADJ else "raw"]
    r = shr[(shr["stat"] == stat) & (shr["tour"] == tour) & (shr["surface"] == surface) & (shr["years"] == years)]
    return float(r[kind].iloc[0])


# ------------------------------------------------------------------------------------------------
# 3. Carry-over

def season_table(rows: pd.DataFrame, stat: str, means: dict, surface: str) -> pd.DataFrame:
    """Per player and season (the evaluation years): the rate's numerator and denominator on ``surface``."""
    g = rows[rows["year"].isin(list(REL_YEARS)) & has(rows, stat)]
    g = g[g["surface"].eq(surface)] if surface != "all" else g
    x, d = centred(g, stat, means, surface) if len(g) else (np.array([]), np.array([]))
    return (pd.DataFrame({"player": g["pcode"].to_numpy(), "year": g["year"].to_numpy(), "x": x, "d": d})
            .groupby(["player", "year"], sort=True)[["x", "d"]].sum())


def shrunk(t: pd.DataFrame, K: float, mu: float) -> tuple[np.ndarray, np.ndarray]:
    """The shrunk rate (x + K mu) / (d + K) and the window's reliability d / (d + K)."""
    x, d = t["x"].to_numpy(), t["d"].to_numpy()
    if not np.isfinite(K):
        return np.full(len(t), mu), np.zeros(len(t))
    return (x + K * mu) / (d + K), d / (d + K)


def carry(y1, y2, R1, R2) -> dict:
    """Correlation of two shrunk rates across players, and the correlation a rate that never changed would give
    at these samples: E[R1 R2] / sqrt(E[R1] E[R2]) (each window's reliability R = d / (d + K)). Their ratio
    estimates how much of the true rate carries over."""
    n = len(y1)
    # a rate with no true spread (K infinite) is shrunk to one value for every player: nothing to correlate
    if n < MIN_UNITS or np.ptp(y1) < 1e-9 or np.ptp(y2) < 1e-9:
        return {"pairs": int(n)}
    r = float(np.corrcoef(y1, y2)[0, 1])
    ceiling = float(np.mean(R1 * R2) / np.sqrt(np.mean(R1) * np.mean(R2)))
    lo, hi = fisher_ci(r, n)
    return {"pairs": int(n), "r": r, "r_lo": lo, "r_hi": hi, "ceiling": ceiling, "true_carry": r / ceiling,
            "true_carry_lo": lo / ceiling, "true_carry_hi": hi / ceiling, "ceiling_low": bool(ceiling < CEILING_MIN),
            "directional_only": bool(n < FIT_UNITS)}


def carryover(rows: pd.DataFrame, means: dict, shr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    years, surfs = [], []
    for stat in STATS:
        for tour in C.TOURS:
            g = rows[rows["tour"].eq(tour)]
            tabs = {}
            for surface in SURFACES:
                t = season_table(g, stat, means, surface)
                K, mu = constants_for(shr, stat, tour, surface), constants_for(shr, stat, tour, surface, "mean")
                y, R = shrunk(t, K, mu)
                t = t.assign(y=y, R=R)
                tabs[surface] = t
                nxt = t.reset_index().assign(year=lambda f: f["year"] - 1).set_index(["player", "year"])
                pair = t.join(nxt, rsuffix="_next", how="inner")
                pair = pair[(pair["d"] > 0) & (pair["d_next"] > 0)]
                years.append({"stat": stat, "tour": tour, "surface": surface, "K_units": K,
                              **carry(pair["y"].to_numpy(), pair["y_next"].to_numpy(), pair["R"].to_numpy(), pair["R_next"].to_numpy())})
            for s1, s2 in (("Hard", "Clay"), ("Hard", "Grass"), ("Clay", "Grass")):
                pair = tabs[s1].join(tabs[s2], rsuffix="_2", how="inner")
                pair = pair[(pair["d"] > 0) & (pair["d_2"] > 0)]
                surfs.append({"stat": stat, "tour": tour, "surfaces": f"{s1}-{s2}",
                              **carry(pair["y"].to_numpy(), pair["y_2"].to_numpy(), pair["R"].to_numpy(), pair["R_2"].to_numpy())})
        log(f"  carry-over {stat}")
    return pd.DataFrame(years), pd.DataFrame(surfs)


# ------------------------------------------------------------------------------------------------
# 4. The next match from a player's history

def sums_before(pcode: np.ndarray, day: np.ndarray, V: np.ndarray, q_pcode: np.ndarray, q_day: np.ndarray) -> np.ndarray:
    """For each query (player, day): the sums of V over that player's rows with an earlier day (day < q_day).
    Rows sorted by player and day, cumulative sums within each player, and a binary search for the cut."""
    V = np.asarray(V, dtype="float64").reshape(len(pcode), -1)
    o = np.lexsort((day, pcode))
    p, dd = pcode[o].astype("int64"), day[o].astype("int64")
    cs = pd.DataFrame(V[o]).groupby(p).cumsum().to_numpy()
    big = 1_000_000
    key = p * big + dd
    pos = np.searchsorted(key, q_pcode.astype("int64") * big + q_day.astype("int64"), side="left")
    start = np.searchsorted(key, q_pcode.astype("int64") * big, side="left")
    res = np.zeros((len(q_pcode), V.shape[1]))
    has = pos > start
    res[has] = cs[pos[has] - 1]
    return res


def lookback_sums(rows: pd.DataFrame, V: np.ndarray, half_lives=()) -> tuple[np.ndarray, dict]:
    """For each row: the sums of V over the same player's earlier matches under the as-of rule (career to date),
    and for each half-life h (weeks) the same sums with each earlier match weighted by 2^(-age / h), age in days
    from its tournament date to this row's. A decayed sum is an as-of sum of V 2^((t - t0) / h), times
    2^(-(T - t0) / h), so the as-of helper keeps the time rule; one call serves every column."""
    V = np.asarray(V, dtype="float64").reshape(len(rows), -1)
    k = V.shape[1]
    tmp = rows[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    blocks = [("career", np.ones(len(rows)))] + [(h, np.exp2((rows["day"].to_numpy() - REF_DAY) / (7.0 * h))) for h in half_lives]
    cols = []
    for b, (name, f) in enumerate(blocks):
        for j in range(k):
            tmp[f"_v{b}_{j}"] = V[:, j] * f
            cols.append(f"_v{b}_{j}")
    s = C.asof_sums(tmp, cols).to_numpy()
    out = {name: s[:, b * k:(b + 1) * k] / f[:, None] for b, (name, f) in enumerate(blocks)}
    career = out.pop("career")
    return career, out


def logloss_terms(x, d, f, poisson: bool) -> np.ndarray:
    """Minus the log-likelihood of each target's x successes in d chances at rate f: binomial (or Poisson, with
    mean f d), summed over the target's chances."""
    if poisson:
        f = np.maximum(f, EPS)
        lam = f * d
        return -(x * np.log(lam) - lam - gammaln(x + 1))
    f = np.clip(f, EPS, 1 - EPS)
    return -(x * np.log(f) + (d - x) * np.log(1 - f))


def forecast(rows: pd.DataFrame, means: dict, shr: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The next match's rate from each player's history, three forms (and variants), scored on the targets."""
    hist_all = rows[rows["status"].eq("completed") & rows["format"].eq("standard")]
    out, chosen = [], {}
    for stat in C.RATES:
        poisson = stat in POISSON
        hist = hist_all[has(hist_all, stat)].reset_index(drop=True)
        x = hist[f"{stat}_n"].to_numpy(dtype="float64")
        d = hist[f"{stat}_d"].to_numpy(dtype="float64")
        mu_s = mu_column(hist, stat, means)
        xc = x - mu_s * d                                    # each match against its surface's average
        V = np.column_stack([xc, d])
        ev_level = hist["level"].isin(C.EVAL_LEVELS).to_numpy().astype("float64")
        sums, decayed = lookback_sums(hist, np.column_stack([xc, d, xc * ev_level, d * ev_level]), HALF_LIVES)
        career, career_ev = sums[:, :2], sums[:, 2:]          # every level; the evaluation levels only
        before = sums_before(hist["pcode"].to_numpy(), hist["day"].to_numpy(), V, hist["pcode"].to_numpy(),
                             hist["day"].to_numpy() - WEEK52)
        last52 = career - before
        first = np.where(stat in SCORE_STATS, C.EVAL_YEARS[0], hist["box_stat_from"].to_numpy())
        target = (hist["evaluation"] & (hist["year"] >= first) & (d > 0)).to_numpy()
        t = hist[target].reset_index(drop=True)
        xt, dt, mt = x[target], d[target], mu_s[target]
        forms = {"tour average": mt}
        K = {tour: constants_for(shr, stat, tour, "all") for tour in C.TOURS}
        Kb = {tour: constants_for(shr, stat, tour, "all", "K_binomial_units") for tour in C.TOURS}
        kt = t["tour"].map(K).to_numpy()
        kbt = t["tour"].map(Kb).to_numpy()

        def shrink(s, k):
            k = np.where(np.isfinite(k), k, 1e12)
            return mt + s[:, 0] / (s[:, 1] + k)
        forms["career to date"] = shrink(career[target], kt)
        forms["career to date, K x 0.5"] = shrink(career[target], kt * 0.5)
        forms["career to date, K x 2"] = shrink(career[target], kt * 2)
        forms["career to date, binomial K"] = shrink(career[target], kbt)
        forms["career to date, evaluation levels only"] = shrink(career_ev[target], kt)
        forms["last 52 weeks"] = shrink(last52[target], kt)
        l52 = last52[target]
        forms["last 52 weeks, not shrunk"] = np.where(l52[:, 1] > 0, mt + l52[:, 0] / np.where(l52[:, 1] > 0, l52[:, 1], 1), mt)
        for h in HALF_LIVES:
            forms[f"decayed, half-life {h} weeks"] = shrink(decayed[h][target, :2], kt)
        if stat in ("spw", "rpw", "tpw"):
            own, opp = t["p_serve_own"].to_numpy(), t["p_serve_opp"].to_numpy()
            forms["serve and return ratings"] = {"spw": own, "rpw": 1 - opp, "tpw": (own + 1 - opp) / 2}[stat]
        # the half-life: chosen on the men's 2013-2018 targets
        tune = (t["tour"].eq(HALF_LIFE_TUNE[0]) & t["year"].isin(list(HALF_LIFE_TUNE[1]))).to_numpy()
        best = min(HALF_LIVES, key=lambda h: logloss_terms(xt[tune], dt[tune], forms[f"decayed, half-life {h} weeks"][tune], poisson).sum())
        chosen[stat] = best
        forms["decayed"] = forms[f"decayed, half-life {best} weeks"]
        ll = {name: logloss_terms(xt, dt, f, poisson) for name, f in forms.items()}
        y = xt / dt
        for tour in C.TOURS:
            for wname, yrs in FORECAST_WINDOWS.items():
                for surface in SURFACES:
                    sel = (t["tour"].eq(tour) & t["year"].isin(list(yrs))
                           & (t["surface"].eq(surface) if surface != "all" else True)).to_numpy()
                    if sel.sum() == 0:
                        continue
                    ds = dt[sel]
                    D = ds.sum()
                    base = ll["tour average"][sel]
                    # the next match's squared error (per chance) splits into the chance of its points (binomial,
                    # or Poisson) and the rest: the player, the opponent, the conditions, the day
                    chance = (mt[sel] if poisson else mt[sel] * (1 - mt[sel])).sum() / D
                    mse_base = float((ds * (y[sel] - mt[sel]) ** 2).sum() / D)
                    non_chance = (mse_base - chance) / mse_base
                    for name, f in forms.items():
                        diff = base - ll[name][sel]                       # per target, positive = better
                        gain = diff.sum() / D
                        se = np.sqrt(((diff - gain * ds) ** 2).sum()) / D
                        mse = float((ds * (y[sel] - f[sel]) ** 2).sum() / D)
                        out.append({"stat": stat, "tour": tour, "window": wname, "surface": surface, "form": name,
                                    "targets": int(sel.sum()), "units": float(D), "unit": UNITS[stat],
                                    "logloss_per_unit": float(ll[name][sel].sum() / D),
                                    "better_milli_per_unit": 1000 * gain, "better_lo": 1000 * (gain - 1.96 * se),
                                    "better_hi": 1000 * (gain + 1.96 * se), "non_chance_part": float(non_chance),
                                    "share_of_non_chance": (float((mse_base - mse) / (mse_base - chance))
                                                            if non_chance >= NON_CHANCE_MIN else np.nan),
                                    "directional_only": bool(sel.sum() < FIT_UNITS)})
        log(f"  forecast {stat}: half-life {best} weeks")
    return pd.DataFrame(out), chosen


# ------------------------------------------------------------------------------------------------
# 6. The typical season, the persistence table and the verdict

def typical_season(rows: pd.DataFrame) -> pd.DataFrame:
    """Per tour x statistic x surface: the median sample of a regular's season. Regulars are player-seasons with
    at least 20 analysis matches carrying the statistic (evaluation years); on a surface, those of their seasons
    with at least one match on it."""
    rel = rows[rows["year"].isin(list(REL_YEARS))]
    out = []
    for stat in STATS:
        g = rel[has(rel, stat)]
        for tour in C.TOURS:
            t = g[g["tour"].eq(tour)]
            per = t.groupby(["pcode", "year"]).size()
            reg = per[per >= REGULAR].index
            for surface in SURFACES:
                ts = t if surface == "all" else t[t["surface"].eq(surface)]
                agg = ts.groupby(["pcode", "year"]).agg(matches=(f"{stat}_d", "size"), units=(f"{stat}_d", "sum"))
                agg = agg[agg.index.isin(reg)]
                out.append({"stat": stat, "tour": tour, "surface": surface, "regular_seasons": int(len(agg)),
                            "typical_matches": float(agg["matches"].median()) if len(agg) else np.nan,
                            "typical_units": float(agg["units"].median()) if len(agg) else np.nan})
    return pd.DataFrame(out)


def reliability_at(rel: pd.DataFrame, n_typ: float) -> dict:
    """The reliability of a typical season's sample of n_typ matches, read off the measured curve: the split-half
    correlation r at h = n_typ / 2 matches (linear in n between the measured n's; h at least 1), from players with
    at least 2h matches, so from players who play a typical season. Stepped up by Spearman-Brown to the whole
    sample: R = n_typ / (n_typ + k_h), with k_h = h (1 - r) / r; at h = n_typ / 2 this is 2r / (1 + r)."""
    g = rel.sort_values("n")
    if not np.isfinite(n_typ) or len(g) == 0:
        return {"reliability": np.nan}
    h = max(n_typ / 2.0, 1.0)
    if h > g["n"].max():
        return {"reliability": np.nan, "h": h, "beyond_measured": True}

    def step_up(r):
        k = h * (1 - r) / r if r > 0 else np.inf
        return (n_typ / (n_typ + k) if np.isfinite(k) else 0.0), k
    r = float(np.interp(h, g["n"], g["r"]))
    rel, k_h = step_up(r)
    lo, _ = step_up(float(np.interp(h, g["n"], g["r_lo"].fillna(g["r"]) if "r_lo" in g else g["r"])))
    hi, _ = step_up(float(np.interp(h, g["n"], g["r_hi"].fillna(g["r"]) if "r_hi" in g else g["r"])))
    units = float(np.interp(h, g["n"], g["units_per_set"]))
    return {"reliability": rel, "reliability_lo": lo, "reliability_hi": hi, "h": h, "r_h": r, "k_h": k_h,
            "units_h": units, "players_h": float(np.interp(h, g["n"], g["player_windows"]))}


def verdict_of(rel: float) -> str | None:
    if not np.isfinite(rel):
        return None
    return "repeats" if rel >= VERDICT[0] else ("repeats weakly" if rel >= VERDICT[1] else "mostly noise")


def persistence(rel: pd.DataFrame, fits: pd.DataFrame, typ: pd.DataFrame, years: pd.DataFrame, shr: pd.DataFrame) -> pd.DataFrame:
    """Per tour x surface x statistic: the reliability of a typical season's sample (read off the measured curve),
    the Spearman-Brown fit, the year-to-year carry-over, the shrinkage constant and the verdict."""
    main = rel[rel["population"].eq("at least 2n matches")]
    f = fits[fits["population"].eq("at least 2n matches")].merge(typ, on=["stat", "tour", "surface"], how="left")
    y = years.rename(columns={"r": "year_to_year_r", "true_carry": "year_to_year_true", "pairs": "year_pairs"})
    f = f.merge(y[["stat", "tour", "surface", "year_to_year_r", "year_to_year_true", "year_pairs"]],
                on=["stat", "tour", "surface"], how="left")
    rows = []
    for _, r in f.iterrows():
        g = main[main["tour"].eq(r["tour"]) & main["surface"].eq(r["surface"]) & main["stat"].eq(r["stat"])]
        at = reliability_at(g, r["typical_matches"])
        rel_t = at["reliability"]
        verdict = verdict_of(rel_t)
        lo, hi = at.get("reliability_lo", np.nan), at.get("reliability_hi", np.nan)
        k = r["k_matches"]
        rows.append({"tour": r["tour"], "surface": r["surface"], "stat": r["stat"],
                     "words": C.RATES.get(r["stat"], ADJ.get(r["stat"])), "unit": UNITS[r["stat"]],
                     "regular_seasons": r["regular_seasons"], "typical_matches": r["typical_matches"],
                     "typical_units": r["typical_units"], "reliability_typical": rel_t,
                     "reliability_typical_lo": lo, "reliability_typical_hi": hi,
                     "split_half_r_at_half_season": at.get("r_h"), "half_season_matches": at.get("h"),
                     "k_at_typical_matches": at.get("k_h"), "k_matches": k, "k_units": r["k_units"],
                     "reliability_typical_from_fit": (r["typical_matches"] / (r["typical_matches"] + k)
                                                      if np.isfinite(k) else 0.0),
                     "fit_on": r["fit_on"], "fit_max_abs_resid": r["fit_max_abs_resid"],
                     "year_to_year_r": r["year_to_year_r"], "year_to_year_true": r["year_to_year_true"],
                     "year_pairs": r["year_pairs"],
                     "K_shrink_units": constants_for(shr, r["stat"], r["tour"], r["surface"]),
                     "K_shrink_matches": constants_for(shr, r["stat"], r["tour"], r["surface"], "K_matches"),
                     "verdict": verdict,
                     # the verdict is firm when the reliability's 95% range stays inside one category
                     "verdict_firm": bool(verdict is not None and verdict_of(lo) == verdict_of(hi) == verdict)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------

def main() -> int:
    rows, typical = load_rows()
    ana = rows[rows["level"].isin(C.EVAL_LEVELS) & rows["status"].eq("completed") & rows["format"].eq("standard")].reset_index(drop=True)
    log(f"player-matches: {len(rows):,}; analysis (evaluation levels, completed, standard): {len(ana):,}")
    means = surface_means(ana)
    res = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "seed": SEED,
           "settings": {"n_grid": N_GRID, "draws": DRAWS, "min_units": MIN_UNITS, "fit_units": FIT_UNITS,
                        "fixed_half": FIXED_HALF, "regular": REGULAR, "boot": BOOT, "half_lives": HALF_LIVES,
                        "window_seasons": WINDOW_SEASONS, "rel_years": [REL_YEARS[0], REL_YEARS[-1]],
                        "shrink_years": {k: [v[0], v[-1]] for k, v in {**SHRINK_YEARS, **ADJ_SHRINK_YEARS}.items()},
                        "stage4_years": STAGE4_YEARS, "verdict_thresholds": VERDICT,
                        "forecast_windows": {k: [v[0], v[-1]] for k, v in FORECAST_WINDOWS.items()}},
           "stats": [{"key": s, "words": C.RATES.get(s, ADJ.get(s)), "unit": UNITS[s],
                      "kind": "score" if s in SCORE_STATS else "box", "chance": "Poisson" if s in POISSON else "binomial"}
                     for s in STATS],
           "surface_means": [{"tour": t, "stat": s, "surface": sf, "mean": v} for (t, s, sf), v in means.items()],
           "typical_opponent_rating": typical}
    res["population"] = {
        "analysis_player_matches": {t: int(ana["tour"].eq(t).sum()) for t in C.TOURS},
        "analysis_matches_2013_2026": {t: int((ana["tour"].eq(t) & ana["year"].isin(list(REL_YEARS))).sum() // 2) for t in C.TOURS},
        "analysis_matches_with_box_2013_2026": {t: int((ana["tour"].eq(t) & ana["year"].isin(list(REL_YEARS)) & ana["spw_d"].notna()).sum() // 2) for t in C.TOURS},
        "history_player_matches": {t: int((rows["tour"].eq(t) & rows["status"].eq("completed") & rows["format"].eq("standard")).sum()) for t in C.TOURS},
        "retired_left_out": {t: int((rows["tour"].eq(t) & rows["status"].eq("retired")).sum() // 2) for t in C.TOURS}}

    rel, fits = reliability(ana, means)
    rel.to_csv(RELIABILITY, index=False)
    log("1 reliability done")
    shr = shrinkage(ana, means)
    shr.to_csv(SHRINKAGE, index=False)
    log("2 shrinkage done")
    years, surfs = carryover(ana, means, shr)
    pd.concat([years.assign(kind="year to year"), surfs.assign(kind="surface to surface")], ignore_index=True).to_csv(CARRYOVER, index=False)
    log("3 carry-over done")
    fc, half = forecast(rows, means, shr)
    fc.to_csv(FORECAST, index=False)
    log("4 forecast done")
    typ = typical_season(ana)
    per = persistence(rel, fits, typ, years, shr)
    per.to_csv(PERSISTENCE, index=False)
    log("6 persistence done")

    # how much the constants move from 2010-2018 to every year
    change = []
    for stat in STATS:
        a_name, b_name = (("2013-2018", "2013-2026") if stat in ADJ else ("2010-2018", "2010-2026"))
        for tour in C.TOURS:
            for surface in SURFACES:
                a = shr[(shr["stat"] == stat) & (shr["tour"] == tour) & (shr["surface"] == surface) & (shr["years"] == a_name)]
                b = shr[(shr["stat"] == stat) & (shr["tour"] == tour) & (shr["surface"] == surface) & (shr["years"] == b_name)]
                if len(a) and len(b):
                    ka, kb = float(a["K_units"].iloc[0]), float(b["K_units"].iloc[0])
                    change.append({"stat": stat, "tour": tour, "surface": surface, "from": a_name, "to": b_name,
                                   "K_from": ka, "K_to": kb, "K_ratio": kb / ka if np.isfinite(ka) and ka > 0 else np.nan,
                                   "mean_from": float(a["mean"].iloc[0]), "mean_to": float(b["mean"].iloc[0]),
                                   "inside_bootstrap_range": bool(a["K_units_lo"].iloc[0] <= kb <= a["K_units_hi"].iloc[0])})
    # the JSON keeps what stage3.md and the report quote; the CSVs keep every row
    rel_keep = ["tour", "surface", "stat", "population", "n", "r", "r_lo", "r_hi", "player_windows", "units_per_set",
                "k_from_this_n", "directional_only"]
    res["reliability"] = {"rows": records(rel[rel_keep]), "fits": records(fits)}
    res["shrinkage"] = {"rows": records(shr), "change": change}
    res["carryover"] = {"year": records(years), "surface": records(surfs)}
    main_forms = ["tour average", "career to date", "last 52 weeks", "decayed", "serve and return ratings"]
    keep_fc = ((fc["surface"].eq("all") & ~fc["form"].str.startswith("decayed, half-life"))
               | (fc["form"].isin(main_forms) & fc["window"].eq("2019-2026")))
    res["forecast"] = {"rows": records(fc[keep_fc]), "half_life_weeks": half,
                       "half_life_rows": records(fc[fc["form"].str.startswith("decayed, half-life") & fc["surface"].eq("all")])}
    res["typical_season"] = records(typ)
    res["persistence"] = records(per)
    res["ratings"] = json.loads(RATINGS_SUMMARY.read_text(encoding="utf-8"))
    res["seconds"] = round(time.time() - T0, 1)
    RESULTS.write_text(json.dumps(res, separators=(",", ":"), default=float), encoding="utf-8")
    log(f"wrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
