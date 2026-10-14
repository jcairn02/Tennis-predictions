"""Return and serve leverage (point sequence study, tester 1): importance weights, the statistics, and the exact
within-set shuffle. Pre-registration: data/studies/point_sequence/lev_prereg.md.

    point_states(P)            per point: sets, games, points before it, tie-break flag and first server, server
    importance(P, pre, ...)    match-win importance of every point under the iid model at the PRE-MATCH serve rates,
                               the match's best-of and deciding-set rule: the quantity of stage2_pbp.Chances.importance,
                               vectorised (a test checks it against Chances to 1e-9)
    leverage(P, w, n)          per player-match RL and SL as numerator X and denominator D
    shuffle_world(P, X, rng)   every set's side-X serve-point outcomes in a random order that re-scores into a valid
                               set with the real final score (rejection sampling), tie-break slots permuted alike

Point arrays are those of trait_common.real_points / replay_points (sorted by match, then point order).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage2_iid as M  # noqa: E402

RULE_NAME = {0: "TB7@6", 1: "TB10@6", 2: "ADV", 3: "TB7@12"}       # trait_common.FINALS codes
CAP = 2000


# ------------------------------------------------------------------------------------------------
# Score states

def point_states(P: dict) -> dict:
    m = P["m"].astype(np.int64)
    set_no = P["set_no"].astype(np.int64)
    gidx = P["game_idx"].astype(np.int64)
    tb = P["is_tb"].astype(bool)
    srv = P["server"].astype(np.int64)
    win = P["winner"].astype(np.int64)
    n = len(m)
    sg = np.ones(n, bool)
    sg[1:] = (m[1:] != m[:-1]) | (gidx[1:] != gidx[:-1])
    gid = np.cumsum(sg) - 1
    fg = np.flatnonzero(sg)
    a = (win == 1).astype(np.int64)
    ca, cb = np.cumsum(a) - a, np.cumsum(1 - a) - (1 - a)
    x = ca - ca[fg][gid]
    y = cb - cb[fg][gid]
    lg = np.r_[fg[1:] - 1, n - 1]
    gwin = win[lg]
    gkey = m[fg] * 16 + set_no[fg]
    ss = np.r_[True, gkey[1:] != gkey[:-1]]
    sid_g = np.cumsum(ss) - 1
    fs = np.flatnonzero(ss)
    wa, wb = (gwin == 1).astype(np.int64), (gwin == 2).astype(np.int64)
    cga, cgb = np.cumsum(wa) - wa, np.cumsum(wb) - wb
    ga_g, gb_g = cga - cga[fs][sid_g], cgb - cgb[fs][sid_g]
    ls = np.r_[fs[1:] - 1, len(fg) - 1]
    swin = gwin[ls]
    mkey = m[fg][fs]
    ms = np.r_[True, mkey[1:] != mkey[:-1]]
    msid = np.cumsum(ms) - 1
    fms = np.flatnonzero(ms)
    xa, xb = (swin == 1).astype(np.int64), (swin == 2).astype(np.int64)
    csa, csb = np.cumsum(xa) - xa, np.cumsum(xb) - xb
    sa_s, sb_s = csa - csa[fms][msid], csb - csb[fms][msid]
    return {"sa": sa_s[sid_g][gid], "sb": sb_s[sid_g][gid], "ga": ga_g[gid], "gb": gb_g[gid], "x": x, "y": y,
            "tb": tb, "first1": (srv[fg] == 1)[gid], "srv1": srv == 1}


# ------------------------------------------------------------------------------------------------
# Probability tables per match (vectorised over matches)

def game_table(s: np.ndarray) -> np.ndarray:
    """P(A wins the game) from A's points x and B's points y (0..4), A winning each point with probability s."""
    G = np.zeros((len(s), 5, 5))
    D = s * s / (s * s + (1 - s) * (1 - s))
    G[:, 4, :3] = 1.0
    G[:, 3, 3] = D
    G[:, 4, 3] = s + (1 - s) * D
    G[:, 3, 4] = s * D
    for tot in range(5, -1, -1):
        for x in range(4):
            y = tot - x
            if 0 <= y <= 3 and not (x == 3 and y == 3):
                G[:, x, y] = s * G[:, x + 1, y] + (1 - s) * G[:, x, y + 1]
    return G


def game_value(G: np.ndarray, mi: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    win = (x >= 4) & (x - y >= 2)
    lose = (y >= 4) & (y - x >= 2)
    deu = (x >= 3) & (y >= 3)
    d = x - y
    xx = np.where(deu, 3 + (d > 0), np.minimum(x, 4))
    yy = np.where(deu, 3 + (d < 0), np.minimum(y, 4))
    xx = np.where(win | lose, 0, xx)
    yy = np.where(win | lose, 0, yy)
    return np.where(win, 1.0, np.where(lose, 0.0, G[mi, xx, yy]))


def _tb_first_serves(k: int) -> bool:
    return k == 0 or ((k - 1) // 2) % 2 == 1


def tb_table(a: np.ndarray, b: np.ndarray, target: int, first_a: bool) -> tuple[np.ndarray, np.ndarray]:
    """P(A wins the tie-break) from A's points x and B's points y (0..target+1); a, b: A wins a point on A's / B's
    serve; first_a: A served the tie-break's first point. Also returns the level value (two-point race)."""
    S = target + 2
    T = np.zeros((len(a), S, S))
    L = a * b / (a * b + (1 - a) * (1 - b))

    def nb(x, y):
        if x >= target and x - y >= 2:
            return 1.0
        if y >= target and y - x >= 2:
            return 0.0
        if x == y and x >= target - 1:
            return L
        return T[:, x, y]
    for tot in range(2 * S - 2, -1, -1):
        for x in range(S):
            y = tot - x
            if y < 0 or y >= S:
                continue
            if (x >= target and x - y >= 2) or (y >= target and y - x >= 2):
                T[:, x, y] = 1.0 if x > y else 0.0
                continue
            if x == y and x >= target - 1:
                T[:, x, y] = L
                continue
            s = a if (_tb_first_serves(x + y) == first_a) else b
            T[:, x, y] = s * nb(x + 1, y) + (1 - s) * nb(x, y + 1)
    return T, L


def tb_value(T: np.ndarray, L: np.ndarray, mi: np.ndarray, x: np.ndarray, y: np.ndarray, target: int) -> np.ndarray:
    mn = np.minimum(x, y)
    j = np.where(mn > target, (mn - target + 1) // 2, 0)
    x, y = x - 2 * j, y - 2 * j
    win = (x >= target) & (x - y >= 2)
    lose = (y >= target) & (y - x >= 2)
    level = (x == y) & (x >= target - 1)
    xx = np.clip(np.where(win | lose | level, 0, x), 0, target + 1)
    yy = np.clip(np.where(win | lose | level, 0, y), 0, target + 1)
    return np.where(win, 1.0, np.where(lose, 0.0, np.where(level, L[mi], T[mi, xx, yy])))


def set_table(hA, hB, rule: str, tb00: tuple) -> tuple[np.ndarray, np.ndarray]:
    """P(A wins the set) from the start of a game at games (ga, gb), A serving it (last axis 1) or not (0).
    tb00[k]: P(A wins the tie-break from 0-0) when A serves its first point (k = 1) or B does (k = 0)."""
    tb_at, _ = M.SET_RULES[rule]
    K = 14 if rule == "TB7@12" else 8
    S = np.zeros((len(hA), K, K, 2))
    level = hA * (1 - hB) / (hA * (1 - hB) + (1 - hA) * hB)

    def val(ga, gb, nx):
        if max(ga, gb) >= 6 and abs(ga - gb) >= 2:
            return np.full(len(hA), 1.0 if ga > gb else 0.0)
        if tb_at is not None and ga == tb_at and gb == tb_at:
            return tb00[nx]
        if tb_at is None and min(ga, gb) >= 5:
            g = hA if nx else 1 - hB
            return level if ga == gb else (g + (1 - g) * level if ga > gb else g * level)
        return S[:, ga, gb, nx]
    for tot in range(2 * K - 2, -1, -1):
        for ga in range(K):
            gb = tot - ga
            if gb < 0 or gb >= K:
                continue
            for nx in (0, 1):
                terminal = (max(ga, gb) >= 6 and abs(ga - gb) >= 2) or (tb_at is not None and ga == tb_at and gb == tb_at) \
                    or (tb_at is None and min(ga, gb) >= 5)
                if not terminal and tb_at is not None and max(ga, gb) > tb_at:
                    continue                                    # unreachable (a tie-break comes first)
                if terminal:
                    S[:, ga, gb, nx] = val(ga, gb, nx)
                else:
                    g = hA if nx else 1 - hB
                    S[:, ga, gb, nx] = g * val(ga + 1, gb, 1 - nx) + (1 - g) * val(ga, gb + 1, 1 - nx)
    return S, level


def set_value(S, level, hA, hB, rule: str, tb00, mi, ga, gb, nx) -> np.ndarray:
    tb_at, _ = M.SET_RULES[rule]
    K = S.shape[1]
    win = (np.maximum(ga, gb) >= 6) & (np.abs(ga - gb) >= 2) & (ga > gb)
    lose = (np.maximum(ga, gb) >= 6) & (np.abs(ga - gb) >= 2) & (gb > ga)
    out = np.where(win, 1.0, 0.0)
    rest = ~win & ~lose
    if tb_at is not None:
        tbs = rest & (ga == tb_at) & (gb == tb_at)
        out = np.where(tbs, np.where(nx == 1, tb00[1][mi], tb00[0][mi]), out)
        rest &= ~tbs
    else:
        adv = rest & (np.minimum(ga, gb) >= 5)
        g = np.where(nx == 1, hA[mi], 1 - hB[mi])
        lv = level[mi]
        av = np.where(ga == gb, lv, np.where(ga > gb, g + (1 - g) * lv, g * lv))
        out = np.where(adv, av, out)
        rest &= ~adv
    gi = np.clip(ga, 0, K - 1)
    gj = np.clip(gb, 0, K - 1)
    return np.where(rest, S[mi, gi, gj, nx], out)


# ------------------------------------------------------------------------------------------------
# Importance

def importance(P: dict, pre_a: np.ndarray, pre_b: np.ndarray, bo: np.ndarray, fcode: np.ndarray,
               chunk: int = 20000) -> np.ndarray:
    """Match-win importance of every point at the pre-match serve rates (pre_a: A wins a point on A's serve)."""
    st = point_states(P)
    m = P["m"].astype(np.int64)
    n_m = len(pre_a)
    w = np.empty(len(m))
    bounds = np.searchsorted(m, np.arange(0, n_m + chunk, chunk))
    for c0 in range(0, n_m, chunk):
        c1 = min(c0 + chunk, n_m)
        p0, p1 = np.searchsorted(m, c0), np.searchsorted(m, c1)
        if p1 == p0:
            continue
        pa, pb = pre_a[c0:c1].astype("float64"), pre_b[c0:c1].astype("float64")
        need = ((bo[c0:c1] + 1) // 2).astype(np.int64)
        fc = fcode[c0:c1].astype(np.int64)
        mi = m[p0:p1] - c0
        a_srv, b_srv = pa, 1 - pb                                  # A wins a point on A's / B's serve
        GA, GB = game_table(a_srv), game_table(b_srv)
        hA, hB = M.game(pa), M.game(pb)
        T7 = {k: tb_table(a_srv, b_srv, 7, bool(k)) for k in (0, 1)}
        T10 = {k: tb_table(a_srv, b_srv, 10, bool(k)) for k in (0, 1)}
        tb00 = {7: (T7[0][0][:, 0, 0], T7[1][0][:, 0, 0]), 10: (T10[0][0][:, 0, 0], T10[1][0][:, 0, 0])}
        sets = {}
        for code, rule in RULE_NAME.items():
            tbp = M.SET_RULES[rule][1]
            sets[code] = set_table(hA, hB, rule, tb00[10] if tbp == 10 else tb00[7])
        set_std = sets[0][0][:, 0, 0, 1]
        set_fin = np.choose(fc, [sets[c][0][:, 0, 0, 1] for c in range(4)])
        Mt = np.zeros((len(pa), 4, 4))
        for sa in range(3, -1, -1):
            for sb in range(3, -1, -1):
                done_a = sa >= need
                done_b = sb >= need
                dec = (sa == need - 1) & (sb == need - 1)
                s = np.where(dec, set_fin, set_std)
                nxt_a = Mt[:, min(sa + 1, 3), sb] if sa < 3 else np.ones(len(pa))
                nxt_b = Mt[:, sa, min(sb + 1, 3)] if sb < 3 else np.zeros(len(pa))
                Mt[:, sa, sb] = np.where(done_a, 1.0, np.where(done_b, 0.0, s * nxt_a + (1 - s) * nxt_b))
        sa, sb = st["sa"][p0:p1], st["sb"][p0:p1]
        ga, gb = st["ga"][p0:p1], st["gb"][p0:p1]
        x, y = st["x"][p0:p1], st["y"][p0:p1]
        tb, first1, srv1 = st["tb"][p0:p1], st["first1"][p0:p1], st["srv1"][p0:p1]
        dec = (sa == need[mi] - 1) & (sb == need[mi] - 1)
        rule = np.where(dec, fc[mi], 0)
        MA = Mt[mi, np.minimum(sa + 1, 3), sb]
        MA = np.where(sa + 1 >= need[mi], 1.0, MA)
        MB = Mt[mi, sa, np.minimum(sb + 1, 3)]
        MB = np.where(sb + 1 >= need[mi], 0.0, MB)
        # regular games
        gw = np.where(srv1, game_value(GA, mi, x + 1, y), game_value(GB, mi, x + 1, y))
        gl = np.where(srv1, game_value(GA, mi, x, y + 1), game_value(GB, mi, x, y + 1))
        nx = (~srv1).astype(np.int64)
        pA = np.zeros(len(mi))
        pB = np.zeros(len(mi))
        for code, rname in RULE_NAME.items():
            sel = (rule == code) & ~tb
            if not sel.any():
                continue
            S, lv = sets[code]
            tbp = M.SET_RULES[rname][1]
            t00 = tb00[10] if tbp == 10 else tb00[7]
            pA[sel] = set_value(S, lv, hA, hB, rname, t00, mi[sel], ga[sel] + 1, gb[sel], nx[sel])
            pB[sel] = set_value(S, lv, hA, hB, rname, t00, mi[sel], ga[sel], gb[sel] + 1, nx[sel])
        VA = pA * MA + (1 - pA) * MB
        VB = pB * MA + (1 - pB) * MB
        imp = (gw - gl) * (VA - VB)
        # tie-breaks
        target = np.where(dec & (fc[mi] == 1), 10, 7)
        for tgt, TT in ((7, T7), (10, T10)):
            for k in (0, 1):
                sel = tb & (target == tgt) & (first1 == bool(k))
                if not sel.any():
                    continue
                Tk, Lk = TT[k]
                tw = tb_value(Tk, Lk, mi[sel], x[sel] + 1, y[sel], tgt)
                tl = tb_value(Tk, Lk, mi[sel], x[sel], y[sel] + 1, tgt)
                imp[sel] = (tw - tl) * (MA[sel] - MB[sel])
        w[p0:p1] = imp
    return w


# ------------------------------------------------------------------------------------------------
# The statistics

def leverage(P: dict, w: np.ndarray, n: int) -> pd.DataFrame:
    """Rows in (mcode, side) order: X_RL, D_RL, X_SL, D_SL, imp_total (side 1 rows only meaningful), imp_tb."""
    m = P["m"].astype(np.int64)
    srv, win = P["server"].astype(np.int64), P["winner"].astype(np.int64)
    out = {}
    for side in (1, 2):
        S = srv == side
        R = ~S
        y = (win == side).astype("float64")
        ns, nr = np.bincount(m, weights=S, minlength=n), np.bincount(m, weights=R, minlength=n)
        ys = np.bincount(m, weights=S * y, minlength=n) / np.maximum(ns, 1)
        yr = np.bincount(m, weights=R * y, minlength=n) / np.maximum(nr, 1)
        out[(side, "X_SL")] = np.bincount(m, weights=S * w * (y - ys[m]), minlength=n)
        out[(side, "D_SL")] = np.bincount(m, weights=S * w, minlength=n)
        out[(side, "X_RL")] = np.bincount(m, weights=R * w * (y - yr[m]), minlength=n)
        out[(side, "D_RL")] = np.bincount(m, weights=R * w, minlength=n)
    rows = np.empty((2 * n, 4))
    for side in (1, 2):
        rows[side - 1::2] = np.column_stack([out[(side, c)] for c in ("X_RL", "D_RL", "X_SL", "D_SL")])
    d = pd.DataFrame(rows, columns=["X_RL", "D_RL", "X_SL", "D_SL"])
    d.insert(0, "side", np.tile([1, 2], n))
    d.insert(0, "mcode", np.repeat(np.arange(n), 2))
    tbm = P["is_tb"].astype(bool)
    d["imp_total"] = np.repeat(np.bincount(m, weights=w, minlength=n), 2)
    d["imp_tb"] = np.repeat(np.bincount(m, weights=w * tbm, minlength=n), 2)
    return d


# ------------------------------------------------------------------------------------------------
# The exact within-set shuffle

def _scan(o: np.ndarray, starts: np.ndarray, lens: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cut each pool's outcome sequence (server won = 1) into games: end-of-game flags per position, and whether the
    pool ends on a game end."""
    end = np.zeros(len(o), bool)
    order = np.argsort(-lens, kind="stable")
    sl = lens[order]
    s = np.zeros(len(starts), np.int64)
    r = np.zeros(len(starts), np.int64)
    for k in range(int(lens.max()) if len(lens) else 0):
        cnt = int(np.searchsorted(-sl, -k, side="left"))
        act = order[:cnt]
        pos = starts[act] + k
        v = o[pos].astype(np.int64)
        s[act] += v
        r[act] += 1 - v
        e = ((s[act] >= 4) | (r[act] >= 4)) & (np.abs(s[act] - r[act]) >= 2)
        end[pos[e]] = True
        s[act[e]] = 0
        r[act[e]] = 0
    return end, (s == 0) & (r == 0)


def set_info(P: dict, fcode: np.ndarray, bo: np.ndarray) -> dict:
    """Per set (in order): match, set number, first server, regular games, tie-break, tie-break score target, the
    games' servers and A-won flags (padded), and per point its set id."""
    m = P["m"].astype(np.int64)
    set_no = P["set_no"].astype(np.int64)
    key = m * 16 + set_no
    ss = np.r_[True, key[1:] != key[:-1]]
    sid = np.cumsum(ss) - 1
    fs = np.flatnonzero(ss)
    nset = len(fs)
    st = point_states(P)
    gidx = P["game_idx"].astype(np.int64)
    sg = np.r_[True, (m[1:] != m[:-1]) | (gidx[1:] != gidx[:-1])]
    fg = np.flatnonzero(sg)
    lg = np.r_[fg[1:] - 1, len(m) - 1]
    g_sid = sid[fg]
    g_tb = P["is_tb"][fg].astype(bool)
    g_srv = P["server"][fg].astype(np.int64)
    g_awon = (P["winner"][lg] == 1)
    reg = ~g_tb
    T = np.bincount(g_sid[reg], minlength=nset)
    has_tb = np.bincount(g_sid[g_tb], minlength=nset) > 0
    mset = m[fs]
    need = (bo[mset] + 1) // 2
    sa, sb = st["sa"][fs], st["sb"][fs]
    dec = (sa == need - 1) & (sb == need - 1)
    rule = np.where(dec, fcode[mset], 0)
    tb_at = np.where(rule == 3, 12, np.where(rule == 2, -1, 6))
    target = np.where(rule == 1, 10, 7)
    maxT = int(T.max())
    rank = np.zeros(len(fg), np.int64)
    rg = np.flatnonzero(reg)
    first_reg = np.r_[True, g_sid[rg][1:] != g_sid[rg][:-1]]
    c = np.arange(len(rg))
    rank[rg] = c - np.maximum.accumulate(np.where(first_reg, c, 0))
    srv_pad = np.zeros((nset, maxT), np.int64)
    awon_pad = np.zeros((nset, maxT), bool)
    srv_pad[g_sid[rg], rank[rg]] = g_srv[rg]
    awon_pad[g_sid[rg], rank[rg]] = g_awon[rg]
    return {"sid": sid, "fs": fs, "nset": nset, "m": mset, "T": T, "has_tb": has_tb, "tb_at": tb_at,
            "target": target, "srv": srv_pad, "awon": awon_pad, "first": P["server"][fs].astype(np.int64)}


def _path_ok(awon: np.ndarray, T: np.ndarray, tb_at: np.ndarray) -> np.ndarray:
    """Whether a set's game sequence (A won each game; padded) ends nowhere before its last regular game."""
    ga = np.cumsum(awon, axis=1)
    gb = np.cumsum(~awon, axis=1)
    idx = np.arange(awon.shape[1])[None, :]
    before = idx < (T[:, None] - 1)
    over = (np.maximum(ga, gb) >= 6) & (np.abs(ga - gb) >= 2)
    tbs = (tb_at[:, None] > 0) & (ga == tb_at[:, None]) & (gb == tb_at[:, None])
    return ~((over | tbs) & before).any(axis=1)


def shuffle_world(P: dict, X: int, rng: np.random.Generator, info: dict) -> tuple[dict, dict]:
    """A copy of the points in which every set's side-X serve-point outcomes are re-ordered at random (regular games
    and tie-break separately) so that the set re-scores validly to its real final score; the rest is unchanged."""
    srv = P["server"].astype(np.int64)
    tb = P["is_tb"].astype(bool)
    sid = info["sid"]
    o_all = (P["winner"] == srv).astype(np.int8)                 # the server won the point
    # ---- regular part: X's pool per set
    xr = np.flatnonzero((srv == X) & ~tb)
    pool = sid[xr]
    first = np.r_[True, pool[1:] != pool[:-1]]
    starts = np.flatnonzero(first)
    lens = np.diff(np.r_[starts, len(xr)])
    psid = pool[starts]                                         # set id of each pool
    o_real = o_all[xr]
    real_end, _ = _scan(o_real, starts, lens)
    pidx = np.cumsum(first) - 1
    nX = np.bincount(pidx[real_end], minlength=len(starts))
    hX = np.bincount(pidx[real_end], weights=o_real[real_end], minlength=len(starts)).astype(np.int64)
    T, tb_at, srv_pad, awon_pad = info["T"][psid], info["tb_at"][psid], info["srv"][psid], info["awon"][psid]
    x_slot = srv_pad == X                                       # which of the set's regular games X serves
    o_new = o_real.copy()
    todo = np.arange(len(starts))
    draws = np.zeros(len(starts), np.int64)
    rounds = 0
    while todo.size and rounds < CAP:
        rounds += 1
        mask = np.zeros(len(starts), bool)
        mask[todo] = True
        pos = np.flatnonzero(mask[pidx])
        perm = np.lexsort((rng.random(pos.size), pidx[pos]))
        cand = o_real[pos][perm]
        sub_starts = np.searchsorted(pos, starts[todo])
        end, complete = _scan(cand, sub_starts, lens[todo])
        loc = np.searchsorted(todo, pidx[pos])
        ng = np.bincount(loc[end], minlength=todo.size)
        nh = np.bincount(loc[end], weights=cand[end], minlength=todo.size).astype(np.int64)
        ok = complete & (ng == nX[todo]) & (nh == hX[todo])
        if ok.any():
            # the path: X's games in their new order fill X's slots; the other server's games keep theirs
            held = np.zeros((todo.size, srv_pad.shape[1] + 64), bool)
            ends_pos = np.flatnonzero(end)
            if ends_pos.size:
                e_loc = loc[ends_pos]
                first_e = np.r_[True, e_loc[1:] != e_loc[:-1]]
                idx_e = np.arange(ends_pos.size)
                r_e = idx_e - np.maximum.accumulate(np.where(first_e, idx_e, 0))
                keep_e = r_e < held.shape[1]
                held[e_loc[keep_e], r_e[keep_e]] = cand[ends_pos[keep_e]] == 1
            aw = awon_pad[todo].copy()
            xs = x_slot[todo]
            # X's k-th game goes to X's k-th slot
            slot_rank = np.cumsum(xs, axis=1) - 1
            xheld = np.take_along_axis(held, np.clip(slot_rank, 0, held.shape[1] - 1), axis=1)
            aw = np.where(xs, xheld if X == 1 else ~xheld, aw)
            path = _path_ok(aw, T[todo], tb_at[todo])
            ok &= path
        acc = todo[ok]
        if acc.size:
            amask = np.zeros(len(starts), bool)
            amask[acc] = True
            sel = amask[pidx[pos]]
            o_new[pos[sel]] = cand[sel]
        draws[todo] += 1
        todo = todo[~ok]
    capped_reg = int(todo.size)
    # ---- tie-break part: X's tie-break slots permuted
    xt = np.flatnonzero((srv == X) & tb)
    tb_rounds, capped_tb = 0, 0
    o_tb_new = o_all[xt].copy() if xt.size else np.array([], np.int8)
    if xt.size:
        allt = np.flatnonzero(tb)
        tset = sid[allt]
        tfirst = np.r_[True, tset[1:] != tset[:-1]]
        tstarts = np.flatnonzero(tfirst)
        tlens = np.diff(np.r_[tstarts, len(allt)])
        tpid = np.cumsum(tfirst) - 1
        maxL = int(tlens.max())
        rk = np.arange(len(allt)) - tstarts[tpid]
        a_real = np.zeros((len(tstarts), maxL), np.int8)
        isx = np.zeros((len(tstarts), maxL), bool)
        valid = np.zeros((len(tstarts), maxL), bool)
        a_real[tpid, rk] = (P["winner"][allt] == 1)
        isx[tpid, rk] = srv[allt] == X
        valid[tpid, rk] = True
        tgt = info["target"][tset[tstarts]]
        xo = (P["winner"][allt] == X)                           # X won the point (on X's serve slots)
        xpos = np.flatnonzero(srv[allt] == X)                   # positions within allt
        xpid = tpid[xpos]
        o_cur = xo[xpos].astype(np.int8)
        todo_t = np.unique(xpid)
        while todo_t.size and tb_rounds < CAP:
            tb_rounds += 1
            mask = np.zeros(len(tstarts), bool)
            mask[todo_t] = True
            sel = np.flatnonzero(mask[xpid])
            perm = np.lexsort((rng.random(sel.size), xpid[sel]))
            cand = o_cur[sel][perm]
            grid = a_real[todo_t].copy()
            loc = np.searchsorted(todo_t, xpid[sel])
            r_in = rk[xpos[sel]]
            grid[loc, r_in] = (cand == 1) if X == 1 else (cand == 0)
            va = valid[todo_t]
            ca = np.cumsum(grid * va, axis=1)
            cb = np.cumsum((1 - grid) * va, axis=1)
            L = tlens[todo_t]
            idx = np.arange(maxL)[None, :]
            t_ = tgt[todo_t][:, None]
            over = ((ca >= t_) | (cb >= t_)) & (np.abs(ca - cb) >= 2)
            early = (over & (idx < (L[:, None] - 1))).any(axis=1)
            ok = ~early
            acc = todo_t[ok]
            if acc.size:
                am = np.zeros(len(tstarts), bool)
                am[acc] = True
                s2 = am[xpid[sel]]
                o_tb_new_idx = sel[s2]
                o_tb_new[o_tb_new_idx] = cand[s2]
            todo_t = todo_t[~ok]
        capped_tb = int(todo_t.size)
    # ---- rebuild the sequence: sort key (match, set, regular game slot, position) with tie-breaks last
    n = len(srv)
    o_out = o_all.copy()
    o_out[xr] = o_new
    if xt.size:
        o_out[xt] = o_tb_new
    winner = np.where(o_out == 1, srv, 3 - srv).astype(np.int8)
    # X's games after the shuffle and their rank among X's games of the set; the other's games keep their slots
    end_new, _ = _scan(o_new, starts, lens)
    pos_in_pool = np.arange(len(xr)) - starts[pidx]
    gstart = np.r_[True, end_new[:-1]] | first
    gk = np.cumsum(gstart) - 1
    game_k = gk - gk[starts][pidx]
    within_x = pos_in_pool - pos_in_pool[np.flatnonzero(gstart)][gk]
    # slot index of X's k-th game: the k-th True in x_slot of the set
    slot_of = np.full((len(starts), srv_pad.shape[1]), -1, np.int64)
    rr, cc = np.nonzero(x_slot)
    k_of = np.cumsum(x_slot, axis=1)[rr, cc] - 1
    slot_of[rr, k_of] = cc
    t_x = slot_of[pidx, game_k]
    # the other server's regular points: their real game slot and position
    orr = np.flatnonzero((srv != X) & ~tb)
    st = point_states(P)
    ga_gb = st["ga"][orr] + st["gb"][orr]
    t_o = ga_gb                                              # games played in the set before this game
    within_o = P["pt_no"][orr].astype(np.int64) - 1
    allt = np.flatnonzero(tb)
    t_t = info["T"][sid[allt]]
    within_t = P["pt_no"][allt].astype(np.int64) - 1
    slot = np.zeros(n, np.int64)
    within = np.zeros(n, np.int64)
    slot[xr], within[xr] = t_x, within_x
    slot[orr], within[orr] = t_o, within_o
    slot[allt], within[allt] = t_t, within_t
    assert (slot[xr] >= 0).all()
    order = np.lexsort((within, slot, sid))
    m = P["m"][order]
    set_no = P["set_no"][order]
    gkey = sid[order] * 1000 + slot[order]
    newg = np.r_[True, gkey[1:] != gkey[:-1]]
    gid = np.cumsum(newg) - 1
    mstart = np.r_[True, m[1:] != m[:-1]]
    g_first_of_match = gid[np.flatnonzero(mstart)]
    game_idx = gid - g_first_of_match[np.cumsum(mstart) - 1]
    fg = np.flatnonzero(newg)
    pt_no = np.arange(n) - fg[gid] + 1
    out = {"m": m, "set_no": set_no, "game_no": np.ones(n, np.int16), "game_idx": game_idx.astype(np.int32),
           "pt_no": pt_no.astype(np.int16), "is_tb": P["is_tb"][order], "server": P["server"][order],
           "winner": winner[order]}
    diag = {"sets": int(info["nset"]), "regular_pools": int(len(starts)), "regular_rounds": rounds,
            "regular_capped_kept_real": capped_reg, "mean_regular_draws": float(draws.mean()),
            "tiebreak_pools_x": int(len(np.unique(sid[xt]))) if xt.size else 0, "tiebreak_rounds": tb_rounds,
            "tiebreak_capped_kept_real": capped_tb}
    return out, diag
