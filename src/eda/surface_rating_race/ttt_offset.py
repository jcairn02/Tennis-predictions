"""TrueSkill Through Time with a surface offset, on the leak-proof timeline.

The model. Each player has an overall skill (one chain over time, as ratings.TTT) and, per surface, an offset (a chain of
its own, moved only by matches on that surface). In a match on surface s each side's performance is its overall skill
plus its offset on s plus N(0, beta^2) noise, and the higher performance wins: TrueSkill's team factor, with the player's
two skills as the team. Where the surface is unknown a side is its overall skill alone.

    overall   prior N(0, sigma0^2), drift gamma^2 per year: the decided TTT's frozen constants (match_timing's ttt_timed)
    offset    prior N(0, sigma_o^2), drift gamma_o^2 per year: tuned on 2013-2018 (tune.py)
    forecast  P(A wins) = Phi((mu_A + o_A - mu_B - o_B) / sqrt(2 beta^2 + s2_A + so2_A + s2_B + so2_B))

It is the Elo-pieces study's surface-offset Elo in TTT's Bayesian form: an offset that starts at 0 and moves only on its
surface, beside an overall rating that every match moves. The decided TTT instead blends an overall chain with a
surface-only chain (keys player x surface, each started at the newcomer's prior), the structure the Elo-pieces study
found biased for players new to a surface.

Inference. Expectation propagation as ratings.TTT, with the team factor: a game's message to each of its nodes is the
moment-matched update of that node from the cavities of all of the game's nodes,
    c^2 = 2 beta^2 + sum of the cavity variances,  t = (sum of the winners' cavity means - the losers') / c,
    node mean += (+/-) s2 / c v(t),  node variance *= 1 - s2 / c^2 w(t),
the exact first two moments of each skill under the truncated linear-Gaussian factor. With every side a single node this
is ratings.TTT's game update operation for operation.

Time. ratings.ttt_pass_timed's two-time rule, unchanged: a rating-moving match joins the model in the batch of its
release day lf + 1, at time lf; a row's forecast reads the model as of its es (drifted to that day) plus the TrueSkill
updates of each skill's own earlier, unreleased matches (round robins excepted); smoothing covers the trailing
window_days once per calendar week of the query days. With offsets=False the pass is ttt_pass_timed's overall pass
exactly (tested: test/surface_rating_race/).
"""
from __future__ import annotations

import math
from bisect import bisect_right

import numpy as np
import pandas as pd
from scipy.special import ndtr

from src.eda.rating_systems.ratings import DAYS_PER_YEAR, INV_SQRT_2PI, SQRT2

OUT_COLS = ["mu_a", "mu_b", "s2_a", "s2_b", "off_a", "off_b", "so2_a", "so2_b", "n_a", "n_b", "ns_a", "ns_b"]
N_SURF = 4


class TTTOffset:
    """ratings.TTT with keys of two kinds (overall: key < n_overall; offset: the rest), each kind with its own prior and
    drift, and games between teams of nodes (winners first). Messages in natural parameters, as ratings.TTT."""

    def __init__(self, n_overall: int, n_keys: int, sigma0: float, gamma: float, sigma_o: float, gamma_o: float,
                 beta: float = 1.0):
        self.n_overall = n_overall
        self.s0 = (sigma0 * sigma0, sigma_o * sigma_o)
        self.g2 = (gamma * gamma, gamma_o * gamma_o)
        self.beta2 = beta * beta
        self.key, self.kind, self.time, self.prev, self.next = [], [], [], [], []
        self.fpi, self.fnu, self.bpi, self.bnu, self.lpi, self.lnu = [], [], [], [], [], []
        self.gn, self.gw, self.gpi, self.gnu = [], [], [], []   # per game: nodes, winners' count, messages per node
        self.batches = []                                        # (time, nodes, games), in time order
        self.last = [-1] * n_keys

    def _drift(self, pi: float, nu: float, days: float, kind: int) -> tuple[float, float]:
        if pi <= 0.0:
            return 0.0, 0.0
        v = 1.0 / pi + self.g2[kind] * days / DAYS_PER_YEAR
        return 1.0 / v, nu / pi / v

    def _fwd(self, nd: int) -> None:
        p = self.prev[nd]
        if p < 0:
            self.fpi[nd], self.fnu[nd] = 1.0 / self.s0[self.kind[nd]], 0.0
        else:
            self.fpi[nd], self.fnu[nd] = self._drift(self.fpi[p] + self.lpi[p], self.fnu[p] + self.lnu[p],
                                                     self.time[nd] - self.time[p], self.kind[nd])

    def _bwd(self, nd: int) -> None:
        q = self.next[nd]
        if q < 0:
            self.bpi[nd] = self.bnu[nd] = 0.0
        else:
            self.bpi[nd], self.bnu[nd] = self._drift(self.bpi[q] + self.lpi[q], self.bnu[q] + self.lnu[q],
                                                     self.time[q] - self.time[nd], self.kind[nd])

    def _game(self, g: int) -> None:
        nodes, nw, mpi, mnu = self.gn[g], self.gw[g], self.gpi[g], self.gnu[g]
        fpi, fnu, bpi, bnu, lpi, lnu = self.fpi, self.fnu, self.bpi, self.bnu, self.lpi, self.lnu
        k = len(nodes)
        cp, cn = [0.0] * k, [0.0] * k
        for j in range(k):
            nd = nodes[j]
            cp[j] = fpi[nd] + bpi[nd] + lpi[nd] - mpi[j]
            cn[j] = fnu[nd] + bnu[nd] + lnu[nd] - mnu[j]
        for j in range(k):
            if cp[j] <= 1e-12:
                return
        m = [cn[j] / cp[j] for j in range(k)]
        s = [1.0 / cp[j] for j in range(k)]
        c2 = 2.0 * self.beta2
        for j in range(k):
            c2 += s[j]
        mw = 0.0
        for j in range(nw):
            mw += m[j]
        ml = 0.0
        for j in range(nw, k):
            ml += m[j]
        c = math.sqrt(c2)
        t = (mw - ml) / c
        if t > -20.0:
            v = INV_SQRT_2PI * math.exp(-0.5 * t * t) / (0.5 * math.erfc(-t / SQRT2))
        else:
            v = -t - 1.0 / t + 2.0 / t ** 3
        ww = v * (v + t)
        for j in range(k):
            sj = s[j]
            s2 = sj * (1.0 - sj / c2 * ww)
            mj = m[j] + sj / c * v if j < nw else m[j] - sj / c * v
            npi = 1.0 / s2 - cp[j]
            nnu = mj / s2 - cn[j]
            nd = nodes[j]
            lpi[nd] += npi - mpi[j]
            lnu[nd] += nnu - mnu[j]
            mpi[j], mnu[j] = npi, nnu

    def add_batch(self, t: float, games: list, batch_iters: int = 2) -> None:
        """games: (winner keys, loser keys) tuples."""
        node_of: dict = {}
        for ws, ls in games:
            for k in ws + ls:
                if k in node_of:
                    continue
                nd = len(self.key)
                p = self.last[k]
                self.key.append(k)
                self.kind.append(1 if k >= self.n_overall else 0)
                self.time.append(t)
                self.prev.append(p)
                self.next.append(-1)
                for arr in (self.fpi, self.fnu, self.bpi, self.bnu, self.lpi, self.lnu):
                    arr.append(0.0)
                if p >= 0:
                    self.next[p] = nd
                self.last[k] = nd
                node_of[k] = nd
                self._fwd(nd)
        gids = []
        for ws, ls in games:
            g = len(self.gn)
            nodes = tuple(node_of[k] for k in ws + ls)
            self.gn.append(nodes)
            self.gw.append(len(ws))
            self.gpi.append([0.0] * len(nodes))
            self.gnu.append([0.0] * len(nodes))
            gids.append(g)
        self.batches.append((t, list(node_of.values()), gids))
        for _ in range(batch_iters):
            for g in gids:
                self._game(g)

    def smooth(self, window: int, sweeps: int = 1) -> None:
        lo = max(0, len(self.batches) - window)
        for _ in range(sweeps):
            for bi in range(len(self.batches) - 1, lo - 1, -1):
                _, nodes, games = self.batches[bi]
                for nd in nodes:
                    self._bwd(nd)
                for g in games:
                    self._game(g)
            for bi in range(lo, len(self.batches)):
                _, nodes, games = self.batches[bi]
                for nd in nodes:
                    self._fwd(nd)
                for g in games:
                    self._game(g)

    def posterior(self, nd: int) -> tuple[float, float]:
        pi = self.fpi[nd] + self.bpi[nd] + self.lpi[nd]
        return (self.fnu[nd] + self.bnu[nd] + self.lnu[nd]) / pi, 1.0 / pi

    def latest(self, k: int, t: float) -> tuple[float, float]:
        kind = 1 if k >= self.n_overall else 0
        nd = self.last[k]
        if nd < 0:
            return 0.0, self.s0[kind]
        mu, s2 = self.posterior(nd)
        return mu, min(s2 + self.g2[kind] * (t - self.time[nd]) / DAYS_PER_YEAR, self.s0[kind])


def offset_key(n_players: int, p: int, s: int) -> int:
    return n_players + N_SURF * p + s


def ttt_offset_pass_timed(es, lf, event, rnd, pa, pb, surf, a_won, upd, n_players: int, sigma0: float, gamma: float,
                          sigma_o: float = 0.3, gamma_o: float = 0.0, beta: float = 1.0, window_days: float = 182.0,
                          sweeps: int = 1, batch_iters: int = 2, smooth_every: str = "week",
                          offsets: bool = True) -> np.ndarray:
    """One chronological pass (rows in the table's order, which is each player's own order). pa, pb: player codes
    0..n_players-1; surf: 0-3 or -1 (unknown). Returns OUT_COLS per row: each side's overall mean and variance, offset
    mean and variance on the match's surface (NaN where the surface is unknown or offsets is False), and the released
    plus pending match counts of the overall and the surface skill."""
    n = len(es)
    if offsets and not sigma_o > 0.0:
        raise ValueError("an offset needs a positive prior deviation")
    n_keys = n_players * (1 + N_SURF) if offsets else n_players
    model = TTTOffset(n_players, n_keys, sigma0, gamma, sigma_o if offsets else 1.0, gamma_o, beta)
    beta2 = beta * beta
    cols = [[math.nan] * n for _ in OUT_COLS]
    o_mua, o_mub, o_sa, o_sb, o_oa, o_ob, o_qa, o_qb, o_na, o_nb, o_ma, o_mb = cols
    NN = [0] * n_keys
    pending = [dict() for _ in range(n_keys)]   # per key: row -> (event, round, d_pi, d_nu); played, not yet released
    by_release: dict = {}                        # release day -> [(row, winner keys, loser keys)]
    times: list = []
    last_week = last_day = None
    pre: dict = {}
    sqrt, exp, erfc = math.sqrt, math.exp, math.erfc
    for i in sorted(range(n), key=lambda r: (es[r], r)):
        S = es[i]
        due = sorted(r for r in by_release if r <= S)
        for r in due:
            games = by_release.pop(r)
            model.add_batch(float(r - 1), [(w, l) for _, w, l in games], batch_iters)
            times.append(float(r - 1))
            for j, w, l in games:
                for k in w + l:
                    pending[k].pop(j, None)
                    NN[k] += 1
            if smooth_every == "batch":
                model.smooth(len(times) - bisect_right(times, r - 1 - window_days), sweeps)
        if due and smooth_every == "week" and S // 7 != last_week:
            model.smooth(len(times) - bisect_right(times, S - 1 - window_days), sweeps)
            last_week = S // 7
        if due or S != last_day:
            pre.clear()
            last_day = S
        s = surf[i]
        use_off = offsets and s >= 0
        e_i, r_i = event[i], rnd[i]
        sides = []
        for p in (pa[i], pb[i]):
            keys = (p, n_players + N_SURF * p + s) if use_off else (p,)
            states = []
            for k in keys:
                st = pre.get(k)
                if st is None:
                    st = pre[k] = model.latest(k, float(S))
                mu, s2 = st
                dpi = dnu = 0.0
                cnt = 0
                for j, (e, r, a, b) in pending[k].items():
                    if j < i and not (e == e_i and r == r_i):
                        dpi, dnu, cnt = dpi + a, dnu + b, cnt + 1
                if cnt:
                    prec = 1.0 / s2 + dpi
                    mu, s2 = (mu / s2 + dnu) / prec, 1.0 / prec
                states.append((k, mu, s2, NN[k] + cnt))
            sides.append(states)
        A, B = sides
        o_mua[i], o_sa[i], o_na[i] = A[0][1], A[0][2], A[0][3]
        o_mub[i], o_sb[i], o_nb[i] = B[0][1], B[0][2], B[0][3]
        if use_off:
            o_oa[i], o_qa[i], o_ma[i] = A[1][1], A[1][2], A[1][3]
            o_ob[i], o_qb[i], o_mb[i] = B[1][1], B[1][2], B[1][3]
        if upd[i]:
            W, L = (A, B) if a_won[i] else (B, A)
            c2 = 2.0 * beta2
            for x in W:
                c2 += x[2]
            for x in L:
                c2 += x[2]
            mw = 0.0
            for x in W:
                mw += x[1]
            ml = 0.0
            for x in L:
                ml += x[1]
            c = sqrt(c2)
            t = (mw - ml) / c
            if t > -20.0:
                v = INV_SQRT_2PI * exp(-0.5 * t * t) / (0.5 * erfc(-t / SQRT2))
            else:
                v = -t - 1.0 / t + 2.0 / t ** 3
            w = v * (v + t)
            for x in W:
                k, mu, s2 = x[0], x[1], x[2]
                mu2, s22 = mu + s2 / c * v, s2 * (1.0 - s2 / c2 * w)
                pending[k][i] = (e_i, r_i, 1.0 / s22 - 1.0 / s2, mu2 / s22 - mu / s2)
            for x in L:
                k, mu, s2 = x[0], x[1], x[2]
                mu2, s22 = mu - s2 / c * v, s2 * (1.0 - s2 / c2 * w)
                pending[k][i] = (e_i, r_i, 1.0 / s22 - 1.0 / s2, mu2 / s22 - mu / s2)
            by_release.setdefault(lf[i] + 1, []).append((i, tuple(x[0] for x in W), tuple(x[0] for x in L)))
    return np.array(cols, dtype="float64").T


def frame_of(out: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(out, columns=OUT_COLS)


def z_parts(o: pd.DataFrame, beta: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The forecast's z = (overall difference + offset difference) / c and its two parts, each over the same c (so
    they add up to z). Unknown surface: offset part 0."""
    oa, ob = o["off_a"].fillna(0.0).to_numpy(), o["off_b"].fillna(0.0).to_numpy()
    qa, qb = o["so2_a"].fillna(0.0).to_numpy(), o["so2_b"].fillna(0.0).to_numpy()
    c = np.sqrt(2.0 * beta * beta + o["s2_a"].to_numpy() + qa + o["s2_b"].to_numpy() + qb)
    z_over = (o["mu_a"].to_numpy() - o["mu_b"].to_numpy()) / c
    z_off = (oa - ob) / c
    return z_over + z_off, z_over, z_off


def p_offset(o: pd.DataFrame, beta: float = 1.0) -> np.ndarray:
    return ndtr(z_parts(o, beta)[0])


def p_overall(o: pd.DataFrame, beta: float = 1.0) -> np.ndarray:
    """The overall skills alone, with their own uncertainty (as ratings.blend with w = 0)."""
    c = np.sqrt(2.0 * beta * beta + o["s2_a"].to_numpy() + o["s2_b"].to_numpy())
    return ndtr((o["mu_a"].to_numpy() - o["mu_b"].to_numpy()) / c)
