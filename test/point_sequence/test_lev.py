"""Tests for return / serve leverage (src/eda/point_sequence/lev_common.py): the vectorised importance against
stage2_pbp.Chances.importance, the exact within-set shuffle's validity, and the RL / SL mirror.

Run: ./python.sh -m pytest test/point_sequence/test_lev.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import lev_common as L  # noqa: E402
from src.eda.point_sequence import replay as R  # noqa: E402
from src.eda.point_sequence import trait_common as T  # noqa: E402
from src.eda.predictability_diagnostic.stage2_pbp import Chances  # noqa: E402


def _matches(n=80, seed=3):
    rng = np.random.default_rng(seed)
    pa, pb = rng.uniform(0.5, 0.75, n), rng.uniform(0.5, 0.75, n)
    bo = rng.choice([3, 5], n)
    fc = np.tile(np.arange(4), n // 4 + 1)[:n]
    s0 = rng.integers(1, 3, n)
    P = T.replay_points(pa, pb, bo, fc, s0, rng)
    pre_a, pre_b = rng.uniform(0.5, 0.72, n), rng.uniform(0.5, 0.72, n)
    return P, bo, fc, s0, pre_a, pre_b


def test_importance_equals_chances():
    P, bo, fc, s0, pre_a, pre_b = _matches()
    w = L.importance(P, pre_a, pre_b, bo, fc, chunk=17)
    st = L.point_states(P)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(w), 3000, replace=False)
    cache = {}
    for i in idx:
        mi = int(P["m"][i])
        if mi not in cache:
            cache[mi] = Chances(pre_a[mi], pre_b[mi], int(bo[mi]), L.RULE_NAME[int(fc[mi])])
        tb = bool(st["tb"][i])
        state = (int(st["sa"][i]), int(st["sb"][i]), int(st["ga"][i]), int(st["gb"][i]), int(st["x"][i]),
                 int(st["y"][i]), tb, bool(st["first1"][i]) if tb else True)
        ref = cache[mi].importance(state, bool(st["srv1"][i]))
        assert w[i] == pytest.approx(ref, abs=1e-9), (i, state)
    assert (w >= -1e-12).all()


def test_shuffle_is_valid_and_preserves_pools():
    P, bo, fc, s0, pre_a, pre_b = _matches(n=200, seed=5)
    info = L.set_info(P, fc, bo)
    n = len(bo)
    for X in (1, 2):
        Q, diag = L.shuffle_world(P, X, np.random.default_rng(X), info)
        assert diag["regular_capped_kept_real"] <= 0.01 * diag["regular_pools"]
        bp = np.r_[0, np.flatnonzero(np.diff(P["m"])) + 1, len(P["m"])]
        bq = np.r_[0, np.flatnonzero(np.diff(Q["m"])) + 1, len(Q["m"])]
        changed = 0
        for i in range(n):
            a, b = bp[i], bp[i + 1]
            c, d = bq[i], bq[i + 1]
            assert b - a == d - c
            rule = R.Rules(int(bo[i]), T.FINAL_NAMES[int(fc[i])])
            rp, rq = R.replay(P["winner"][a:b], rule), R.replay(Q["winner"][c:d], rule)
            assert rq.status == "complete"
            assert rq.sets == rp.sets                     # same set scores, tie-break scores included
            srv = R.rule_servers(rq.game_idx, rq.pt_no, rq.is_tb, int(Q["server"][c]))
            assert (srv == Q["server"][c:d]).all()
            assert (rq.game_idx == Q["game_idx"][c:d]).all() and (rq.is_tb == Q["is_tb"][c:d]).all()
            for s in np.unique(P["set_no"][a:b]):
                for sv in (1, 2):
                    mp = (P["set_no"][a:b] == s) & (P["server"][a:b] == sv)
                    mq = (Q["set_no"][c:d] == s) & (Q["server"][c:d] == sv)
                    op = P["winner"][a:b][mp] == sv
                    oq = Q["winner"][c:d][mq] == sv
                    assert op.sum() == oq.sum() and mp.sum() == mq.sum()
                    if sv != X:                           # the other server's points keep their order
                        assert (op == oq).all()
            changed += int((P["winner"][a:b] != Q["winner"][c:d]).any())
        assert changed > n // 2


def test_rl_mirrors_opponent_sl():
    P, bo, fc, s0, pre_a, pre_b = _matches(n=60, seed=9)
    w = L.importance(P, pre_a, pre_b, bo, fc)
    d = L.leverage(P, w, len(bo))
    a, b = d[d["side"] == 1].reset_index(drop=True), d[d["side"] == 2].reset_index(drop=True)
    assert np.allclose(a["X_RL"], -b["X_SL"]) and np.allclose(a["D_RL"], b["D_SL"])
    assert np.allclose(b["X_RL"], -a["X_SL"]) and np.allclose(b["D_RL"], a["D_SL"])
