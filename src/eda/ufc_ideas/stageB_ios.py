"""Stage B, part 2: IOS ridge ratings per statistic, the UFC pipeline's add_ios_ridge_stats (features/v4/ios_query.py)
rebuilt for tennis: a batch, exactly solved twin of Stage 3's online serve and return ratings, extended to every serve-side
box-score statistic.

SUPERSEDED for new work (docs/decisions/2026-10-05-match-timing.md). This module's snapshots release every result whose
event STARTED before the snapshot, so an event still running (a Grand Slam's second week, an event dated earlier in the
same week) reaches other players' matches played before it. The leak-proof solver is src/eda/match_timing/ios_time.py
(run_timed: a result enters the solve the day after its latest possible finish; a match reads the solve of its
earliest possible start), fed by src/eda/match_timing/timing.parquet; rebuild.py builds the inputs with it. This file
is kept as the record of the studies that used it (its pcg solver and tuned constants are reused). The tuned constants
reach the builders through the IOS constants registry (src/eda/ios_constants/registry.py), not from this file's summary:
a re-run writes a new stageB_ios_summary.json, which changes no input until it is added as a version and activated.

For each serve-side statistic s (spw, ace, df, first_in, first_won, second_won, hold, bp_saved; the return side is the
same observations seen from the returner: return points won is one minus the server's spw, breaks one minus holds,
break points converted one minus saved), every completed standard-format box-score match gives two observations (A
serving, B serving):

    y = logit((x + 1/2) / (d + 1)) - logit(mu)  ~  O_server - D_returner

mu the tour's average of s on the match's surface (Stage 3's, 2010-2018, as Stage 4 used them). At each snapshot (a
tournament week) the ratings minimise

    sum_k w_k (y_k - O_a(k) + D_b(k))^2 + kappa (|O|^2 + |D|^2),   w_k = 2^(-age_k / h) x (d_k / d_typical)^tau

over the observations of earlier weeks only (age in weeks to the snapshot; d_typical the statistic's mean units per box
score match on the tour in 2010-2018, so a typical match weighs 1 and kappa is in typical matches). The normal equations
are solved by a Jacobi-preconditioned conjugate gradient warm-started from the previous snapshot (the UFC
_ios_ridge_pcg); the sums are kept as running totals in time-scaled units, so a snapshot costs its new observations and
the solve. A player never seen has O = D = 0.

The same event's earlier rounds (and, on the four-weekly tuning snapshots, the block's earlier weeks) are added by a
leak-free incremental step: each player's own O and D are re-solved with every other rating held at the snapshot,
O' = (f (P + kappa) O + sum_gap w (y + D_opponent)) / (f P + kappa + sum_gap w), with P the player's data weight at the
snapshot and f = 2^(-(t - snapshot) / h) the decay of the snapshot's data to the match's week; D likewise. Only the
player's matches the time rule lets the match see enter the gap sums (common.asof_sums within the player and snapshot).

Tuning (2013-2018 only, then frozen): per statistic and tour, h in {13, 26, 52, 104, 208, inf} weeks x kappa in
{0.3, 1, 3, 10, 30, 100} x tau in {0, 1} (the Brief's grid, h from 26 and kappa 1 to 30, extended after a first run chose
its edges for most statistics; its own choice is reported beside), by the next-match log loss per unit of the statistic
(binomial: the match's x in d units at expit(logit mu + O_server - D_returner)) on the evaluation-level matches of
2013-2018, with observations up to 2018.
The tuning runs on the same weekly snapshots as the features (measured at 1-2.5 seconds a run, so the four-weekly
fallback the Brief allows was not needed; run(mode="block") keeps it); the chosen constants are then run over the whole
history.

The probe (as stage3_ratings.probe_by_round), for spw and hold on both tours, on the slice from 2023 (history inside the
slice): at 4 cut matches of 2026, the outcomes of every match the cut may not see are redrawn and the path re-run; the
pre-match values of the protected matches (earlier weeks, and the cut event's rounds up to the cut's) must not move.

Writes, in data/studies/ufc_ideas/:
    stageB_ios.parquet           per match of the table (872,704): A's and B's pre-match O and D of every statistic
                                 (float32), with the incremental step
    stageB_ios_features.parquet  per pool match: ios_O_<s>|single, ios_D_<s>|single (A - B), ios_matchup_points|single,
                                 ios_matchup_games|single (the log-odds of the iid model's chance that A wins), and three
                                 diagnostics, ios_matchup_points|diagnostic: h 4 weeks / h 13 weeks / kappa 10 (the points
                                 matchup with one constant changed from the tuned ones; added after the first rundown showed
                                 the batch ratings, tuned on the statistic, trailing the online ones given Elo)
    stageB_ios_tuning.csv        every tuning setting: tour, statistic, h, kappa, tau, log loss per unit and the gain on
                                 the surface average (milli-log-loss per unit)
    stageB_ios_summary.json      the chosen constants, the grids' flatness, the out-of-sample scores, spw beside Stage 3's
                                 online ratings, the incremental step's effect, the probe, solver statistics, timings

Run: ./python.sh src/eda/ufc_ideas/stageB_ios.py   (about 16 minutes with 5 worker processes: the tuning 11, the
     weekly runs 2, the diagnostics 1, the probe 1; set STAGEB_WORKERS to use fewer)
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")       # Stage B's share of the machine: at most 5 processes or threads at once

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import common as H  # noqa: E402
from src.eda.ufc_ideas import stageB_common as B  # noqa: E402

IOS_PARQUET = B.OUT / "stageB_ios.parquet"
IOS_FEATURES = B.OUT / "stageB_ios_features.parquet"
IOS_TUNING = B.OUT / "stageB_ios_tuning.csv"
IOS_SUMMARY = B.OUT / "stageB_ios_summary.json"
STAGE3_RATINGS_SUMMARY = C.OUT / "stage3_ratings_summary.json"
STAGE3_RATINGS = C.OUT / "stage3_ratings.parquet"

IOS_STATS = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
RETURN_OF = {"spw": "rpw", "hold": "brk", "bp_saved": "bp_conv", "first_won": "rpw_first", "second_won": "rpw_second"}
# The Brief's grid is h in {26, 52, 104, 208, inf} weeks x kappa in {1, 3, 10, 30}. A first run chose its edges for most
# statistics (kappa 1 for serve points won, first-serve points won, holds and aces; kappa 30 for break points saved; h 26
# for aces and first serves in), so the grid was extended (disclosed) to h = 13 and kappa = 0.3 and 100. Rows of the
# Brief's own grid are flagged in_brief_grid in stageB_ios_tuning.csv, and its own choice is reported beside.
HS = (13.0, 26.0, 52.0, 104.0, 208.0, np.inf)
KAPPAS = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
BRIEF_GRID = {"h": (26.0, 52.0, 104.0, 208.0, np.inf), "kappa": (1.0, 3.0, 10.0, 30.0)}
TAUS = (0, 1)
BLOCK_DAYS = 28                      # four-weekly snapshots (the Brief's fallback; not needed: see TUNE_MODE)
TUNE_MODE = "weekly"                 # a weekly tuning run (observations to 2018) takes 1-2.5 s, so the grid runs weekly
TUNE_FROM, TUNE_TO = "2013-01-01", "2018-12-31"
WINDOWS = {"2013-2018": range(2013, 2019), "2019-2026": range(2019, 2027), "2022-2026": range(2022, 2027)}
RTOL = 1e-8
MAX_ITER = 1000
WORKERS = int(os.environ.get("STAGEB_WORKERS", "5"))   # the Brief's cap is 5 worker processes per stage
PROBE_FROM = "2023-01-01"
PROBE_STATS = ("spw", "hold")
PROBE_CUTS = 4
PROBE_ATOL = 1e-9
# the points matchup again with one constant changed from the statistic's tuning (added after the first rundown showed the
# batch ratings trailing the online ones as a predictor of the winner given Elo while forecasting serve points as well)
DIAGNOSTICS = (("h 4 weeks", {"h": 4.0}), ("h 13 weeks", {"h": 13.0}), ("kappa 10", {"kappa": 10.0}))


def hl_name(h: float) -> str:
    return "inf" if not np.isfinite(h) else f"{h:g}"


# ------------------------------------------------------------------------------------------------
# Inputs: per tour, compact arrays

def tour_inputs(rows: pd.DataFrame, sa: dict, typ: dict, tour: str) -> dict:
    """Everything a run reads for one tour, as plain arrays over the tour's rows (in the table's order, so the two rows
    of a match stay adjacent: a row's opponent is its position ^ 1)."""
    idx = np.flatnonzero(rows["tour"].to_numpy() == tour)
    assert len(idx) % 2 == 0 and (rows["match_id"].to_numpy()[idx[0::2]] == rows["match_id"].to_numpy()[idx[1::2]]).all()
    pid = pd.factorize(rows["pcode"].to_numpy()[idx])[0]
    d = {"tour": tour, "idx": idx, "pid": pid.astype(np.int64), "n_players": int(pid.max()) + 1,
         "day": rows["day"].to_numpy()[idx].astype(np.int64),
         "tournament_date": rows["tournament_date"].to_numpy()[idx],
         "tournament_id": rows["tournament_id"].to_numpy()[idx].astype(object),
         "round_order": rows["round_order"].to_numpy()[idx].astype(np.int64),
         "year": rows["year"].to_numpy()[idx], "evaluation": rows["evaluation"].to_numpy()[idx].astype(bool),
         "eval_level": rows["eval_level"].to_numpy()[idx].astype(bool), "stats": {}}
    for s in IOS_STATS:
        a = sa[s]
        d["stats"][s] = {"ok": a["ok"][idx], "x": a["x"][idx], "d": a["d"][idx], "y": a["c"][idx],
                         "mu": a["mu_scale"][idx], "typ": typ[(s, tour)]}
    return d


# ------------------------------------------------------------------------------------------------
# The solver

def pcg(matvec, diag: np.ndarray, b: np.ndarray, x0: np.ndarray, rtol: float = RTOL, max_iter: int = MAX_ITER):
    """Jacobi-preconditioned conjugate gradient for an SPD system (the UFC _ios_ridge_pcg). Returns (x, iterations,
    converged)."""
    x = x0.copy()
    r = b - matvec(x)
    inv = 1.0 / diag
    z = r * inv
    p = z.copy()
    rz = float(r @ z)
    bn = float(np.linalg.norm(b))
    if bn == 0.0:
        return np.zeros_like(b), 0, True
    for it in range(max_iter):
        if float(np.linalg.norm(r)) <= rtol * bn:
            return x, it, True
        Ap = matvec(p)
        den = float(p @ Ap)
        if den <= 0.0:
            break
        alpha = rz / den
        x = x + alpha * p
        r = r - alpha * Ap
        z = r * inv
        rz_new = float(r @ z)
        if rz <= 0.0:
            break
        p = z + (rz_new / rz) * p
        rz = rz_new
    return x, max_iter, bool(float(np.linalg.norm(r)) <= rtol * bn)


class System:
    """The observations of one statistic on one tour, sorted by day, with the fixed sparsity pattern of the
    server-by-returner weight matrix W (every pair that ever meets) and of its transpose."""

    def __init__(self, td: dict, stat: str, until_day: int | None = None):
        st = td["stats"][stat]
        ok = st["ok"].copy()
        if until_day is not None:
            ok &= td["day"] <= until_day
        k = np.flatnonzero(ok)
        o = np.argsort(td["day"][k], kind="stable")
        k = k[o]
        self.rows = k
        self.srv = td["pid"][k]
        self.ret = td["pid"][k ^ 1]
        self.y = st["y"][k]
        self.d = st["d"][k]
        self.day = td["day"][k]
        self.typ = st["typ"]
        n = td["n_players"]
        self.n = n
        key = self.srv * n + self.ret
        uniq, self.pair = np.unique(key, return_inverse=True)
        ps, pr = uniq // n, uniq % n
        self.n_pairs = len(uniq)
        indptr = np.r_[0, np.cumsum(np.bincount(ps, minlength=n))]
        self.W = sp.csr_matrix((np.zeros(len(uniq)), pr.astype(np.int32), indptr.astype(np.int64)), shape=(n, n))
        perm = np.lexsort((ps, pr))
        indptr_t = np.r_[0, np.cumsum(np.bincount(pr, minlength=n))]
        self.WT = sp.csr_matrix((np.zeros(len(uniq)), ps[perm].astype(np.int32), indptr_t.astype(np.int64)), shape=(n, n))
        self.perm = perm


def snapshot_path(sysm: System, groups_day: np.ndarray, h: float, kappa: float, tau: int):
    """Solve the ridge system at each snapshot day in ``groups_day`` (ascending) with the observations of earlier days.
    Yields (snapshot index, O, D, P, Q, iterations): P and Q the players' data weights as server and as returner."""
    n = sysm.n
    ref = float(B.REF_DAY)
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    w0 = (sysm.d / sysm.typ) ** tau if tau else np.ones(len(sysm.d))
    ws = w0 * np.exp2((sysm.day - ref) * lam)              # time-scaled weights: the decay is a common factor later
    Pc, Qc, bOc, bDc = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    PWc = np.zeros(sysm.n_pairs)
    ptr = 0
    x = np.zeros(2 * n)
    W, WT = sysm.W, sysm.WT
    for gi, S in enumerate(groups_day):
        new = int(np.searchsorted(sysm.day, S, side="left"))
        if new > ptr:
            sl = slice(ptr, new)
            Pc += np.bincount(sysm.srv[sl], weights=ws[sl], minlength=n)
            Qc += np.bincount(sysm.ret[sl], weights=ws[sl], minlength=n)
            wy = ws[sl] * sysm.y[sl]
            bOc += np.bincount(sysm.srv[sl], weights=wy, minlength=n)
            bDc -= np.bincount(sysm.ret[sl], weights=wy, minlength=n)
            PWc += np.bincount(sysm.pair[sl], weights=ws[sl], minlength=sysm.n_pairs)
            ptr = new
        g = np.exp2(-(S - ref) * lam)
        P, Q = Pc * g, Qc * g
        W.data[:] = PWc * g
        WT.data[:] = W.data[sysm.perm]
        dO, dD = P + kappa, Q + kappa

        def matvec(v):
            o, dd = v[:n], v[n:]
            return np.concatenate([dO * o - W @ dd, dD * dd - WT @ o])
        b = np.concatenate([bOc * g, bDc * g])
        x, it, conv = pcg(matvec, np.concatenate([dO, dD]), b, x)
        yield gi, x[:n], x[n:], P, Q, it, conv


def run(td: dict, stat: str, h: float, kappa: float, tau: int, mode: str = "weekly", from_day: int | None = None,
        until_day: int | None = None, every_row: bool = True) -> dict:
    """One path of the ratings for one statistic and tour: the snapshot values and the incremental values of every row
    whose snapshot lies in [from_day, until_day] (the rest NaN). mode "weekly": a snapshot per tournament week; "block":
    one per four weeks (tuning). every_row False: the incremental values only where the statistic was played (the
    tuning's targets), which spares the as-of pass over the rows without a box score."""
    sysm = System(td, stat, until_day=until_day)
    day = td["day"]
    if mode == "weekly":
        gday = day
    else:
        d0 = int(day.min())
        gday = d0 + ((day - d0) // BLOCK_DAYS) * BLOCK_DAYS
    in_range = np.ones(len(day), dtype=bool)
    if from_day is not None:
        in_range &= gday >= from_day
    if until_day is not None:
        in_range &= day <= until_day
    snaps, ginv = np.unique(gday[in_range], return_inverse=True)
    rows_in = np.flatnonzero(in_range)
    order = np.argsort(ginv, kind="stable")
    bounds = np.r_[0, np.cumsum(np.bincount(ginv, minlength=len(snaps)))]
    pid = td["pid"]
    nr = len(day)
    Os, Ds, Ps, Qs = (np.full(nr, np.nan) for _ in range(4))
    its, nonconv = [], 0
    for gi, O, D, P, Q, it, conv in snapshot_path(sysm, snaps, h, kappa, tau):
        r = rows_in[order[bounds[gi]:bounds[gi + 1]]]
        p = pid[r]
        Os[r], Ds[r], Ps[r], Qs[r] = O[p], D[p], P[p], Q[p]
        its.append(it)
        nonconv += int(not conv)
    # the incremental step: each player's own O and D re-solved with the gap observations (earlier weeks of the snapshot's
    # block, and the same event's earlier rounds), every other rating held at the snapshot
    st = td["stats"][stat]
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    ok = st["ok"] & in_range
    opp = np.arange(nr) ^ 1
    w0 = np.where(ok, (st["d"] / st["typ"]) ** tau if tau else 1.0, 0.0)
    e = np.exp2((day - gday) * lam)                          # decay scaling inside the snapshot's group
    okr = ok[opp]                                            # the opponent served in that match: a return observation
    w0r = w0[opp]
    V = np.column_stack([np.where(ok, w0 * e, 0.0),
                         np.where(ok, w0 * e * (st["y"] + np.nan_to_num(Ds[opp])), 0.0),
                         np.where(okr, w0r * e, 0.0),
                         np.where(okr, w0r * e * (np.nan_to_num(Os[opp]) - st["y"][opp]), 0.0)])
    sub_mask = in_range if every_row else (in_range & (ok | okr))
    sub = np.flatnonzero(sub_mask)
    gpos = np.full(nr, -1, dtype=np.int64)
    gpos[rows_in] = ginv
    key = pid[sub].astype(np.int64) * (len(snaps) + 1) + gpos[sub]
    frame = pd.DataFrame({"player_id": key, "tournament_date": td["tournament_date"][sub],
                          "tournament_id": td["tournament_id"][sub], "round_order": td["round_order"][sub]})
    cols = [f"v{j}" for j in range(4)]
    for j, c in enumerate(cols):
        frame[c] = V[sub, j]
    G = np.zeros((nr, 4))
    G[sub] = C.asof_sums(frame, cols).to_numpy()
    f = np.exp2(-(day - gday) * lam)
    G *= f[:, None]
    O1 = (f * (Ps + kappa) * Os + G[:, 1]) / (f * Ps + kappa + G[:, 0])
    D1 = (f * (Qs + kappa) * Ds + G[:, 3]) / (f * Qs + kappa + G[:, 2])
    return {"O_snap": Os, "D_snap": Ds, "O": O1, "D": D1, "in_range": in_range,
            "solver": {"snapshots": int(len(snaps)), "observations": int(len(sysm.y)), "pairs": int(sysm.n_pairs),
                       "players": int(sysm.n), "iterations_mean": float(np.mean(its)) if its else 0.0,
                       "iterations_max": int(np.max(its)) if its else 0, "not_converged": nonconv}}


def score(td: dict, stat: str, res: dict, years, incremental: bool = True, sel_extra: np.ndarray | None = None) -> dict:
    """Log loss per unit of the statistic over the evaluation-level box-score rows of ``years`` (each row the server's
    match), at expit(mu + O_server - D_returner), against the tour's surface average."""
    st = td["stats"][stat]
    nr = len(td["day"])
    opp = np.arange(nr) ^ 1
    O = res["O"] if incremental else res["O_snap"]
    D = res["D"] if incremental else res["D_snap"]
    sel = st["ok"] & td["evaluation"] & np.isin(td["year"], list(years)) & np.isfinite(O) & np.isfinite(D[opp])
    if sel_extra is not None:
        sel &= sel_extra
    x, d, mu = st["x"][sel], st["d"][sel], st["mu"][sel]
    p = np.clip(expit(mu + O[sel] - D[opp][sel]), 1e-12, 1 - 1e-12)
    p0 = np.clip(expit(mu), 1e-12, 1 - 1e-12)
    ll = -(x * np.log(p) + (d - x) * np.log(1 - p))
    ll0 = -(x * np.log(p0) + (d - x) * np.log(1 - p0))
    U = float(d.sum())
    diff = ll0 - ll
    gain = diff.sum() / U
    se = np.sqrt(((diff - gain * d) ** 2).sum()) / U
    return {"rows": int(sel.sum()), "units": U, "logloss_per_unit": float(ll.sum() / U),
            "logloss_surface_average": float(ll0.sum() / U), "better_milli_per_unit": 1000 * float(gain),
            "better_lo": 1000 * float(gain - 1.96 * se), "better_hi": 1000 * float(gain + 1.96 * se)}


# ------------------------------------------------------------------------------------------------
# Workers

_W: dict = {}


def init_worker(inputs: dict) -> None:
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    _W.update(inputs)


def tune_task(args) -> list[dict]:
    tour, stat, h, kappa, tau = args
    td = _W[tour]
    t0 = time.time()
    fd = int(np.datetime64(TUNE_FROM, "D").astype("int64"))
    ud = int(np.datetime64(TUNE_TO, "D").astype("int64"))
    res = run(td, stat, h, kappa, tau, mode=TUNE_MODE, from_day=fd, until_day=ud, every_row=False)
    sc = score(td, stat, res, range(2013, 2019))
    return [{"tour": tour, "stat": stat, "h": h, "kappa": kappa, "tau": tau, **sc, **res["solver"],
             "seconds": round(time.time() - t0, 2)}]


def final_task(args) -> dict:
    tour, stat, h, kappa, tau = args
    td = _W[tour]
    t0 = time.time()
    res = run(td, stat, h, kappa, tau, mode="weekly")
    scores = {}
    for w, yrs in WINDOWS.items():
        scores[w] = {"incremental": score(td, stat, res, yrs), "snapshot_only": score(td, stat, res, yrs, incremental=False)}
    return {"tour": tour, "stat": stat, "O": res["O"].astype("float64"), "D": res["D"].astype("float64"),
            "O_snap": res["O_snap"], "D_snap": res["D_snap"], "scores": scores, "solver": res["solver"],
            "seconds": round(time.time() - t0, 1)}


# ------------------------------------------------------------------------------------------------
# Beside Stage 3's online ratings (spw)

def stage3_comparison(rows: pd.DataFrame, sa: dict, ios: dict) -> list[dict]:
    """IOS spw scored on exactly Stage 3's scoring set (stage3_ratings.py: evaluation-level matches that move the
    ratings, both servers, every format), against Stage 3's own figures read from stage3_ratings_summary.json. The
    surface-average log loss is recomputed on the same points as a check that the sets are the same."""
    summ = json.loads(STAGE3_RATINGS_SUMMARY.read_text(encoding="utf-8"))
    rt = pd.read_parquet(STAGE3_RATINGS, columns=["match_id", "updates", "mu_logit"]).set_index("match_id")
    A = np.arange(0, len(rows), 2)
    mid = rows["match_id"].to_numpy()[A]
    upd = rt["updates"].reindex(mid).to_numpy(dtype=bool)
    mu = rt["mu_logit"].reindex(mid).to_numpy(dtype="float64")
    out = []
    lvl = rows["level"].to_numpy()[A]
    yr = rows["year"].to_numpy()[A]
    tour = rows["tour"].to_numpy()[A]
    n_a, w_a = rows["spw_d"].to_numpy(dtype="float64")[A], rows["spw_n"].to_numpy(dtype="float64")[A]
    n_b, w_b = rows["spw_d"].to_numpy(dtype="float64")[A + 1], rows["spw_n"].to_numpy(dtype="float64")[A + 1]
    mu_traits = sa["spw"]["mu_scale"][A]
    Oa, Ob = ios["O"][A], ios["O"][A + 1]
    Da, Db = ios["D"][A], ios["D"][A + 1]
    for t in C.TOURS:
        det = {d["tour"]: d for d in summ["tuning_detail"]}[t]
        for w in det["scored"]:
            y0, y1 = (int(v) for v in w["window"].split("-"))
            sel = (tour == t) & upd & np.isin(lvl, C.EVAL_LEVELS) & (yr >= y0) & (yr <= y1)
            pa = np.clip(expit(mu_traits[sel] + Oa[sel] - Db[sel]), 1e-12, 1 - 1e-12)
            pb = np.clip(expit(mu_traits[sel] + Ob[sel] - Da[sel]), 1e-12, 1 - 1e-12)
            na, wa, nb, wb = n_a[sel], w_a[sel], n_b[sel], w_b[sel]
            pts = float((na + nb).sum())
            ll = float(-(wa * np.log(pa) + (na - wa) * np.log(1 - pa) + wb * np.log(pb) + (nb - wb) * np.log(1 - pb)).sum() / pts)
            p0 = np.clip(expit(mu[sel]), 1e-12, 1 - 1e-12)
            ll0 = float(-(wa * np.log(p0) + (na - wa) * np.log(1 - p0) + wb * np.log(p0) + (nb - wb) * np.log(1 - p0)).sum() / pts)
            out.append({"tour": t, "window": w["window"], "matches": int(sel.sum()), "serve_points": pts,
                        "stage3_matches": w["matches"], "stage3_serve_points": w["serve_points"],
                        "same_set": bool(int(sel.sum()) == w["matches"] and abs(pts - w["serve_points"]) < 0.5),
                        "surface_average_recomputed": ll0, "stage3_surface_average": w["logloss_surface_mean"],
                        "ios_logloss": ll, "stage3_logloss": w["logloss"],
                        "ios_better_milli_per_point": 1000 * (w["logloss_surface_mean"] - ll),
                        "stage3_better_milli_per_point": w["better_milli_per_point"],
                        "ios_minus_stage3_milli_per_point": 1000 * (w["logloss"] - ll)})
    return out


# ------------------------------------------------------------------------------------------------
# Features for the pool

def matchup_points(rows: pd.DataFrame, sa: dict, O: np.ndarray, D: np.ndarray) -> np.ndarray:
    """The log-odds of the iid model's chance that A wins, from A's and B's expected serve-point shares
    expit(mu + O_server - D_returner), using only scheduled format metadata."""
    A, Bi = B.pool_rows(rows)
    mu = sa["spw"]["mu_scale"][A]
    pa = expit(mu + O[A] - D[Bi])
    pb = expit(mu + O[Bi] - D[A])
    return B.F.safe_logit(B.F.scheduled_iid_prob(pa, pb, rows.iloc[A]))


def features(rows: pd.DataFrame, sa: dict, ios: dict, means: dict) -> dict:
    A, Bi = B.pool_rows(rows)
    out = {}
    for s in IOS_STATS:
        out[f"ios_O_{s}|single"] = ios[s]["O"][A] - ios[s]["O"][Bi]
        out[f"ios_D_{s}|single"] = ios[s]["D"][A] - ios[s]["D"][Bi]
    out["ios_matchup_points|single"] = matchup_points(rows, sa, ios["spw"]["O"], ios["spw"]["D"])
    mh = sa["hold"]["mu_scale"][A]
    ha = expit(mh + ios["hold"]["O"][A] - ios["hold"]["D"][Bi])
    hb = expit(mh + ios["hold"]["O"][Bi] - ios["hold"]["D"][A])
    out["ios_matchup_games|single"] = B.F.safe_logit(B.F.scheduled_iid_prob(
        B.F.serve_rate_for_hold(ha), B.F.serve_rate_for_hold(hb), rows.iloc[A]))
    return out


# ------------------------------------------------------------------------------------------------
# The probe

def probe(rows: pd.DataFrame, means: dict, typ: dict, chosen: dict) -> dict:
    """stage3_ratings.probe_by_round for the weekly path with the incremental step, per statistic and tour."""
    sl = rows["tournament_date"].ge(pd.Timestamp(PROBE_FROM)).to_numpy()
    base_rows = B.F.prepare(rows[sl].reset_index(drop=True).drop(columns=["day", "pcode"]))
    rng = np.random.default_rng(B.SEED + 7)
    out = {}
    for t in C.TOURS:
        for s in PROBE_STATS:
            c = chosen[(t, s)]
            sa0 = B.stat_arrays(base_rows, means, (s,))
            td0 = tour_inputs_one(base_rows, sa0, typ, t, s)
            r0 = run(td0, s, c["h"], c["kappa"], c["tau"])
            base = np.column_stack([r0["O"], r0["D"]])
            day, ev, rn = td0["day"], td0["ev"], td0["round_order"]
            okc = td0["stats"][s]["ok"] & (td0["year"] == td0["year"].max())
            cand = np.flatnonzero(okc)
            rec = {"cuts": 0, "protected_rows_checked": 0, "protected_rows_changed": 0, "later_rows_changed": 0,
                   "largest_protected_difference": 0.0}
            for cidx in rng.choice(cand, size=min(PROBE_CUTS, len(cand)), replace=False):
                later = (day > day[cidx]) | ((day == day[cidx]) & ((ev != ev[cidx]) | (rn >= rn[cidx])))
                keep = (day < day[cidx]) | ((day == day[cidx]) & (ev == ev[cidx]) & (rn <= rn[cidx]))
                pert = base_rows.copy()
                x = pert[f"{s}_n"].to_numpy(dtype="float64").copy()
                dd = pert[f"{s}_d"].to_numpy(dtype="float64")
                lat_full = np.zeros(len(pert), dtype=bool)
                lat_full[td0["idx"]] = later
                draw = np.floor(rng.random(len(x)) * (np.nan_to_num(dd) + 1))
                pert[f"{s}_n"] = np.where(lat_full & np.isfinite(x), np.minimum(draw, np.nan_to_num(dd)), x)
                pert = B.F.prepare(pert)
                sa1 = B.stat_arrays(pert, means, (s,))
                td1 = tour_inputs_one(pert, sa1, typ, t, s)
                r1 = run(td1, s, c["h"], c["kappa"], c["tau"])
                got = np.column_stack([r1["O"], r1["D"]])
                # Stage 4's tolerance: the as-of sums subtract a round's total from a running total, so a redrawn value of
                # the cut's own round can move an earlier sum in its last bits (about 1e-17 here); a leak moves it by more
                diff = ~np.all(np.isclose(got, base, equal_nan=True, rtol=0, atol=PROBE_ATOL), axis=1)
                gap = np.where(keep[:, None] & np.isfinite(got) & np.isfinite(base), np.abs(got - base), 0.0)
                rec["cuts"] += 1
                rec["protected_rows_checked"] += int(keep.sum())
                rec["protected_rows_changed"] += int((diff & keep).sum())
                rec["later_rows_changed"] += int((diff & ~keep).sum())
                rec["largest_protected_difference"] = max(rec["largest_protected_difference"], float(gap.max()))
            out[f"{t}|{s}"] = rec
            B.log(f"  probe {t} {s}: {rec}")
    return out


def tour_inputs_one(rows: pd.DataFrame, sa: dict, typ: dict, tour: str, stat: str) -> dict:
    """tour_inputs for one statistic (the probe), with the event code."""
    idx = np.flatnonzero(rows["tour"].to_numpy() == tour)
    pid = pd.factorize(rows["pcode"].to_numpy()[idx])[0]
    a = sa[stat]
    return {"tour": tour, "idx": idx, "pid": pid.astype(np.int64), "n_players": int(pid.max()) + 1,
            "day": rows["day"].to_numpy()[idx].astype(np.int64), "ev": rows["ev"].to_numpy()[idx],
            "tournament_date": rows["tournament_date"].to_numpy()[idx],
            "tournament_id": rows["tournament_id"].to_numpy()[idx].astype(object),
            "round_order": rows["round_order"].to_numpy()[idx].astype(np.int64),
            "year": rows["year"].to_numpy()[idx], "evaluation": rows["evaluation"].to_numpy()[idx].astype(bool),
            "stats": {stat: {"ok": a["ok"][idx], "x": a["x"][idx], "d": a["d"][idx], "y": a["c"][idx],
                             "mu": a["mu_scale"][idx], "typ": typ[(stat, tour)]}}}


# ------------------------------------------------------------------------------------------------

def flatness(grid: pd.DataFrame, label: str = "extended") -> list[dict]:
    out = []
    for (t, s), g in grid.groupby(["tour", "stat"]):
        best = g["better_milli_per_unit"].max()
        rec = {"grid": label, "tour": t, "stat": s, "settings": int(len(g)), "best": float(best),
               "worst": float(g["better_milli_per_unit"].min()),
               "within_0_01": int((g["better_milli_per_unit"] >= best - 0.01).sum()),
               "within_0_1": int((g["better_milli_per_unit"] >= best - 0.1).sum()), "marginal": {}}
        for k in ("h", "kappa", "tau"):
            rec["marginal"][k] = {(hl_name(v) if k == "h" else f"{v:g}"): float(x)
                                  for v, x in g.groupby(k)["better_milli_per_unit"].max().items()}
        out.append(rec)
    return out


def main() -> int:
    t_start = time.time()
    timings = {}
    rows, _ = B.load_rows()
    means = B.surface_means()
    sa = B.stat_arrays(rows, means, IOS_STATS + ("rpw", "brk", "bp_conv", "rpw_first", "rpw_second"))
    typ = B.typical_units(rows, sa)
    inputs = {t: tour_inputs(rows, sa, typ, t) for t in C.TOURS}
    timings["setup"] = round(time.time() - t_start, 1)
    B.log("inputs ready")

    # ---------------------------------------------------------------- tuning: weekly snapshots, observations to 2018
    t0 = time.time()
    tasks = [(t, s, h, k, tau) for s in IOS_STATS for t in C.TOURS for h in HS for k in KAPPAS for tau in TAUS]
    recs = []
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker, initargs=(inputs,)) as ex:
        for i, r in enumerate(ex.map(tune_task, tasks, chunksize=1)):
            recs.extend(r)
            if (i + 1) % 40 == 0:
                B.log(f"  tuned {i + 1} of {len(tasks)}")
    grid = pd.DataFrame(recs)
    grid["in_brief_grid"] = grid["h"].isin(BRIEF_GRID["h"]) & grid["kappa"].isin(BRIEF_GRID["kappa"])
    timings["tuning"] = round(time.time() - t0, 1)
    chosen, brief = {}, {}
    grid["chosen"] = False
    grid["chosen_in_brief_grid"] = False
    for (t, s), g in grid.groupby(["tour", "stat"]):
        b = g.loc[g["better_milli_per_unit"].idxmax()]
        gb = g[g["in_brief_grid"]]
        bb = gb.loc[gb["better_milli_per_unit"].idxmax()]
        grid.loc[b.name, "chosen"] = True
        grid.loc[bb.name, "chosen_in_brief_grid"] = True
        chosen[(t, s)] = {"h": float(b["h"]), "kappa": float(b["kappa"]), "tau": int(b["tau"]),
                          "tuning_better_milli_per_unit": float(b["better_milli_per_unit"])}
        brief[(t, s)] = {"h": float(bb["h"]), "kappa": float(bb["kappa"]), "tau": int(bb["tau"]),
                         "tuning_better_milli_per_unit": float(bb["better_milli_per_unit"])}
        B.log(f"  chosen {t} {s}: h {hl_name(b['h'])}, kappa {b['kappa']:g}, tau {int(b['tau'])} "
              f"({b['better_milli_per_unit']:.3f} milli per unit); the Brief's grid: h {hl_name(bb['h'])}, kappa "
              f"{bb['kappa']:g}, tau {int(bb['tau'])} ({bb['better_milli_per_unit']:.3f})")
    grid.to_csv(IOS_TUNING, index=False)

    # ---------------------------------------------------------------- the frozen constants on weekly snapshots
    t0 = time.time()
    ftasks = [(t, s, chosen[(t, s)]["h"], chosen[(t, s)]["kappa"], chosen[(t, s)]["tau"]) for s in IOS_STATS for t in C.TOURS]
    finals = {}
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker, initargs=(inputs,)) as ex:
        for r in ex.map(final_task, ftasks, chunksize=1):
            finals[(r["tour"], r["stat"])] = r
            B.log(f"  weekly {r['tour']} {r['stat']}: {r['seconds']}s, mean PCG iterations "
                  f"{r['solver']['iterations_mean']:.1f}, not converged {r['solver']['not_converged']}")
    timings["weekly_runs"] = round(time.time() - t0, 1)
    ios = {}
    for s in IOS_STATS:
        O, D = np.full(len(rows), np.nan), np.full(len(rows), np.nan)
        Os, Ds = np.full(len(rows), np.nan), np.full(len(rows), np.nan)
        for t in C.TOURS:
            idx = inputs[t]["idx"]
            r = finals[(t, s)]
            O[idx], D[idx], Os[idx], Ds[idx] = r["O"], r["D"], r["O_snap"], r["D_snap"]
        ios[s] = {"O": O, "D": D, "O_snap": Os, "D_snap": Ds}
    A = np.arange(0, len(rows), 2)
    tab = pd.DataFrame({"match_id": rows["match_id"].to_numpy()[A], "tour": rows["tour"].to_numpy()[A],
                        "year": rows["year"].to_numpy()[A]})
    for s in IOS_STATS:
        for side, off in (("a", 0), ("b", 1)):
            tab[f"O_{s}_{side}"] = ios[s]["O"][A + off].astype("float32")
            tab[f"D_{s}_{side}"] = ios[s]["D"][A + off].astype("float32")
    tab.to_parquet(IOS_PARQUET, index=False, compression="zstd")
    feats = features(rows, sa, ios, means)
    # diagnostics: the points matchup with a shorter memory or a heavier ridge than the statistic's tuning chose, to see
    # whether the winner's signal and the statistic's forecast want different constants (scored in the rundown)
    t0 = time.time()
    dtasks, dmeta = [], []
    for label, over in DIAGNOSTICS:
        for t in C.TOURS:
            c = {**chosen[(t, "spw")], **over}
            dtasks.append((t, "spw", c["h"], c["kappa"], c["tau"]))
            dmeta.append((label, t, c))
    diag_scores = []
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker, initargs=(inputs,)) as ex:
        dres = list(ex.map(final_task, dtasks, chunksize=1))
    for label, _ in DIAGNOSTICS:
        O, D = np.full(len(rows), np.nan), np.full(len(rows), np.nan)
        for (lab, t, c), r in zip(dmeta, dres):
            if lab != label:
                continue
            idx = inputs[t]["idx"]
            O[idx], D[idx] = r["O"], r["D"]
            diag_scores.append({"diagnostic": label, "tour": t, "h": c["h"], "kappa": c["kappa"], "tau": c["tau"],
                                **{f"spw_{w}": v["incremental"]["better_milli_per_unit"] for w, v in r["scores"].items()}})
        feats[f"ios_matchup_points|diagnostic: {label}"] = matchup_points(rows, sa, O, D)
    timings["diagnostics"] = round(time.time() - t0, 1)
    pool = H.load_pool()
    Ap, _ = B.pool_rows(rows)
    assert (pool["match_id"].to_numpy() == rows["match_id"].to_numpy()[Ap]).all()
    fr = pd.DataFrame({"match_id": pool["match_id"].to_numpy()})
    for k, v in feats.items():
        fr[k] = np.asarray(v, dtype="float32")
    fr.to_parquet(IOS_FEATURES, index=False, compression="zstd")
    B.log(f"wrote {IOS_PARQUET.name} and {IOS_FEATURES.name}")

    comp = stage3_comparison(rows, sa, ios["spw"])
    for c in comp:
        B.log(f"  spw beside Stage 3, {c['tour']} {c['window']}: IOS {c['ios_better_milli_per_point']:.3f}, Stage 3 "
              f"{c['stage3_better_milli_per_point']:.3f} milli per point (same set: {c['same_set']})")

    t0 = time.time()
    pr = probe(rows, means, typ, chosen)
    timings["probe"] = round(time.time() - t0, 1)
    timings["total"] = round(time.time() - t_start, 1)

    out_scores = []
    for (t, s), r in finals.items():
        for w, v in r["scores"].items():
            for kind, sc in v.items():
                out_scores.append({"tour": t, "stat": s, "window": w, "kind": kind, **sc})
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "settings": {"stats": list(IOS_STATS), "h": [hl_name(h) for h in HS], "kappa": list(KAPPAS), "tau": list(TAUS),
                     "tuning_snapshots_days": BLOCK_DAYS, "tune_window": [TUNE_FROM, TUNE_TO], "rtol": RTOL,
                     "max_iter": MAX_ITER, "return_of": RETURN_OF},
        "chosen": [{"tour": t, "stat": s, **c} for (t, s), c in chosen.items()],
        "brief_grid_choice": [{"tour": t, "stat": s, **c} for (t, s), c in brief.items()],
        "brief_grid": {"h": [hl_name(h) for h in BRIEF_GRID["h"]], "kappa": list(BRIEF_GRID["kappa"])},
        "typical_units": [{"stat": s, "tour": t, "units": typ[(s, t)]} for s in IOS_STATS for t in C.TOURS],
        "flatness": flatness(grid) + flatness(grid[grid["in_brief_grid"]], "brief"),
        "scores": out_scores,
        "stage3_comparison": comp,
        "diagnostics": diag_scores,
        "solver": [{"tour": t, "stat": s, **r["solver"], "seconds": r["seconds"]} for (t, s), r in finals.items()],
        "tuning_seconds": {"mean": float(grid["seconds"].mean()), "max": float(grid["seconds"].max())},
        "probe": pr,
        "seconds": timings,
    }
    B.jdump(summary, IOS_SUMMARY)
    B.log(f"wrote {IOS_TUNING.name}, {IOS_SUMMARY.name}; total {timings['total']:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
