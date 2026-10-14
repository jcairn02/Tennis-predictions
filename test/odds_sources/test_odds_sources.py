"""Offline tests for the odds-sources study (src/eda/odds_sources/): synthetic rows only."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.odds_sources import common as C  # noqa: E402
from src.eda.odds_sources import pools as P  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402


def test_coherent_needs_both_prices_above_one_and_a_sane_overround():
    ok = C.coherent([1.9, 1.0, 1.5, 3.0, np.nan], [1.9, 5.0, 1.5, 3.0, 2.0])
    # 1.9/1.9: 1.053 ok; a price of 1.00 is a placeholder; 1.5/1.5 sums to 1.33; 3/3 sums to 0.67; missing
    assert ok.tolist() == [True, False, False, False, False]
    p = C.devig([1.25], [4.2])
    assert abs(p[0] - (0.8 / (0.8 + 1 / 4.2))) < 1e-12


def test_median_and_mean_of_log_odds_respect_their_minimum_counts():
    P_ = np.array([[0.6, 0.7, np.nan], [0.5, np.nan, np.nan], [0.2, 0.3, 0.9]])
    med = C.median_logit(P_, 2)
    assert np.isnan(med[1]) and abs(med[2] - 0.3) < 1e-12
    mean = C.mean_logit(P_, 1)
    assert abs(mean[1] - 0.5) < 1e-12
    assert abs(C.lg(mean[0]) - 0.5 * (C.lg(0.6) + C.lg(0.7))) < 1e-12
    w = C.mean_logit(np.array([[0.6, 0.8]]), weights=[0.25, 0.75])
    assert abs(C.lg(w[0]) - (0.25 * C.lg(0.6) + 0.75 * C.lg(0.8))) < 1e-12


def frame(rows: dict) -> pd.DataFrame:
    n = len(next(iter(rows.values())))
    base = {"match_id": [f"m{i}" for i in range(n)], "season": [2020] * n, "block": list(range(n)),
            "a_won": [1] * n, "td_date": pd.to_datetime(["2020-01-06"] * n), "td_round": ["R32"] * n}
    return pd.DataFrame({**base, **rows})


def test_drop_late_removes_only_oddstrader_lines_stamped_late():
    df = frame({"p_ot8": [0.6, 0.7], "ot8_a": [1.6, 1.4], "ot8_b": [2.4, 3.0], "over_ot8": [1.04, 1.05],
                "after_ot8_min": [10.0, 45.0], "p_ps": [0.6, 0.7]})
    out = Q.drop_late(df)
    assert out["p_ot8"].tolist()[0] == 0.6 and np.isnan(out["p_ot8"].tolist()[1]) and np.isnan(out["ot8_a"][1])
    assert out["p_ps"].tolist() == [0.6, 0.7] and df["p_ot8"].notna().all()     # the input is left as it was


def test_referees_leave_out_the_same_book_maxima_openings_and_derived_columns():
    df = frame({f"p_{s}": [0.5] for s in ("ps", "ot20", "ot20o", "ot8", "ot131", "avg", "max", "b365", "ot5",
                                          "ot106", "pm_m30", "otmed", "pb", "ot44")})
    assert Q.reference_names(df, "ps") == ["ot8", "ot131", "avg", "b365", "ot5", "ot106", "ot44"]
    assert Q.reference_names(df, "ot8") == ["ps", "ot20", "avg", "b365", "ot5", "ot106", "ot44"]
    assert "b365" not in Q.reference_names(df, "ot106") and "ot5" not in Q.reference_names(df, "b365")


def test_a_mirror_image_is_gross_and_swapped_but_only_when_the_others_agree():
    others = {"p_avg": [0.80, 0.80, 0.80], "p_b365": [0.79, 0.80, 0.55], "p_ot44": [0.81, 0.80, 0.95],
              "p_ot9": [0.80, 0.80, 0.80]}
    df = frame({"p_ps": [0.20, 0.82, 0.20], **others})
    r = Q.disagreement(df, "ps")
    gross, swap, _ = r.pop("_flags")
    assert gross.tolist() == [True, False, False]     # row 3: the others disagree among themselves (wide range)
    assert swap.tolist() == [True, False, False]       # 0.20 is the mirror image of 0.80
    assert r["gross"] == 1 and r["swapped"] == 1


def test_gross_needs_ten_points_of_chance_not_just_log_odds():
    df = frame({"p_ps": [0.979], "p_avg": [0.927], "p_b365": [0.927], "p_ot44": [0.927]})
    gross, _, _ = Q.disagreement(df, "ps")["_flags"]
    assert not gross[0]                                 # 1.3 apart in log-odds, 5 points in chance


def test_the_guard_keeps_the_book_nearer_the_others():
    df = frame({"p_ps": [0.80, 0.60, 0.80], "p_bol": [0.50, 0.62, 0.50], "p_ot8": [0.50, 0.62, 0.50],
                "p_avg": [0.79, 0.61, np.nan], "p_b365": [0.80, 0.60, np.nan], "p_ot44": [0.81, 0.61, np.nan]})
    out, counts = P.guarded(df)
    assert abs(out[0] - 0.80) < 1e-12                              # far apart: Pinnacle sides with the others
    assert abs(C.lg(out[1]) - 0.5 * (C.lg(0.60) + C.lg(0.62))) < 1e-12   # close: the average of the two
    assert abs(C.lg(out[2]) - 0.5 * (C.lg(0.80) + C.lg(0.50))) < 1e-12   # no other books: the average of the two
    assert counts["acted"] == 1 and counts["kept_pinnacle"] == 1


def test_weights_are_walk_forward_and_sum_to_one():
    rng = np.random.default_rng(0)
    n = 3000
    season = np.repeat([2018, 2019, 2020], n)
    z = rng.normal(0, 1, 3 * n)
    y = (rng.random(3 * n) < C.ex(z)).astype(float)
    df = pd.DataFrame({"season": season, "a_won": y, "p_ps": C.ex(z + rng.normal(0, 0.1, 3 * n)),
                       "p_bol": C.ex(z + rng.normal(0, 0.5, 3 * n))})
    out, weights = P.weighted(df, ["ps", "bol"])
    assert np.isnan(out[season == 2018]).all()                     # nothing earlier to learn from
    assert set(weights) == {"2019", "2020"} and weights["2019"]["n_fit"] == n
    for w in weights.values():
        assert abs(sum(w["weights"].values()) - 1) < 1e-3 and w["weights"]["ps"] > w["weights"]["bol"]


def test_mean_ci_and_slope_ci():
    v = np.array([1.0, 2.0, 3.0, 4.0])
    ci = C.mean_ci(v, np.array([0, 0, 1, 1]), scale=1.0)
    assert ci["est"] == 2.5 and ci["lo"] < 2.5 < ci["hi"] and ci["blocks"] == 2
    rng = np.random.default_rng(1)
    z = rng.normal(0, 1.2, 20000)
    y = (rng.random(len(z)) < C.ex(1.1 * z)).astype(float)
    s = C.slope_ci(z, y, np.arange(len(z)) // 50)
    assert s["lo"] < 1.1 < s["hi"]
