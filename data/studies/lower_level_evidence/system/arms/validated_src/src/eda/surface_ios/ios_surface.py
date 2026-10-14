"""Leak-proof IOS ratings with player-by-surface deviations (the surface-IOS study).

The model, per statistic and tour (Stage B's IOS, src/eda/ufc_ideas/stageB_ios.py, on the leak-proof timeline of
src/eda/match_timing/ios_time.py), now with a surface term for every player:

    y_k = O_a + E_a,s - D_b - F_b,s + noise          a the server, b the returner, s the match's surface

    minimise  sum_k w_k (y_k - O_a - E_a,s + D_b + F_b,s)^2 + kappa (|O|^2 + |D|^2) + kappa_s (|E|^2 + |F|^2)

w_k = 2^(-age/h) (d_k/d_typical)^tau as in Stage B. kappa_s shrinks every surface value towards the player's
all-surface value: it is the Gaussian-prior (random-effects) reading of "a player's level on clay is their overall level
plus a deviation that needs evidence". kappa_s = inf gives E = F = 0 and the existing pooled IOS exactly. A surface of 0
(unknown) gets no deviation term.

Timeline (ios_time's two-time rule, unchanged): a result enters the solve on the day after its latest possible finish;
a match reads the solve of its earliest possible start; the time decay uses the best-estimate day. Each player's own
earlier matches that the snapshot does not hold yet are then added to their own block (O, E_1..E_4 or D, F_1..F_4), every
other player held at the snapshot: an exact re-solve of the player's block, which reduces to ios_time's incremental
step when kappa_s = inf.

The normal equations are solved by conjugate gradients with a block preconditioner: each player's (O, E_1..E_4) block
is an arrowhead matrix [[P + kappa, P_s], [P_s, diag(P_s + kappa_s)]] (P_s the player's serve weight on surface s),
inverted exactly; likewise (D, F). The cross-player coupling goes through one sparse matrix per surface, W_s (the
server-by-returner weights of the matches on s), whose product with (D + F_s) gives both W_s D and W_s F_s.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from src.eda.surface_ios import common as C  # noqa: F401  (sets sys.path)
from src.eda.ufc_ideas import stageB_common as B

S = C.N_SURF                 # surfaces with a deviation term: codes 1..S; code 0 (unknown) has none
LOOKBACK = 24                # own earlier matches examined for the incremental step (as ios_time)
RTOL = 1e-8
MAX_ITER = 2000
OFF = 1e12                   # a one-sided "no deviation" penalty (E or F held at ~1e-12 of the data's scale)


def split_kappa(kappa_s) -> tuple[float, float, bool]:
    """kappa_s is one penalty for both the serve (E) and return (F) deviations, or a pair (kappa_E, kappa_F). Returns
    (kappa_E, kappa_F, surface_terms); an infinite side of a pair becomes OFF, both infinite means the pooled IOS."""
    if isinstance(kappa_s, (tuple, list)):
        kE, kF = (float(v) for v in kappa_s)
        if not np.isfinite(kE) and not np.isfinite(kF):
            return np.inf, np.inf, False
        return (kE if np.isfinite(kE) else OFF), (kF if np.isfinite(kF) else OFF), True
    k = float(kappa_s)
    return k, k, bool(np.isfinite(k))


def arrow_solve(alpha, c, d, r0, r):
    """Solve, row by row, [[alpha, c^T], [c, diag(d)]] [x0; x] = [r0; r] (alpha, r0: (m,); c, d, r: (m, S)).
    d may hold inf (no deviation term): its x is 0."""
    with np.errstate(invalid="ignore", divide="ignore"):
        inv = np.where(np.isfinite(d), 1.0 / d, 0.0)
    schur = alpha - (c * c * inv).sum(axis=1)
    x0 = (r0 - (c * r * inv).sum(axis=1)) / schur
    x = (r - c * x0[:, None]) * inv
    return x0, x


class Arrow:
    """arrow_solve factored once for repeated right-hand sides, in the surface-major layout: c, d are (S, m)."""

    def __init__(self, alpha: np.ndarray, c: np.ndarray, d: np.ndarray):
        self.c = c
        self.inv = 1.0 / d
        self.ci = c * self.inv
        self.schur_inv = 1.0 / (alpha - (c * self.ci).sum(axis=0))

    def solve(self, r0: np.ndarray, r: np.ndarray):
        x0 = (r0 - (self.ci * r).sum(axis=0)) * self.schur_inv
        return x0, r * self.inv - self.ci * x0


def pcg_block(matvec, precond, b: np.ndarray, x0: np.ndarray, rtol: float = RTOL, max_iter: int = MAX_ITER):
    """Preconditioned conjugate gradient (stageB_ios.pcg with a general preconditioner). Returns (x, iterations,
    converged)."""
    x = x0.copy()
    r = b - matvec(x)
    bn = float(np.linalg.norm(b))
    if bn == 0.0:
        return np.zeros_like(b), 0, True
    z = precond(r)
    p = z.copy()
    rz = float(r @ z)
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
        z = precond(r)
        rz_new = float(r @ z)
        if rz <= 0.0:
            break
        p = z + (rz_new / rz) * p
        rz = rz_new
    return x, max_iter, bool(float(np.linalg.norm(r)) <= rtol * bn)


class SurfaceSystem:
    """One statistic's observations on one tour, sorted by release day, with the (server, returner, surface) pattern:
    one CSR matrix per surface code 0..S (fixed sparsity; values refreshed at each snapshot) and its transpose."""

    def __init__(self, td: dict, stat: str, release: np.ndarray, obs: np.ndarray, typ: float):
        st = td["stats"][stat]
        k = np.flatnonzero(st["ok"] & np.isfinite(release) & np.isfinite(obs))
        k = k[np.argsort(release[k], kind="stable")]
        # only players in some observation enter the system: anyone else has no data, so their ratings are exactly 0
        srv_full, ret_full = td["pid"][k], td["pid"][k ^ 1]
        self.active = np.unique(np.r_[srv_full, ret_full])
        self.n_full = int(td["n_players"])
        self.cmap = np.full(self.n_full, -1, dtype=np.int64)
        self.cmap[self.active] = np.arange(len(self.active))
        n = len(self.active)
        self.n = n
        self.srv, self.ret = self.cmap[srv_full], self.cmap[ret_full]
        self.surf = td["surf"][k].astype(np.int64)
        if (self.surf < 0).any() or (self.surf > S).any():
            raise ValueError("surface codes must be 0..S")
        self.y, self.d = st["y"][k], st["d"][k]
        self.release, self.obs = release[k].astype(np.int64), obs[k].astype(np.float64)
        self.typ = typ
        key = (self.srv * n + self.ret) * (S + 1) + self.surf
        uniq, self.triple = np.unique(key, return_inverse=True)
        self.n_triples = len(uniq)
        ts = uniq % (S + 1)
        pr = (uniq // (S + 1)) % n
        ps = (uniq // (S + 1)) // n
        self.W, self.WT, self.slot = [], [], []
        for s in range(S + 1):
            m = np.flatnonzero(ts == s)                 # triples of surface s (uniq order: server-major)
            a, b = ps[m], pr[m]
            indptr = np.r_[0, np.cumsum(np.bincount(a, minlength=n))]
            W = sp.csr_matrix((np.zeros(len(m)), b.astype(np.int32), indptr.astype(np.int64)), shape=(n, n))
            perm = np.lexsort((a, b))
            indptr_t = np.r_[0, np.cumsum(np.bincount(b, minlength=n))]
            WT = sp.csr_matrix((np.zeros(len(m)), a[perm].astype(np.int32), indptr_t.astype(np.int64)), shape=(n, n))
            self.W.append(W)
            self.WT.append((WT, perm))
            self.slot.append(m)


def snapshots(sysm: SurfaceSystem, days: np.ndarray, h: float, kappa: float, kappa_s: float, tau: int):
    """Yield (i, O, D, E, F, P, Q, Ps, Qs, iterations, converged) for each snapshot day (ascending), each solved over
    the observations released on or before that day. E, F, Ps, Qs are (n, S) for surfaces 1..S."""
    n, ref = sysm.n, float(B.REF_DAY)
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    w0 = (sysm.d / sysm.typ) ** tau if tau else np.ones(len(sysm.d))
    ws = w0 * np.exp2((sysm.obs - ref) * lam)
    kE, kF, surface_terms = split_kappa(kappa_s)
    Pc, Qc, bOc, bDc = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    Psc, Qsc, bEc, bFc = (np.zeros((S + 1, n)) for _ in range(4))       # surface-major
    TWc = np.zeros(sysm.n_triples)
    ptr = 0
    nS = n * S
    nv = 2 * n + 2 * nS if surface_terms else 2 * n
    x = np.zeros(nv)
    for i, Sday in enumerate(days):
        new = int(np.searchsorted(sysm.release, Sday, side="right"))
        if new > ptr:
            sl = slice(ptr, new)
            srv, ret, sf, w = sysm.srv[sl], sysm.ret[sl], sysm.surf[sl], ws[sl]
            wy = w * sysm.y[sl]
            Pc += np.bincount(srv, weights=w, minlength=n)
            Qc += np.bincount(ret, weights=w, minlength=n)
            bOc += np.bincount(srv, weights=wy, minlength=n)
            bDc -= np.bincount(ret, weights=wy, minlength=n)
            if surface_terms:
                np.add.at(Psc, (sf, srv), w)
                np.add.at(Qsc, (sf, ret), w)
                np.add.at(bEc, (sf, srv), wy)
                np.add.at(bFc, (sf, ret), -wy)
            TWc += np.bincount(sysm.triple[sl], weights=w, minlength=sysm.n_triples)
            ptr = new
        g = np.exp2(-(Sday - ref) * lam)
        P, Q = Pc * g, Qc * g
        Ws, WTs = [], []
        for s in range(S + 1):
            W = sysm.W[s]
            W.data[:] = TWc[sysm.slot[s]] * g
            WT, perm = sysm.WT[s]
            WT.data[:] = W.data[perm]
            Ws.append(W)
            WTs.append(WT)
        if not surface_terms:
            dO, dD = P + kappa, Q + kappa

            def matvec(v, dO=dO, dD=dD, Ws=Ws, WTs=WTs):
                o, dd = v[:n], v[n:]
                return np.concatenate([dO * o - sum(W @ dd for W in Ws), dD * dd - sum(WT @ o for WT in WTs)])
            diag = np.concatenate([dO, dD])
            b = np.concatenate([bOc * g, bDc * g])
            x, it, conv = pcg_block(matvec, lambda r, diag=diag: r / diag, b, x)
            zero = np.zeros((n, S))
            yield i, x[:n], x[n:], zero, zero, P, Q, zero, zero, it, conv
            continue
        Ps, Qs = Psc[1:] * g, Qsc[1:] * g                # (S, n): surfaces 1..S, surface-major
        aO, aD = P + kappa, Q + kappa
        dE, dF = Ps + kE, Qs + kF
        AO, AD = Arrow(aO, Ps, dE), Arrow(aD, Qs, dF)
        o_, d_, e_, f_ = slice(0, n), slice(n, 2 * n), slice(2 * n, 2 * n + nS), slice(2 * n + nS, nv)

        def matvec(v, aO=aO, aD=aD, dE=dE, dF=dF, Ps=Ps, Qs=Qs, Ws=Ws, WTs=WTs):
            O, D = v[o_], v[d_]
            E, F = v[e_].reshape(S, n), v[f_].reshape(S, n)
            gs = np.empty((S, n))
            hs = np.empty((S, n))
            for s in range(S):
                gs[s] = Ws[s + 1] @ (D + F[s])
                hs[s] = WTs[s + 1] @ (O + E[s])
            out = np.empty(nv)
            out[o_] = aO * O + (Ps * E).sum(axis=0) - Ws[0] @ D - gs.sum(axis=0)
            out[d_] = aD * D + (Qs * F).sum(axis=0) - WTs[0] @ O - hs.sum(axis=0)
            out[e_] = (Ps * O + dE * E - gs).reshape(-1)
            out[f_] = (Qs * D + dF * F - hs).reshape(-1)
            return out

        def precond(r, AO=AO, AD=AD):
            out = np.empty(nv)
            x0, xs = AO.solve(r[o_], r[e_].reshape(S, n))
            out[o_], out[e_] = x0, xs.reshape(-1)
            x0, xs = AD.solve(r[d_], r[f_].reshape(S, n))
            out[d_], out[f_] = x0, xs.reshape(-1)
            return out
        b = np.concatenate([bOc * g, bDc * g, (bEc[1:] * g).reshape(-1), (bFc[1:] * g).reshape(-1)])
        x, it, conv = pcg_block(matvec, precond, b, x)
        yield (i, x[o_], x[d_], x[e_].reshape(S, n).T, x[f_].reshape(S, n).T, P, Q, Ps.T, Qs.T, it, conv)


def own_order(td: dict) -> np.ndarray:
    """Positions of the tour's rows sorted by player, then tournament week, event and round: each player's sequence."""
    return np.lexsort((td["round_order"], td["ev"], td["day"], td["pid"]))


def run(td: dict, stat: str, h: float, kappa: float, kappa_s: float, tau: int, typ: float,
        until_day: int | None = None, lookback: int = LOOKBACK) -> dict:
    """Pre-match ratings of every row of one tour for one statistic on the leak-proof timeline.

    Returns, per row (NaN where the row's query day lies after ``until_day``): the effective serve and return ratings
    on the match's own surface after the incremental step (O_eff = O + E_s, D_eff = D + F_s), their all-surface parts
    (O, D) and surface parts (E_s, F_s), and the snapshot values before the incremental step; plus solver statistics."""
    es, lf, obs = td["es"], td["lf"], td["obs"]
    release = np.where(np.isfinite(lf), lf + 1, np.nan)
    query = es.astype(np.float64)
    if np.any(release <= query):
        raise ValueError("a match's latest possible finish precedes its earliest possible start")
    sysm = SurfaceSystem(td, stat, release, obs, typ)
    nr = len(td["pid"])
    pid, surf = td["pid"], td["surf"].astype(np.int64)
    cp = sysm.cmap[pid]
    cp = np.where(cp >= 0, cp, sysm.n)                    # a player outside the system reads the zero row appended
    in_range = np.ones(nr, dtype=bool) if until_day is None else (query <= until_day)
    days, ginv = np.unique(query[in_range], return_inverse=True)
    rows_in = np.flatnonzero(in_range)
    order = np.argsort(ginv, kind="stable")
    bounds = np.r_[0, np.cumsum(np.bincount(ginv, minlength=len(days)))]
    O_s, D_s, P_s, Q_s = (np.full(nr, np.nan) for _ in range(4))
    E_all, F_all, PS_all, QS_all = (np.full((nr, S), np.nan) for _ in range(4))
    its, nonconv = [], 0
    z1, zS = np.zeros(1), np.zeros((1, S))
    for i, O, D, E, F, P, Q, Ps, Qs, it, conv in snapshots(sysm, days, h, kappa, kappa_s, tau):
        r = rows_in[order[bounds[i]:bounds[i + 1]]]
        p = cp[r]
        O_s[r], D_s[r] = np.r_[O, z1][p], np.r_[D, z1][p]
        P_s[r], Q_s[r] = np.r_[P, z1][p], np.r_[Q, z1][p]
        E_all[r], F_all[r] = np.vstack([E, zS])[p], np.vstack([F, zS])[p]
        PS_all[r], QS_all[r] = np.vstack([Ps, zS])[p], np.vstack([Qs, zS])[p]
        its.append(it)
        nonconv += int(not conv)

    # each row's own-surface snapshot deviation (0 for an unknown surface)
    sidx = np.clip(surf - 1, 0, S - 1)
    known = surf >= 1
    E_row = np.where(known, E_all[np.arange(nr), sidx], 0.0)
    F_row = np.where(known, F_all[np.arange(nr), sidx], 0.0)

    # the incremental step over each player's own unreleased earlier matches, every other rating held at the snapshot
    st = td["stats"][stat]
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    ok = st["ok"] & np.isfinite(release)
    w0 = np.where(ok, (st["d"] / typ) ** tau if tau else 1.0, 0.0)
    opp = np.arange(nr) ^ 1
    okr, w0r = ok[opp], w0[opp]
    y, yr = st["y"], st["y"][opp]
    # the opponent's effective rating on the gap match's own surface, at the gap match's own snapshot
    Dopp = np.nan_to_num(D_s[opp] + F_row[opp])
    Oopp = np.nan_to_num(O_s[opp] + E_row[opp])
    seq = own_order(td)
    sp_ = pid[seq]
    day, ev, rn = td["day"][seq], td["ev"][seq], td["round_order"][seq]
    rel_s, q_s, obs_s = release[seq], query[seq], obs[seq]
    GO, GOy, GD, GDy = (np.zeros((nr, S + 1)) for _ in range(4))
    gaps = np.zeros(nr, dtype=np.int64)
    for k in range(1, lookback + 1):
        tgt = np.arange(k, nr)
        src = tgt - k
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
        sg = surf[sr]
        # within one k each target row appears once, so the fancy-index updates have no duplicates
        GO[tg, sg] += np.where(ok[sr], w0[sr] * e, 0.0)
        GOy[tg, sg] += np.where(ok[sr], w0[sr] * e * (y[sr] + Dopp[sr]), 0.0)
        GD[tg, sg] += np.where(okr[sr], w0r[sr] * e, 0.0)
        GDy[tg, sg] += np.where(okr[sr], w0r[sr] * e * (Oopp[sr] - yr[sr]), 0.0)
        gaps[tg] += 1
    kE, kF, surface_terms = split_kappa(kappa_s)
    if surface_terms:
        E_snap = np.nan_to_num(E_all)
        F_snap = np.nan_to_num(F_all)
        PSn, QSn = np.nan_to_num(PS_all), np.nan_to_num(QS_all)
        aO = P_s + kappa
        aD = Q_s + kappa
        rO = aO * O_s + (PSn * E_snap).sum(axis=1) + GOy.sum(axis=1)
        rE = PSn * O_s[:, None] + (PSn + kE) * E_snap + GOy[:, 1:]
        O1, E1 = arrow_solve(aO + GO.sum(axis=1), PSn + GO[:, 1:], PSn + kE + GO[:, 1:], rO, rE)
        rD = aD * D_s + (QSn * F_snap).sum(axis=1) + GDy.sum(axis=1)
        rF = QSn * D_s[:, None] + (QSn + kF) * F_snap + GDy[:, 1:]
        D1, F1 = arrow_solve(aD + GD.sum(axis=1), QSn + GD[:, 1:], QSn + kF + GD[:, 1:], rD, rF)
        E1_row = np.where(known, E1[np.arange(nr), sidx], 0.0)
        F1_row = np.where(known, F1[np.arange(nr), sidx], 0.0)
    else:
        O1 = ((P_s + kappa) * O_s + GOy.sum(axis=1)) / (P_s + kappa + GO.sum(axis=1))
        D1 = ((Q_s + kappa) * D_s + GDy.sum(axis=1)) / (Q_s + kappa + GD.sum(axis=1))
        E1_row = np.zeros(nr)
        F1_row = np.zeros(nr)
        E1 = F1 = None
    out = {"O_eff": O1 + E1_row, "D_eff": D1 + F1_row, "O": O1, "D": D1, "E": E1_row, "F": F1_row,
           "O_snap": O_s, "D_snap": D_s, "E_snap": E_row, "F_snap": F_row, "gap_matches": gaps,
           "P": P_s, "Q": Q_s, "P_surf": np.where(known, np.nan_to_num(PS_all)[np.arange(nr), sidx], 0.0),
           "Q_surf": np.where(known, np.nan_to_num(QS_all)[np.arange(nr), sidx], 0.0),
           "solver": {"snapshots": int(len(days)), "observations": int(len(sysm.y)), "triples": int(sysm.n_triples),
                      "players": int(sysm.n), "players_in_history": int(sysm.n_full),
                      "iterations_mean": float(np.mean(its)) if its else 0.0,
                      "iterations_max": int(np.max(its)) if its else 0, "not_converged": nonconv,
                      "rows_with_incremental_gap": int((gaps > 0).sum())}}
    if E1 is not None:
        out["E_all"], out["F_all"] = E1, F1          # every surface's deviation after the incremental step (n, S)
    if until_day is not None:
        for k_ in ("O_eff", "D_eff", "O", "D", "E", "F", "O_snap", "D_snap", "E_snap", "F_snap", "P", "Q", "P_surf",
                   "Q_surf"):
            out[k_] = np.where(in_range, out[k_], np.nan)
    return out


def row_logloss(td: dict, stat: str, res: dict) -> tuple[np.ndarray, np.ndarray]:
    """Per row (the server's match): the binomial log loss of the statistic at expit(mu + O_eff,server -
    D_eff,returner), and at the tour's surface average alone; NaN where the row has no box score or no rating."""
    st = td["stats"][stat]
    nr = len(td["pid"])
    opp = np.arange(nr) ^ 1
    O, D = res["O_eff"], res["D_eff"][opp]
    x, d, mu = st["x"], st["d"], st["mu"]
    with np.errstate(invalid="ignore", over="ignore"):
        p = np.clip(1.0 / (1.0 + np.exp(-(mu + O - D))), 1e-12, 1 - 1e-12)
        p0 = np.clip(1.0 / (1.0 + np.exp(-mu)), 1e-12, 1 - 1e-12)
        ll = -(x * np.log(p) + (d - x) * np.log(1 - p))
        ll0 = -(x * np.log(p0) + (d - x) * np.log(1 - p0))
    ok = st["ok"] & np.isfinite(ll)
    return np.where(ok, ll, np.nan), np.where(ok, ll0, np.nan)


def score(td: dict, stat: str, res: dict, years, sel_extra: np.ndarray | None = None, by_surface: bool = True) -> dict:
    """Log loss per unit of the statistic over the evaluation-level box-score rows of ``years`` (each row the server's
    match) at expit(mu + O_eff,server - D_eff,returner), and the gain over the tour's surface average (milli per unit,
    positive = better); by surface code as well."""
    st = td["stats"][stat]
    ll, ll0 = row_logloss(td, stat, res)
    sel = np.isfinite(ll) & td["evaluation"] & np.isin(td["year"], list(years))
    if sel_extra is not None:
        sel = sel & sel_extra

    def one(m):
        U = float(st["d"][m].sum())
        return {"rows": int(m.sum()), "units": U, "ll_sum": float(ll[m].sum()), "ll0_sum": float(ll0[m].sum()),
                "logloss_per_unit": float(ll[m].sum() / U) if U else np.nan,
                "better_milli_per_unit": 1000 * float((ll0[m].sum() - ll[m].sum()) / U) if U else np.nan}
    out = {"all": one(sel)}
    if by_surface:
        for s in range(1, S + 1):
            out[C.SURF_NAMES[s]] = one(sel & (td["surf"] == s))
    return out
