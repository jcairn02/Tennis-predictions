"""The P9 point-details harness (src/eda/p9_point_details/harness.py, harness_calibrate.py): symmetry, cross-fitting,
the new part, the missing-value handling and the planted-signal recovery. Synthetic data only: no match result, no P9
table and no candidate statistic is read."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.p9_point_details import harness as H  # noqa: E402
from src.eda.p9_point_details import harness_calibrate as HC  # noqa: E402
from src.eda.p9_point_details import harness_population as HP  # noqa: E402


def synthetic(n: int = 6000, gamma: float = 0.0, seed: int = 0, k_inputs: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A population in the harness's layout: two years of dates, prices and two model columns, an outcome drawn from
    the price (plus gamma times the hidden column x_true), and an inputs table (A - B) for the tour rows."""
    rng = np.random.default_rng(seed)
    days = pd.Timestamp("2025-01-06") + pd.to_timedelta(rng.integers(0, 640, n), unit="D")
    L = rng.normal(0, 1.2, n)
    x_true = rng.standard_normal(n)
    y = rng.random(n) < expit(L + gamma * x_true)
    tour = rng.random(n) < 0.4
    pop = pd.DataFrame({"match_id": [f"m{i:06d}" for i in range(n)], "tournament_date": days,
                        "level_group": np.where(tour, "tour", "challenger"),
                        "draw": np.where(rng.random(n) < 0.3, "qualifying", "main"), "finished": rng.random(n) < 0.96,
                        "priced": True, "has_model": tour, "a_won": y, "price_logit": L,
                        "model_logit_full": np.where(tour, L + rng.normal(0, 0.1, n), np.nan),
                        "model_logit_s1": np.where(tour, L + rng.normal(0, 0.1, n), np.nan),
                        "player_a_id": [f"p{i}" for i in rng.integers(0, 500, n)],
                        "player_b_id": [f"p{i}" for i in rng.integers(0, 500, n)], "x_true": x_true})
    Z = pd.DataFrame(rng.standard_normal((n, k_inputs)), columns=[f"in{j}" for j in range(k_inputs)],
                     index=pop["match_id"])
    return pop, Z


def swap(pop: pd.DataFrame, Z: pd.DataFrame, x: pd.Series, rows: np.ndarray):
    """A and B exchanged on the given rows: the result's coding, every log-odds, the feature and the inputs mirrored."""
    p, z, f = pop.copy(), Z.copy(), x.copy()
    p.loc[rows, "a_won"] = ~p.loc[rows, "a_won"]
    for c in ("price_logit", "model_logit_full", "model_logit_s1"):
        p.loc[rows, c] = -p.loc[rows, c]
    ids = p.loc[rows, "match_id"].to_numpy()
    f.loc[ids] = -f.loc[ids]
    z.loc[ids] = -z.loc[ids]
    return p, z, f


# ----------------------------------------------------------------------------------------- symmetry
def test_swapping_a_and_b_changes_no_score():
    pop, Z = synthetic(gamma=0.15, seed=1)
    rng = np.random.default_rng(2)
    x = pd.Series(pop["x_true"].to_numpy() + rng.normal(0, 1, len(pop)), index=pop["match_id"])
    x[rng.random(len(x)) < 0.3] = np.nan                         # partial coverage: both missing handlings run
    a = H.score(pop, x, 1, ("all", "tour", "challenger"), ("price", "model", "model_s1"), inputs=Z, n_boot=500)
    flip = rng.random(len(pop)) < 0.5
    p2, z2, x2 = swap(pop, Z, x, flip)
    b = H.score(p2, x2, 1, ("all", "tour", "challenger"), ("price", "model", "model_s1"), inputs=z2, n_boot=500)
    assert len(a) == len(b) and len(a) > 0
    for c in ("b_per_rms", "se_per_rms", "z", "p_one_sided", "gain_mll", "lo", "hi", "p_better", "lo_t", "hi_t",
              "r2_on_inputs", "corr_with_base"):
        np.testing.assert_allclose(a[c].to_numpy(float), b[c].to_numpy(float), rtol=1e-7, atol=1e-9, err_msg=c)
    assert (a["reading"] == b["reading"]).all()


def test_the_declared_direction_flips_the_one_sided_p():
    pop, _ = synthetic(gamma=0.2, seed=3)
    rows = pop.copy()
    x = rows["x_true"].to_numpy()
    up = H.z_test(rows["a_won"].to_numpy(float), rows["price_logit"].to_numpy(float), x,
                  H.blocks(rows["tournament_date"].to_numpy(), 7), "free", 1)
    down = H.z_test(rows["a_won"].to_numpy(float), rows["price_logit"].to_numpy(float), x,
                    H.blocks(rows["tournament_date"].to_numpy(), 7), "free", -1)
    assert up["z"] > 3 and up["p_one_sided"] < 0.01 and down["p_one_sided"] > 0.99
    assert up["p_one_sided"] + down["p_one_sided"] == pytest.approx(1.0)


def test_cells_get_their_own_slope_and_curvature():
    L = np.array([0.5, -1.0, 2.0, 1.5, -0.3])
    cells = np.array(["tour|main", "tour|main", "challenger|main", "challenger|main", "challenger|qualifying"])
    x = np.arange(5.0)
    X, off = H.design(L, x, "free", cells=cells)
    assert X.shape == (5, 4) and (off == 0).all()            # three slopes, then the feature
    assert (np.count_nonzero(X[:, :3], axis=1) == 1).all()
    np.testing.assert_array_equal(X[:, :3].sum(axis=1), L)
    X, _ = H.design(L, x, "curve", cells=cells)
    assert X.shape == (5, 7)                                  # a slope and a curvature term per cell, then the feature
    X, off = H.design(L, x, "offset", cells=cells)
    assert X.shape == (5, 1) and (off == L).all()
    np.testing.assert_array_equal(H.design(-L, -x, "curve", cells=cells)[0], -H.design(L, x, "curve", cells=cells)[0])


# ----------------------------------------------------------------------------------------- cross-fitting
def test_a_blocks_forecast_never_reads_its_own_results():
    pop, _ = synthetic(gamma=0.2, seed=4)
    y = pop["a_won"].to_numpy(float)
    L = pop["price_logit"].to_numpy(float)
    x = pop["x_true"].to_numpy()
    blk = H.blocks(pop["tournament_date"].to_numpy(), 28)
    target = np.unique(blk)[5]
    y2 = y.copy()
    y2[blk == target] = 1 - y2[blk == target]                    # every result of one block reversed
    for v in ("offset", "free"):
        e1, e2 = H.crossfit(y, L, x, blk, v), H.crossfit(y2, L, x, blk, v)
        np.testing.assert_array_equal(e1[blk == target], e2[blk == target])
        assert not np.allclose(e1[blk != target], e2[blk != target])


def test_crossfit_equals_a_fit_on_the_other_blocks():
    pop, _ = synthetic(gamma=0.2, seed=5)
    y = pop["a_won"].to_numpy(float)
    L = pop["price_logit"].to_numpy(float)
    x = pop["x_true"].to_numpy()
    blk = H.blocks(pop["tournament_date"].to_numpy(), 28)
    e = H.crossfit(y, L, x, blk, "free")
    b0 = np.unique(blk)[3]
    tr = blk != b0
    b, _, _ = H.fit_logit(np.column_stack([L, x])[tr], y[tr])
    np.testing.assert_allclose(e[blk == b0], (np.column_stack([L, x]) @ b)[blk == b0], rtol=1e-8)
    # the offset variant's base-only arm is the base itself
    np.testing.assert_array_equal(H.crossfit(y, L, None, blk, "offset"), L)


def test_a_useless_column_costs_a_little_out_of_sample():
    pop, _ = synthetic(gamma=0.0, seed=6)
    rng = np.random.default_rng(7)
    y, L = pop["a_won"].to_numpy(float), pop["price_logit"].to_numpy(float)
    blk = H.blocks(pop["tournament_date"].to_numpy(), 28)
    gains = [H.gain_test(y, L, rng.standard_normal(len(y)), blk, "offset", n_boot=200)["gain"] for _ in range(30)]
    assert -0.6 < np.mean(gains) < 0.0                            # about -1000 / n per match, n = 6,000


def test_boot_gain_readings():
    blk = np.repeat(np.arange(20), 50)
    assert H.boot_gain(np.full(1000, 0.5) + np.random.default_rng(0).normal(0, 0.1, 1000), blk)["reading"] == "better"
    assert H.boot_gain(np.full(1000, -0.5) + np.random.default_rng(0).normal(0, 0.1, 1000), blk)["reading"] == "worse"
    r = H.boot_gain(np.random.default_rng(1).normal(0, 5, 1000), blk)
    assert r["reading"] == "unresolved" and 0 < r["p_better"] < 1


# ----------------------------------------------------------------------------------------- new part and missing values
def test_new_part_is_orthogonal_to_the_inputs_and_keeps_missing_values():
    rng = np.random.default_rng(8)
    Z = rng.standard_normal((500, 4))
    x = Z @ np.array([0.5, -0.2, 0.0, 0.3]) + rng.standard_normal(500)
    x[:50] = np.nan
    r, r2 = H.new_part(x, Z)
    assert np.isnan(r[:50]).all() and np.isfinite(r[50:]).all()
    np.testing.assert_allclose(Z[50:].T @ r[50:], 0.0, atol=1e-9)
    assert 0.1 < r2 < 0.6


def test_missing_values_scored_as_subset_and_with_the_indicator():
    pop, Z = synthetic(gamma=0.2, seed=9)
    x = pd.Series(pop["x_true"].to_numpy(), index=pop["match_id"])
    x.iloc[::3] = np.nan
    t = H.score(pop, x, 1, ("all",), ("price",), with_new_part=False, n_boot=300)
    assert set(t["missing"]) == {"subset", "indicator"}
    sub = t[t["missing"] == "subset"]
    ind = t[t["missing"] == "indicator"]
    assert (sub["matches"].to_numpy() < ind["matches"].to_numpy()).all()
    assert sub["coverage"].iloc[0] == pytest.approx(2 / 3, abs=0.01)
    assert (sub["z"] > 2).all() and (ind["z"] > 2).all()


def test_model_bases_only_at_tour_level():
    pop, Z = synthetic(seed=10)
    x = pd.Series(np.random.default_rng(11).standard_normal(len(pop)), index=pop["match_id"])
    t = H.score(pop, x, 1, ("all", "tour", "challenger"), ("price", "model"), inputs=Z, n_boot=200)
    assert set(t.loc[t["base"] == "model", "population"]) == {"tour"}
    assert set(t.loc[t["part"] == "new part", "population"]) == {"tour"}


# ----------------------------------------------------------------------------------------- the planted signal
def test_gamma_gives_the_planted_gain():
    L = np.random.default_rng(12).normal(0, 1.2, 4000)
    for g in (0.25, 1.0, 2.0):
        assert HC.kl_gain(L, HC.gamma_for(L, g)) == pytest.approx(g, rel=1e-4)


def test_a_planted_signal_is_recovered():
    rng = np.random.default_rng(13)
    n = 20000
    L = rng.normal(0, 1.2, n)
    days = pd.Timestamp("2025-01-06") + pd.to_timedelta(rng.integers(0, 640, n), unit="D")
    week, blk = H.blocks(days.to_numpy(), 7), H.blocks(days.to_numpy(), 28)
    gam = HC.gamma_for(L, 2.0)
    x = rng.standard_normal(n)
    y = (rng.random(n) < expit(L + gam * x)).astype(float)
    z = H.z_test(y, L, x, week, "free", 1)
    g = H.gain_test(y, L, x, blk, "free", n_boot=500)
    assert z["z"] > 4 and z["b"] == pytest.approx(gam, abs=0.04)
    assert g["reading"] == "better" and 1.0 < g["gain"] < 3.5
    y0 = (rng.random(n) < expit(L)).astype(float)
    assert abs(H.z_test(y0, L, x, week, "free", 1)["z"]) < 4


# ----------------------------------------------------------------------------------------- the window
def test_last_date_keeps_the_matches_played_by_that_day():
    pop, _ = synthetic(seed=14)
    pop["date"] = pop["tournament_date"] + pd.to_timedelta(np.random.default_rng(15).integers(0, 7, len(pop)), unit="D")
    w = H.window(pop, "2026-07-28")
    assert 0 < len(w) < len(pop) and (w["date"] <= pd.Timestamp("2026-07-28")).all()
    assert len(w) == int((pop["date"] <= pd.Timestamp("2026-07-28")).sum())
    assert H.window(pop, None) is pop


def test_last_date_is_refused_with_the_bases_report():
    with pytest.raises(SystemExit):                                  # before any table is read
        H.main(["--bases-report", "--last-date", "2026-07-28"])


def test_a_window_reaching_a_protected_period_is_named(monkeypatch, capsys):
    pop, _ = synthetic(seed=16)                                      # dates to about 7 Oct 2026; moved to about 21 Oct
    pop["date"] = pop["tournament_date"] + pd.Timedelta(days=14)
    monkeypatch.setattr(H, "load_population", lambda path=H.POP: pop)
    assert H.main(["--orientation"]) == 0
    err = capsys.readouterr().err
    assert "reaches H1" in err and "--last-date 2026-10-18 leaves out H1" in err  # the repository's register
    assert H.main(["--orientation", "--last-date", "2026-10-18"]) == 0
    assert "H1" not in capsys.readouterr().err


# ----------------------------------------------------------------------------------------- the blinding guard
def test_the_p9_tables_and_the_build_folder_are_refused():
    for p in (HP.ROOT / "data" / "dump" / "points" / "infosys_atp_recent" / "rally.parquet",
              HP.ROOT / "data" / "studies" / "p9_point_details" / "build" / "anything.parquet"):
        with pytest.raises(RuntimeError):
            HP._check_path(p)
    assert HP._check_path(HP.STAGE0) == HP.STAGE0
