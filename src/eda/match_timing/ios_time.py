"""IOS ridge ratings on a leak-proof timeline (the match-timing study).

Stage B's solver (src/eda/ufc_ideas/stageB_ios.py) released every observation whose tournament START week preceded the
snapshot, so the late rounds of a two-week event entered the ratings of an event that started during its second week,
days before they were played. Here each observation has

    release day  = its latest possible finish + 1   (the first day the result surely exists)
    query day    = its earliest possible start      (the solve a match's own forecast reads)
    obs day      = its best-estimate day            (the age used by the time decay)

and a snapshot on day S solves the same ridge system over the observations released on or before S. So a result can
reach another match's ratings only if it surely finished before that match could start.

The incremental step then adds, to each player's own O and D, his own earlier matches that the snapshot does not hold
yet (same-event earlier rounds, and earlier events whose window has not closed), every other rating held at the
snapshot, exactly as Stage B's step did for same-event rounds. A player's own sequence is real (nobody plays two events
at once), so these are always earlier: earlier tournament weeks, or earlier rounds of the same event. Other events of the
same week and other matches of the same round are never added.

The ratings are otherwise Stage B's: y = logit((x + 1/2)/(d + 1)) - logit(mu) ~ O_server - D_returner, weights
2^(-age/h) (d/d_typical)^tau, ridge kappa, Jacobi-preconditioned conjugate gradient warm-started day to day.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from src.eda.match_timing import common as MT  # noqa: F401  (sets sys.path)
from src.eda.ufc_ideas import stageB_common as B
from src.eda.ufc_ideas import stageB_ios as I

LOOKBACK = 24       # own earlier matches examined for the incremental step (a window never spans more)


class TimedSystem:
    """One statistic's observations on one tour, sorted by release day, with the server-by-returner pattern."""

    def __init__(self, td: dict, stat: str, release: np.ndarray, obs: np.ndarray):
        st = td["stats"][stat]
        k = np.flatnonzero(st["ok"] & np.isfinite(release) & np.isfinite(obs))
        k = k[np.argsort(release[k], kind="stable")]
        n = td["n_players"]
        self.rows, self.n = k, n
        self.srv, self.ret = td["pid"][k], td["pid"][k ^ 1]
        self.y, self.d = st["y"][k], st["d"][k]
        self.release, self.obs = release[k].astype(np.int64), obs[k].astype(np.float64)
        self.typ = st["typ"]
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


def snapshots(sysm: TimedSystem, days: np.ndarray, h: float, kappa: float, tau: int):
    """Yield (i, O, D, P, Q, iterations, converged) for each snapshot day (ascending), each solved over the
    observations released on or before that day."""
    n, ref = sysm.n, float(B.REF_DAY)
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    w0 = (sysm.d / sysm.typ) ** tau if tau else np.ones(len(sysm.d))
    ws = w0 * np.exp2((sysm.obs - ref) * lam)
    Pc, Qc, bOc, bDc = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    PWc = np.zeros(sysm.n_pairs)
    ptr, x = 0, np.zeros(2 * n)
    W, WT = sysm.W, sysm.WT
    for i, S in enumerate(days):
        new = int(np.searchsorted(sysm.release, S, side="right"))
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

        def matvec(v, dO=dO, dD=dD):
            o, dd = v[:n], v[n:]
            return np.concatenate([dO * o - W @ dd, dD * dd - WT @ o])
        b = np.concatenate([bOc * g, bDc * g])
        x, it, conv = I.pcg(matvec, np.concatenate([dO, dD]), b, x)
        yield i, x[:n], x[n:], P, Q, it, conv


def own_order(td: dict) -> np.ndarray:
    """Positions of the tour's rows sorted by player, then tournament week, event and round: each player's sequence."""
    return np.lexsort((td["round_order"], td["ev"], td["day"], td["pid"]))


def run_timed(td: dict, stat: str, h: float, kappa: float, tau: int, es: np.ndarray, lf: np.ndarray,
              obs: np.ndarray, lookback: int = LOOKBACK) -> dict:
    """Pre-match O and D of every row of one tour for one statistic, on the leak-proof timeline.

    es, lf, obs: per row of ``td`` (both rows of a match share them): earliest possible start, latest possible finish
    and best-estimate day of the match, integer days. Returns O, D (with the incremental step), the snapshot values and
    solver statistics."""
    release = np.where(np.isfinite(lf), lf + 1, np.nan)
    query = es.astype(np.float64)
    if np.any(release <= query):
        # an inverted window (latest finish before earliest start) would put a match's own result into its own ratings
        raise ValueError("a match's latest possible finish precedes its earliest possible start")
    sysm = TimedSystem(td, stat, release, obs)
    nr = len(td["pid"])
    pid = td["pid"]
    days, ginv = np.unique(query, return_inverse=True)
    order = np.argsort(ginv, kind="stable")
    bounds = np.r_[0, np.cumsum(np.bincount(ginv, minlength=len(days)))]
    Os, Ds, Ps, Qs = (np.full(nr, np.nan) for _ in range(4))
    its, nonconv = [], 0
    for i, O, D, P, Q, it, conv in snapshots(sysm, days, h, kappa, tau):
        r = order[bounds[i]:bounds[i + 1]]
        p = pid[r]
        Os[r], Ds[r], Ps[r], Qs[r] = O[p], D[p], P[p], Q[p]
        its.append(it)
        nonconv += int(not conv)

    # the incremental step over each player's own unreleased earlier matches
    st = td["stats"][stat]
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    ok = st["ok"] & np.isfinite(release)
    w0 = np.where(ok, (st["d"] / st["typ"]) ** tau if tau else 1.0, 0.0)
    opp = np.arange(nr) ^ 1
    okr, w0r = ok[opp], w0[opp]
    y, yr = st["y"], st["y"][opp]
    Dopp, Oopp = np.nan_to_num(Ds[opp]), np.nan_to_num(Os[opp])
    seq = own_order(td)
    sp_ = pid[seq]
    day, ev, rn = td["day"][seq], td["ev"][seq], td["round_order"][seq]
    rel_s, q_s, obs_s = release[seq], query[seq], obs[seq]
    G = np.zeros((nr, 4))
    gaps = np.zeros(nr, dtype=np.int64)
    for k in range(1, lookback + 1):
        tgt = np.arange(k, nr)                  # a row, at its position in the players' sequences
        src = tgt - k                           # the row k places earlier in the sequence
        same = sp_[src] == sp_[tgt]
        precedes = (day[src] < day[tgt]) | ((ev[src] == ev[tgt]) & (rn[src] < rn[tgt]))
        unreleased = rel_s[src] > q_s[tgt]
        use = same & precedes & unreleased
        if not use.any():
            if not same.any():
                break
            continue
        tg, sr = seq[tgt[use]], seq[src[use]]
        age = np.maximum(q_s[tgt[use]] - obs_s[src[use]], 0.0)
        e = np.exp2(-age * lam)
        G[tg, 0] += np.where(ok[sr], w0[sr] * e, 0.0)
        G[tg, 1] += np.where(ok[sr], w0[sr] * e * (y[sr] + Dopp[sr]), 0.0)
        G[tg, 2] += np.where(okr[sr], w0r[sr] * e, 0.0)
        G[tg, 3] += np.where(okr[sr], w0r[sr] * e * (Oopp[sr] - yr[sr]), 0.0)
        gaps[tg] += 1
    O1 = ((Ps + kappa) * Os + G[:, 1]) / (Ps + kappa + G[:, 0])
    D1 = ((Qs + kappa) * Ds + G[:, 3]) / (Qs + kappa + G[:, 2])
    return {"O_snap": Os, "D_snap": Ds, "O": O1, "D": D1, "gap_matches": gaps,
            "solver": {"snapshots": int(len(days)), "observations": int(len(sysm.y)), "pairs": int(sysm.n_pairs),
                       "players": int(sysm.n), "iterations_mean": float(np.mean(its)) if its else 0.0,
                       "iterations_max": int(np.max(its)) if its else 0, "not_converged": nonconv,
                       "rows_with_incremental_gap": int((gaps > 0).sum())}}


def tour_inputs(rows: pd.DataFrame, sa: dict, typ: dict, tour: str, stats) -> dict:
    """Stage B's per-tour arrays for the requested statistics, with the event code (the incremental step's key)."""
    idx = np.flatnonzero(rows["tour"].to_numpy() == tour)
    mid = rows["match_id"].to_numpy()
    assert len(idx) % 2 == 0 and (mid[idx[0::2]] == mid[idx[1::2]]).all()
    pid = pd.factorize(rows["pcode"].to_numpy()[idx])[0]
    d = {"tour": tour, "idx": idx, "pid": pid.astype(np.int64), "n_players": int(pid.max()) + 1,
         "day": rows["day"].to_numpy()[idx].astype(np.int64), "ev": rows["ev"].to_numpy()[idx].astype(np.int64),
         "round_order": rows["round_order"].to_numpy()[idx].astype(np.int64), "stats": {}}
    for s in stats:
        a = sa[s]
        d["stats"][s] = {"ok": a["ok"][idx], "x": a["x"][idx], "d": a["d"][idx], "y": a["c"][idx],
                         "mu": a["mu_scale"][idx], "typ": typ[(s, tour)]}
    return d
