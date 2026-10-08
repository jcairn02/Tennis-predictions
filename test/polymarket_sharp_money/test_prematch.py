"""Offline tests for the pre-match closing-price analysis (no network, no staged data)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "polymarket_sharp_money"))

import build_positions as B  # noqa: E402
import prematch as P  # noqa: E402


def test_edge_is_expected_profit_at_the_closing_price_and_sums_to_zero():
    # a taker buys 200 shares of player 0 at 0.50 from a maker; the close is 0.5075
    df = pd.DataFrame([("m", "t1", 0, "taker", "BUY", 0, 0.50, 200, 1), ("m", "t1", 1, "maker", "SELL", 0, 0.50, 200, 1)],
                      columns=["condition_id", "tx_hash", "seq", "proxy_wallet", "side", "outcome_index", "price", "size",
                               "timestamp"])
    df = B.backed_bets(B.add_roles(df))
    edge = P.edge_vs_close(df.d.to_numpy(), df.pi0.to_numpy(), np.full(2, 0.5075))
    assert np.isclose(edge[0], 1.50) and np.isclose(edge[1], -1.50)   # $1.50 on a $100 bet, and its mirror
    # backing player 1 at 0.40 when player 0 closes at 0.55 (player 1 at 0.45): +5c a share
    one = B.backed_bets(pd.DataFrame([("m", "t", 0, "w", "BUY", 1, 0.40, 10, 1)], columns=df.columns[:9]))
    assert np.isclose(P.edge_vs_close(one.d.to_numpy(), one.pi0.to_numpy(), np.array([0.55]))[0], 10 * 0.05)


def test_record_uses_one_observation_per_market():
    hist = pd.DataFrame({"proxy_wallet": ["w"] * 4, "condition_id": list("abcd"), "stake": [100.0] * 4,
                         "edge": [2.0, 1.0, 3.0, 2.0]})
    r = P.record(hist).loc["w"]
    assert r.n_hist == 4 and np.isclose(r.rate, 0.02)
    resid = np.array([0.0, -1.0, 1.0, 0.0])
    assert np.isclose(r.se, np.sqrt((resid ** 2).sum() * 4 / 3) / 400)
    assert np.isclose(r.z, 0.02 / r.se)


def test_group_rules_need_ten_matches_and_two_standard_errors():
    assert P.group_of(np.array([9, 10, 10, 10, 50]), np.array([5.0, 2.0, 1.9, -2.0, np.nan])).tolist() == \
        ["unsure", "win", "unsure", "lose", "unsure"]


def test_crossfit_scores_each_match_from_the_others_only():
    pos = pd.DataFrame({"proxy_wallet": ["w"] * 4, "condition_id": list("abcd"), "stake": [100.0] * 4,
                        "edge": [5.0, 5.0, -5.0, -5.0]})
    out = P.crossfit(pos, pd.Series({"a": 0, "b": 0, "c": 1, "d": 1})).set_index("condition_id")
    assert np.allclose(out.loc[["a", "b"], "rate"], -0.05) and np.allclose(out.loc[["c", "d"], "rate"], 0.05)
    assert (out.group == "unsure").all() and out.few_bets.all()        # two other matches: too few for a verdict
