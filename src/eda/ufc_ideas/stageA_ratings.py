"""Stage A of "ideas borrowed from UFC-predictions", part 1: the Bradley-Terry rating (BT) and the market-embedded skill
rating (MESR), tuned on 2013-2018 and frozen, every match's pre-match values, and the probes.

The Bradley-Terry rating (the UFC project's add_bt_rating, adapted to tennis)
    P(A beats B) = sigmoid(s_A - s_B). At a snapshot every earlier result is re-solved at once: the MAP of
        sum_k w_k [log(1 + exp(eta_k)) - y_k eta_k] + (lambda / 2) sum_i (s_i - m_i)^2,   eta_k = s_A - s_B,
    w_k = 2^(-age_k / half_life) x the result weight (retirements may count less), age from the snapshot date. One edge
    per match whose status moves ratings (completed or retired, as the owner decided for Elo), every singles level
    from 2010, per tour. m_i is the anchor for a newcomer in the v4 informed form, m_i = anchor x max(0, 1 - n_i / 6),
    n_i the player's edges in the snapshot (chosen once and kept fixed: tennis players arrive in large numbers at the
    ITF level and play many matches quickly, so the pull fades over the first six rather than stopping after one).
    Solved by damped Newton (Armijo backtracking when a step would move a rating by more than 0.5) on the sparse
    Hessian with a preconditioned conjugate gradient, warm-started from the previous snapshot plus the last date's
    in-event steps. Edges whose decay weight is below 1e-4 are dropped (with the chosen half-life, 0.5 years, results
    over about 6.6 years old).
    A player with no edge in the snapshot has rating m_i (the anchor).

The time rule (the Brief's, as stage1_baselines.elo_pass implements it for Elo)
    A snapshot is solved at every distinct tournament date of the tour (almost all Mondays; elo_pass's "week"), from
    the edges of earlier dates only. A player's rating for a match is the snapshot plus what their earlier rounds of
    the same event added, each through a one-step local Newton update with the opponent's rating held fixed:
        step_i = w (y - p) / (w p (1 - p) + lambda + I_i + J_i),
    p from the two pre-match ratings, I_i the player's information at the snapshot (sum of w p (1 - p) over their
    snapshot edges, at the solution), J_i the information their earlier rounds of this event added. A round's steps
    are held back until the next round of that event (a round robin's matches never see each other), and they never
    reach another event (two events of one date never see each other); the next snapshot re-solves everything.

Variants (each its own column): the games-margin-weighted BT (each edge's weight times the winner's share of the
games over its 2010-2018 mean, Stage 4's scale, read from stage4_constants.csv); the no-decay BT (the best grid row
without decay); the surface BT, s_i + u_{i,surface} with its own ridge lambda_u on the deviations (grid 1, 3, 10; the
other constants the primary's), whose within-event step uses the combined rating's information from the 2 x 2 block
of (s_i, u_{i,surface}).

MESR (the UFC project's add_mesr / v4 mesr.py, adapted)
    Edges: the matches with a coherent closing-odds probability (stage1_odds.parquet, p_avg_a) whose status is
    completed or retired, from 2010 (2010-2012 warm up, as they do for Elo and BT): d_k = logit(p_avg_a).
    At a snapshot: minimise sum_k w_k (d_k - (s_A - s_B))^2 + lambda sum_i (s_i - m_i)^2, w_k = 2^(-age / half_life),
    m_i = anchor for a player with at most one odds edge in the snapshot, 0 otherwise (the UFC rule, as the Brief
    sets it). A linear sparse solve (conjugate gradient, warm-started); no edge is dropped. The same time rule as
    BT: snapshots at every tournament date from earlier dates' odds, plus the same event's earlier rounds through
    the exact one-player least-squares step w (d - Delta) / (w + lambda + I_i + J_i). The snapshot-only value is kept
    too (mesr_snap_*). A player with no odds edge visible under the rule has no MESR (missing).

Tuning (per tour; then frozen). BT: the log loss of P(A wins) on the evaluation matches of 2013-2018 (the matches
Stage 1 tuned Elo on), every snapshot (weekly, no coarsening), over the Brief's grid half-life {0.75, 1.5, 3, 6, none}
years x lambda {0.1, 0.35, 1, 3} x anchor {0, -0.5, -1} x retirement weight {1, 0.5}; that grid's best lay at its corner
(the shortest half-life, the smallest lambda), so it was widened past it in two rounds (BT_GRID_EXT); then lambda_u for
the surface BT. MESR: the log loss of sigmoid(s_A - s_B) against the result on the evaluation matches of 2013-2018 with
odds on which both players have an MESR, over half-life {0.5, 1, 2, 4} x lambda {0.3, 1, 3} x anchor {0, -0.5, -1},
widened in three rounds (MESR_GRID_EXT). BT's tuning passes read history to the end of 2018 only; the frozen full passes
reproduce them (checked). MESR's grid runs on the whole history (its 2013-2018 values are the same, each pass being
causal) to give the out-of-sample gap to the closing log-odds as well.

Probes (stage1_baselines.probe_by_round's design, cut by date, event and round): on the matches from 2024 (history
inside the slice), at random cuts every result (or for MESR every closing probability; for the games BT also every
games share) the rule does not let the cut see is redrawn and the pass re-run; the pre-match values of the matches
the cut may see must not move. A deliberately leaky BT (snapshots that include their own date) is probed as a control.

Writes, in data/studies/ufc_ideas/:
    stageA_bt.parquet         one row per match of Stage 0's table (872,704): pre-match bt_a, bt_b, p_bt_a, the
                              players' snapshot edge counts (n_a, n_b) and earlier rounds of this event (nev_a, nev_b),
                              and the variants' ratings (bt_games_*, bt_nodecay_*, bt_surface_*; float32)
    stageA_mesr.parquet       one row per match: pre-match mesr_a, mesr_b (missing where the player has no odds edge
                              visible), p_mesr_a (where both exist), odds-edge counts, the snapshot-only values
    stageA_bt_tuning.csv      the BT grid (and the surface grid): log loss 2013-2018 per tour and setting
    stageA_mesr_tuning.csv    the MESR grid, with the out-of-sample root-mean-square gap to the closing log-odds
    stageA_bt_summary.json    the chosen constants (BT, variants, MESR), the grids' flatness, the probes, timings,
                              snapshot counts, solver statistics, and the ten highest-rated players per tour in 2026

Run (5 worker processes), in two invocations that each fit in about 45 minutes:
    ./python.sh src/eda/ufc_ideas/stageA_ratings.py --grid-only     the grids (their passes' times are in the tuning
                                                                    CSVs' "seconds"; about 44 minutes on a shared
                                                                    machine when built)
    ./python.sh src/eda/ufc_ideas/stageA_ratings.py --reuse-grid    reads the grids back (running any setting missing)
                                                                    and does the rest: the surface grid, the full passes,
                                                                    the checks, the probes, the outputs (its time is the
                                                                    summary's "seconds")
Without flags it does both in one run.

How long it ran (2 Oct 2026, 5 workers, on a machine shared with two other stages): the grids in four invocations as they
were widened (1,482, 928, 171 and 32 seconds; the passes' own times sum to 12,745 seconds, stageA_bt_summary.json
"timings"), then the --reuse-grid run in 1,285 seconds (its "seconds").
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator, cg
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "ufc_ideas"
BT_PARQUET = OUT / "stageA_bt.parquet"
MESR_PARQUET = OUT / "stageA_mesr.parquet"
BT_TUNING = OUT / "stageA_bt_tuning.csv"
MESR_TUNING = OUT / "stageA_mesr_tuning.csv"
SUMMARY = OUT / "stageA_bt_summary.json"
ODDS = C.OUT / "stage1_odds.parquet"
CONSTANTS = C.OUT / "stage4_constants.csv"

WORKERS = 5
UPDATES = ("completed", "retired")               # statuses whose result moves ratings (Stage 1's "ret" rule)
TUNE_YEARS = range(2013, 2019)
K_DECAY = 6.0                                    # the informed anchor fades over a newcomer's first six edges
MIN_W = 1e-4                                     # edges whose decay weight is below this are dropped (BT)
NEWTON_TOL = 1e-3                                # stop when the largest rating step is below this
CG_RTOL = 1e-7                                   # the conjugate gradient's relative residual
FULL_STEP = 0.5                                  # a Newton step moving no rating by more than this is taken whole
BT_GRID = {"half_life": [0.75, 1.5, 3.0, 6.0, None], "lam": [0.1, 0.35, 1.0, 3.0], "anchor": [0.0, -0.5, -1.0],
           "ret_w": [1.0, 0.5]}
SURF_GRID = [1.0, 3.0, 10.0]
MESR_GRID = {"half_life": [0.5, 1.0, 2.0, 4.0], "lam": [0.3, 1.0, 3.0], "anchor": [0.0, -0.5, -1.0]}
# The Brief's grids put the best at their corner (the shortest half-life and the smallest lambda, for BT and MESR
# alike), with the surface steep there, so each is widened past that corner, as Stage 1 widened Elo's (the
# retirement weight 1 is the better value on both tours throughout the Brief's grid, so the extension keeps it)
# (two rounds: the first round's best BT anchor, and MESR's half-life and lambda, were again at its edge)
BT_GRID_EXT = [{"half_life": [0.25, 0.35, 0.5, 0.75], "lam": [0.01, 0.03, 0.1], "anchor": [-0.5, -1.0, -1.5],
                "ret_w": [1.0]},
               {"half_life": [0.5, 0.75], "lam": [0.1], "anchor": [-2.0, -2.5], "ret_w": [1.0]}]
MESR_GRID_EXT = [{"half_life": [0.125, 0.25, 0.35, 0.5], "lam": [0.03, 0.1, 0.3], "anchor": [-1.0, -1.5, -2.0]},
                 {"half_life": [0.03, 0.06, 0.09, 0.125], "lam": [0.003, 0.01, 0.03], "anchor": [-1.0, -1.5]},
                 {"half_life": [0.09, 0.125, 0.18], "lam": [0.0003, 0.001, 0.003], "anchor": [-1.0]}]
N_SURF = len(B.SURFACES)                         # Hard, Clay, Grass, Carpet
PROBE_FROM = "2024-01-01"                        # the probes' slice
PROBE_CUTS = 6
SEED = 20261002
LAST_YEAR = None                                 # the whole table
T0 = time.time()

# A reduced run to check the script end to end (history to 2014, one or two values per constant, outputs to the
# directory named by STAGEA_SMOKE_DIR); never used for the study's outputs.
SMOKE = os.environ.get("STAGEA_SMOKE_DIR")
if SMOKE:
    OUT = Path(SMOKE)
    BT_PARQUET, MESR_PARQUET = OUT / "stageA_bt.parquet", OUT / "stageA_mesr.parquet"
    BT_TUNING, MESR_TUNING, SUMMARY = OUT / "stageA_bt_tuning.csv", OUT / "stageA_mesr_tuning.csv", OUT / "stageA_bt_summary.json"
    BT_GRID = {"half_life": [3.0, None], "lam": [1.0], "anchor": [-0.5], "ret_w": [1.0]}
    SURF_GRID = [3.0, 10.0]
    MESR_GRID = {"half_life": [1.0, 2.0], "lam": [1.0], "anchor": [-0.5]}
    BT_GRID_EXT = [{"half_life": [1.5, 3.0], "lam": [1.0], "anchor": [-0.5], "ret_w": [1.0]}]
    MESR_GRID_EXT = [{"half_life": [0.5], "lam": [1.0], "anchor": [-0.5]}]
    TUNE_YEARS = range(2013, 2014)
    LAST_YEAR = 2014
    PROBE_FROM, PROBE_CUTS = "2014-06-01", 2


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Inputs

def load_table() -> pd.DataFrame:
    """Stage 0's matches in the table's order, with the winner's share of the games (side A's row of
    stage0_match_players, as stage4_features.winner_shares reads it) and the closing-odds probability that A wins."""
    m = C.load_matches(["match_id", "tour", "year", "evaluation", "status", "surface", "tournament_id",
                        "tournament_date", "round_order", "player_a_id", "player_b_id", "a_won"])
    if LAST_YEAR is not None:
        m = m[m["year"].le(LAST_YEAR)].reset_index(drop=True)
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "games_won_n", "games_won_d"])
    ga = mp[mp["side"].eq("A")].set_index("match_id")
    gn = m["match_id"].map(ga["games_won_n"]).to_numpy(dtype="float64")
    gd = m["match_id"].map(ga["games_won_d"]).to_numpy(dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        share_a = np.where(gd > 0, gn / gd, np.nan)
    m["games_share"] = np.where(m["a_won"].to_numpy(dtype=bool), share_a, 1 - share_a)
    od = pd.read_parquet(ODDS, columns=["match_id", "p_avg_a"]).set_index("match_id")
    m["p_avg_a"] = m["match_id"].map(od["p_avg_a"]).to_numpy(dtype="float64")
    return m


def games_scales() -> dict:
    """Stage 4's weighted-Elo scale for games (the mean winner's share over the rated matches of 2010-2018)."""
    c = pd.read_csv(CONSTANTS)
    c = c[c["kind"].eq("weighted Elo scale") & c["stat"].eq("elo_games")]
    return {r["tour"]: float(r["value"]) for _, r in c.iterrows()}


def history(t: pd.DataFrame, scale: float) -> dict:
    """The arrays a pass reads for one tour's matches, already in the table's order: stage1_baselines.history_arrays
    (week = tournament date in days, event, round, players, result, surface) plus what moves ratings, the result
    weights' inputs, the closing log-odds, each side's (player, event) slot and the (date, round) groups."""
    h = {k: (np.asarray(v) if isinstance(v, list) else v) for k, v in B.history_arrays(t).items()}
    h["week"] = h["week"].astype("int64")
    h["a"], h["b"] = h["a"].astype("int64"), h["b"].astype("int64")
    h["surf"] = h["surf"].astype("int64")
    status = t["status"].to_numpy()
    h["upd"] = np.isin(status, UPDATES)
    h["ret"] = status == "retired"
    sh = t["games_share"].to_numpy(dtype="float64")
    h["games_w"] = np.where(np.isfinite(sh), sh / scale, 1.0)
    p = t["p_avg_a"].to_numpy(dtype="float64")
    h["odds_ok"] = h["upd"] & np.isfinite(p)
    h["d"] = np.where(h["odds_ok"], logit(np.clip(np.nan_to_num(p, nan=0.5), 1e-9, 1 - 1e-9)), np.nan)
    h["eval"] = t["evaluation"].to_numpy(dtype=bool)
    h["year"] = t["year"].to_numpy()
    h["match_id"] = t["match_id"].to_numpy()
    add_layout(h)
    return h


def add_layout(h: dict) -> None:
    """The per-pass layout: each side's (player, event) slot, the distinct dates and the (date, round) groups."""
    n = h["n_players"]
    ev = np.asarray(h["event"], dtype="int64")
    keys = np.concatenate([ev * n + h["a"], ev * n + h["b"]])
    slot, uniq = pd.factorize(keys)
    h["slot_a"], h["slot_b"], h["n_slots"] = slot[:len(ev)], slot[len(ev):], len(uniq)
    week, rnd = h["week"], np.asarray(h["rnd"], dtype="int64")
    assert (np.diff(week) >= 0).all(), "the table's order is by date"
    same_day = np.diff(week) == 0
    assert (np.diff(rnd)[same_day] >= 0).all(), "within a date, the table's order is by round"
    h["udays"], h["day_start"] = np.unique(week, return_index=True)
    h["day_start"] = np.append(h["day_start"], len(week))
    brk = np.flatnonzero((np.diff(week) != 0) | (np.diff(rnd) != 0)) + 1
    h["grp_start"] = np.concatenate([[0], brk, [len(week)]])
    h["day_grp"] = np.searchsorted(h["grp_start"], h["day_start"])


def subset(h: dict, rows: np.ndarray) -> dict:
    """The history restricted to a contiguous block of rows (a slice in time), with its own layout."""
    out = {k: (v[rows] if isinstance(v, np.ndarray) and len(v) == len(h["week"]) else v) for k, v in h.items()}
    for k in ("week", "event", "rnd", "a_won"):
        out[k] = np.asarray(h[k])[rows]
    add_layout(out)
    return out


# ------------------------------------------------------------------------------------------------
# The sparse design: each edge's columns and signs, and the Hessian's fixed layout

class Design:
    """The design matrix X of a set of edges in time order (one row per edge: +1 at A's columns, -1 at B's) and the
    CSR layout of X' diag(h) X + diag(ridge), so that each Newton iteration fills the Hessian with one bincount.

    The off-diagonal pairs are numbered by first appearance, so the pairs of the edges before any point form a
    prefix; the layout holds only the pairs seen so far plus the next EPOCH edges' (rebuilt when a pass moves past
    it), so early snapshots do not pay for the whole history's pattern."""

    EPOCH = 25_000

    def __init__(self, cols: np.ndarray, signs: np.ndarray, n_var: int, block_players: int | None = None):
        self.cols, self.signs, self.n_var = cols, signs, n_var
        self.block_players = block_players          # the surface BT: precondition each player's block exactly
        m, q = cols.shape
        self.simple = q == 2 and bool((signs[:, 0] == 1).all() and (signs[:, 1] == -1).all())
        psg, keys = [], []
        for i, j in itertools.combinations(range(q), 2):
            sg = signs[:, i] * signs[:, j]
            ok = (sg != 0) & (cols[:, i] != cols[:, j])
            lo, hi = np.minimum(cols[:, i], cols[:, j]), np.maximum(cols[:, i], cols[:, j])
            keys.append(np.where(ok, lo * n_var + hi, -1))
            psg.append(np.where(ok, sg, 0.0))
        keys = np.column_stack(keys)                               # (m, pairs per edge), edge-major
        valid = keys >= 0
        flat = keys.ravel()
        vpos = np.flatnonzero(valid.ravel())
        uk, first, inv = np.unique(flat[vpos], return_index=True, return_inverse=True)
        rank = np.empty(len(uk), dtype="int64")
        by_first = np.argsort(first, kind="stable")
        rank[by_first] = np.arange(len(uk))                         # number pairs by first appearance
        pid = np.zeros(flat.shape, dtype="int64")                  # invalid pairs: id 0 with sign 0 (no effect)
        pid[vpos] = rank[inv]
        self.pair_id = pid.reshape(keys.shape)
        self.pair_sign = np.column_stack(psg)
        self.n_pairs = len(uk)
        self.pair_key = uk[by_first]                               # each pair's lo * n_var + hi, by id
        first_edge = np.sort(vpos[first] // keys.shape[1])         # the edge at which each pair first appears
        self.pairs_upto = np.searchsorted(first_edge, np.arange(m + 1), side="left")   # pairs among edges < k
        self.neg = self.simple                                     # every pair's sign is -1: skip the multiply
        self.P, self.cover = -1, -1

    def _layout(self, P: int) -> None:
        n_var = self.n_var
        uk = self.pair_key[:P]
        r = np.concatenate([uk // n_var, uk % n_var, np.arange(n_var)])
        c = np.concatenate([uk % n_var, uk // n_var, np.arange(n_var)])
        order = np.lexsort((c, r))
        self.perm = order
        indices = c[order].astype("int32")
        indptr = np.concatenate([[0], np.cumsum(np.bincount(r, minlength=n_var))]).astype("int32")
        self._buf = np.empty(2 * P + n_var)
        self._H = sp.csr_matrix((np.zeros(len(order)), indices, indptr), shape=(n_var, n_var))
        self.P = P

    def eta(self, x, lo, hi):
        if self.simple:
            return x[self.cols[lo:hi, 0]] - x[self.cols[lo:hi, 1]]
        return (self.signs[lo:hi] * x[self.cols[lo:hi]]).sum(axis=1)

    def xt(self, r, lo, hi):
        """X' r over the edges lo..hi."""
        if self.simple:
            return (np.bincount(self.cols[lo:hi, 0], r, self.n_var) - np.bincount(self.cols[lo:hi, 1], r, self.n_var))
        out = np.zeros(self.n_var)
        for k in range(self.cols.shape[1]):
            out += np.bincount(self.cols[lo:hi, k], self.signs[lo:hi, k] * r, self.n_var)
        return out

    def diag(self, hh, lo, hi):
        """The data part of the Hessian's diagonal: sum of h over each column's edges."""
        if self.simple:
            return np.bincount(self.cols[lo:hi, 0], hh, self.n_var) + np.bincount(self.cols[lo:hi, 1], hh, self.n_var)
        out = np.zeros(self.n_var)
        for k in range(self.cols.shape[1]):
            out += np.bincount(self.cols[lo:hi, k], self.signs[lo:hi, k] ** 2 * hh, self.n_var)
        return out

    def hessian(self, hh, lo, hi, ridge):
        """X' diag(hh) X + diag(ridge) over the edges lo..hi, in the fixed layout (one matrix object, its data
        overwritten: use it before the next call). Also returns the data part of the diagonal."""
        if hi > self.cover or hi + 2 * self.EPOCH < self.cover:  # a new epoch (or a new pass from the start)
            self.cover = min(len(self.cols), hi + self.EPOCH)
            self._layout(int(self.pairs_upto[self.cover]))
        P, n = self.P, self.n_var
        if self.neg:
            pv = np.bincount(self.pair_id[lo:hi, 0], hh, P)
            np.negative(pv, out=self._buf[:P])
        else:
            self._buf[:P] = np.bincount(self.pair_id[lo:hi].ravel(), (self.pair_sign[lo:hi] * hh[:, None]).ravel(), P)
        self._buf[P:2 * P] = self._buf[:P]
        dd = self.diag(hh, lo, hi)
        np.add(dd, ridge, out=self._buf[2 * P:2 * P + n])
        np.take(self._buf, self.perm, out=self._H.data)
        return self._H, dd


def bt_design(h: dict, E: np.ndarray, surface: bool) -> Design:
    a, b = h["a"][E], h["b"][E]
    N = h["n_players"]
    if not surface:
        return Design(np.column_stack([a, b]), np.column_stack([np.ones(len(E)), -np.ones(len(E))]), N)
    s = h["surf"][E]
    k = s >= 0
    ua = np.where(k, N + N_SURF * a + np.maximum(s, 0), 0)
    ub = np.where(k, N + N_SURF * b + np.maximum(s, 0), 0)
    sg = np.column_stack([np.ones(len(E)), -np.ones(len(E)), np.where(k, 1.0, 0.0), np.where(k, -1.0, 0.0)])
    return Design(np.column_stack([a, b, ua, ub]), sg, N * (1 + N_SURF), block_players=N)


# ------------------------------------------------------------------------------------------------
# Solvers

def jacobi(dd, ridge, n_players=None):
    """The preconditioner: the inverse diagonal; for the surface BT (``n_players`` given) the exact inverse of each
    player's arrowhead block (s_i coupled to u_{i,surface} through the player's matches on that surface: the data
    coupling equals u's own data information), by the Schur complement."""
    full = dd + ridge
    if n_players is None:
        return lambda v: v / full
    N = n_players
    Du = full[N:].reshape(N, N_SURF)
    bc = dd[N:].reshape(N, N_SURF)
    S = full[:N] - (bc ** 2 / Du).sum(axis=1)

    def apply(v):
        vs, vu = v[:N], v[N:].reshape(N, N_SURF)
        zs = (vs - (bc * vu / Du).sum(axis=1)) / S
        return np.concatenate([zs, ((vu - bc * zs[:, None]) / Du).ravel()])
    return apply


def _cg(H, g, precond, x0=None):
    M = LinearOperator(H.shape, matvec=precond, dtype="float64")
    it = [0]

    def cb(_):
        it[0] += 1
    d, info = cg(H, g, x0=x0, rtol=CG_RTOL, atol=0.0, maxiter=5000, M=M, callback=cb)
    if info != 0:
        raise RuntimeError(f"conjugate gradient did not converge (info {info})")
    return d, it[0]


def newton_bt(x, dsg: Design, lo, hi, y, w, ridge, mvec, tol=None, max_iter=100):
    """The MAP of the weighted logistic likelihood plus the ridge toward m, by damped Newton from x: a full step when
    no rating moves by more than FULL_STEP, otherwise Armijo backtracking on the objective. Stops when the largest
    step is below tol. Returns the solution, the data part of the Hessian's diagonal at it (each variable's
    information), and the Newton and CG iteration counts."""
    tol = NEWTON_TOL if tol is None else tol

    def objective(eta_, x_):
        return float(np.sum(w * (np.logaddexp(0.0, eta_) - y * eta_)) + 0.5 * np.sum(ridge * (x_ - mvec) ** 2))
    eta = dsg.eta(x, lo, hi)
    f = None
    n_it = n_cg = 0
    for _ in range(max_iter):
        p = expit(eta)
        g = dsg.xt(w * (p - y), lo, hi) + ridge * (x - mvec)
        H, dd = dsg.hessian(w * p * (1 - p), lo, hi, ridge)
        d, k = _cg(H, -g, jacobi(dd, ridge, dsg.block_players))
        n_cg += k
        big = float(np.max(np.abs(d)))
        t = 1.0
        if big <= FULL_STEP:
            x = x + d
            eta = dsg.eta(x, lo, hi)
            f = None
        else:
            if f is None:
                f = objective(eta, x)
            gd = float(g @ d)
            while True:
                xn = x + t * d
                etan = dsg.eta(xn, lo, hi)
                fn = objective(etan, xn)
                if fn <= f + 1e-4 * t * gd or t < 1e-8:
                    break
                t *= 0.5
            x, eta, f = xn, etan, fn
        n_it += 1
        if t * big < tol:
            break
    else:
        raise RuntimeError("Newton did not converge")
    p = expit(eta)
    return x, dsg.diag(w * p * (1 - p), lo, hi), n_it, n_cg


def solve_ls(x0, dsg: Design, lo, hi, dvals, w, lam, mvec):
    """MESR's snapshot: the minimiser of sum w (d - eta)^2 + lambda ||s - m||^2 (one linear solve, warm-started)."""
    ridge = np.full(dsg.n_var, lam)
    H, dd = dsg.hessian(w, lo, hi, ridge)
    rhs = dsg.xt(w * dvals, lo, hi) + lam * mvec
    r0 = rhs - H @ x0
    if not np.any(r0):
        return x0, dd, 0
    d, k = _cg(H, r0, jacobi(dd, ridge))
    return x0 + d, dd.copy(), k


# ------------------------------------------------------------------------------------------------
# The passes

def _decay(age_days, half_life):
    if half_life is None:
        return np.ones(len(age_days))
    return np.exp2(-age_days / (365.25 * half_life))


def bt_pass(h: dict, cfg: dict, leaky: bool = False, design: Design | None = None, stats: dict | None = None,
            final_state: bool = False):
    """One chronological BT pass under the time rule. cfg: half_life (years or None), lam, anchor, ret_w, and
    optionally games (weight each edge by its games share) and lam_u (the surface BT). Returns an array with one row
    per match: A's and B's pre-match rating, their snapshot edge counts and their earlier rounds of this event.

    LEAKS across overlapping events (the match-timing audit, 5 Oct 2026; docs/decisions/2026-10-05-match-timing.md):
    a snapshot releases every result of an event whose start date precedes it, so an event still running (a Grand
    Slam's second week, an event dated earlier in the same week) reaches other players' matches played before it.
    Rebuild on the leak-proof timeline (src/eda/match_timing/timing.parquet) before any further use.
    ``leaky`` (a control for the probe only) lets a snapshot include its own date."""
    hl, lam, anchor = cfg["half_life"], float(cfg["lam"]), float(cfg["anchor"])
    lam_u = cfg.get("lam_u")
    surface = lam_u is not None
    N = h["n_players"]
    a, b, surf = h["a"], h["b"], h["surf"]
    y_all = np.asarray(h["a_won"], dtype=bool).astype("float64")
    rw = np.where(h["ret"], float(cfg["ret_w"]), 1.0) * (h["games_w"] if cfg.get("games") else 1.0)
    E = np.flatnonzero(h["upd"])
    eday, ey, erw, ea, eb = h["week"][E], y_all[E], rw[E], a[E], b[E]
    dsg = design if design is not None else bt_design(h, E, surface)
    n_var = dsg.n_var
    ridge = np.full(n_var, lam)
    if surface:
        ridge[N:] = float(lam_u)
    maxage = np.inf if hl is None else 365.25 * hl * np.log2(1.0 / MIN_W)
    x = np.zeros(n_var)
    x[:N] = anchor
    x_start = x.copy()                    # the next solve's starting point: x plus the last date's in-event steps
    dd = np.zeros(n_var)
    out = np.full((len(a), 6), np.nan)
    delta, J, nev = np.zeros(h["n_slots"]), np.zeros(h["n_slots"]), np.zeros(h["n_slots"])
    slot_a, slot_b, gs, ds_ = h["slot_a"], h["slot_b"], h["grp_start"], h["day_start"]
    prev = None
    n_it = n_cg = n_solves = 0
    for t, D in enumerate(h["udays"]):
        hi = int(np.searchsorted(eday, D, "right" if leaky else "left"))
        lo = 0 if hl is None else int(np.searchsorted(eday, D - maxage, "left"))
        cnt = np.bincount(ea[lo:hi], minlength=N) + np.bincount(eb[lo:hi], minlength=N)
        if hi > lo:
            if hl is not None or prev != (lo, hi):
                mvec = np.zeros(n_var)
                mvec[:N] = anchor * np.maximum(0.0, 1.0 - cnt / K_DECAY)
                w = erw[lo:hi] * _decay((D - eday[lo:hi]).astype("float64"), hl)
                x, dd, k1, k2 = newton_bt(x_start, dsg, lo, hi, ey[lo:hi], w, ridge, mvec)
                n_it, n_cg, n_solves = n_it + k1, n_cg + k2, n_solves + 1
        else:
            x = np.zeros(n_var)
            x[:N] = anchor
            dd = np.zeros(n_var)
        prev = (lo, hi)
        x_start = x.copy()
        info_s = dd[:N] + lam
        for g in range(h["day_grp"][t], h["day_grp"][t + 1]):
            i0, i1 = gs[g], gs[g + 1]
            pa, pb, sa, sb, su = a[i0:i1], b[i0:i1], slot_a[i0:i1], slot_b[i0:i1], surf[i0:i1]
            base_a, base_b = x[pa].copy(), x[pb].copy()
            ia, ib = info_s[pa].copy(), info_s[pb].copy()
            if surface:
                k = su >= 0
                if k.any():
                    ca, cb_ = N + N_SURF * pa[k] + su[k], N + N_SURF * pb[k] + su[k]
                    base_a[k] += x[ca]
                    base_b[k] += x[cb_]
                    ia[k] = _eff_info(ia[k], dd[ca], float(lam_u))
                    ib[k] = _eff_info(ib[k], dd[cb_], float(lam_u))
            ra, rb = base_a + delta[sa], base_b + delta[sb]
            out[i0:i1, 0], out[i0:i1, 1] = ra, rb
            out[i0:i1, 2], out[i0:i1, 3] = cnt[pa], cnt[pb]
            out[i0:i1, 4], out[i0:i1, 5] = nev[sa], nev[sb]
            u = h["upd"][i0:i1]
            if u.any():
                p = expit(ra[u] - rb[u])
                wk = rw[i0:i1][u]
                hk = wk * p * (1 - p)
                r = wk * (y_all[i0:i1][u] - p)
                ua, ub = sa[u], sb[u]
                step_a = r / (hk + ia[u] + J[ua])
                step_b = -r / (hk + ib[u] + J[ub])
                np.add.at(delta, ua, step_a)
                np.add.at(delta, ub, step_b)
                np.add.at(J, ua, hk)
                np.add.at(J, ub, hk)
                np.add.at(nev, ua, 1.0)
                np.add.at(nev, ub, 1.0)
        # warm start for the next snapshot: each player's in-event steps of this date (a starting point only; the
        # next snapshot's solution does not depend on it beyond the solver's tolerance)
        sl = np.concatenate([slot_a[ds_[t]:ds_[t + 1]], slot_b[ds_[t]:ds_[t + 1]]])
        pl = np.concatenate([a[ds_[t]:ds_[t + 1]], b[ds_[t]:ds_[t + 1]]])
        u_sl, first = np.unique(sl, return_index=True)
        x_start[:N] += np.bincount(pl[first], delta[u_sl], minlength=N)
    if stats is not None:
        stats.update({"snapshots": int(len(h["udays"])), "solves": n_solves, "newton_iterations": n_it,
                      "cg_iterations": n_cg})
    if final_state:
        return out, x
    return out


def _eff_info(Hs, Iu, lam_u):
    """The information of the combined rating s_i + u_{i,surface} from the 2 x 2 block of the Hessian (Hs = I_i +
    lambda, Iu = the player's information on the surface): 1 / ([1 1] H^-1 [1 1]')."""
    Hu = Iu + lam_u
    return (Hs * Hu - Iu ** 2) / (Hs + Hu - 2 * Iu)


def mesr_pass(h: dict, cfg: dict, leaky: bool = False, design: Design | None = None, stats: dict | None = None):
    """One chronological MESR pass under the time rule. cfg: half_life (years), lam, anchor. Returns per match: A's
    and B's pre-match MESR (missing where the player has no odds edge visible), their snapshot odds-edge counts and
    earlier rounds of this event with odds, and the snapshot-only values.

    LEAKS across overlapping events as bt_pass does (the match-timing audit, 5 Oct 2026), and its edges are closing
    odds, so a later-played match's price can reach an earlier-played match. Rebuild on the leak-proof timeline
    (src/eda/match_timing/timing.parquet) before any further use."""
    hl, lam, anchor = float(cfg["half_life"]), float(cfg["lam"]), float(cfg["anchor"])
    N = h["n_players"]
    a, b = h["a"], h["b"]
    dvals_all = np.asarray(h["d"], dtype="float64")
    ok = np.asarray(h["odds_ok"], dtype=bool)
    E = np.flatnonzero(ok)
    eday, ed, ea, eb = h["week"][E], dvals_all[E], a[E], b[E]
    dsg = design if design is not None else Design(np.column_stack([ea, eb]),
                                                   np.column_stack([np.ones(len(E)), -np.ones(len(E))]), N)
    x = np.full(N, anchor)
    dd = np.zeros(N)
    out = np.full((len(a), 8), np.nan)
    delta, J, nev = np.zeros(h["n_slots"]), np.zeros(h["n_slots"]), np.zeros(h["n_slots"])
    slot_a, slot_b, gs = h["slot_a"], h["slot_b"], h["grp_start"]
    n_cg = n_solves = 0
    for t, D in enumerate(h["udays"]):
        hi = int(np.searchsorted(eday, D, "right" if leaky else "left"))
        cnt = np.bincount(ea[:hi], minlength=N) + np.bincount(eb[:hi], minlength=N)
        mvec = np.where(cnt <= 1, anchor, 0.0)
        if hi > 0:
            w = _decay((D - eday[:hi]).astype("float64"), hl)
            x, dd, k = solve_ls(x, dsg, 0, hi, ed[:hi], w, lam, mvec)
            n_cg, n_solves = n_cg + k, n_solves + 1
        else:
            x, dd = mvec.copy(), np.zeros(N)
        info = dd + lam
        for g in range(h["day_grp"][t], h["day_grp"][t + 1]):
            i0, i1 = gs[g], gs[g + 1]
            pa, pb, sa, sb = a[i0:i1], b[i0:i1], slot_a[i0:i1], slot_b[i0:i1]
            ra, rb = x[pa] + delta[sa], x[pb] + delta[sb]
            ea_ok, eb_ok = (cnt[pa] + nev[sa]) > 0, (cnt[pb] + nev[sb]) > 0
            out[i0:i1, 0] = np.where(ea_ok, ra, np.nan)
            out[i0:i1, 1] = np.where(eb_ok, rb, np.nan)
            out[i0:i1, 2], out[i0:i1, 3] = cnt[pa], cnt[pb]
            out[i0:i1, 4], out[i0:i1, 5] = nev[sa], nev[sb]
            out[i0:i1, 6] = np.where(cnt[pa] > 0, x[pa], np.nan)
            out[i0:i1, 7] = np.where(cnt[pb] > 0, x[pb], np.nan)
            u = ok[i0:i1]
            if u.any():
                resid = dvals_all[i0:i1][u] - (ra[u] - rb[u])
                ua, ub = sa[u], sb[u]
                np.add.at(delta, ua, resid / (1.0 + info[pa[u]] + J[ua]))
                np.add.at(delta, ub, -resid / (1.0 + info[pb[u]] + J[ub]))
                np.add.at(J, ua, 1.0)
                np.add.at(J, ub, 1.0)
                np.add.at(nev, ua, 1.0)
                np.add.at(nev, ub, 1.0)
    if stats is not None:
        stats.update({"snapshots": int(len(h["udays"])), "solves": n_solves, "cg_iterations": n_cg})
    return out


# ------------------------------------------------------------------------------------------------
# Workers (tuning and the full passes run in a pool of WORKERS processes)

_W: dict = {}


def init_worker() -> None:
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    m = load_table()
    sc = games_scales()
    for tour in C.TOURS:
        t = m[m["tour"].eq(tour)].reset_index(drop=True)
        _W[(tour, "full")] = history(t, sc[tour])
        last = int(np.flatnonzero(t["year"].le(TUNE_YEARS[-1]).to_numpy()).max())
        _W[(tour, "tune")] = history(t.iloc[:last + 1].reset_index(drop=True), sc[tour])


def _hist(tour: str, span: str) -> dict:
    if not _W:
        init_worker()
    return _W[(tour, span)]


def _design(tour: str, span: str, kind: str) -> Design:
    key = ("design", tour, span, kind)
    if key not in _W:
        h = _hist(tour, span)
        if kind == "mesr":
            E = np.flatnonzero(h["odds_ok"])
            _W[key] = Design(np.column_stack([h["a"][E], h["b"][E]]),
                             np.column_stack([np.ones(len(E)), -np.ones(len(E))]), h["n_players"])
        else:
            _W[key] = bt_design(h, np.flatnonzero(h["upd"]), kind == "surface")
    return _W[key]


def tune_eval_mask(h: dict) -> np.ndarray:
    return h["eval"] & np.isin(h["year"], list(TUNE_YEARS))


def job(spec: dict) -> dict:
    """One pass: spec = {kind: bt | mesr, tour, span: tune | full, cfg}, optionally return_rows (the per-match
    array), final_state (the last snapshot's ratings) and tight (the solver's tolerances tightened, as a check)."""
    global NEWTON_TOL, CG_RTOL
    t0 = time.time()
    h = _hist(spec["tour"], spec["span"])
    st: dict = {}
    x_last = None
    if spec["kind"] == "bt":
        kind = "surface" if spec["cfg"].get("lam_u") is not None else "plain"
        saved = (NEWTON_TOL, CG_RTOL)
        if spec.get("tight"):
            NEWTON_TOL, CG_RTOL = 1e-8, 1e-11
        try:
            res = bt_pass(h, spec["cfg"], design=_design(spec["tour"], spec["span"], kind), stats=st,
                          final_state=bool(spec.get("final_state")))
        finally:
            NEWTON_TOL, CG_RTOL = saved
        if spec.get("final_state"):
            res, x_last = res
        p = expit(res[:, 0] - res[:, 1])
        mask = tune_eval_mask(h)
        rec = {"log_loss_2013_2018": B.log_loss(p[mask], h["a_won"][mask]), "matches": int(mask.sum())}
    else:
        res = mesr_pass(h, spec["cfg"], design=_design(spec["tour"], spec["span"], "mesr"), stats=st)
        p = expit(res[:, 0] - res[:, 1])
        mask = tune_eval_mask(h) & h["odds_ok"] & np.isfinite(p)
        rec = {"log_loss_2013_2018": B.log_loss(p[mask], h["a_won"][mask]), "matches": int(mask.sum())}
        late = h["eval"] & h["odds_ok"] & np.isfinite(p) & (h["year"] >= 2019)
        gap = (res[late, 0] - res[late, 1]) - h["d"][late]
        rec.update({"rms_gap_2019_2026": float(np.sqrt(np.mean(gap ** 2))) if late.any() else np.nan,
                    "rms_gap_matches": int(late.sum())})
    rec.update({"tour": spec["tour"], "kind": spec["kind"], **{k: v for k, v in spec["cfg"].items()},
                "seconds": round(time.time() - t0, 2), **st})
    if spec.get("return_rows"):
        rec["rows"] = res
    if x_last is not None:
        rec["x_last"] = x_last
    return rec


def probe_job(spec: dict) -> dict:
    """The probes cut by date, event and round, on the matches from PROBE_FROM (history inside the slice)."""
    t0 = time.time()
    h_full = _hist(spec["tour"], "full")
    rows = np.flatnonzero(h_full["week"] >= np.datetime64(PROBE_FROM, "D").astype("int64"))
    h = subset(h_full, rows)
    cfg, what = spec["cfg"], spec["what"]
    if what in ("bt", "bt_leaky"):
        leaky = what == "bt_leaky"

        def ratings(hh):
            return bt_pass({**h, "a_won": np.asarray(hh["a_won"], dtype=bool)}, cfg, leaky=leaky)
        res = B.probe_by_round(h, ratings, n_cuts=PROBE_CUTS, seed=SEED, from_quantile=0.5)
    else:
        res = probe_generic(h, what, cfg, n_cuts=PROBE_CUTS, seed=SEED)
    return {"tour": spec["tour"], "what": what, **res, "slice_matches": int(len(rows)),
            "slice_from": PROBE_FROM, "seconds": round(time.time() - t0, 1)}


def probe_generic(h: dict, what: str, cfg: dict, n_cuts: int, seed: int, from_quantile: float = 0.5) -> dict:
    """stage1_baselines.probe_by_round with the input the pass reads redrawn: for the games BT the result and the
    games share, for the surface BT the result, for MESR the closing log-odds."""
    rng = np.random.default_rng(seed)

    def run(hh):
        return mesr_pass(hh, cfg) if what == "mesr" else bt_pass(hh, cfg)
    base = run(h)
    week, event, rnd = h["week"], np.asarray(h["event"]), np.asarray(h["rnd"])
    cand = np.flatnonzero(week >= np.quantile(week, from_quantile))
    changed_protected = protected = changed_open = 0
    for c in rng.choice(cand, size=min(n_cuts, len(cand)), replace=False):
        later = (week > week[c]) | ((week == week[c]) & ((event != event[c]) | (rnd >= rnd[c])))
        keep = (week < week[c]) | ((week == week[c]) & (event == event[c]) & (rnd <= rnd[c]))
        hh = dict(h)
        if what == "mesr":
            hh["d"] = np.where(later & h["odds_ok"], rng.normal(0.0, 1.5, len(week)), h["d"])
        else:
            won = np.asarray(h["a_won"], dtype=bool)
            hh["a_won"] = np.where(later & (rng.random(len(week)) < 0.5), ~won, won)
            if cfg.get("games"):
                hh["games_w"] = np.where(later, rng.uniform(0.5, 1.6, len(week)), h["games_w"])
        got = run(hh)
        diff = ~np.all(np.isclose(got, base, equal_nan=True), axis=1)
        protected += int(keep.sum())
        changed_protected += int((diff & keep).sum())
        changed_open += int((diff & ~keep).sum())
    return {"cuts": int(min(n_cuts, len(cand))), "protected_matches_checked": protected,
            "protected_matches_changed": changed_protected, "later_matches_changed": changed_open}


# ------------------------------------------------------------------------------------------------
# Summaries

def flatness(g: pd.DataFrame, params: list[str]) -> dict:
    """How flat a tuning grid is: its best and worst, how many settings come within 0.1, 0.5 and 1 milli-log-loss of
    the best, and the best log loss at each value of each constant (the others free)."""
    best = float(g["log_loss_2013_2018"].min())
    out = {"best": best, "worst": float(g["log_loss_2013_2018"].max()), "settings": int(len(g)),
           "within_0_1_milli": int((g["log_loss_2013_2018"] <= best + 0.0001).sum()),
           "within_0_5_milli": int((g["log_loss_2013_2018"] <= best + 0.0005).sum()),
           "within_1_milli": int((g["log_loss_2013_2018"] <= best + 0.001).sum()), "best_by_value": {}}
    for p in params:
        col = g[p].astype(object).where(g[p].notna(), "none")
        out["best_by_value"][p] = {str(k): {"log_loss": float(v), "milli_above_best": round(1000 * (float(v) - best), 3)}
                                   for k, v in g.groupby(col)["log_loss_2013_2018"].min().items()}
    return out


def top_players(h: dict, x: np.ndarray, names: pd.Series, players: np.ndarray, year: int, k: int = 10) -> list:
    """The k highest BT ratings at the final snapshot among players with a rated match in ``year``."""
    act = np.zeros(h["n_players"], dtype=bool)
    sel = h["upd"] & (h["year"] == year)
    act[h["a"][sel]] = True
    act[h["b"][sel]] = True
    idx = np.flatnonzero(act)
    order = idx[np.argsort(-x[idx])][:k]
    return [{"rank": i + 1, "player_id": str(players[j]), "name": str(names.get(players[j], "")),
             "bt": round(float(x[j]), 4)} for i, j in enumerate(order)]


def player_names() -> pd.Series:
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "player_id", "player_name"])
    mo = C.load_matches(["match_id", "order"]).set_index("match_id")["order"]
    mp["order"] = mp["match_id"].map(mo)
    return mp.sort_values("order").groupby("player_id")["player_name"].last()


# ------------------------------------------------------------------------------------------------

def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """zstd with byte-stream-split for the float columns (random-looking floats compress about a quarter better)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    fl = [c for c in df.columns if df[c].dtype.kind == "f"]
    strs = [c for c in df.columns if df[c].dtype.kind not in "fiub"]
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), path, compression="zstd", compression_level=12,
                   use_dictionary=strs, use_byte_stream_split=fl)


def cfg_of(row) -> dict:
    hl = row.get("half_life")
    none = hl is None or (isinstance(hl, str) and hl == "none") or (isinstance(hl, float) and np.isnan(hl))
    return {"half_life": None if none else float(hl), "lam": float(row["lam"]), "anchor": float(row["anchor"]),
            "ret_w": float(row["ret_w"])}


def choose(grid: pd.DataFrame, mgrid: pd.DataFrame) -> tuple[dict, dict, dict]:
    chosen, nodecay, mchosen = {}, {}, {}
    for tour in C.TOURS:
        g = grid[grid["tour"].eq(tour)]
        chosen[tour] = cfg_of(g.loc[g["log_loss_2013_2018"].idxmin()])
        none = g["half_life"].isna() | g["half_life"].astype(str).eq("none")
        gn = g[none]
        nodecay[tour] = cfg_of(gn.loc[gn["log_loss_2013_2018"].idxmin()])
        mg = mgrid[mgrid["tour"].eq(tour)]
        br = mg.loc[mg["log_loss_2013_2018"].idxmin()]
        mchosen[tour] = {"half_life": float(br["half_life"]), "lam": float(br["lam"]), "anchor": float(br["anchor"])}
    return chosen, nodecay, mchosen


def write_tuning(grid: pd.DataFrame, sgrid: pd.DataFrame | None, mgrid: pd.DataFrame) -> None:
    parts = [grid] + ([sgrid.assign(grid="surface")] if sgrid is not None else [])
    tuning = pd.concat(parts, ignore_index=True)
    tuning["half_life"] = tuning["half_life"].astype(object).where(tuning["half_life"].notna(), "none")
    if "lam_u" not in tuning:
        tuning["lam_u"] = np.nan
    cols = ["grid", "tour", "half_life", "lam", "anchor", "ret_w", "lam_u", "log_loss_2013_2018", "matches", "seconds",
            "snapshots", "solves", "newton_iterations", "cg_iterations"]
    tuning[cols].sort_values(["grid", "tour", "log_loss_2013_2018"]).to_csv(BT_TUNING, index=False)
    mcols = ["grid", "tour", "half_life", "lam", "anchor", "log_loss_2013_2018", "matches", "rms_gap_2019_2026",
             "rms_gap_matches", "seconds", "snapshots", "solves", "cg_iterations"]
    mgrid[mcols].sort_values(["grid", "tour", "log_loss_2013_2018"]).to_csv(MESR_TUNING, index=False)


def grid_of(g: pd.DataFrame, tour: str, cfg: dict, kind: str) -> str:
    """The grid label of a chosen setting."""
    for r in g[g["tour"].eq(tour)].to_dict("records"):
        if spec_key(kind, tour, r) == spec_key(kind, tour, cfg):
            return str(r["grid"])
    return ""


def on_edge(g: pd.DataFrame, cfg: dict, params: list[str]) -> dict:
    """For each constant, whether the chosen value is the smallest or largest value tried (no decay counts as the
    longest half-life)."""
    out = {}
    for p in params:
        vals = g[p].astype(float).fillna(np.inf) if p == "half_life" else g[p].astype(float)
        v = cfg[p]
        v = np.inf if v is None else float(v)
        out[p] = {"value": "none" if np.isinf(v) else v, "lowest_tried": bool(v <= vals.min()),
                  "highest_tried": bool(v >= vals.max())}
    return out


def spec_key(kind: str, tour: str, cfg: dict) -> tuple:
    hl = cfg.get("half_life")
    hl = "none" if hl is None or (isinstance(hl, float) and np.isnan(hl)) or hl == "none" else round(float(hl), 6)
    key = (kind, tour, hl, round(float(cfg["lam"]), 6), round(float(cfg["anchor"]), 6))
    return key + ((round(float(cfg["ret_w"]), 6),) if kind == "bt" else ())


def grid_specs() -> list[dict]:
    """Every setting of the Brief's grids and of their extensions, each labelled with its grid (a setting in both is
    the Brief's). BT's grid runs on the tuning history; MESR's on the whole history (cheap): its 2013-2018 values are
    a tuning pass's, since each pass is causal, and 2019-2026 gives the out-of-sample gap to the closing log-odds."""
    specs, seen = [], set()
    for kind, span, grids in (("bt", "tune", [("bt", BT_GRID)] + [("bt_extended", g) for g in BT_GRID_EXT]),
                              ("mesr", "full", [("mesr", MESR_GRID)] + [("mesr_extended", g) for g in MESR_GRID_EXT])):
        for label, G in grids:
            for tour in C.TOURS:
                for vals in itertools.product(*G.values()):
                    cfg = dict(zip(G.keys(), vals))
                    key = spec_key(kind, tour, cfg)
                    if key not in seen:
                        seen.add(key)
                        specs.append({"kind": kind, "tour": tour, "span": span, "grid": label, "cfg": cfg})
    return specs


def read_grids() -> list[dict]:
    """The grid rows an earlier run wrote (stageA_bt_tuning.csv, stageA_mesr_tuning.csv), as job records."""
    recs = []
    if BT_TUNING.exists():
        t = pd.read_csv(BT_TUNING)
        t = t[~t["grid"].eq("surface")]
        t["half_life"] = pd.to_numeric(t["half_life"].replace("none", np.nan))
        recs += [{**r, "kind": "bt"} for r in t.drop(columns=["lam_u"]).to_dict("records")]
    if MESR_TUNING.exists():
        t = pd.read_csv(MESR_TUNING)
        if "grid" not in t:
            t["grid"] = "mesr"
        recs += [{**r, "kind": "mesr"} for r in t.to_dict("records")]
    return recs


def final_snapshot(h: dict, cfg: dict, x_last: np.ndarray) -> tuple[np.ndarray, str]:
    """One more snapshot a week after the table's last date, from every edge (the ratings as of the end of the
    table), warm-started from the pass's last snapshot."""
    E = np.flatnonzero(h["upd"])
    D = int(h["udays"][-1]) + 7
    dec = _decay((D - h["week"][E]).astype("float64"), cfg["half_life"])
    keep = dec >= (MIN_W if cfg["half_life"] is not None else 0.0)
    w = np.where(h["ret"][E], cfg["ret_w"], 1.0) * dec
    E, w = E[keep], w[keep]
    N = h["n_players"]
    cnt = np.bincount(h["a"][E], minlength=N) + np.bincount(h["b"][E], minlength=N)
    mvec = cfg["anchor"] * np.maximum(0.0, 1.0 - cnt / K_DECAY)
    x, _, _, _ = newton_bt(x_last, bt_design(h, E, False), 0, len(E), np.asarray(h["a_won"], dtype=float)[E], w,
                           np.full(N, cfg["lam"]), mvec)
    return x, str(pd.Timestamp(D, unit="D").date())


def main(argv: list[str] | None = None) -> int:
    """Phases (each in the pool): 1. the BT and MESR grids on the tuning history (written at once; --reuse-grid reads
    them back instead); 2. the surface grid, the full passes (primary, games, no-decay, MESR) and the checks (the
    chosen tuning pass again, and with tight tolerances); 3. the surface BT's full pass and the probes."""
    argv = sys.argv[1:] if argv is None else argv
    OUT.mkdir(parents=True, exist_ok=True)
    for var in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[var] = "1"
    timings = {}
    m = load_table()
    sc = games_scales()
    log(f"matches: {len(m):,}; games scale {sc}")
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker) as ex:
        # ---- phase 1: the BT and MESR grids and their extensions (with --reuse-grid, the settings an earlier run
        # wrote are read back and only the missing ones run)
        t1 = time.time()
        specs = grid_specs()
        done = read_grids() if "--reuse-grid" in argv else []
        have = {spec_key(r["kind"], r["tour"], r) for r in done}
        todo = [s for s in specs if spec_key(s["kind"], s["tour"], s["cfg"]) not in have]
        todo.sort(key=lambda s: (s["kind"] != "bt", s["cfg"].get("lam", 0), s["tour"]))   # the slowest first
        log(f"grids: {len(specs)} settings, {len(specs) - len(todo)} read back, {len(todo)} to run")
        recs = list(done)
        for i, r in enumerate(ex.map(job, todo, chunksize=1)):
            recs.append(r)
            if (i + 1) % 20 == 0:
                log(f"  grid: {i + 1} of {len(todo)} passes")
        wanted = {spec_key(s["kind"], s["tour"], s["cfg"]): s["grid"] for s in specs}
        for r in recs:                                       # every row labelled with the grid that defines it
            r["grid"] = wanted.get(spec_key(r["kind"], r["tour"], r), r.get("grid"))
        grid = pd.DataFrame([r for r in recs if r["kind"] == "bt"])
        mgrid = pd.DataFrame([r for r in recs if r["kind"] == "mesr"])
        write_tuning(grid, None, mgrid)
        timings["grids_seconds_this_run"] = round(time.time() - t1, 1)
        timings["grid_passes_run_this_run"] = len(todo)
        timings["grid_passes_read_back"] = len(specs) - len(todo)
        timings["grid_pass_seconds_total"] = round(float(grid["seconds"].sum() + mgrid["seconds"].sum()), 1)
        log(f"grids done in {timings['grids_seconds_this_run']}s; written")
        chosen, nodecay, mchosen = choose(grid, mgrid)
        for tour in C.TOURS:
            log(f"{tour}: BT {chosen[tour]}; no decay {nodecay[tour]}; MESR {mchosen[tour]}")
        if "--grid-only" in argv:
            return 0

        # ---- phase 2: the surface grid, the full passes, the checks
        t2 = time.time()
        specs2 = [{"kind": "bt", "tour": tour, "span": "tune", "cfg": {**chosen[tour], "lam_u": lu}, "name": "surface_grid"}
                  for tour in C.TOURS for lu in SURF_GRID]
        for tour in C.TOURS:
            specs2.append({"kind": "bt", "tour": tour, "span": "full", "cfg": {**chosen[tour]}, "name": "bt",
                           "return_rows": True, "final_state": True})
            specs2.append({"kind": "bt", "tour": tour, "span": "full", "cfg": {**chosen[tour], "games": True},
                           "name": "bt_games", "return_rows": True})
            if chosen[tour]["half_life"] is not None:
                specs2.append({"kind": "bt", "tour": tour, "span": "full", "cfg": {**nodecay[tour]}, "name": "bt_nodecay",
                               "return_rows": True})
            specs2.append({"kind": "mesr", "tour": tour, "span": "full", "cfg": {**mchosen[tour]}, "name": "mesr",
                           "return_rows": True})
            specs2.append({"kind": "bt", "tour": tour, "span": "tune", "cfg": {**chosen[tour]}, "name": "check",
                           "return_rows": True})
            specs2.append({"kind": "bt", "tour": tour, "span": "tune", "cfg": {**chosen[tour]}, "name": "check_tight",
                           "return_rows": True, "tight": True})
        specs2.sort(key=lambda s: (s["name"] != "surface_grid", s["span"] != "full"))
        res2 = list(ex.map(job, specs2, chunksize=1))
        sgrid = pd.DataFrame([r for s, r in zip(specs2, res2) if s["name"] == "surface_grid"])
        full = {(s["name"], s["tour"]): r for s, r in zip(specs2, res2) if s["name"] != "surface_grid"}
        timings["surface_grid_full_passes_and_checks_seconds"] = round(time.time() - t2, 1)
        lam_u = {}
        for tour in C.TOURS:
            g = sgrid[sgrid["tour"].eq(tour)]
            lam_u[tour] = float(g.loc[g["log_loss_2013_2018"].idxmin(), "lam_u"])
        write_tuning(grid, sgrid, mgrid)
        log(f"phase 2 done in {timings['surface_grid_full_passes_and_checks_seconds']}s; lambda_u {lam_u}")

        # ---- phase 3: the surface BT's full pass and the probes
        t3 = time.time()
        specs3 = [{"kind": "bt", "tour": tour, "span": "full", "cfg": {**chosen[tour], "lam_u": lam_u[tour]},
                   "return_rows": True, "name": "bt_surface"} for tour in C.TOURS]
        probe_specs = []
        for tour in C.TOURS:
            probe_specs += [{"tour": tour, "what": "bt_surface", "cfg": {**chosen[tour], "lam_u": lam_u[tour]}},
                            {"tour": tour, "what": "bt", "cfg": chosen[tour]},
                            {"tour": tour, "what": "bt_leaky", "cfg": chosen[tour]},
                            {"tour": tour, "what": "bt_games", "cfg": {**chosen[tour], "games": True}},
                            {"tour": tour, "what": "mesr", "cfg": mchosen[tour]}]
        f3 = [ex.submit(job, s) for s in specs3]
        fp = [ex.submit(probe_job, s) for s in probe_specs]
        for s, f in zip(specs3, f3):
            full[(s["name"], s["tour"])] = f.result()
        probes = [f.result() for f in fp]
        timings["surface_full_and_probes_seconds"] = round(time.time() - t3, 1)
        for p in probes:
            log(f"probe {p['tour']} {p['what']}: {p['protected_matches_changed']} of {p['protected_matches_checked']} "
                f"protected changed; {p['later_matches_changed']} later changed")

    # ---- checks: the tuning pass is the full pass's prefix; the solver's tolerance against a tight solve
    checks = {}
    for tour in C.TOURS:
        r_t, r_f = full[("check", tour)]["rows"], full[("bt", tour)]["rows"]
        r_tt = full[("check_tight", tour)]["rows"]
        checks[tour] = {"tuning_pass_vs_full_pass_prefix_max_abs": float(np.max(np.abs(r_t[:, :2] - r_f[:len(r_t), :2]))),
                        "rows": int(len(r_t)),
                        "standard_vs_tight_tolerance_max_abs": float(np.max(np.abs(r_t[:, :2] - r_tt[:, :2]))),
                        "tight": {"newton_tol": 1e-8, "cg_rtol": 1e-11},
                        "log_loss_2013_2018_standard": full[("check", tour)]["log_loss_2013_2018"],
                        "log_loss_2013_2018_tight": full[("check_tight", tour)]["log_loss_2013_2018"],
                        "grid_log_loss_2013_2018": float(grid[grid["tour"].eq(tour)]["log_loss_2013_2018"].min())}
        log(f"checks {tour}: {checks[tour]}")
        assert checks[tour]["tuning_pass_vs_full_pass_prefix_max_abs"] < 1e-6, checks
        assert checks[tour]["standard_vs_tight_tolerance_max_abs"] < 1e-4, checks

    # ---- outputs: stageA_bt.parquet, stageA_mesr.parquet
    out = m[["match_id", "tour", "year"]].copy()
    blocks = {k: np.full((len(m), 6), np.nan) for k in ("bt", "bt_games", "bt_nodecay", "bt_surface")}
    mblock = np.full((len(m), 8), np.nan)
    for tour in C.TOURS:
        idx = np.flatnonzero(m["tour"].eq(tour).to_numpy())
        for k in blocks:
            key = (k, tour) if (k, tour) in full else ("bt", tour)        # no separate no-decay pass: the primary
            assert full[key]["rows"].shape[0] == len(idx)
            blocks[k][idx] = full[key]["rows"]
        mblock[idx] = full[("mesr", tour)]["rows"]
    bt = blocks["bt"]
    out["bt_a"], out["bt_b"] = bt[:, 0], bt[:, 1]
    out["p_bt_a"] = expit(bt[:, 0] - bt[:, 1])
    out["n_a"], out["n_b"] = bt[:, 2].astype("int16"), bt[:, 3].astype("int16")
    out["nev_a"], out["nev_b"] = bt[:, 4].astype("int8"), bt[:, 5].astype("int8")
    for k in ("bt_games", "bt_nodecay", "bt_surface"):
        out[f"{k}_a"], out[f"{k}_b"] = blocks[k][:, 0].astype("float32"), blocks[k][:, 1].astype("float32")
    write_parquet(out, BT_PARQUET)
    mo = m[["match_id", "tour", "year"]].copy()
    mo["mesr_a"], mo["mesr_b"] = mblock[:, 0], mblock[:, 1]
    mo["p_mesr_a"] = expit(mblock[:, 0] - mblock[:, 1])
    mo["n_odds_a"], mo["n_odds_b"] = mblock[:, 2].astype("int32"), mblock[:, 3].astype("int32")
    mo["nev_odds_a"], mo["nev_odds_b"] = mblock[:, 4].astype("int16"), mblock[:, 5].astype("int16")
    mo["mesr_snap_a"], mo["mesr_snap_b"] = mblock[:, 6].astype("float32"), mblock[:, 7].astype("float32")
    write_parquet(mo, MESR_PARQUET)
    log(f"wrote {BT_PARQUET.name} ({BT_PARQUET.stat().st_size / 1e6:.1f} MB), {MESR_PARQUET.name} "
        f"({MESR_PARQUET.stat().st_size / 1e6:.1f} MB)")

    # ---- the ten highest-rated players per tour at the end of the table (2026)
    names = player_names()
    top = {}
    init_worker()
    for tour in C.TOURS:
        h = _hist(tour, "full")
        t = m[m["tour"].eq(tour)]
        players = np.unique(np.concatenate([t["player_a_id"].to_numpy(), t["player_b_id"].to_numpy()]))
        x_end, as_of = final_snapshot(h, chosen[tour], full[("bt", tour)]["x_last"])
        top[tour] = {"as_of": as_of, "players": top_players(h, x_end, names, players, 2026)}
        log(f"top {tour}: " + ", ".join(p["name"] for p in top[tour]["players"]))

    # ---- the summary
    def solver_stats(r):
        return {k: r[k] for k in ("snapshots", "solves", "newton_iterations", "cg_iterations", "seconds") if k in r}

    def mesr_row(tour):
        mg = mgrid[mgrid["tour"].eq(tour)]
        c = mchosen[tour]
        return mg[mg["half_life"].eq(c["half_life"]) & mg["lam"].eq(c["lam"]) & mg["anchor"].eq(c["anchor"])].iloc[0]
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "design": {"anchor_rule": f"informed: m_i = anchor x max(0, 1 - n_i / {K_DECAY:g}), n_i the player's edges in "
                                  "the snapshot", "k_decay": K_DECAY, "min_decay_weight": MIN_W,
                   "newton_tol": NEWTON_TOL, "cg_rtol": CG_RTOL, "full_step": FULL_STEP,
                   "updates": list(UPDATES), "tuning_years": [TUNE_YEARS[0], TUNE_YEARS[-1]],
                   "snapshots": "every distinct tournament date of the tour, from earlier dates' edges",
                   "within_event": "one-step local Newton update per earlier round of the same event",
                   "mesr_anchor_rule": "m_i = anchor for a player with at most one odds edge in the snapshot, 0 otherwise",
                   "mesr_edges": "matches with a coherent closing-odds probability (stage1_odds.parquet p_avg_a), "
                                 "completed or retired, from 2010",
                   "games_weight": "the winner's share of the games over Stage 4's 2010-2018 mean (1 where the score "
                                   "has no games), times the retirement weight"},
        "grids": {"bt": {k: [("none" if v is None else v) for v in vals] for k, vals in BT_GRID.items()},
                  "bt_extended": BT_GRID_EXT, "surface_lam_u": SURF_GRID, "mesr": MESR_GRID,
                  "mesr_extended": MESR_GRID_EXT},
        "chosen_from_grid": {tour: {"bt": grid_of(grid, tour, chosen[tour], "bt"),
                                    "mesr": grid_of(mgrid, tour, mchosen[tour], "mesr")} for tour in C.TOURS},
        "on_edge_of_settings_tried": {tour: {"bt": on_edge(grid[grid["tour"].eq(tour)], chosen[tour], list(BT_GRID)),
                                             "mesr": on_edge(mgrid[mgrid["tour"].eq(tour)], mchosen[tour], list(MESR_GRID)),
                                             "surface_lam_u": on_edge(sgrid[sgrid["tour"].eq(tour)], {"lam_u": lam_u[tour]},
                                                                      ["lam_u"])} for tour in C.TOURS},
        "games_scale": sc,
        "chosen": {tour: {"bt": {**chosen[tour], "half_life": chosen[tour]["half_life"] or "none"},
                          "bt_nodecay": {**nodecay[tour], "half_life": "none"},
                          "bt_surface_lam_u": lam_u[tour], "mesr": mchosen[tour]} for tour in C.TOURS},
        "nodecay_is_primary": {tour: chosen[tour]["half_life"] is None for tour in C.TOURS},
        "flatness": {tour: {"bt": flatness(grid[grid["tour"].eq(tour) & grid["grid"].eq("bt")], list(BT_GRID)),
                            "bt_all": flatness(grid[grid["tour"].eq(tour)], list(BT_GRID)),
                            "surface": flatness(sgrid[sgrid["tour"].eq(tour)], ["lam_u"]),
                            "mesr": flatness(mgrid[mgrid["tour"].eq(tour) & mgrid["grid"].eq("mesr")], list(MESR_GRID)),
                            "mesr_all": flatness(mgrid[mgrid["tour"].eq(tour)], list(MESR_GRID))} for tour in C.TOURS},
        "mesr_rms_gap_chosen": {tour: {"rms_gap_2019_2026": float(mesr_row(tour)["rms_gap_2019_2026"]),
                                       "matches": int(mesr_row(tour)["rms_gap_matches"])} for tour in C.TOURS},
        "full_passes": {f"{name}|{tour}": solver_stats(r) for (name, tour), r in full.items()},
        "tuning_pass_seconds": {k: {"median": float(v.median()), "max": float(v.max())}
                                for k, v in [("bt", grid["seconds"]), ("mesr", mgrid["seconds"]),
                                             ("surface", sgrid["seconds"])]},
        "checks": checks,
        "probes": probes,
        "top10_2026": top,
        "timings": timings,
        "workers": WORKERS,
    }
    summary["seconds"] = round(time.time() - T0, 1)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log(f"wrote {SUMMARY.name}; total {summary['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
