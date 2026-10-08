"""Stage 2 of the predictability diagnostic: the chance of winning if every point were an independent draw.

The "iid model" (independent and identically distributed points): each player wins each point on their
own serve with a fixed probability, whatever the score. From the two players' serve-point rates it gives
the chance of holding a service game, of winning a tiebreak, a set and a match, under the match's format.
Stage 2 feeds it the rates each player achieved in the match itself (its "randomness floor") and uses it
to say what break points and tiebreaks "should" have given.

    game(p)                              P(the server holds), winning each serve point with probability p
    tiebreak(pa, pb, target, a_first)    P(A wins a tiebreak to ``target`` points, won by two)
    set_win(pa, pb, rule, a_first)       P(A wins a set) under a set rule (SET_RULES)
    match_win(pa, pb, best_of, final)    P(A wins the match): every set but the deciding one is "TB7@6"
    match_win_by(pa, pb, best_of, final) the same with a best-of and a deciding-set rule per match
    simulate(pa, pb, best_of, final)     the same rules played point by point (a check, and the floor's optimism)
    slam_rules(), deciding_set_rule()    the Grand Slams' deciding-set rules (stage2_slam_final_set_rules.csv)

pa and pb are each player's probability of winning a point on their own serve; arrays broadcast, and
every function is vectorised over matches. Serving order: the first server of a tiebreak serves one
point, then the players alternate every two points; within a set the players alternate service games,
and a tiebreak counts as one game for the alternation. The tests show that the chance of winning a
tiebreak or a set does not depend on who serves first (Newton and Keller's result), so sets are
independent draws and the match follows from the two set probabilities.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

RULES_CSV = Path(__file__).resolve().parents[3] / "data" / "studies" / "predictability_diagnostic" / \
    "stage2_slam_final_set_rules.csv"

# set rule -> (games all at which a tiebreak is played, or None for an advantage set; tiebreak points)
SET_RULES = {"TB7@6": (6, 7), "TB10@6": (6, 10), "TB7@12": (12, 7), "ADV": (None, 0)}
RULE_WORDS = {"TB7@6": "a 7-point tiebreak at 6-6", "TB10@6": "a 10-point tiebreak at 6-6",
              "TB7@12": "a 7-point tiebreak at 12-12", "ADV": "an advantage set (won by two games, no tiebreak)"}
STANDARD = "TB7@6"


def _arrays(pa, pb):
    pa, pb = np.broadcast_arrays(np.asarray(pa, dtype="float64"), np.asarray(pb, dtype="float64"))
    return pa, pb


def _share(x, y):
    """x / (x + y), one half where both are zero (two players who never lose a point on serve)."""
    tot = x + y
    return np.divide(x, tot, out=np.full_like(tot, 0.5), where=tot > 0)


def game(p):
    """P(the server wins a game to 4 points, by two) when each serve point is won with probability p."""
    p = np.asarray(p, dtype="float64")
    q = 1.0 - p
    deuce = _share(p * p, q * q)                    # from deuce: two points in a row before the receiver
    return p ** 4 * (1 + 4 * q + 10 * q * q) + 20 * p ** 3 * q ** 3 * deuce


def _tb_first_serves(k: int) -> bool:
    """Whether the tiebreak's first server serves point k (0-indexed): 1, then 2-2-2 alternation."""
    return k == 0 or ((k - 1) // 2) % 2 == 1


def tiebreak(pa, pb, target: int = 7, a_first: bool = True):
    """P(A wins a tiebreak to ``target`` points, won by two). From target-1 all, each pair of points has one
    served by each player, so the rest is a two-point race."""
    pa, pb = _arrays(pa, pb)
    a_srv, b_srv = pa, 1.0 - pb                     # A wins a point on A's serve, on B's serve
    won = np.zeros_like(pa)
    layer = {(0, 0): np.ones_like(pa)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == target - 1 and j == target - 1:
                won += r * _share(a_srv * b_srv, (1 - a_srv) * (1 - b_srv))
                continue
            w = a_srv if _tb_first_serves(i + j) == a_first else b_srv
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                if max(ni, nj) >= target and abs(ni - nj) >= 2:
                    if ni > nj:
                        won += r * pr
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return won


def set_win(pa, pb, rule: str = STANDARD, a_first: bool = True):
    """P(A wins a set) under ``rule``: first to six games, won by two, with a tiebreak at 6-6 (or 12-12),
    or an advantage set. The set's first server serves first in its tiebreak (game 2n of the set)."""
    pa, pb = _arrays(pa, pb)
    tb_at, tb_points = SET_RULES[rule]
    hold_a, hold_b = game(pa), game(pb)
    won = np.zeros_like(pa)
    layer = {(0, 0): np.ones_like(pa)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if tb_at is not None and i == tb_at and j == tb_at:
                won += r * tiebreak(pa, pb, tb_points, a_first=a_first)
                continue
            if tb_at is None and i == j and i >= 5:
                # advantage set from 5-5: each pair of games has one service game each, so it ends when one
                # player wins both games of a pair
                won += r * _share(hold_a * (1 - hold_b), (1 - hold_a) * hold_b)
                continue
            a_serves = ((i + j) % 2 == 0) == a_first
            w = hold_a if a_serves else 1 - hold_b
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                if max(ni, nj) >= 6 and abs(ni - nj) >= 2:
                    if ni > nj:
                        won += r * pr
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return won


def match_win(pa, pb, best_of: int = 3, final_rule: str = STANDARD, set_rule: str = STANDARD):
    """P(A wins a best-of-``best_of`` match): every set under ``set_rule`` but the deciding one (played at
    one set all, or two all), which follows ``final_rule``."""
    pa, pb = _arrays(pa, pb)
    s = set_win(pa, pb, set_rule)
    f = s if final_rule == set_rule else set_win(pa, pb, final_rule)
    need = (int(best_of) + 1) // 2
    won = np.zeros_like(pa)
    layer = {(0, 0): np.ones_like(pa)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            w = f if i == need - 1 and j == need - 1 else s
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                if ni == need:
                    won += r * pr
                elif nj < need:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return won


def match_win_by(pa, pb, best_of, final_rule):
    """match_win with a best-of (3 or 5) and a deciding-set rule per match (arrays of equal length)."""
    pa, pb = _arrays(pa, pb)
    bo = np.asarray(best_of)
    fr = np.asarray(final_rule, dtype=object)
    out = np.full(pa.shape, np.nan)
    for b in np.unique(bo):
        for r in pd.unique(fr):
            m = (bo == b) & (fr == r)
            if m.any():
                out[m] = match_win(pa[m], pb[m], int(b), r)
    return out


def tiebreak_target(final_rule) -> np.ndarray:
    """Points needed to win a deciding-set tiebreak under each rule (7 where the rule has none)."""
    pts = {k: (v[1] if v[0] is not None else 7) for k, v in SET_RULES.items()}
    return np.array([pts[r] for r in final_rule], dtype="int64")


# ------------------------------------------------------------------------------------------------
# The Grand Slams' deciding-set rules

SLAM_NAMES = (("aus open", "AO"), ("australian open", "AO"), ("roland garros", "RG"), ("wimbledon", "WIM"),
              ("us open", "USO"))


def slam_of(name: str) -> str | None:
    """AO, RG, WIM or USO from a Grand Slam's tournament name (the 2021 AO qualifying was 'Doha Aus Open
    Qualies' and 'Dubai Aus Open Qualies'); None for anything else."""
    n = str(name).lower().strip()
    for key, code in SLAM_NAMES:          # 'aus open' contains 'us open': it is checked first
        if key in n:
            return code
    return None


@lru_cache(maxsize=1)
def slam_rules() -> pd.DataFrame:
    r = pd.read_csv(RULES_CSV, dtype={"tiebreak_at": "Int64", "tiebreak_points": "Int64"})
    code = np.where(r["final_set"].eq("advantage"), "ADV",
                    "TB" + r["tiebreak_points"].astype(str) + "@" + r["tiebreak_at"].astype(str))
    return r.assign(rule=code)


def deciding_set_rule(level: pd.Series, tournament_name: pd.Series, year: pd.Series, qualifying: pd.Series) -> pd.Series:
    """Each match's deciding-set rule: the Slam's rule for its draw and year (stage2_slam_final_set_rules.csv);
    every other event plays a 7-point tiebreak at 6-6 in every set."""
    rules = slam_rules()
    out = pd.Series(STANDARD, index=level.index, dtype=object)
    gs = level.eq("GS")
    slam = tournament_name.where(gs).map(lambda n: slam_of(n) if isinstance(n, str) else None)
    draw = np.where(qualifying.astype(bool), "qualifying", "main")
    for row in rules.itertuples():
        hit = gs & slam.eq(row.slam) & (draw == row.draw) & year.between(row.first_year, row.last_year)
        out[hit] = row.rule
    unknown = gs & slam.isna()
    if unknown.any():
        raise ValueError(f"Grand Slam events with no rule: {sorted(tournament_name[unknown].unique())}")
    return out


# ------------------------------------------------------------------------------------------------
# Point-by-point simulation of the same rules

def simulate(pa, pb, best_of, final_rule, seed: int = 0, max_points: int = 5000) -> dict:
    """Play each match point by point, every point won by the server with their fixed probability.

    Returns ``a_won`` and, per player (columns: A, B), serve points played and won, break points faced and
    saved (a point on which the receiver would win a service game; tiebreak points are not break points), and
    tiebreaks won; ``tiebreaks`` is the number played and ``deciding_tb`` whether the deciding set ended in one.
    So the box score a simulated match would show can be set against the rates it was played at. The first
    server of each match is drawn at random."""
    pa, pb = _arrays(pa, pb)
    n = pa.size
    rng = np.random.default_rng(seed)
    need = (np.broadcast_to(np.asarray(best_of), (n,)).astype("int64") + 1) // 2
    fr = np.broadcast_to(np.asarray(final_rule, dtype=object), (n,))
    fr_at = np.array([SET_RULES[r][0] or 0 for r in fr], dtype="int64")      # 0: advantage, no tiebreak
    fr_pts = np.array([SET_RULES[r][1] for r in fr], dtype="int64")
    p_srv = np.stack([pa.ravel(), pb.ravel()], axis=1)
    sets = np.zeros((n, 2), dtype="int64")
    games = np.zeros((n, 2), dtype="int64")
    pts = np.zeros((n, 2), dtype="int64")
    server = rng.integers(0, 2, n)               # who serves the next game
    in_tb = np.zeros(n, dtype=bool)
    tb_first = np.zeros(n, dtype="int64")
    tb_target = np.zeros(n, dtype="int64")
    served = np.zeros((n, 2), dtype="int64")
    won_srv = np.zeros((n, 2), dtype="int64")
    bp_faced = np.zeros((n, 2), dtype="int64")
    bp_saved = np.zeros((n, 2), dtype="int64")
    tb_won = np.zeros((n, 2), dtype="int64")
    deciding_tb = np.zeros(n, dtype=bool)
    done = np.zeros(n, dtype=bool)
    a_won = np.zeros(n, dtype=bool)
    for _ in range(max_points):
        idx = np.flatnonzero(~done)
        if idx.size == 0:
            break
        k = pts[idx, 0] + pts[idx, 1]
        tb = in_tb[idx]
        tb_srv = np.where((k == 0) | (((k - 1) // 2) % 2 == 1), tb_first[idx], 1 - tb_first[idx])
        srv = np.where(tb, tb_srv, server[idx])
        win = rng.random(idx.size) < p_srv[idx, srv]
        pw = np.where(win, srv, 1 - srv)
        rcv_pts, srv_pts = pts[idx, 1 - srv], pts[idx, srv]
        bp = ~tb & (rcv_pts >= 3) & (rcv_pts > srv_pts)
        bp_faced[idx[bp], srv[bp]] += 1
        bp_saved[idx[bp & win], srv[bp & win]] += 1
        served[idx, srv] += 1
        won_srv[idx, srv] += win
        pts[idx, pw] += 1
        target = np.where(tb, tb_target[idx], 4)
        lead = pts[idx, pw] - pts[idx, 1 - pw]
        over = (pts[idx, pw] >= target) & (lead >= 2)
        g, gw, gtb = idx[over], pw[over], tb[over]
        if g.size == 0:
            continue
        tb_won[g[gtb], gw[gtb]] += 1
        games[g, gw] += 1
        pts[g] = 0
        server[g] = 1 - np.where(gtb, tb_first[g], server[g])    # a tiebreak counts as one game
        in_tb[g] = False
        final = (sets[g, 0] == need[g] - 1) & (sets[g, 1] == need[g] - 1)
        at = np.where(final, fr_at[g], 6)
        gwin, glose = games[g, gw], games[g, 1 - gw]
        set_over = gtb | ((gwin >= 6) & (gwin - glose >= 2))
        start = ~set_over & (at > 0) & (games[g, 0] == at) & (games[g, 1] == at)
        s = g[start]
        in_tb[s] = True
        tb_first[s] = server[s]
        tb_target[s] = np.where(final[start], fr_pts[g][start], 7)
        so, sw = g[set_over], gw[set_over]
        deciding_tb[g[set_over & final & gtb]] = True
        sets[so, sw] += 1
        games[so] = 0
        fin = sets[so, sw] >= need[so]
        done[so[fin]] = True
        a_won[so[fin]] = sw[fin] == 0
    if not done.all():
        raise RuntimeError(f"{int((~done).sum())} simulated matches unfinished after {max_points} points")
    return {"a_won": a_won, "served": served, "won": won_srv, "bp_faced": bp_faced, "bp_saved": bp_saved,
            "tb_won": tb_won, "tiebreaks": tb_won.sum(axis=1), "deciding_tb": deciding_tb}
