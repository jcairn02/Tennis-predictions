"""Tests of the pair-strength study (src/eda/pair_strength/): the modulators' swap symmetry, the slope regression on
planted effects, the walk-forward layers' use of past seasons only, and the final test's primary on SYNTHETIC outcomes
(the real 2025-2026 population and forecasts, no result read)."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.pair_strength import common as C  # noqa: E402


def synthetic_frame(n: int = 20_000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    players = np.array([f"p{i}" for i in range(400)])
    pa = rng.choice(players, n)
    pb = rng.choice(players, n)
    return pd.DataFrame({
        "tour": rng.choice(["atp", "wta"], n), "season": rng.choice(np.arange(2014, 2025), n),
        "block": rng.integers(0, 120, n), "player_a_id": pa, "player_b_id": pb,
        "elo_R_a": rng.normal(2200, 150, n), "elo_R_b": rng.normal(2200, 150, n),
        "rank_a": rng.integers(1, 300, n).astype(float), "rank_b": rng.integers(1, 300, n).astype(float),
        "ttt_mu_a": rng.normal(0, 1, n), "ttt_mu_b": rng.normal(0, 1, n), "overround_avg": rng.uniform(0.03, 0.08, n),
        "age_a": rng.uniform(18, 35, n), "age_b": rng.uniform(18, 35, n), "elo_N_a": rng.integers(0, 500, n),
        "elo_N_b": rng.integers(0, 500, n), "z_market": rng.normal(0, 1.2, n)})


def swapped(F: pd.DataFrame) -> pd.DataFrame:
    G = F.copy()
    for stem in ("elo_R", "rank", "ttt_mu", "age", "elo_N"):
        G[f"{stem}_a"], G[f"{stem}_b"] = F[f"{stem}_b"].to_numpy(), F[f"{stem}_a"].to_numpy()
    G["z_market"] = -F["z_market"].to_numpy()
    return G


def test_modulators_are_symmetric():
    F = synthetic_frame(5_000)
    F.loc[:50, "z_market"] = 0.0                       # even prices: the favourite's tie-break must be symmetric
    a, b = C.add_modulators(F), C.add_modulators(swapped(F))
    cols = [c for c in a.columns if c.startswith(("pr_", "s_"))]
    assert len(cols) >= 20
    for c in cols:
        x, y = a[c].to_numpy(float), b[c].to_numpy(float)
        assert np.allclose(x, y, equal_nan=True), c


def test_slope_fit_recovers_a_planted_modulation():
    F = synthetic_frame(40_000, seed=1)
    rng = np.random.default_rng(2)
    eta = F["z_market"].to_numpy(float)
    s = rng.normal(0, 1, len(F))
    tour_slope = np.where(F["tour"] == "atp", 0.9, 0.95)
    for b_true in (-0.08, 0.0):
        y = rng.random(len(F)) < expit(tour_slope * eta + b_true * s * eta)
        F["a_won"] = y
        r = C.slope_fit(F, np.ones(len(F), bool), eta, {"s": s})["terms"]["s"]
        assert abs(r["b"] - b_true) < 4 * r["se"], (b_true, r)
        assert 0.5 < r["se"] / r["se_model"] < 2.0


def test_walk_forward_reads_only_earlier_seasons():
    from src.eda.pair_strength import deploy as D
    F = C.add_modulators(synthetic_frame(30_000, seed=3))
    F["level"] = "T250"
    rng = np.random.default_rng(4)
    eta = F["z_market"].to_numpy(float)
    F["a_won"] = rng.random(len(F)) < expit(0.9 * eta)
    p1, _ = D.walk_forward(F, eta, "lin")
    G = F.copy()
    late = G["season"].to_numpy() >= 2020
    G.loc[late, "a_won"] = ~G.loc[late, "a_won"].astype(bool)   # reverse every result from 2020 on
    p2, _ = D.walk_forward(G, eta, "lin")
    early = F["season"].to_numpy() <= 2020                      # 2020 is fitted on 2014-2019 only
    assert np.allclose(p1[early], p2[early], equal_nan=True)
    assert not np.allclose(p1[~early], p2[~early])


TEST_FILES = [C.ROOT / "data/studies/surface_rating_race/model/model_frame.parquet",
              C.ROOT / "data/studies/surface_elo_pieces/pieces.parquet"]


@pytest.mark.skipif(not all(p.exists() for p in TEST_FILES), reason="data not on disk")
def test_final_primary_on_synthetic_outcomes():
    """The primary's machinery on the real test population and forecasts with SYNTHETIC outcomes: unbiased for a
    planted b, and about 5% one-sided rejections without one. No 2025-2026 result is read."""
    warnings.simplefilter("ignore")
    from src.eda.pair_strength import final_test as FT
    f = FT.population(with_results=False)
    assert "a_won" not in f.columns
    K = FT.constants()
    z = f["match_id"].map(FT.eta("model", FT.SEEDS_ALL, FT.TEST)).to_numpy(float)
    s = FT.standardise(f, K)
    assert np.isfinite(z).all() and np.isfinite(s).all()
    rng = np.random.default_rng(20261007)
    a = np.where(f["tour"] == "atp", 0.9, 0.9)
    rejections, bs = 0, []
    for _ in range(150):
        f["a_won"] = rng.random(len(f)) < expit(a * z)
        r = FT.coef(f, z, s)
        rejections += r["p_one_sided_expected"] < 0.05
    assert rejections / 150 < 0.12                     # nominal 5%; 150 draws
    for _ in range(60):
        f["a_won"] = rng.random(len(f)) < expit(a * z - 0.06 * s * z)
        bs.append(FT.coef(f, z, s)["b"])
    assert abs(np.mean(bs) + 0.06) < 0.015
