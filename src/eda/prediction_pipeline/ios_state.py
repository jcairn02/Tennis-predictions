"""The surface IOS with a saved solver state: checkpoint after any snapshot day, resume later.

The decided solver (src/eda/surface_ios/ios_surface.py; with the level layer for men,
src/eda/lower_level_evidence/level_layer_ios.py: surface_snapshots / snapshots_fe and solve_surface / solve_fe) walks
the snapshot days in order. Its state between two days is small and exact:
    ptr                  the observations already released (sorted by release day)
    the accumulators     Pc, Qc, bOc, bDc, Psc, Qsc, bEc, bFc, TWc (and with level effects PLc, QLc, PsLc, QsLc, SLc,
                         bBc): sums of fixed per-observation terms w0 * m * 2^((obs - ref) / 7h), so a new day adds its
                         released observations and nothing earlier changes
    x                    the last day's solution, the next solve's warm start (PCG to a relative residual of 1e-8)
Each row then reads the snapshot of its earliest possible start (es), and its own earlier matches not yet released are
added by the incremental ("gap") step, which needs the snapshot values of those in-flight matches' rows.

This module copies the decided loops' arithmetic in the same order (so a resumed run on the same system is the full
run bit for bit), and adds:
    Snap.state() / Snap.from_state()   the checkpoint (np.savez-able arrays)
    map_state(...)                     a checkpoint made on an older table moved onto today's system (players and
                                       (server, returner, surface) triples matched by player code)
    resume_rows(...)                   per-row outputs for the rows after the checkpoint: snapshot values from the resumed
                                       loop, then the gap step over each row's own predecessors (stored in-flight values
                                       for the earlier ones)

Modes: "fe" (solve_fe: men's runs with level effects), "plain" (solve_surface's arithmetic: men without a level effect,
and the women's decided solver ios_surface.run, which it equals with every m = 1 and delta = 0).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


def _mods():
    from src.eda.lower_level_evidence import level_layer_ios as LLEIOS
    from src.eda.surface_ios import ios_surface as IS
    from src.eda.ufc_ideas import stageB_common as B
    return LLEIOS, IS, B


@dataclass
class Setup:
    """One run (tour, statistic, kind) as build_features.task sets it up, through run_surface's dispatch."""
    tour: str
    stat: str
    kind: str
    h: float
    kappa: float
    kappa_s: object
    tau: int
    typ: float
    mode: str                         # "fe" or "plain"
    mult: np.ndarray
    delta: np.ndarray
    fe_code: np.ndarray | None
    n_fe: int
    kappa_beta: float
    td: dict
    sysm: object = None
    fe: np.ndarray | None = None      # per observation (system order)
    release: np.ndarray = None
    query: np.ndarray = None
    days: np.ndarray = None
    order: np.ndarray = None
    bounds: np.ndarray = None
    cp: np.ndarray = None
    info: dict = field(default_factory=dict)


def constants_for(tour: str, stat: str, kind: str = "surface") -> tuple[float, float, object, int, float]:
    """(h, kappa, kappa_s, tau, typ) of a run, as build_features.task computes them from the registry in effect."""
    from src.eda.ios_constants import registry as IC
    from src.eda.surface_ios import common as SC
    constants = IC.pin()
    choice = IC.surface_choice(constants)[f"{tour}|{stat}"]
    chosen, typ = SC.ios_constants()
    c = chosen[(tour, stat)]
    if kind == "current":
        hm, ksm = 1.0, None
    elif choice["variant"] == "shared":
        hm, ksm = choice["h_mult"], choice["ks_mult"]
    elif choice["variant"] == "return_only":
        hm, ksm = choice["h_mult"], (choice["kE_mult"], choice["kF_mult"])
    else:
        raise ValueError(f"{tour}|{stat}: pooled variant has no surface run")
    h = c["h"] * hm
    if ksm is None:
        ks = np.inf
    elif isinstance(ksm, (tuple, list)):
        ks = tuple(c["kappa"] * (np.inf if v is None else v) for v in ksm)
    else:
        ks = c["kappa"] * ksm
    return h, c["kappa"], ks, c["tau"], typ[(stat, tour)]


def make_setup(td: dict, stat: str, kind: str = "surface") -> Setup:
    """run_surface's dispatch, without running: the level layer's row plan (men), or the decided solver (women)."""
    LLEIOS, IS, _ = _mods()
    tour = td["tour"]
    h, kappa, ks, tau, typ = constants_for(tour, stat, kind)
    if not IS.split_kappa(ks)[2]:
        raise NotImplementedError("only the surface runs (finite kappa_s) are prototyped here")
    nr = len(td["pid"])
    plan = LLEIOS.row_plan(td, stat, "ios")
    if plan is None:
        mode, mult, delta, fe_code, n_fe = "plain", np.ones(nr), np.zeros(nr), None, 0
    elif LLEIOS._has_fe(plan):
        mode, mult, delta = "fe", np.asarray(plan.mult, dtype=np.float64), np.zeros(nr)
        fe_code = np.asarray(plan.fe_code, dtype=np.int64)
        n_fe = int(fe_code.max()) + 1 if (fe_code >= 0).any() else 0
    else:
        mode, mult, delta, fe_code, n_fe = "plain", np.asarray(plan.mult, np.float64), np.asarray(plan.delta, np.float64), None, 0
    s = Setup(tour, stat, kind, h, kappa, ks, tau, typ, mode, mult, delta, fe_code, n_fe, float(kappa), td)
    es, lf, obs = td["es"], td["lf"], td["obs"]
    s.release = np.where(np.isfinite(lf), lf + 1, np.nan)
    s.query = es.astype(np.float64)
    if np.any(s.release <= s.query):
        raise ValueError("a match's latest possible finish precedes its earliest possible start")
    s.sysm = LLEIOS.SurfaceSystemL(td, stat, s.release, obs, typ, mult, delta if mode == "plain" else np.zeros(nr))
    if mode == "fe":
        s.fe = fe_code[s.sysm.rows]
    cp = s.sysm.cmap[td["pid"]]
    s.cp = np.where(cp >= 0, cp, s.sysm.n)
    s.days, ginv = np.unique(s.query, return_inverse=True)
    s.order = np.argsort(ginv, kind="stable")
    s.bounds = np.r_[0, np.cumsum(np.bincount(ginv, minlength=len(s.days)))]
    s.info = {"mode": mode, "n_fe": n_fe, "h": h, "kappa": kappa, "kappa_s": ks, "tau": tau, "typ": typ,
              "observations": int(len(s.sysm.y)), "players": int(s.sysm.n), "triples": int(s.sysm.n_triples),
              "days": int(len(s.days))}
    return s


class Snap:
    """The snapshot loop's state and one step, copied from surface_snapshots ("plain") and snapshots_fe ("fe")."""

    ACC = ("Pc", "Qc", "bOc", "bDc", "Psc", "Qsc", "bEc", "bFc", "TWc")
    ACC_FE = ("PLc", "QLc", "PsLc", "QsLc", "SLc", "bBc")

    def __init__(self, s: Setup):
        LLEIOS, IS, B = _mods()
        S = IS.S
        sysm = s.sysm
        self.s = s
        n, ref = sysm.n, float(B.REF_DAY)
        self.ref = ref
        self.lam = 0.0 if not np.isfinite(s.h) else 1.0 / (7.0 * s.h)
        w0 = (sysm.d / sysm.typ) ** s.tau if s.tau else np.ones(len(sysm.d))
        self.ws = w0 * sysm.m * np.exp2((sysm.obs - ref) * self.lam)
        self.kE, self.kF, surface_terms = IS.split_kappa(s.kappa_s)
        assert surface_terms
        self.Pc, self.Qc, self.bOc, self.bDc = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
        self.Psc, self.Qsc, self.bEc, self.bFc = (np.zeros((S + 1, n)) for _ in range(4))
        self.TWc = np.zeros(sysm.n_triples)
        nL = s.n_fe
        if s.mode == "fe":
            self.PLc, self.QLc = np.zeros((n, nL)), np.zeros((n, nL))
            self.PsLc, self.QsLc = (np.zeros((S + 1, n, nL)) for _ in range(2))
            self.SLc, self.bBc = np.zeros(nL), np.zeros(nL)
        self.ptr = 0
        self.i = -1                          # index of the last day solved
        nS = n * S
        self.nv = 2 * n + 2 * nS + (nL if s.mode == "fe" else 0)
        self.x = np.zeros(self.nv)
        self.its = []

    # ------------------------------------------------------------------
    def step(self, i: int):
        """Solve snapshot day days[i] (must be the next day); returns the generator's yield tuple."""
        LLEIOS, IS, _ = _mods()
        S = IS.S
        s, sysm = self.s, self.s.sysm
        n, ref, lam = sysm.n, self.ref, self.lam
        kappa, kE, kF = s.kappa, self.kE, self.kF
        nS = n * S
        nv = self.nv
        Sday = s.days[i]
        new = int(np.searchsorted(sysm.release, Sday, side="right"))
        fe_mode = s.mode == "fe"
        if new > self.ptr:
            sl = slice(self.ptr, new)
            srv, ret, sf, w = sysm.srv[sl], sysm.ret[sl], sysm.surf[sl], self.ws[sl]
            wy = w * sysm.y[sl]
            self.Pc += np.bincount(srv, weights=w, minlength=n)
            self.Qc += np.bincount(ret, weights=w, minlength=n)
            self.bOc += np.bincount(srv, weights=wy, minlength=n)
            self.bDc -= np.bincount(ret, weights=wy, minlength=n)
            np.add.at(self.Psc, (sf, srv), w)
            np.add.at(self.Qsc, (sf, ret), w)
            np.add.at(self.bEc, (sf, srv), wy)
            np.add.at(self.bFc, (sf, ret), -wy)
            self.TWc += np.bincount(sysm.triple[sl], weights=w, minlength=sysm.n_triples)
            if fe_mode:
                fl = s.fe[sl]
                nL = s.n_fe
                has = fl >= 0
                if has.any():
                    np.add.at(self.PLc, (srv[has], fl[has]), w[has])
                    np.add.at(self.QLc, (ret[has], fl[has]), w[has])
                    np.add.at(self.PsLc, (sf[has], srv[has], fl[has]), w[has])
                    np.add.at(self.QsLc, (sf[has], ret[has], fl[has]), w[has])
                    self.SLc += np.bincount(fl[has], weights=w[has], minlength=nL)
                    self.bBc += np.bincount(fl[has], weights=wy[has], minlength=nL)
            self.ptr = new
        g = np.exp2(-(Sday - ref) * lam)
        P, Q = self.Pc * g, self.Qc * g
        Ws, WTs = [], []
        for s_ in range(S + 1):
            W = sysm.W[s_]
            W.data[:] = self.TWc[sysm.slot[s_]] * g
            WT, perm = sysm.WT[s_]
            WT.data[:] = W.data[perm]
            Ws.append(W)
            WTs.append(WT)
        Ps, Qs = self.Psc[1:] * g, self.Qsc[1:] * g
        aO, aD = P + kappa, Q + kappa
        dE, dF = Ps + kE, Qs + kF
        AO, AD = IS.Arrow(aO, Ps, dE), IS.Arrow(aD, Qs, dF)
        if not fe_mode:
            o_, d_, e_, f_ = slice(0, n), slice(n, 2 * n), slice(2 * n, 2 * n + nS), slice(2 * n + nS, nv)

            def matvec(v, aO=aO, aD=aD, dE=dE, dF=dF, Ps=Ps, Qs=Qs, Ws=Ws, WTs=WTs):
                O, D = v[o_], v[d_]
                E, F = v[e_].reshape(S, n), v[f_].reshape(S, n)
                gs = np.empty((S, n))
                hs = np.empty((S, n))
                for s_ in range(S):
                    gs[s_] = Ws[s_ + 1] @ (D + F[s_])
                    hs[s_] = WTs[s_ + 1] @ (O + E[s_])
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
            b = np.concatenate([self.bOc * g, self.bDc * g, (self.bEc[1:] * g).reshape(-1), (self.bFc[1:] * g).reshape(-1)])
            self.x, it, conv = IS.pcg_block(matvec, precond, b, self.x)
            x = self.x
            self.i = i
            self.its.append(it)
            return (i, x[o_], x[d_], x[e_].reshape(S, n).T, x[f_].reshape(S, n).T, P, Q, Ps.T, Qs.T, None, None, None,
                    it, conv)
        nL = s.n_fe
        PL, QL = self.PLc * g, self.QLc * g
        dB = self.SLc * g + s.kappa_beta
        bB = self.bBc * g
        b_ = slice(nv - nL, nv)
        PsL, QsL = self.PsLc[1:] * g, self.QsLc[1:] * g
        o_, d_, e_, f_ = slice(0, n), slice(n, 2 * n), slice(2 * n, 2 * n + nS), slice(2 * n + nS, 2 * n + 2 * nS)

        def matvec(v, aO=aO, aD=aD, dE=dE, dF=dF, Ps=Ps, Qs=Qs, Ws=Ws, WTs=WTs, PL=PL, QL=QL, PsL=PsL, QsL=QsL,
                   dB=dB):
            O, D = v[o_], v[d_]
            E, F = v[e_].reshape(S, n), v[f_].reshape(S, n)
            bt = v[b_]
            gs = np.empty((S, n))
            hs = np.empty((S, n))
            for s_ in range(S):
                gs[s_] = Ws[s_ + 1] @ (D + F[s_])
                hs[s_] = WTs[s_ + 1] @ (O + E[s_])
            out = np.empty(nv)
            out[o_] = aO * O + (Ps * E).sum(axis=0) - Ws[0] @ D - gs.sum(axis=0) + PL @ bt
            out[d_] = aD * D + (Qs * F).sum(axis=0) - WTs[0] @ O - hs.sum(axis=0) - QL @ bt
            out[e_] = (Ps * O + dE * E - gs + PsL @ bt).reshape(-1)
            out[f_] = (Qs * D + dF * F - hs - QsL @ bt).reshape(-1)
            out[b_] = (dB * bt + PL.T @ O - QL.T @ D + np.einsum("snl,sn->l", PsL, E)
                       - np.einsum("snl,sn->l", QsL, F))
            return out

        def precond(r, AO=AO, AD=AD, dB=dB):
            out = np.empty(nv)
            x0, xs = AO.solve(r[o_], r[e_].reshape(S, n))
            out[o_], out[e_] = x0, xs.reshape(-1)
            x0, xs = AD.solve(r[d_], r[f_].reshape(S, n))
            out[d_], out[f_] = x0, xs.reshape(-1)
            out[b_] = r[b_] / dB
            return out
        b = np.concatenate([self.bOc * g, self.bDc * g, (self.bEc[1:] * g).reshape(-1), (self.bFc[1:] * g).reshape(-1), bB])
        self.x, it, conv = IS.pcg_block(matvec, precond, b, self.x)
        x = self.x
        self.i = i
        self.its.append(it)
        return (i, x[o_], x[d_], x[e_].reshape(S, n).T, x[f_].reshape(S, n).T, P, Q, Ps.T, Qs.T, x[b_].copy(), PL, QL,
                it, conv)

    # ------------------------------------------------------------------
    def state(self) -> dict:
        out = {k: getattr(self, k) for k in self.ACC}
        if self.s.mode == "fe":
            out.update({k: getattr(self, k) for k in self.ACC_FE})
        out.update({"x": self.x, "ptr": np.int64(self.ptr), "i": np.int64(self.i), "day": np.float64(self.s.days[self.i])})
        return {k: np.array(v, copy=True) for k, v in out.items()}

    @classmethod
    def from_state(cls, s: Setup, st: dict) -> "Snap":
        self = cls(s)
        for k in cls.ACC + (cls.ACC_FE if s.mode == "fe" else ()):
            arr = np.array(st[k], copy=True)
            if arr.shape != getattr(self, k).shape:
                raise ValueError(f"state {k}: shape {arr.shape}, system needs {getattr(self, k).shape}")
            setattr(self, k, arr)
        self.x = np.array(st["x"], copy=True)
        if self.x.shape != (self.nv,):
            raise ValueError("state x does not fit the system")
        self.ptr = int(st["ptr"])
        day = float(st["day"])
        self.i = int(np.searchsorted(s.days, day, side="left"))
        if self.i >= len(s.days) or s.days[self.i] != day:
            raise ValueError("the checkpoint day is not a snapshot day of this system")
        if int(np.searchsorted(s.sysm.release, day, side="right")) != self.ptr:
            raise ValueError("observations released by the checkpoint day differ from the checkpoint's")
        return self


# ----------------------------------------------------------------------------------------------
# Per-row snapshot values (what solve_fe / solve_surface keep for every row)

ROW_KEYS = ("O_s", "D_s", "P_s", "Q_s", "E_all", "F_all", "PS_all", "QS_all", "B_all")


def empty_rows(s: Setup) -> dict:
    _, IS, _ = _mods()
    S = IS.S
    nr = len(s.td["pid"])
    out = {k: np.full(nr, np.nan) for k in ("O_s", "D_s", "P_s", "Q_s")}
    out.update({k: np.full((nr, S), np.nan) for k in ("E_all", "F_all", "PS_all", "QS_all")})
    out["B_all"] = np.full((nr, max(s.n_fe, 1)), np.nan)
    return out


def record_day(s: Setup, rows: dict, yielded) -> None:
    _, IS, _ = _mods()
    S = IS.S
    i, O, D, E, F, P, Q, Ps, Qs, beta, PL, QL, it, conv = yielded
    rows_in = np.arange(len(s.td["pid"]))
    r = rows_in[s.order[s.bounds[i]:s.bounds[i + 1]]]
    p = s.cp[r]
    z1, zS = np.zeros(1), np.zeros((1, S))
    rows["O_s"][r], rows["D_s"][r] = np.r_[O, z1][p], np.r_[D, z1][p]
    rows["P_s"][r], rows["Q_s"][r] = np.r_[P, z1][p], np.r_[Q, z1][p]
    rows["E_all"][r], rows["F_all"][r] = np.vstack([E, zS])[p], np.vstack([F, zS])[p]
    rows["PS_all"][r], rows["QS_all"][r] = np.vstack([Ps, zS])[p], np.vstack([Qs, zS])[p]
    if s.mode == "fe" and s.n_fe:
        rows["B_all"][r] = beta


def run_days(snap: Snap, rows: dict, upto: int | None = None, checkpoints: dict | None = None) -> dict:
    """Solve the days after snap.i up to index `upto` (inclusive; default all), recording each row's snapshot values;
    `checkpoints` {day: None} is filled with the state after each named day."""
    s = snap.s
    last = len(s.days) - 1 if upto is None else upto
    t0 = time.time()
    nonconv = 0
    first = snap.i + 1
    for i in range(first, last + 1):
        y = snap.step(i)
        record_day(s, rows, y)
        nonconv += int(not y[-1])
        if checkpoints is not None and float(s.days[i]) in checkpoints:
            checkpoints[float(s.days[i])] = snap.state()
    return {"days": int(max(last + 1 - first, 0)), "seconds": round(time.time() - t0, 2), "not_converged": nonconv}


# ----------------------------------------------------------------------------------------------
# The gap step and the outputs, for chosen target rows (the decided code computes them for every row at once; per
# target the additions are made in the same order k = 1..lookback, so a subset gives the same numbers)

def outputs(s: Setup, rows: dict, targets: np.ndarray | None = None, lookback: int | None = None) -> dict:
    """O_eff, D_eff (and parts) for the target rows (default: every row), from the per-row snapshot values in `rows`
    (every row a target reads must be filled: the targets, their opponents, and their unreleased own predecessors with
    their opponents)."""
    _, IS, _ = _mods()
    S = IS.S
    td = s.td
    lookback = IS.LOOKBACK if lookback is None else lookback
    nr = len(td["pid"])
    tg_all = np.arange(nr) if targets is None else np.asarray(targets, dtype=np.int64)
    pid, surf = td["pid"], td["surf"].astype(np.int64)
    sidx = np.clip(surf - 1, 0, S - 1)
    known = surf >= 1
    O_s, D_s, P_s, Q_s = rows["O_s"], rows["D_s"], rows["P_s"], rows["Q_s"]
    E_all, F_all, PS_all, QS_all = rows["E_all"], rows["F_all"], rows["PS_all"], rows["QS_all"]
    E_row = np.where(known, E_all[np.arange(nr), sidx], 0.0)
    F_row = np.where(known, F_all[np.arange(nr), sidx], 0.0)
    st = td["stats"][s.stat]
    lam = 0.0 if not np.isfinite(s.h) else 1.0 / (7.0 * s.h)
    release, query, obs = s.release, s.query, td["obs"]
    ok = st["ok"] & np.isfinite(release) & (s.mult > 0)
    w0 = np.where(ok, ((st["d"] / s.typ) ** s.tau if s.tau else 1.0) * s.mult, 0.0)
    opp = np.arange(nr) ^ 1
    okr, w0r = ok[opp], w0[opp]
    if s.mode == "fe" and s.n_fe:
        bl = np.where(s.fe_code >= 0, rows["B_all"][np.arange(nr), np.clip(s.fe_code, 0, None)], 0.0)
        y = st["y"] - np.nan_to_num(bl)
    elif s.mode == "fe":
        y = st["y"].astype(np.float64)
    else:
        y = st["y"] - s.delta
    yr = y[opp]
    Dopp = np.nan_to_num(D_s[opp] + F_row[opp])
    Oopp = np.nan_to_num(O_s[opp] + E_row[opp])
    seq = IS.own_order(td)
    pos = np.empty(nr, dtype=np.int64)
    pos[seq] = np.arange(nr)
    sp_ = pid[seq]
    day, ev, rn = td["day"][seq], td["ev"][seq], td["round_order"][seq]
    rel_s, q_s, obs_s = release[seq], query[seq], obs[seq]
    m = len(tg_all)
    GO, GOy, GD, GDy = (np.zeros((m, S + 1)) for _ in range(4))
    gaps = np.zeros(m, dtype=np.int64)
    tpos = pos[tg_all]
    for k in range(1, lookback + 1):
        okk = tpos - k >= 0
        tgt = tpos[okk]
        src = tgt - k
        same = sp_[src] == sp_[tgt]
        precedes = (day[src] < day[tgt]) | ((ev[src] == ev[tgt]) & (rn[src] < rn[tgt]))
        unreleased = rel_s[src] > q_s[tgt]
        use = same & precedes & unreleased
        if not use.any():
            continue
        j = np.flatnonzero(okk)[use]          # index into the targets
        sr = seq[src[use]]
        age = np.maximum(q_s[tgt[use]] - obs_s[src[use]], 0.0)
        e = np.exp2(-age * lam)
        sg = surf[sr]
        GO[j, sg] += np.where(ok[sr], w0[sr] * e, 0.0)
        GOy[j, sg] += np.where(ok[sr], w0[sr] * e * (y[sr] + Dopp[sr]), 0.0)
        GD[j, sg] += np.where(okr[sr], w0r[sr] * e, 0.0)
        GDy[j, sg] += np.where(okr[sr], w0r[sr] * e * (Oopp[sr] - yr[sr]), 0.0)
        gaps[j] += 1
    kE, kF, _ = IS.split_kappa(s.kappa_s)
    t = tg_all
    E_snap = np.nan_to_num(E_all[t])
    F_snap = np.nan_to_num(F_all[t])
    PSn, QSn = np.nan_to_num(PS_all[t]), np.nan_to_num(QS_all[t])
    aO = P_s[t] + s.kappa
    aD = Q_s[t] + s.kappa
    rO = aO * O_s[t] + (PSn * E_snap).sum(axis=1) + GOy.sum(axis=1)
    rE = PSn * O_s[t][:, None] + (PSn + kE) * E_snap + GOy[:, 1:]
    O1, E1 = IS.arrow_solve(aO + GO.sum(axis=1), PSn + GO[:, 1:], PSn + kE + GO[:, 1:], rO, rE)
    rD = aD * D_s[t] + (QSn * F_snap).sum(axis=1) + GDy.sum(axis=1)
    rF = QSn * D_s[t][:, None] + (QSn + kF) * F_snap + GDy[:, 1:]
    D1, F1 = IS.arrow_solve(aD + GD.sum(axis=1), QSn + GD[:, 1:], QSn + kF + GD[:, 1:], rD, rF)
    kn, si = known[t], sidx[t]
    E1_row = np.where(kn, E1[np.arange(m), si], 0.0)
    F1_row = np.where(kn, F1[np.arange(m), si], 0.0)
    return {"rows": t, "O_eff": O1 + E1_row, "D_eff": D1 + F1_row, "O": O1, "D": D1, "E": E1_row, "F": F1_row,
            "gap_matches": gaps}


def full_run(s: Setup, checkpoints: dict | None = None) -> tuple[dict, dict, dict]:
    """The whole history (the decided run, through this module's copy): per-row outputs, per-row snapshot values and
    the run's record; `checkpoints` {day: None} gets the states after those days."""
    snap = Snap(s)
    rows = empty_rows(s)
    rec = run_days(snap, rows, checkpoints=checkpoints)
    out = outputs(s, rows)
    rec["iterations_mean"] = float(np.mean(snap.its)) if snap.its else 0.0
    return out, rows, rec


# ----------------------------------------------------------------------------------------------
# Checkpoint files: the solver state plus the in-flight rows' snapshot values

def inflight_rows(s: Setup, day: float) -> np.ndarray:
    """Rows queried by `day` whose match is not yet released then (release > day): the only earlier rows a later
    row's gap step or a later opponent reads. Both rows of each such match (a match's rows share es and lf)."""
    return np.flatnonzero((s.query <= day) & (s.release > day))


def save_checkpoint(path, s: Setup, state: dict, rows: dict) -> dict:
    day = float(state["day"])
    fl = inflight_rows(s, day)
    keys = s.td.get("row_key")
    payload = {f"st_{k}": v for k, v in state.items()}
    payload.update({f"row_{k}": rows[k][fl] for k in ROW_KEYS})
    payload["row_index"] = fl
    if keys is not None:
        payload["row_key"] = np.asarray(keys)[fl]
    payload["active_pid"] = s.sysm.active
    payload["triple_keys"] = triple_keys(s)
    np.savez(path, **payload)
    import os
    return {"inflight_rows": int(len(fl)), "bytes": int(os.path.getsize(path))}


def triple_keys(s: Setup) -> np.ndarray:
    """Each triple of the system as (server pid, returner pid, surface), as one int64 key independent of the system's
    player numbering."""
    _, IS, _ = _mods()
    S = IS.S
    sysm = s.sysm
    n = sysm.n
    srv_c = np.empty(sysm.n_triples, dtype=np.int64)
    ret_c = np.empty(sysm.n_triples, dtype=np.int64)
    sur = np.empty(sysm.n_triples, dtype=np.int64)
    srv_c[sysm.triple] = sysm.srv
    ret_c[sysm.triple] = sysm.ret
    sur[sysm.triple] = sysm.surf
    a = sysm.active
    big = int(sysm.n_full) + 1
    return (a[srv_c] * big + a[ret_c]) * (S + 1) + sur


def map_state(old: dict, old_active: np.ndarray, old_triples: np.ndarray, s_new: Setup, n_fe_old: int) -> dict:
    """A checkpoint of an older table's system moved onto today's: player blocks by pid, triples by key. New players
    and new triples start at zero (they have no released observation before the checkpoint day: checked by the
    caller through ptr)."""
    _, IS, _ = _mods()
    S = IS.S
    sysm = s_new.sysm
    n_new = sysm.n
    pos = sysm.cmap[old_active]
    if (pos < 0).any():
        raise ValueError("a player of the old system is not in the new one")
    out = {}
    for k in ("Pc", "Qc", "bOc", "bDc"):
        v = np.zeros(n_new)
        v[pos] = old[k]
        out[k] = v
    for k in ("Psc", "Qsc", "bEc", "bFc"):
        v = np.zeros((S + 1, n_new))
        v[:, pos] = old[k]
        out[k] = v
    new_keys = triple_keys(s_new)
    order = np.argsort(new_keys)
    j = order[np.searchsorted(new_keys[order], old_triples)]
    if not np.array_equal(new_keys[j], old_triples):
        raise ValueError("a triple of the old system is not in the new one")
    v = np.zeros(sysm.n_triples)
    v[j] = old["TWc"]
    out["TWc"] = v
    if s_new.mode == "fe":
        if s_new.n_fe != n_fe_old:
            raise ValueError("the level effects differ between the systems")
        nL = s_new.n_fe
        for k in ("PLc", "QLc"):
            v = np.zeros((n_new, nL))
            v[pos] = old[k]
            out[k] = v
        for k in ("PsLc", "QsLc"):
            v = np.zeros((S + 1, n_new, nL))
            v[:, pos] = old[k]
            out[k] = v
        out["SLc"], out["bBc"] = old["SLc"].copy(), old["bBc"].copy()
    n_old = len(old_active)
    xo = old["x"]
    x = np.zeros(2 * n_new + 2 * n_new * S + (s_new.n_fe if s_new.mode == "fe" else 0))
    x[pos] = xo[:n_old]
    x[n_new + pos] = xo[n_old:2 * n_old]
    Eo = xo[2 * n_old:2 * n_old + n_old * S].reshape(S, n_old)
    Fo = xo[2 * n_old + n_old * S:2 * n_old + 2 * n_old * S].reshape(S, n_old)
    E = np.zeros((S, n_new))
    F = np.zeros((S, n_new))
    E[:, pos], F[:, pos] = Eo, Fo
    x[2 * n_new:2 * n_new + n_new * S] = E.reshape(-1)
    x[2 * n_new + n_new * S:2 * n_new + 2 * n_new * S] = F.reshape(-1)
    if s_new.mode == "fe":
        x[2 * n_new + 2 * n_new * S:] = xo[2 * n_old + 2 * n_old * S:]
    out["x"] = x
    out["ptr"] = old["ptr"]
    out["i"] = old["i"]
    out["day"] = old["day"]
    return out
