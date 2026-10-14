"""Offline tests for the bet-timing study (src/eda/bet_timing/): no fit, no network, synthetic data only."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402
from src.eda.bet_timing import frame as F  # noqa: E402
from src.eda.bet_timing import score as S  # noqa: E402


def test_devig_is_proportional_and_sums_to_one():
    p = C.devig(np.array([1.5, 2.0]), np.array([2.6, 2.0]))
    assert p[1] == pytest.approx(0.5)
    a, b = 1 / 1.5, 1 / 2.6
    assert p[0] == pytest.approx(a / (a + b))
    assert C.devig(2.6, 1.5) == pytest.approx(1 - p[0])


def test_stake_follows_the_owners_rule():
    s = C.stake(np.array([1.25, 1.5, 2.0, 3.0, 5.0]))
    assert s == pytest.approx([4.0, 2.0, 1.0, 0.75, 0.625])
    with pytest.raises(ValueError):
        C.stake(np.array([1.0]))


def test_inputs_known_at_the_quote():
    day = 86400.0
    prev = pd.DataFrame({"prev_lf_a": [100.0, 100.0, -np.inf, 100.0], "prev_lf_b": [-np.inf, 100.0, -np.inf, 100.0],
                         "same_event_a": [False, True, False, False], "same_event_b": [False, False, False, True]})
    t = np.array([101.4, 100.5, 0.0, 101.2]) * day
    # row 0: previous match's last possible day ends by 101.33 < 101.4; row 1: B's previous match (another event, day
    # 100) may end after 100.5; row 2: no previous match; row 3: A's previous may end after 101.2, B's is this event
    assert F.known(prev, t).tolist() == [True, False, True, False]
    assert not F.known(prev, np.full(4, np.nan)).any()


def test_decomposition_identity_holds_exactly():
    rng = np.random.default_rng(0)
    n = 4000
    theta = rng.normal(0, 1.2, n)
    y = (rng.random(n) < C.ex(theta)).astype(float)
    x = pd.DataFrame({"y": y, "block": rng.integers(0, 40, n),
                      "p_e": C.ex(theta + rng.normal(0, 0.5, n)), "p_c": C.ex(theta + rng.normal(0, 0.3, n))})
    x["q_e"] = C.ex(0.9 * C.lg(x["p_e"]) + 0.1 * theta)
    x["q_c"] = C.ex(0.9 * C.lg(x["p_c"]) + 0.1 * theta)
    r = S.decompose(x, "e", "c", np.ones(n, bool), "synthetic")
    lhs = r["E_early"]["est"] - r["E_close"]["est"]
    assert lhs == pytest.approx(r["S_softness"]["est"] - r["A_model_loss"]["est"], abs=1e-9)
    assert lhs == pytest.approx(r["net_E_early_minus_E_close"]["est"], abs=1e-9)
    assert r["S_softness"]["est"] > 0                    # the noisier price is softer


def test_back_picks_the_larger_expected_return_above_the_threshold():
    q = np.array([0.6, 0.6, 0.3, 0.5])
    d_a = np.array([1.8, 1.6, 2.5, 1.9])
    d_b = np.array([2.1, 2.4, 1.5, 1.9])
    side, d, ev = S.back(q, d_a, d_b, 0.0)
    # 0: A ev 0.08, B ev -0.16 -> A; 1: A -0.04, B -0.04 -> no bet; 2: A -0.25, B 0.05 -> B; 3: both -0.05 -> none
    assert side.tolist() == [1, -1, 0, -1]
    assert d[0] == 1.8 and d[2] == 1.5
    assert S.back(q, d_a, d_b, 0.06)[0].tolist() == [1, -1, -1, -1]


def test_book_bets_arithmetic():
    g = pd.DataFrame({"q_bol_open": [0.6, 0.3], "bol_open_a": [1.8, 2.5], "bol_open_b": [2.1, 1.5],
                      "p_bol_open": [0.55, 0.40], "p_bol_close": [0.60, 0.35], "y": [1.0, 1.0]})
    s = S.book_bets(g, "bol_open", 0.0)
    assert s["bet"].tolist() == [True, True]
    # bet 0: A at 1.8 (favourite: stake 1/0.8 = 1.25, wins 1); bet 1: B at 1.5 (stake 2), A won -> loses 2
    assert s["stake"].tolist() == pytest.approx([1.25, 2.0])
    assert s["profit"].tolist() == pytest.approx([1.0, -2.0])
    # CLV: the stake times (close chance of the side x odds - 1): 1.25 (0.60 x 1.8 - 1); 2 (0.65 x 1.5 - 1)
    assert s["clv"].tolist() == pytest.approx([1.25 * 0.08, 2 * -0.025])
    assert s["fav"].tolist() == [True, True]


def test_mean_ci_and_ratio():
    v = np.r_[np.ones(50), np.zeros(50)]
    blk = np.repeat(np.arange(10), 10)
    r = S.mean_ci(v, blk, 1.0)
    assert r["est"] == pytest.approx(0.5) and r["lo"] < 0.5 < r["hi"] and r["blocks"] == 10
    q = S.ratio_boot(np.full(100, 2.0), np.ones(100), blk, 1)
    assert q["est"] == pytest.approx(2.0) and q["lo"] == pytest.approx(2.0) and q["hi"] == pytest.approx(2.0)


def test_logit_cluster_recovers_a_slope():
    rng = np.random.default_rng(3)
    n = 20000
    z1, z2 = rng.normal(0, 1, n), rng.normal(0, 0.3, n)
    y = (rng.random(n) < C.ex(1.0 * z1 + 1.5 * z2)).astype(float)
    r = S.logit_cluster(np.column_stack([z1, z2]), y, rng.integers(0, 50, n))
    assert r["lo"][0] < 1.0 < r["hi"][0] and r["lo"][1] < 1.5 < r["hi"][1]


def test_queries_replace_only_the_odds_input_and_flip_it():
    from src.eda.bet_timing import fits as FT
    from src.eda.serve_speed_tabpfn import arms as A
    names, kinds, _ = A.base_inputs()
    rng = np.random.default_rng(1)
    X = pd.DataFrame({c: rng.normal(size=3) for c in names})
    ids = np.array(["m1", "m2", "m3"])
    prices = pd.DataFrame({"match_id": ids, **{f"p_{b}": [0.6, np.nan, 0.3] for b in C.PRICE_BLOCKS}})
    qs = FT.queries(prices, X, ids)
    Xq, qids = qs["bol_open"]
    assert qids.tolist() == ["m1", "m3"] and len(Xq) == 4
    assert Xq["odds_logit"].iloc[:2].to_numpy() == pytest.approx(C.lg([0.6, 0.3]))
    assert Xq["odds_logit"].iloc[2:].to_numpy() == pytest.approx(-C.lg([0.6, 0.3]))
    other = [c for c in names if c != "odds_logit"]
    assert np.allclose(Xq[other].iloc[:2].to_numpy(), X.loc[[0, 2], other].to_numpy())
    assert len(qs["td"][0]) == 6 and qs["td"][0]["odds_logit"].iloc[0] == X["odds_logit"].iloc[0]
