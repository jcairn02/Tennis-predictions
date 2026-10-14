"""Shared pieces of Stage B ("ideas borrowed from UFC-predictions", Stage B: adjperf / adjdef, IOS ridge ratings per
statistic, and performance split by the opponent's strength). Imported by stageB_adjperf.py, stageB_ios.py,
stageB_split.py, stageB_rundown.py and the tests; it writes nothing.

What is here:
    * the statistics of Stage B, their sides and mirrors, and each one's per-match value on the log-odds scale (the
      log scale for break points faced per service game), centred on the tour's average on the match's surface;
    * the pool (the Stage 4 pool, in the table's order) as row indices of the player-match table;
    * the pair index of the step-1 history: for every box-score player-match, the same player's earlier box-score
      player-matches under the Brief's time rule (earlier tournament weeks, and earlier rounds of the same event; never
      the match itself, another match of the same round, or another event of the same week);
    * decayed and windowed as-of sums (Stage 3's lookback_sums and sums_before, unchanged);
    * the in-sample tuning score (stage4_rundown.newton): the log-loss improvement of [logit p_elo, feature] over
      logit p_elo alone, fitted and scored on the same matches.
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

OUT = ROOT / "data" / "studies" / "ufc_ideas"
DOCS = ROOT / "docs" / "studies" / "ufc_ideas"
STAGE4_CONSTANTS = C.OUT / "stage4_constants.csv"

SERVE_SIDE = ("spw", "first_won", "second_won", "ace", "df", "first_in", "hold", "bp_saved", "bp_faced_pg")
RETURN_SIDE = ("rpw", "brk", "bp_conv", "rpw_first", "rpw_second")
MATCH_SIDE = ("tpw",)
STATS = SERVE_SIDE + RETURN_SIDE + MATCH_SIDE
POISSON = {"bp_faced_pg"}                      # a count per game: the log scale
# the same quantity seen from the other player: A's return statistic in a match is one minus B's serve statistic
MIRROR = {"spw": "rpw", "rpw": "spw", "first_won": "rpw_first", "rpw_first": "first_won", "second_won": "rpw_second",
          "rpw_second": "second_won", "hold": "brk", "brk": "hold", "bp_saved": "bp_conv", "bp_conv": "bp_saved",
          "tpw": "tpw"}
WORDS = {"spw": "serve points won", "rpw": "return points won", "tpw": "total points won",
         "hold": "service games held", "brk": "return games won (breaks)", "ace": "aces per serve point",
         "df": "double faults per serve point", "first_in": "first serves in", "first_won": "first-serve points won",
         "second_won": "second-serve points won", "bp_saved": "break points saved", "bp_conv": "break points converted",
         "bp_faced_pg": "break points faced per service game",
         "rpw_first": "return points won against the first serve",
         "rpw_second": "return points won against the second serve"}
UNIT_WORDS = {"spw": "serve points", "rpw": "return points", "tpw": "points", "hold": "service games",
              "brk": "return games", "ace": "serve points", "df": "serve points", "first_in": "serve points",
              "first_won": "first serves in", "second_won": "second-serve points", "bp_saved": "break points faced",
              "bp_conv": "break-point chances", "bp_faced_pg": "service games",
              "rpw_first": "return points against first serves", "rpw_second": "return points against second serves"}
SHRINK_YEARS = range(2010, 2019)              # population priors and typical units (Stage 3's constants' years)
TUNE_YEARS = range(2013, 2019)                # tuning targets (2010-2012 warm up)
WEEK52 = 364                                  # days: the last 52 weeks (Stage 3's)
REF_DAY = T.REF_DAY
SEED = 20261002
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def side_of(stat: str) -> str:
    return "serve" if stat in SERVE_SIDE else ("return" if stat in RETURN_SIDE else "match")


def jdump(obj, path: Path) -> None:
    """JSON with an infinite half-life written as the string "inf" (float("inf") reads it back) and NaN as null."""
    path.write_text(json.dumps(clean(obj), indent=1, default=_default), encoding="utf-8")


def clean(o):
    if isinstance(o, dict):
        return {(k if isinstance(k, str) else str(k)): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        v = float(o)
        if np.isnan(v):
            return None
        if np.isinf(v):
            return "inf" if v > 0 else "-inf"
        return v
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return v if np.isfinite(v) else None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


# ------------------------------------------------------------------------------------------------
# Rows, the pool, the statistics

def load_rows() -> tuple[pd.DataFrame, dict]:
    """The Stage 4 player-match table (two rows per match, A then B, in the table's order), as stage4_features builds
    it: Stage 0's counts, Stage 3's pre-match serve and return ratings, Stage 1's surface Elo and the closing odds."""
    return F.load_rows()


def pool_rows(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """A's and B's row of each pool match (the Stage 4 pool, in the table's order)."""
    pool = F.pool_mask(rows)
    A = np.flatnonzero(pool) * 2
    return A, A + 1


def surface_means() -> dict:
    """Per statistic: {(tour, surface or 'all'): the tour's average}, as Stage 4 used them (stage4_constants.csv,
    'surface average': Stage 3's for the stored rates, Stage 4's for the return points against each serve)."""
    k = pd.read_csv(STAGE4_CONSTANTS)
    k = k[k["kind"].eq("surface average")]
    out: dict = {}
    for r in k.itertuples(index=False):
        out.setdefault(r.stat, {})[(r.tour, r.surface)] = float(r.value)
    return out


def to_scale(stat: str, p) -> np.ndarray:
    """A share on the log-odds scale; a count per game on the log scale."""
    p = np.asarray(p, dtype="float64")
    return np.log(p) if stat in POISSON else logit(p)


def from_scale(stat: str, y) -> np.ndarray:
    y = np.asarray(y, dtype="float64")
    return np.exp(y) if stat in POISSON else expit(y)


def stat_arrays(rows: pd.DataFrame, means: dict, stats=STATS) -> dict:
    """Per statistic: count x, units d, ok (the row enters the statistic's history: completed, standard format, box
    score, units > 0), the match's value on the scale ((x + 1/2) / (d + 1), log-odds or log), the tour's average on the
    match's surface on the same scale (mu), and the centred value c = value - mu (0 where not ok)."""
    xd = F.stat_xd(rows)
    out = {}
    for s in stats:
        x, d, ok = xd[s]
        ok = ok & (d > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            v = to_scale(s, (x + 0.5) / (d + 1.0))
        # a count outside 0..d has no value on the scale (one box score: W15 Malta 2025, R16, break points saved -1 of 5
        # and converted 6 of 5); it is left out of this statistic, as a missing box score would be
        ok = ok & np.isfinite(v)
        mu = F.mu_of_rows(rows, means[s])
        m = to_scale(s, mu)
        c = np.where(ok, v - m, 0.0)
        out[s] = {"x": np.where(ok, x, 0.0), "d": np.where(ok, d, 0.0), "ok": ok, "v": np.where(ok, v, np.nan),
                  "mu": mu, "mu_scale": m, "c": c}
    return out


def typical_units(rows: pd.DataFrame, sa: dict) -> dict:
    """Per (statistic, tour): the mean units of a box-score match, 2010-2018 (a reference match for the K priors and the
    units weights: K matches x typical units^tau)."""
    yr = rows["year"].to_numpy()
    tour = rows["tour"].to_numpy()
    sel_y = np.isin(yr, list(SHRINK_YEARS))
    out = {}
    for s, a in sa.items():
        for t in C.TOURS:
            m = a["ok"] & sel_y & (tour == t)
            out[(s, t)] = float(a["d"][m].mean())
    return out


def per_tour(values: dict, tour: np.ndarray) -> np.ndarray:
    """values {'atp': x, 'wta': y} spread over rows by tour."""
    return np.where(tour == "atp", values["atp"], values["wta"])


# ------------------------------------------------------------------------------------------------
# The step-1 pair index: (target box row, earlier visible box row of the same player)

class PairIndex:
    """For every box-score row k (positions 0..n-1 of ``box_idx``, in the player-time order of ``order``): the same
    player's earlier box-score rows that k may see. In that order the visible rows of k are two runs, the player's
    rows of earlier tournament weeks [p_start, day_start) and the same event's earlier rounds [ev_start, rnd_start); so
    the match itself, another match of the same round (a round robin) and another event of the same week are never
    included. Pairs are generated in target order, chunk by chunk, so that no pass holds them all at once."""

    def __init__(self, rows: pd.DataFrame, box_idx: np.ndarray, chunk_pairs: int = 12_000_000):
        self.box_idx = np.asarray(box_idx)
        pc = rows["pcode"].to_numpy()[box_idx].astype("int64")
        dy = rows["day"].to_numpy()[box_idx].astype("int64")
        ev = rows["ev"].to_numpy()[box_idx].astype("int64")
        rn = rows["round_order"].to_numpy()[box_idx].astype("int64")
        od = rows["order"].to_numpy()[box_idx].astype("int64")
        o = np.lexsort((od, rn, ev, dy, pc))
        self.order = o                                      # sorted position -> position in box_idx
        n = len(o)
        pcs, dys, evs, rns = pc[o], dy[o], ev[o], rn[o]
        pos = np.arange(n)

        def starts(new):
            return np.maximum.accumulate(np.where(new, pos, 0))
        first = np.r_[True, np.zeros(n - 1, dtype=bool)]
        new_p = first | np.r_[False, pcs[1:] != pcs[:-1]]
        new_d = new_p | np.r_[False, dys[1:] != dys[:-1]]
        new_e = new_d | np.r_[False, evs[1:] != evs[:-1]]
        new_r = new_e | np.r_[False, rns[1:] != rns[:-1]]
        self.p_start, self.day_start = starts(new_p), starts(new_d)
        self.ev_start, self.rnd_start = starts(new_e), starts(new_r)
        self.L1 = self.day_start - self.p_start
        self.L2 = self.rnd_start - self.ev_start
        self.L = self.L1 + self.L2
        self.day_sorted = dys
        self.n = n
        self.n_pairs = int(self.L.sum())
        cum = np.cumsum(self.L)
        bounds = [0]
        while bounds[-1] < n:
            target = (cum[bounds[-1] - 1] if bounds[-1] > 0 else 0) + chunk_pairs
            nxt = int(np.searchsorted(cum, target, side="right"))
            bounds.append(min(max(nxt, bounds[-1] + 1), n))
        self.bounds = bounds

    def chunks(self):
        """Yield (tgt, src, dt): sorted positions of the target and of the earlier row, and the days between them."""
        for a, b in zip(self.bounds[:-1], self.bounds[1:]):
            L, L1 = self.L[a:b], self.L1[a:b]
            tot = int(L.sum())
            if tot == 0:
                continue
            tgt = np.repeat(np.arange(a, b, dtype=np.int64), L)
            off = np.repeat(np.cumsum(L) - L, L)
            within = np.arange(tot, dtype=np.int64) - off
            l1 = np.repeat(L1, L)
            src = np.where(within < l1, np.repeat(self.p_start[a:b], L) + within,
                           np.repeat(self.ev_start[a:b], L) + (within - l1))
            dt = (self.day_sorted[tgt] - self.day_sorted[src]).astype("float64")
            yield tgt, src, dt

    def to_sorted(self, v: np.ndarray) -> np.ndarray:
        """A per-box-row array (positions of box_idx) in the pair index's sorted order."""
        return np.asarray(v)[self.order]

    def from_sorted(self, v: np.ndarray) -> np.ndarray:
        out = np.empty_like(v)
        out[self.order] = v
        return out


def decay(dt_days: np.ndarray, half_life_weeks: float) -> np.ndarray:
    """2^(-age / h), age in weeks; 1 for an infinite half-life."""
    if not np.isfinite(half_life_weeks):
        return np.ones(len(dt_days))
    return np.exp2(-dt_days / (7.0 * half_life_weeks))


def pair_moments(P: PairIndex, specs: dict, wanted) -> dict:
    """Weighted moments of the earlier rows' values for every target row. ``specs`` maps a name to (a, valid, units):
    per box row, in P's sorted order, the value, whether it exists, and its units. For each (name, half-life h, tau) in
    ``wanted``: S0 = sum w, S1 = sum w a and M = sum w |a - S1/S0| over the target's visible earlier rows, with
    w = 2^(-age/h) x units^tau (0 where the value does not exist). Returns {(name, h, tau): (S0, S1, M)}.

    The mean absolute deviation needs the target's own mean: within a chunk (which always holds every pair of its
    targets) the mean is formed first, then the deviations from it, so the result is exact."""
    wanted = list(dict.fromkeys(wanted))
    prep = {}
    for name in {w[0] for w in wanted}:
        a, valid, units = specs[name]
        valid = np.asarray(valid, dtype=bool)
        av = np.where(valid, np.nan_to_num(np.asarray(a, dtype="float64")), 0.0)
        un = np.asarray(units, dtype="float64")
        taus = {t for n_, _, t in wanted if n_ == name}
        prep[name] = (av, {t: np.where(valid, un ** t if t != 0 else 1.0, 0.0) for t in taus})
    out = {k: (np.zeros(P.n), np.zeros(P.n), np.zeros(P.n)) for k in wanted}
    hs = {h for _, h, _ in wanted}
    for tgt, src, dt in P.chunks():
        lo, hi = int(tgt[0]), int(tgt[-1]) + 1
        rel = tgt - lo
        m = hi - lo
        decs = {h: decay(dt, h) for h in hs}
        gathered = {}
        for name, h, t in wanted:
            av, uv = prep[name]
            if name not in gathered:
                gathered[name] = av[src]
            a = gathered[name]
            w = decs[h] * uv[t][src]
            S0, S1, M = out[(name, h, t)]
            s0 = np.bincount(rel, weights=w, minlength=m)
            s1 = np.bincount(rel, weights=w * a, minlength=m)
            with np.errstate(divide="ignore", invalid="ignore"):
                mean = np.where(s0 > 0, s1 / np.where(s0 > 0, s0, 1.0), 0.0)
            S0[lo:hi] += s0
            S1[lo:hi] += s1
            M[lo:hi] += np.bincount(rel, weights=w * np.abs(a - mean[rel]), minlength=m)
        del gathered
    return out


# ------------------------------------------------------------------------------------------------
# As-of sums (the time rule) on a subset of rows

def asof_frame(rows: pd.DataFrame, idx: np.ndarray, key: np.ndarray | None = None) -> pd.DataFrame:
    """The columns lookback_sums / asof_sums read, for the rows idx (optionally with another player key)."""
    f = pd.DataFrame({"player_id": (rows["pcode"].to_numpy()[idx] if key is None else np.asarray(key)[idx]),
                      "tournament_date": rows["tournament_date"].to_numpy()[idx],
                      "tournament_id": rows["tournament_id"].to_numpy()[idx],
                      "round_order": rows["round_order"].to_numpy()[idx],
                      "day": rows["day"].to_numpy()[idx]})
    return f


def windowed_sums(frame: pd.DataFrame, V: np.ndarray, half_lives=()) -> dict:
    """For each row of ``frame``: the sums of V over the same player's earlier rows under the time rule, as the career
    (no decay), each decayed half-life, and the last 52 weeks (events starting up to 364 days before, plus the same
    event's earlier rounds). {'career': .., h: .., '52 weeks': ..}."""
    car, dec = T.lookback_sums(frame, V, tuple(half_lives))
    pc = np.asarray(frame["player_id"].to_numpy())
    pcode = pd.factorize(pd.Series(pc))[0]
    day = frame["day"].to_numpy()
    bef = T.sums_before(pcode, day, np.asarray(V, dtype="float64").reshape(len(frame), -1), pcode, day - WEEK52)
    out = {"career": car, "52 weeks": car - bef}
    out.update(dec)
    return out


# ------------------------------------------------------------------------------------------------
# The tuning score

def lr_improvement(base_logit: np.ndarray, X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """In-sample log-loss improvement (milli-log-loss, positive = better) of a logistic regression without an intercept
    on [base, x] over one on [base] alone, for every column x of X (n, k), all fitted and scored on the same rows."""
    n, k = X.shape
    sd = X.std(axis=0)
    Xs = X / np.where(sd > 0, sd, 1.0)
    Z = np.empty((k, n, 2))
    Z[:, :, 0] = base_logit[None, :]
    Z[:, :, 1] = Xs.T
    b = R.newton(Z, y, np.zeros((k, 2)))
    p = expit((Z @ b[:, :, None])[:, :, 0])
    llm = R.ll(p, y[None, :]).mean(axis=1)
    b0 = R.newton(base_logit[None, :, None], y, np.zeros((1, 1)))
    ll0 = R.ll(expit(base_logit * b0[0, 0]), y).mean()
    out = 1000 * (ll0 - llm)
    out[sd == 0] = np.nan
    return out
