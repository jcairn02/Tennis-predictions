import numpy as np
import pandas as pd
from scipy.special import expit
from src.eda.predictive_frontier.score import holm, select_past, walk


def sample():
    rng = np.random.default_rng(204)
    x = rng.normal(size=(2000, 2))
    return pd.DataFrame({"year": np.repeat(np.arange(2016, 2021), 400), "evaluation": True,
                         "base": x[:, 0], "extra": x[:, 1],
                         "a_won": rng.binomial(1, expit(x[:, 0] + x[:, 1] / 4))})


def test_target_outcomes_cannot_change_own_season_predictions_or_selection():
    f = sample()
    p, records = walk(f, ["base", "extra"], ["extra"])
    f.loc[f.year >= 2019, "a_won"] = 1 - f.loc[f.year >= 2019, "a_won"]
    changed, updated = walk(f, ["base", "extra"], ["extra"])
    assert np.allclose(p[f.year <= 2019], changed[f.year <= 2019], equal_nan=True)
    assert [r for r in records if r["year"] <= 2019] == [r for r in updated if r["year"] <= 2019]
    assert not np.allclose(p[f.year == 2020], changed[f.year == 2020])


def test_model_and_penalty_side_exchange_symmetry():
    f = sample()
    p, _ = walk(f, ["base", "extra"], ["extra"])
    f[["base", "extra"]] *= -1
    f["a_won"] = 1-f.a_won
    q, _ = walk(f, ["base", "extra"], ["extra"])
    finite = np.isfinite(p)
    assert np.allclose(p[finite]+q[finite], 1, atol=1e-10)


def test_selector_cannot_see_current_outcomes():
    f = sample()
    preds = {"baseline": expit(f.base.to_numpy()), "extra": expit(f.extra.to_numpy())}
    p, records = select_past(f, preds)
    f.loc[f.year == 2020, "a_won"] = 1-f.loc[f.year == 2020, "a_won"]
    q, changed = select_past(f, preds)
    assert np.array_equal(p, q)
    assert records == changed
    assert all(max(r["validation_years"], default=-1) < r["year"] for r in records)


def test_holm_known_values_and_order():
    assert np.allclose(holm([.04, .001, .03]), [.06, .003, .06])
