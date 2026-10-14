"""Architect memo (edge_anatomy, round 1): how much more a match's points-won share tells about a pre-match strength
shift than its win/loss result does, under the iid point model (simulation; reads no data).

A shift delta in A's point-level log-odds (on serve and on return alike) moves P(A wins the match) and E[A's share of
all points played]. The Fisher information per match about delta is
    from the result:      (dP/ddelta)^2 / (P(1-P))
    from the point share: (dE[share]/ddelta)^2 / Var(share)
Their ratio is how many times more matches a test on the result needs than a test on the point share, for a signal that
acts through point-level strength. Cases: men (serve-point win 0.64) and women (0.56), best of 3 and best of 5, an even
match and a 70/30 match.
Run: ./python.sh data/studies/edge_anatomy/team/architect/point_share_information.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.special import expit, logit

RNG = np.random.default_rng(20261012)
OUT = Path(__file__).resolve().parent / "point_share_information.txt"


def game(p, rng, n):
    """Simulate n service games won by the server with point probability p; returns (won, points_server, points_ret)."""
    won = np.zeros(n, bool)
    ps = np.zeros(n, int)
    pr = np.zeros(n, int)
    a = np.zeros(n, int)
    b = np.zeros(n, int)
    live = np.ones(n, bool)
    while live.any():
        idx = np.flatnonzero(live)
        w = rng.random(len(idx)) < p[idx]
        a[idx] += w
        b[idx] += ~w
        ps[idx] += w
        pr[idx] += ~w
        done = ((a[idx] >= 4) | (b[idx] >= 4)) & (np.abs(a[idx] - b[idx]) >= 2)
        won[idx[done]] = a[idx[done]] > b[idx[done]]
        live[idx[done]] = False
    return won, ps, pr


def tiebreak(pa_srv, pb_srv, rng, n):
    """Simulate n tiebreaks (A serves first point); returns (A won, A points, B points)."""
    a = np.zeros(n, int)
    b = np.zeros(n, int)
    won = np.zeros(n, bool)
    live = np.ones(n, bool)
    k = 0
    while live.any():
        idx = np.flatnonzero(live)
        a_serves = ((k + 1) // 2) % 2 == 0
        p = pa_srv[idx] if a_serves else 1 - pb_srv[idx]
        w = rng.random(len(idx)) < p
        a[idx] += w
        b[idx] += ~w
        done = ((a[idx] >= 7) | (b[idx] >= 7)) & (np.abs(a[idx] - b[idx]) >= 2)
        won[idx[done]] = a[idx[done]] > b[idx[done]]
        live[idx[done]] = False
        k += 1
    return won, a, b


def match(pa, pb, best_of, n, rng):
    """pa = P(A wins a point on A's serve), pb = P(B wins a point on B's serve). Returns (A won, A share of points)."""
    sets_a = np.zeros(n, int)
    sets_b = np.zeros(n, int)
    pts_a = np.zeros(n, int)
    pts_b = np.zeros(n, int)
    need = best_of // 2 + 1
    live = np.ones(n, bool)
    a_serves_first = np.ones(n, bool)
    while live.any():
        idx = np.flatnonzero(live)
        ga = np.zeros(len(idx), int)
        gb = np.zeros(len(idx), int)
        set_live = np.ones(len(idx), bool)
        server_a = a_serves_first[idx].copy()
        while set_live.any():
            j = np.flatnonzero(set_live)
            tb = (ga[j] == 6) & (gb[j] == 6)
            jt, jg = j[tb], j[~tb]
            if len(jg):
                sa = server_a[jg]
                p = np.where(sa, pa[idx[jg]], pb[idx[jg]])
                w, s_pts, r_pts = game(p, rng, len(jg))
                a_won_game = np.where(sa, w, ~w)
                ga[jg] += a_won_game
                gb[jg] += ~a_won_game
                pts_a[idx[jg]] += np.where(sa, s_pts, r_pts)
                pts_b[idx[jg]] += np.where(sa, r_pts, s_pts)
                server_a[jg] = ~sa
                fin = ((ga[jg] >= 6) | (gb[jg] >= 6)) & (np.abs(ga[jg] - gb[jg]) >= 2) | (ga[jg] == 7) | (gb[jg] == 7)
                set_live[jg[fin]] = False
            if len(jt):
                w, a_pts, b_pts = tiebreak(pa[idx[jt]], pb[idx[jt]], rng, len(jt))
                ga[jt] += w
                gb[jt] += ~w
                pts_a[idx[jt]] += a_pts
                pts_b[idx[jt]] += b_pts
                set_live[jt] = False
        sets_a[idx] += ga > gb
        sets_b[idx] += gb > ga
        a_serves_first[idx] = ~a_serves_first[idx]
        done = (sets_a[idx] == need) | (sets_b[idx] == need)
        live[idx[done]] = False
    return sets_a == need, pts_a / (pts_a + pts_b)


def info_ratio(serve, best_of, base_shift, n=200_000, h=0.05):
    out = {}
    for sgn in (-1, 0, 1):
        d = base_shift + sgn * h
        pa = np.full(n, expit(logit(serve) + d))
        pb = np.full(n, expit(logit(serve) - d))
        won, share = match(pa, pb, best_of, n, RNG)
        out[sgn] = (won.mean(), share.mean(), share.var())
    P0, S0, V0 = out[0]
    dP = (out[1][0] - out[-1][0]) / (2 * h)
    dS = (out[1][1] - out[-1][1]) / (2 * h)
    info_result = dP ** 2 / (P0 * (1 - P0))
    info_share = dS ** 2 / V0
    return P0, S0, np.sqrt(V0), info_result, info_share, info_share / info_result


def main():
    lines = ["case | P(A wins) | E[share] | SD(share) | info from result | info from share | ratio share/result"]
    for tour, serve in (("men", 0.64), ("women", 0.56)):
        for bo in (3, 5) if tour == "men" else (3,):
            for label, shift in (("even", 0.0), ("70/30", None)):
                if shift is None:
                    # find the point-level shift that gives about 70% match wins
                    lo, hi = 0.0, 0.5
                    for _ in range(14):
                        mid = (lo + hi) / 2
                        pa = np.full(20_000, expit(logit(serve) + mid))
                        pb = np.full(20_000, expit(logit(serve) - mid))
                        w, _ = match(pa, pb, bo, 20_000, RNG)
                        lo, hi = (mid, hi) if w.mean() < 0.70 else (lo, mid)
                    shift = (lo + hi) / 2
                r = info_ratio(serve, bo, shift)
                lines.append(f"{tour} bo{bo} {label} (shift {shift:.3f}) | {r[0]:.3f} | {r[1]:.4f} | {r[2]:.4f} | "
                             f"{r[3]:.3f} | {r[4]:.3f} | {r[5]:.1f}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
