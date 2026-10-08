"""Tests for A1-T / I2 (src/eda/point_sequence/trait_common.py): the point-level replayer against the builder's scoring
rules, the vectorised statistics against a plain per-match reference, and the frozen priors.

Run: ./python.sh -m pytest test/point_sequence/test_trait.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import replay as R  # noqa: E402
from src.eda.point_sequence import trait_common as T  # noqa: E402


def _simulate(n=600, seed=1):
    rng = np.random.default_rng(seed)
    pa = rng.uniform(0.45, 0.8, n)
    pb = rng.uniform(0.45, 0.8, n)
    bo = rng.choice([3, 5], n)
    fc = rng.integers(0, 4, n)
    s0 = rng.integers(1, 3, n)
    P = T.replay_points(pa, pb, bo, fc, s0, rng)
    return P, pa, pb, bo, fc, s0


def test_replayer_follows_the_builders_rules():
    P, pa, pb, bo, fc, s0 = _simulate()
    m = P["m"]
    bounds = np.r_[0, np.flatnonzero(np.diff(m)) + 1, len(m)]
    assert len(bounds) - 1 == len(pa)
    for i in range(len(pa)):
        a, b = bounds[i], bounds[i + 1]
        w = P["winner"][a:b]
        rep = R.replay(w, R.Rules(int(bo[i]), T.FINAL_NAMES[int(fc[i])]))
        assert rep.status == "complete", i
        assert (rep.set_no == P["set_no"][a:b]).all()
        assert (rep.game_no == P["game_no"][a:b]).all()
        assert (rep.game_idx == P["game_idx"][a:b]).all()
        assert (rep.pt_no == P["pt_no"][a:b]).all()
        assert (rep.is_tb == P["is_tb"][a:b]).all()
        srv = R.rule_servers(rep.game_idx, rep.pt_no, rep.is_tb, int(s0[i]))
        assert (srv == P["server"][a:b]).all()
        assert P["server"][a] == s0[i]


def test_replayer_rates_are_the_serve_rates():
    rng = np.random.default_rng(7)
    n = 4000
    pa, pb = np.full(n, 0.66), np.full(n, 0.55)
    P = T.replay_points(pa, pb, np.full(n, 3), np.zeros(n, int), rng.integers(1, 3, n), rng)
    sa = P["server"] == 1
    won = P["winner"] == P["server"]
    assert abs(won[sa].mean() - 0.66) < 0.005
    assert abs(won[~sa].mean() - 0.55) < 0.005


def _reference(points: pd.DataFrame) -> dict:
    """Plain per-match computation of every statistic, for one match's points (in order)."""
    games = []
    for gi, g in points.groupby("game_idx", sort=True):
        games.append({"set": int(g["set_no"].iloc[0]), "tb": bool(g["is_tb"].iloc[0]), "srv": int(g["server"].iloc[0]),
                      "win": int(g["winner"].iloc[-1]), "sw": (g["winner"] == g["server"]).astype(int).tolist()})
    out = {}
    for side in (1, 2):
        opp = 3 - side
        o = {}
        mine = [i for i, g in enumerate(games) if g["srv"] == side and not g["tb"]]
        theirs = [i for i, g in enumerate(games) if g["srv"] == opp and not g["tb"]]

        def prev_ok(i, k=1):
            return i - k >= 0 and games[i - k]["set"] == games[i]["set"] and not games[i - k]["tb"]

        def excess(target, rest, won):
            n1, h1 = len(target), sum(won(i) for i in target)
            n0, h0 = len(rest), sum(won(i) for i in rest)
            return (h1 - n1 * h0 / n0, n1) if n0 > 0 else (0.0, 0.0)

        held = lambda i: games[i]["win"] == side  # noqa: E731
        ab = [i for i in mine if prev_ok(i) and games[i - 1]["srv"] == opp and games[i - 1]["win"] == side]
        o["S1"] = excess(ab, [i for i in mine if i not in ab], held)
        bb = [i for i in theirs if prev_ok(i) and games[i - 1]["srv"] == side and games[i - 1]["win"] == opp]
        o["S2"] = excess(bb, [i for i in theirs if i not in bb], held)
        ah = [i for i in mine if prev_ok(i, 2) and games[i - 2]["srv"] == side and games[i - 2]["win"] == side]
        o["P0"] = excess(ah, [i for i in mine if i not in ah], held)
        nw = [(len(games[i]["sw"]), sum(games[i]["sw"])) for i in mine]
        N, W = sum(a for a, _ in nw), sum(b for _, b in nw)
        ph = W / N if N else 0.0
        var = N * ph * (1 - ph)
        o["S4"] = (sum((w - k * ph) ** 2 for k, w in nw) - var, var) if var > 0 else (0.0, 0.0)
        X = D = 0.0
        for i in mine:
            s = games[i]["sw"]
            a, b, k = sum(s), len(s) - sum(s), len(s)
            if a > 0 and b > 0:
                runs = 1 + sum(1 for j in range(1, k) if s[j] != s[j - 1])
                X += (1 + 2 * a * b / k) - runs
                D += 2 * a * b * (2 * a * b - k) / (k * k * (k - 1))
        o["S4r"] = (X, D)
        sp = points[points["server"] == side]
        per = sp.groupby("set_no").apply(lambda g: pd.Series({"n": len(g), "w": int((g["winner"] == side).sum())}))
        N, W = per["n"].sum(), per["w"].sum()
        ph = W / N
        var = N * ph * (1 - ph)
        o["S5"] = (float(((per["w"] - per["n"] * ph) ** 2).sum() - var), var) if var > 0 else (0.0, 0.0)
        cells = {}
        for i in mine:
            s = games[i]["sw"]
            sb = rb = 0
            for j, y in enumerate(s):
                if j >= 1:
                    if sb >= 3 and rb >= 3:
                        st = ("deuce", int(np.clip(sb - rb, -1, 1)))
                    else:
                        st = (sb, rb)
                    cells.setdefault(st, []).append((s[j - 1], y))
                sb += y
                rb += 1 - y
        X = D = 0.0
        for v in cells.values():
            xs = np.array([x for x, _ in v], float)
            ys = np.array([y for _, y in v], float)
            dx = xs - xs.mean()
            X += float((dx * ys).sum())
            D += float((dx * dx).sum())
        o["S3"] = (X, D)
        out[side] = o
    return out


def test_statistics_match_a_plain_reference():
    P, pa, pb, bo, fc, s0 = _simulate(n=250, seed=3)
    n = len(pa)
    pm, tot = T.point_stats(P, n, late_set=np.where(bo == 3, 2, 3))
    df = pd.DataFrame({k: v for k, v in P.items()})
    for i in range(n):
        ref = _reference(df[df["m"] == i])
        for side in (1, 2):
            row = pm[(pm["mcode"] == i) & (pm["side"] == side)].iloc[0]
            for s in T.STATS:
                x, d = ref[side][s]
                assert row[f"X_{s}"] == pytest.approx(x, abs=1e-9), (i, side, s)
                assert row[f"D_{s}"] == pytest.approx(d, abs=1e-9), (i, side, s)
    # totals
    assert (tot["pts"].to_numpy() == np.bincount(P["m"], minlength=n)).all()
    assert (pm.groupby("mcode")["svpt"].sum().to_numpy() == tot["pts"].to_numpy()).all()


def test_priors_are_frozen_on_2018():
    rng = np.random.default_rng(0)
    k = 6000
    rows = pd.DataFrame({"tour": rng.choice(["atp", "wta"], k), "surface": rng.choice(["Hard", "Clay"], k),
                         "year": rng.integers(2013, 2025, k), "player": rng.integers(0, 300, k).astype(str),
                         "N": rng.integers(40, 120, k)})
    rows["P"] = np.clip(rng.normal(0.62, 0.08, k), 0.05, 0.95)
    a = T.fit_priors(rows)
    rows2 = rows.copy()
    late = rows2["year"] > 2018
    rows2.loc[late, "P"] = 0.9
    b = T.fit_priors(rows2)
    assert a == b


def test_s4_permutation_preserves_pools_and_rescoring():
    from src.eda.point_sequence import trait_s4_perm as SP
    P, pa, pb, bo, fc, s0 = _simulate(n=300, seed=11)
    n = len(pa)
    pl = SP.pools_of(P)
    order, diag = SP.permute(pl, None)
    assert diag["real_order_valid_pools"] == diag["pools"]
    X0, D0, G0, H0 = SP.s4_rows(SP.pseudo_points(pl, order), n)
    pm, _ = T.point_stats(P, n)
    pm = pm.sort_values(["mcode", "side"], kind="mergesort")
    assert np.allclose(pm["X_S4"].to_numpy(), X0) and np.allclose(pm["D_S4"].to_numpy(), D0)
    assert (pm["svc_games"].to_numpy() == G0).all() and (pm["holds"].to_numpy() == H0).all()
    order, diag = SP.permute(pl, np.random.default_rng(5))
    assert diag["pools_at_cap_kept_real_order"] == 0
    Pp = SP.pseudo_points(pl, order)
    assert Pp["_valid"].all()
    # per-pool won / served preserved, and every pool is a permutation of itself
    assert (np.bincount(pl["pool"], weights=pl["y"][order]) == np.bincount(pl["pool"], weights=pl["y"])).all()
    assert (np.sort(order) == np.arange(len(order))).all()
    assert (pl["pool"][order] == pl["pool"]).all()
    X1, D1, _, _ = SP.s4_rows(Pp, n)
    assert np.allclose(D1, D0)          # p-hat and serve points per player-match unchanged


def test_s4_permutation_is_uniform_over_complete_orders():
    from src.eda.point_sequence import trait_s4_perm as SP
    # one pool: 4 won + 4 lost; the only complete-game orders are WWWWLLLL and LLLLWWWW
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0], np.int8)
    k = 400
    pl = {"y": np.tile(y, k), "starts": np.arange(k) * 8, "lens": np.full(k, 8), "pool": np.repeat(np.arange(k), 8),
          "m": np.repeat(np.arange(k), 8), "set_no": np.ones(8 * k, np.int64), "server": np.ones(8 * k, np.int64)}
    order, diag = SP.permute(pl, np.random.default_rng(1))
    seqs = pl["y"][order].reshape(k, 8)
    first = seqs[:, 0]
    assert set(map(tuple, seqs)) <= {tuple(y), tuple(1 - y)}
    assert 0.4 < first.mean() < 0.6
