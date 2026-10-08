"""Tests for the stage scripts of the study "rating systems against Elo" (src/eda/rating_systems/stage*.py).

    * Stage A: the grid widening (geometric; the correlation widened in 1 - rho so it never reaches 1; natural bounds
      never crossed), the grid read-back keys the settings as the grid run keys them;
    * Stage B: the comparison block (log losses, Elo minus each forecaster, the share of the Elo-to-market gap closed,
      the coin-to-market share) on a hand-made example;
    * Stage C: every ladder model's references exist, each base has the six steps, and the two-rating models refer to
      both of their single-rating models.

Run: ./python.sh -m pytest test/rating_systems/test_stages.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.rating_systems import stageA_ratings as A  # noqa: E402
from src.eda.rating_systems import stageB_compare as SB  # noqa: E402
from src.eda.rating_systems import stageC_orthogonality as SC  # noqa: E402


def grid_rows(system: str, values: dict, best: dict) -> pd.DataFrame:
    """Every combination of ``values`` with a log loss lowest at ``best``."""
    rows = []
    for combo in pd.MultiIndex.from_product(list(values.values())):
        cfg = dict(zip(values.keys(), combo))
        dist = sum((math.log(cfg[p]) - math.log(best[p])) ** 2 if cfg[p] > 0 and best[p] > 0 else abs(cfg[p] - best[p])
                   for p in values)
        rows.append({**cfg, "log_loss_2013_2018": 0.6 + dist})
    return pd.DataFrame(rows)


def test_widening_is_geometric_and_stops_at_natural_bounds():
    vals = {"sigma0": [1.5, 2.0, 2.5], "tau": [0.0, 0.01, 0.02], "gamma": [0.3, 0.4, 0.5]}
    g = grid_rows("trueskill", vals, {"sigma0": 2.5, "tau": 0.0, "gamma": 0.3})
    add = A.widen("trueskill", "atp", g, vals)
    assert add["sigma0"] == pytest.approx(2.5 * 2.5 / 2.0)             # past the upper edge, the edge's ratio
    assert add["gamma"] == pytest.approx(0.3 * 0.3 / 0.4)              # past the lower edge
    assert "tau" not in add                                            # tau 0 is a natural bound


def test_the_correlation_is_widened_in_one_minus_rho_and_never_reaches_one():
    vals = {"rd0": [500.0, 600.0], "sigma0": [0.06, 0.07], "rho": [0.97, 0.98, 0.99, 0.995]}
    g = grid_rows("glicko_cs", vals, {"rd0": 500.0, "sigma0": 0.07, "rho": 0.995})
    add = A.widen("glicko_cs", "atp", g, vals)
    assert add["rho"] == pytest.approx(1 - 0.005 ** 2 / 0.01) and add["rho"] < 1.0
    g = grid_rows("glicko_cs", vals, {"rd0": 600.0, "sigma0": 0.06, "rho": 0.97})
    assert A.widen("glicko_cs", "atp", g, vals)["rho"] == pytest.approx(1 - 0.03 ** 2 / 0.02)


def test_grid_read_back_keys_settings_as_the_grid_run_does(tmp_path, monkeypatch):
    t = pd.DataFrame([{"system": "glicko_cs", "tour": "atp", "round": "grid", "rd0": 600.0, "sigma0": 0.07, "rho": 0.985,
                       "log_loss_2013_2018": 0.58625, "matches": 64208, "seconds": 5.0},
                      {"system": "ttt", "tour": "wta", "round": "widened 1", "sigma0": 2.0, "gamma": 0.4, "window": 52.0,
                       "log_loss_2013_2018": 0.598, "matches": 25676, "seconds": 60.0}])
    path = tmp_path / "stageA_tuning.csv"
    t.to_csv(path, index=False)
    monkeypatch.setattr(A, "TUNING", path)
    got = A.read_grid()
    assert ("atp",) + A.cfg_key("glicko_cs", {"rd0": 600.0, "sigma0": 0.07, "rho": 0.985}) in got
    assert ("wta",) + A.cfg_key("ttt", {"sigma0": 2.0, "gamma": 0.4, "window": 52.0}) in got
    assert got[("wta",) + A.cfg_key("ttt", {"sigma0": 2.0, "gamma": 0.4, "window": 52.0})]["round"] == "widened 1"


def test_compare_block_reads_gaps_and_shares_as_defined():
    """Elo, a system and the market on six matches: the block's log losses, Elo minus the system, the share of the
    Elo-to-market gap the system closes and its distance from a coin to the market."""
    y = np.array([1, 0, 1, 1, 0, 1], dtype=bool)
    P = {"elo": np.array([0.6, 0.4, 0.55, 0.7, 0.45, 0.5]), "sys": np.array([0.65, 0.35, 0.6, 0.72, 0.4, 0.55]),
         "market": np.array([0.7, 0.3, 0.62, 0.75, 0.35, 0.6])}
    L = {k: SB.ll_rows(v, y) for k, v in P.items()}
    weeks = np.array(["w1", "w1", "w2", "w2", "w3", "w3"])
    out = SB.compare(L, ["elo", "sys", "market"], np.ones(6, dtype=bool), weeks, True)
    ll = {k: float(np.mean(L[k])) for k in P}
    assert out["ll"] == pytest.approx(ll)
    assert out["elo_minus"]["sys"]["milli"] == pytest.approx(1000 * (ll["elo"] - ll["sys"]))
    assert out["gap_closed"]["sys"] == pytest.approx((ll["elo"] - ll["sys"]) / (ll["elo"] - ll["market"]))
    assert out["coin_to_market"]["sys"] == pytest.approx((math.log(2) - ll["sys"]) / (math.log(2) - ll["market"]))
    assert out["elo_minus"]["sys"]["weeks"] == 3


def test_every_ladder_reference_is_a_model_or_a_raw_forecast():
    specs, refs = SC.ladder_specs()
    known = set(specs) | {"elo_raw", "market_raw"}
    for name, rr in refs.items():
        assert set(rr) <= known, name
    for base in SC.BASES:
        steps = [n for n in specs if n.startswith(f"{base}_")]
        assert len(steps) == len(SC.STEPS), base
        assert specs[f"{base}_full"][0] == SC.BASES[base]
    for base in SC.BASES:
        if base == "elo":
            continue
        assert set(refs[f"elo+{base}_full"]) >= {"elo_full", f"{base}_full"}
        assert specs[f"elo+{base}_full"][:2] == ["elo_logit", SC.BASES[base]]
