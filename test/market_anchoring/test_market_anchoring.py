"""Checks of the market-anchoring study's time rule, chronology and symmetry."""
import numpy as np
import pandas as pd
from scipy.special import expit

from src.eda.market_anchoring import common as C
from src.eda.market_anchoring import meta_label as M
from src.eda.market_anchoring import surface_stats as S


def anchored_sample(seed=11):
    rng = np.random.default_rng(seed)
    n = 3200
    m = rng.normal(scale=1.2, size=n)
    x = rng.normal(size=(n, 2))
    return pd.DataFrame({"year": np.repeat(np.arange(2013, 2021), n // 8), "evaluation": True,
                         "p_mkt": expit(m), "x1": x[:, 0], "x2": x[:, 1],
                         "a_won": rng.binomial(1, expit(1.05 * m + 0.15 * x[:, 0])).astype(float)})


def brute_force(key, day, wv, w, half_life):
    out_s, out_n = np.zeros_like(wv), np.zeros_like(w)
    for i in range(len(key)):
        prior = (key == key[i]) & (day < day[i])
        f = np.exp2(-(day[i] - day[prior]) / half_life)[:, None]
        out_s[i], out_n[i] = (wv[prior] * f).sum(axis=0), (w[prior] * f).sum(axis=0)
    return out_s, out_n


def test_decayed_snapshot_uses_strictly_earlier_days_only():
    rng = np.random.default_rng(3)
    day = np.sort(rng.integers(0, 40, size=300))
    key = rng.integers(0, 12, size=300)
    w = rng.uniform(0.2, 2.0, size=(300, 2))
    wv = w * rng.normal(size=(300, 2))
    got = S.decayed_snapshot(key, day, wv, w, 30.0)
    want = brute_force(key, day, wv, w, 30.0)
    np.testing.assert_allclose(got[0], want[0], atol=1e-10)
    np.testing.assert_allclose(got[1], want[1], atol=1e-10)


def test_same_day_and_future_values_cannot_reach_a_snapshot():
    day = np.array([0, 5, 5, 9])
    key = np.zeros(4, dtype=int)
    w = np.ones((4, 1))
    wv = np.array([[1.0], [2.0], [4.0], [8.0]])
    s, n = S.decayed_snapshot(key, day, wv, w, 1e9)
    np.testing.assert_allclose(s[1:3, 0], [1.0, 1.0], rtol=1e-6)    # day-5 rows see day 0 only, not each other
    np.testing.assert_allclose([s[3, 0], n[3, 0]], [7.0, 3.0], rtol=1e-6)  # day 9 sees days 0 and 5, never itself
    assert s[0, 0] == 0.0 and n[0, 0] == 0.0


def test_future_outcomes_cannot_change_earlier_anchored_forecasts():
    frame = anchored_sample()
    before = C.walk_model(frame, ["x1", "x2"], "p_mkt", False, True)
    altered = frame.copy()
    altered.loc[altered.year.eq(2020), "a_won"] = 1 - altered.loc[altered.year.eq(2020), "a_won"]
    after = C.walk_model(altered, ["x1", "x2"], "p_mkt", False, True)
    np.testing.assert_allclose(before, after, equal_nan=True)   # a season's own labels never enter its fit
    altered.loc[altered.year.eq(2018), "a_won"] = 1 - altered.loc[altered.year.eq(2018), "a_won"]
    later = C.walk_model(altered, ["x1", "x2"], "p_mkt", False, True)
    early = frame.year.le(2018).to_numpy()
    np.testing.assert_allclose(before[early], later[early], equal_nan=True)
    assert not np.allclose(before[~early], later[~early])


def test_anchored_forecast_is_side_symmetric():
    frame = anchored_sample()
    swapped = frame.assign(p_mkt=1 - frame.p_mkt, x1=-frame.x1, x2=-frame.x2, a_won=1 - frame.a_won)
    for fixed in (True, False):
        p = C.walk_model(frame, ["x1", "x2"], "p_mkt", fixed, True)
        q = C.walk_model(swapped, ["x1", "x2"], "p_mkt", fixed, True)
        np.testing.assert_allclose(p, -q, equal_nan=True, atol=1e-8)   # log-odds of the other side


def test_offset_without_nudges_returns_the_market():
    frame = anchored_sample()
    frame["zero"] = 0.0
    eta = C.walk_model(frame, ["zero"], "p_mkt", True, True)
    scored = np.isfinite(eta)
    np.testing.assert_allclose(eta[scored], C.clip_logit(frame.p_mkt)[scored], atol=1e-8)


def test_meta_fit_never_shrinks_the_market_term():
    frame = anchored_sample()
    y = frame.a_won.to_numpy()
    x = np.column_stack([C.clip_logit(frame.p_mkt), frame.x1, frame.x2])
    strong = M.fit_with_intercept(x, y, ridge=1e3)(x)
    # Nudges are crushed by the huge ridge but the market slope survives: forecasts track the market.
    assert np.corrcoef(C.clip_logit(strong), x[:, 0])[0, 1] > 0.999
