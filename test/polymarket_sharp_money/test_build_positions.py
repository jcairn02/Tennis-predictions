"""Offline tests for the sharp-money position builder (no network, no staged data)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "polymarket_sharp_money"))

import build_positions as B  # noqa: E402


def fills(rows):
    cols = ["condition_id", "tx_hash", "seq", "proxy_wallet", "side", "outcome_index", "price", "size", "timestamp"]
    return pd.DataFrame(rows, columns=cols)


def prepare(df, y0, fee_rate=0.0, rebate_rate=0.0):
    df = B.backed_bets(B.add_roles(df))
    df["y0"], df["fee_rate"], df["rebate_rate"] = y0, fee_rate, rebate_rate
    return B.pnl_and_fees(df)


def test_backed_bet_normalisation():
    df = B.backed_bets(fills([
        ("m", "t1", 0, "a", "BUY", 0, 0.3, 10, 1),
        ("m", "t2", 1, "a", "SELL", 0, 0.3, 10, 1),
        ("m", "t3", 2, "a", "BUY", 1, 0.6, 10, 1),
        ("m", "t4", 3, "a", "SELL", 1, 0.6, 10, 1),
    ]))
    assert df.backs0.tolist() == [True, False, False, True]
    assert np.allclose(df.q, [0.3, 0.7, 0.6, 0.4])
    assert np.allclose(df.stake, [3.0, 7.0, 6.0, 4.0])
    assert np.allclose(df.d, [10, -10, -10, 10])
    assert np.allclose(df.pi0, [0.3, 0.3, 0.4, 0.4])


@pytest.mark.parametrize("y0", [1.0, 0.0, 0.5])
def test_both_parties_sum_to_zero_for_normal_and_mint_matches(y0):
    df = prepare(fills([
        # normal: taker buys outcome 0 at 0.35 from a maker selling outcome 0
        ("m", "t1", 0, "taker", "BUY", 0, 0.35, 400, 5),
        ("m", "t1", 1, "maker1", "SELL", 0, 0.35, 200, 5),
        # mint: the rest of the same fill is a maker buying outcome 1 at 0.65
        ("m", "t1", 2, "maker2", "BUY", 1, 0.65, 200, 5),
    ]), y0)
    assert df.is_taker.tolist() == [True, False, False]
    assert abs(df.gross.sum()) < 1e-9
    assert np.isclose(df.stake.sum(), 400.0)  # both sides together stake exactly the shares traded


def test_taker_fee_and_pro_rata_maker_rebate():
    t = B.FEE_CASH_START + 60
    df = prepare(fills([
        ("m", "t1", 0, "taker", "BUY", 0, 0.5, 100, t),
        ("m", "t1", 1, "maker1", "SELL", 0, 0.5, 75, t),
        ("m", "t1", 2, "maker2", "SELL", 0, 0.5, 25, t),
    ]), 1.0, fee_rate=0.05, rebate_rate=0.15)
    assert np.isclose(df.fee.iloc[0], 100 * 0.05 * 0.25)  # 1.25 USDC, the documented peak at p = 0.5
    assert np.allclose(df.fee.iloc[1:], 0.0)
    assert np.allclose(df.rebate, [0.0, 0.15 * 1.25 * 0.75, 0.15 * 1.25 * 0.25])
    assert np.isclose(df.net.sum(), -1.25 * (1 - 0.15))


def test_no_cash_fee_before_fees_were_charged():
    t = B.FEE_CASH_START - 60
    df = prepare(fills([
        ("m", "t1", 0, "taker", "SELL", 0, 0.5, 100, t),
        ("m", "t1", 1, "maker", "BUY", 0, 0.5, 100, t),
    ]), 1.0, fee_rate=0.03, rebate_rate=0.25)
    assert np.allclose(df.fee, 0.0) and np.allclose(df.rebate, 0.0)


@pytest.mark.parametrize("y0", [1.0, 0.0])
def test_fee_taken_in_shares_is_charged_at_settlement_value(y0):
    # observed April 2026: taker buys at 0.12, makers deliver 32 + 23.5 shares, taker receives 52.5696
    df = prepare(fills([
        ("m", "t1", 0, "taker", "BUY", 0, 0.12, 52.5696, 5),
        ("m", "t1", 1, "maker1", "SELL", 0, 0.12, 32.0, 5),
        ("m", "t1", 2, "maker2", "BUY", 1, 0.88, 23.5, 5),
    ]), y0, fee_rate=0.03)
    taker = df.iloc[0]
    assert np.isclose(taker.share_fee, 55.5 - 52.5696) and np.isclose(taker.size_gross, 55.5)
    assert abs(df.gross.sum()) < 1e-9                                  # zero-sum on the matched quantity
    assert np.isclose(taker.net, 52.5696 * y0 - 0.12 * 55.5)            # what the taker actually got and paid
    assert np.allclose(df.fee.iloc[1:], 0.0)


def test_qv_variance_buy_and_hold_and_round_trip():
    df = B.backed_bets(fills([
        ("m", "t1", 1, "hold", "BUY", 0, 0.4, 10, 1),
        ("m", "t2", 3, "trip", "BUY", 0, 0.5, 10, 1),
        ("m", "t3", 2, "trip", "SELL", 0, 0.6, 10, 2),
    ]))
    order, group, first, last = B.position_groups(df.proxy_wallet, df.condition_id, df.timestamp, df.seq)
    terms, h = B.qv_terms(df.d.to_numpy()[order], df.pi0.to_numpy()[order], group, last)
    var = np.bincount(group, weights=terms)
    wallets = df.proxy_wallet.to_numpy()[order][first].tolist()
    assert np.isclose(var[wallets.index("hold")], 100 * 0.4 * 0.6)
    assert np.isclose(var[wallets.index("trip")], 100 * 0.1 ** 2)  # exposure only while the price moved 0.5 -> 0.6
    assert np.isclose(h[last][wallets.index("trip")], 0.0)


def test_markouts_use_the_later_taker_price_of_the_same_market():
    df = B.backed_bets(B.add_roles(fills([
        ("m", "t1", 0, "a", "BUY", 0, 0.40, 10, 100),      # taker buys outcome 0 at 0.40
        ("m", "t1", 1, "mk", "SELL", 0, 0.40, 10, 100),    # its maker
        ("m", "t2", 2, "b", "BUY", 0, 0.50, 5, 200),       # later taker trade at 0.50 (within 5 minutes)
        ("m", "t2", 3, "mk", "SELL", 0, 0.50, 5, 200),
        ("n", "t3", 0, "c", "BUY", 1, 0.30, 10, 150),      # another market must not leak in
        ("n", "t3", 1, "mk", "SELL", 1, 0.30, 10, 150),
    ])))
    df["start_ts"] = [150.0, 150.0, 150.0, 150.0, np.nan, np.nan]
    out = B.markouts(df, horizons=(300,))
    assert np.allclose(out["mo5m"][:4], [10 * 0.10, -10 * 0.10, 0.0, 0.0])
    assert np.allclose(out["mo5m"][4:], 0.0)
    # closing line = last taker price before the start (0.40), so the first trade has no CLV, the rest none either
    assert np.allclose(out["clv"], 0.0)


def test_within_one_second_rows_run_in_reverse_api_order():
    df = fills([("m", "t1", 0, "w", "BUY", 0, 0.5, 1, 7), ("m", "t2", 1, "w", "BUY", 0, 0.4, 1, 7)])
    order, *_ = B.position_groups(df.proxy_wallet, df.condition_id, df.timestamp, df.seq)
    assert df.seq.to_numpy()[order].tolist() == [1, 0]


def test_qv_variance_is_unbiased_for_a_martingale_price():
    """Random trading on a Polya-urn price path: mean P&L ~ 0 and mean estimated variance ~ realised variance."""
    rng = np.random.default_rng(7)
    pnl, est = [], []
    for _ in range(4000):
        a, b = 2.0, 2.0
        prices, ds = [], []
        for _step in range(6):
            p = a / (a + b)
            prices.append(p)
            ds.append(rng.choice([-1.0, 1.0]) * rng.uniform(1, 5))
            if rng.random() < p:
                a += 1
            else:
                b += 1
        y = float(rng.random() < a / (a + b))
        prices, ds = np.array(prices), np.array(ds)
        pnl.append(float(np.sum(ds * (y - prices))))
        terms, _ = B.qv_terms(ds, prices, np.zeros(len(ds), dtype=int), np.r_[np.zeros(len(ds) - 1, bool), True])
        est.append(terms.sum())
    pnl = np.array(pnl)
    assert abs(pnl.mean()) < 4 * pnl.std() / np.sqrt(len(pnl))
    assert abs(np.mean(est) / pnl.var() - 1.0) < 0.08


def test_event_type_mapping_and_overrides():
    assert B.event_type("challenger_125_inferred", "ATP", "Bloomfield Hills") == "challenger"
    assert B.event_type("challenger_125_inferred", "WTA", "Montreux") == "wta125"
    assert B.event_type("challenger_125_inferred", "ATP", "BNP Paribas Nordic Open") == "t250_atp"
    assert B.event_type("challenger_125_inferred", "WTA", "Sao Paulo Open, Qualification") == "tour_qual"
    assert B.event_type("team_exhibition", "?", "W50 Guiyang") == "itf_u"
    assert B.event_type("itf", "?", "ITF Hurghada", "M") == "itf_m"
    assert B.event_type("itf", "?", "ITF Bastad", "W") == "itf_w"
    assert B.event_type("slam_main", "WTA", "Wimbledon WTA") == "slam_wta"
    assert B.event_type("tour_1000", "ATP", "Cincinnati Open") == "t1000_atp"
    assert B.event_type("outrights", "?", "US Open") is None


def test_match_gender_uses_agreeing_known_players_only():
    lookup = {"nico hipfl": "M", "pablo perez ramos": "M", "jasmijn gimbrere": "W", "alex smith": None}
    assert B.name_key("Pablo Pérez-Ramos") == "pablo perez ramos"
    assert B.match_gender("ITF Hurghada: Nico Hipfl vs Pablo Perez Ramos", lookup) == "M"
    assert B.match_gender("ITF Bastad: Jasmijn Gimbrere vs. Unknown Person", lookup) == "W"
    assert B.match_gender("ITF X: Alex Smith vs Unknown Person", lookup) is None
    assert B.match_gender("ITF X: Nico Hipfl vs Jasmijn Gimbrere", lookup) is None


def test_scheduled_start_is_epoch_seconds(monkeypatch):
    events = pd.DataFrame({"id": ["e1"], "slug": ["s"], "title": ["ATP X: A vs B"], "league": ["X"],
                           "sport_date": ["2025-10-17"], "bucket_slug": ["tour_250"], "bucket_tour": ["ATP"],
                           "gameId": ["g1"]})
    markets = pd.DataFrame({"id": ["m1"], "question": ["q"], "conditionId": ["c1"], "sportsMarketType": ["moneyline"],
                            "event_id": ["e1"], "closed": ["True"], "outcomes": ['["A", "B"]'],
                            "outcomePrices": ['["1", "0"]'], "clobTokenIds": ['["t0", "t1"]'],
                            "gameStartTime": ["2025-10-17 12:30:00+00"], "volumeNum": ["10"]})
    monkeypatch.setattr(B.pd, "read_parquet", lambda path, columns=None: events if "event" in str(path) else markets)
    monkeypatch.setattr(B, "gender_lookup", lambda: {})
    monkeypatch.setattr(B, "fee_fields", lambda: {})
    out = B.build_markets({"c1"})
    assert out.start_ts.iloc[0] == 1760704200
    assert out.status.iloc[0] == "decisive" and out.y0.iloc[0] == 1.0


def test_settlement_parsing():
    assert B.settlement('["1", "0"]') == ("decisive", 1.0)
    assert B.settlement('["0", "1"]') == ("decisive", 0.0)
    assert B.settlement('["0.5", "0.5"]') == ("void", 0.5)
    assert B.settlement('["0.9995", "0.0005"]')[0] == "unresolved"
    assert B.settlement(None)[0] == "unresolved"
