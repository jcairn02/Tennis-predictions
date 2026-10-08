"""Offline tests for the line-sharpening study: start detection, price lookups, the book arithmetic and the
order-book replay (synthetic data, no network)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.line_sharpening import books as BK  # noqa: E402
from src.eda.line_sharpening import common as K  # noqa: E402


# --------------------------------------------------------------------------------------
# start detection
# --------------------------------------------------------------------------------------
def path_with_play(start_play: float, quiet_until: float, end: float, rng: np.random.Generator):
    """Minute points: flat-ish before `start_play`, in-play swings (about 2c a minute) after it."""
    t = np.arange(quiet_until, end, 60.0)
    p = np.full(len(t), 0.60)
    live = t >= start_play
    p[live] = 0.60 + np.cumsum(rng.choice([-0.02, 0.02], live.sum()))
    return t, np.clip(p, 0.02, 0.98)


def test_detects_the_first_live_minute():
    rng = np.random.default_rng(1)
    listed = 1_000_000.0
    t, p = path_with_play(listed + 3 * 3600, listed - 10 * 3600, listed + 6 * 3600, rng)
    d = K.detect_start(t, p, listed)
    assert d == pytest.approx(listed + 3 * 3600, abs=60)


def test_a_single_prematch_jump_is_not_play():
    t = np.arange(0.0, 20 * 3600, 60.0)
    p = np.full(len(t), 0.55)
    p[300:] = 0.62          # one 7c news move, then quiet
    assert np.isnan(K.detect_start(t, p, 10 * 3600))


def test_no_detection_outside_the_search_window():
    rng = np.random.default_rng(2)
    listed = 1_000_000.0
    t, p = path_with_play(listed - 8 * 3600, listed - 12 * 3600, listed - 7 * 3600, rng)
    assert np.isnan(K.detect_start(t, p, listed))       # play 8 h before the listed start: outside [-6 h, +30 h]


# --------------------------------------------------------------------------------------
# lookups and scoring
# --------------------------------------------------------------------------------------
def test_lookup_takes_the_last_point_of_the_same_market_within_age():
    keys = np.array([0, 0, 0, 1, 1])
    times = np.array([100.0, 200.0, 300.0, 150.0, 5000.0])
    vals = np.array([0.1, 0.2, 0.3, 0.7, 0.8])
    v, t = K.lookup(keys, times, vals, np.array([0, 0, 1, 1, 0]), np.array([250.0, 99.0, 160.0, 4000.0, 9999.0]),
                    max_age=3600)
    assert v[0] == 0.2 and t[0] == 200.0
    assert np.isnan(v[1])                      # before the market's first point
    assert v[2] == 0.7
    assert np.isnan(v[3])                      # 3,850 s old
    assert np.isnan(v[4])                      # market 0's last point is 9,699 s old


def test_log_loss_matches_definition():
    assert K.log_loss(np.array([0.8]), np.array([1]))[0] == pytest.approx(-np.log(0.8))
    assert K.log_loss(np.array([0.8]), np.array([0]))[0] == pytest.approx(-np.log(0.2))


# --------------------------------------------------------------------------------------
# book arithmetic
# --------------------------------------------------------------------------------------
def test_buy_side_vwap_and_capacity():
    prices = np.array([0.50, 0.51, 0.53])
    sizes = np.array([400.0, 400.0, 10000.0])        # $200 at 0.50, $204 at 0.51
    out = BK.buy_side(prices, sizes, mid=0.495)
    assert out["vwap_100"] == pytest.approx(0.50)
    # $300: 400 shares at 0.50 ($200) + 196.08 shares at 0.51 ($100)
    assert out["vwap_300"] == pytest.approx(300 / (400 + 100 / 0.51))
    # within 1c of mid (0.505): all of 0.50, then 0.51 until the average reaches 0.505 -> 400 more shares
    assert out["cap_1"] == pytest.approx(200 + 0.51 * 400)
    # within 2c (0.515): 0.50 and 0.51 whole (avg 0.505), then 0.53 until avg = 0.515: s = (0.515*800 - 404)/0.015
    s = (0.515 * 800 - 404) / (0.53 - 0.515)
    assert out["cap_2"] == pytest.approx(404 + 0.53 * s)


def test_buy_side_when_the_touch_is_beyond_the_limit():
    out = BK.buy_side(np.array([0.60]), np.array([1000.0]), mid=0.55)
    assert out["cap_1"] == 0.0 and out["cap_2"] == 0.0
    assert out["vwap_300"] == pytest.approx(0.60)


def test_buy_side_book_too_thin():
    out = BK.buy_side(np.array([0.50]), np.array([100.0]), mid=0.495)    # $50 on the book
    assert np.isnan(out["vwap_100"])


def test_snapshot_mirrors_the_other_side():
    bids = {0.48: 1000.0, 0.47: 1000.0}     # B can be bought at 0.52 (1000 shares) and 0.53
    asks = {0.50: 1000.0}
    s = BK.snapshot(bids, asks)
    assert s["mid"] == pytest.approx(0.49) and s["spread"] == pytest.approx(0.02)
    assert s["vwap_b_300"] == pytest.approx(0.52)        # $300 fits in the 0.52 level ($520)
    assert s["vwap_a_300"] == pytest.approx(0.50)


# --------------------------------------------------------------------------------------
# replay
# --------------------------------------------------------------------------------------
def test_replay_applies_snapshots_and_level_changes_in_order():
    ev = pd.DataFrame({
        "ts_s": [10.0, 70.0, 80.0, 130.0],
        "event_type": ["book", "price_change", "price_change", "book"],
        "price": [np.nan, 0.50, 0.51, np.nan],
        "size": [np.nan, 0.0, 300.0, np.nan],
        "side": [None, "SELL", "SELL", None],
        "bids": ['[["0.48","100"]]', None, None, '[["0.40","100"]]'],
        "asks": ['[["0.50","100"],["0.52","100"]]', None, None, '[["0.45","100"]]'],
    })
    rows, _ = BK.replay(ev, np.array([0.0, 60.0, 120.0, 180.0]))
    assert [r["t"] for r in rows] == [60.0, 120.0, 180.0]          # unknown before the first snapshot
    assert rows[0]["best_ask"] == 0.50
    assert rows[1]["best_ask"] == 0.51                             # 0.50 removed, 0.51 added
    assert rows[2]["best_bid"] == 0.40 and rows[2]["best_ask"] == 0.45   # replaced by the second snapshot


def test_replay_repairs_quotes_the_exchange_no_longer_shows():
    ev = pd.DataFrame({
        "ts_s": [10.0, 70.0],
        "event_type": ["book", "price_change"],
        "price": [np.nan, 0.30],
        "size": [np.nan, 50.0],
        "side": [None, "BUY"],
        "bids": ['[["0.45","100"],["0.44","100"]]', None],
        "asks": ['[["0.46","1000"],["0.47","1000"],["0.60","100"]]', None],
        # the exchange says: best bid 0.44, best ask 0.60 (0.45 bid and 0.46-0.47 asks pulled, rows missing)
        "best_bid": [np.nan, 0.44],
        "best_ask": [np.nan, 0.60],
    })
    rows, stats = BK.replay(ev, np.array([60.0, 120.0]))
    assert rows[0]["best_ask"] == 0.46 and rows[0]["bbo_match"]
    assert rows[1]["best_bid"] == 0.44 and rows[1]["best_ask"] == 0.60 and rows[1]["bbo_match"]
    assert stats["repairs"] == 2
    unrepaired, _ = BK.replay(ev, np.array([120.0]), repair=False)
    assert unrepaired[0]["best_ask"] == 0.46 and not unrepaired[0]["bbo_match"]


# --------------------------------------------------------------------------------------
# validated start
# --------------------------------------------------------------------------------------
def test_decided_at_is_the_last_exit_from_the_open_band():
    t = np.arange(10.0)
    p = np.array([0.5, 0.6, 0.98, 0.5, 0.7, 0.99, 0.995, 0.999, 0.999, 1.0])
    assert K.decided_at(t, p) == 5.0
    assert np.isnan(K.decided_at(t[:5], p[:5]))       # still open at the end


def test_validated_start_skips_an_early_prematch_swing():
    rng = np.random.default_rng(3)
    listed = 1_000_000.0
    t = np.arange(listed - 10 * 3600, listed + 3 * 3600, 60.0)
    p = np.full(len(t), 0.50)
    swing = (t >= listed - 5 * 3600) & (t < listed - 5 * 3600 + 20 * 60)   # 20 minutes of 2c flicker, 5 h early
    p[swing] = 0.50 + rng.choice([-0.02, 0.02], swing.sum())
    live = (t >= listed) & (t < listed + 100 * 60)                           # play: 3-4c swings drifting up
    p[live] = np.clip(0.50 + np.cumsum(rng.choice([-0.03, 0.04], live.sum())), 0.04, 0.96)
    p[t >= listed + 100 * 60] = 1.0                                          # decided after 100 minutes
    d, dec, tries = K.validated_start(t, p, listed)
    assert tries == 2                                                        # the swing, then play
    assert d == pytest.approx(listed, abs=120)
    assert dec == listed + 100 * 60


# --------------------------------------------------------------------------------------
# scoring and bootstrap
# --------------------------------------------------------------------------------------
def test_scores_sign_and_clv():
    from src.eda.line_sharpening import evaluate as EV
    s = EV.scores(np.array([0.50]), np.array([0.60]), np.array([1.0]))
    assert s["dll"][0] == pytest.approx(1000 * (np.log(0.6) - np.log(0.5)))     # 0.50 is the worse forecast: positive
    assert s["dll"][0] > 0
    assert s["move"][0] == pytest.approx(10.0)
    assert s["clv"][0] == pytest.approx(100 * (0.60 / 0.50 - 1))        # back player A at 0.50, close 0.60


def test_boot_means_covers_the_mean():
    from src.eda.line_sharpening import evaluate as EV
    rng = np.random.default_rng(0)
    x = np.c_[rng.normal(1.0, 1.0, 4000), rng.normal(-2.0, 0.5, 4000)]
    b = EV.boot_means(x, seed=1, draws=400)
    assert b[1, 0] < 1.0 < b[2, 0] and b[1, 1] < -2.0 < b[2, 1]
    assert b[2, 0] - b[1, 0] == pytest.approx(2 * 1.96 / np.sqrt(4000), rel=0.25)


# --------------------------------------------------------------------------------------
# early-versus-close betting
# --------------------------------------------------------------------------------------
def test_decide_backs_the_side_with_the_better_ev_after_spread_and_fee():
    from src.eda.line_sharpening import timing_bets as TB
    m = np.array([0.60, 0.40, 0.50])
    p = np.array([0.50, 0.50, 0.50])
    fee = np.array([0.05, 0.05, 0.0])
    side, ask, f, ev = TB.decide(m, p, fee, tau=0.0)
    assert list(side) == [1, 0, -1]                          # A, B, no bet (no edge after the half-cent spread)
    assert ask[0] == pytest.approx(0.505) and ask[1] == pytest.approx(0.505)
    assert f[0] == pytest.approx(0.05 * 0.495)
    assert ev[0] == pytest.approx(0.60 / 0.505 - 1 - 0.05 * 0.495)
    side2, *_ = TB.decide(m, p, fee, tau=0.2)
    assert list(side2) == [-1, -1, -1]                       # 15.6% EV is below a 20% threshold


def test_boot_ratio_is_profit_per_dollar_staked():
    from src.eda.line_sharpening import timing_bets as TB
    ret = np.array([1.0, -1.0, 0.0, 0.5])
    bet = np.array([1.0, 1.0, 0.0, 1.0])
    est, lo, hi = TB.boot(ret, bet, seed=3)
    assert est == pytest.approx(0.5 / 3)
    assert lo <= est <= hi
