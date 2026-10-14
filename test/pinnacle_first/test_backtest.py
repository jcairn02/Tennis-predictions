"""Tests of the Pinnacle-first backtest (src/eda/pinnacle_first/backtest.py): synthetic only.

The sealed holdout's results are never read; a bet's return follows the owner's staking; the top-half rule's threshold
for a season comes from earlier seasons only.

Run: ./python.sh -m pytest test/pinnacle_first -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.pinnacle_first import backtest as B  # noqa: E402


class FakePaths:
    def __init__(self, path: Path):
        self.model_frame = path


def test_results_from_the_sealed_holdout_are_never_read(tmp_path):
    f = pd.DataFrame({"match_id": ["a", "b", "c"], "a_won": [1, 0, 1],
                      "tournament_date": pd.to_datetime(["2026-07-20", "2026-07-28", "2026-07-29"])})
    f.to_parquet(tmp_path / "f.parquet", index=False)
    y = B.outcomes(FakePaths(tmp_path / "f.parquet"))
    assert y.index.tolist() == ["a", "b"] and y.tolist() == [1.0, 0.0]


def frame(rows: list[dict]) -> pd.DataFrame:
    g = pd.DataFrame(rows)
    g["block"] = np.arange(len(g))
    return g


def test_a_bet_returns_what_the_owners_staking_says():
    # A at 2.00 with q 0.6 (edge 20%): to win 1 unit, stake 1; A at 1.50 with q 0.8 (edge 20%): stake 2, wins 1
    g = frame([{"q_new": 0.6, "q_new_stage1": 0.5, "q_old": 0.5, "q_control": 0.5, "pin_a": 2.0, "pin_b": 2.0,
                "y": 1.0},
               {"q_new": 0.8, "q_new_stage1": 0.5, "q_old": 0.5, "q_control": 0.5, "pin_a": 1.5, "pin_b": 2.9,
                "y": 0.0}])
    rows = {r["forecast"]: r for r in B.cell(g, "pin_a", "pin_b", {k: 0.0 for k in B.FORECASTS}, {"t": 1})}
    new = rows["new"]
    assert new["bets"] == 2 and new["staked"] == pytest.approx(3.0) and new["profit"] == pytest.approx(1.0 - 2.0)
    assert new["roi"] == pytest.approx(-1.0 / 3.0)
    assert rows["old"]["bets"] == 1          # q 0.5 at 2.9 on B is worth backing (edge 45%); at 2.0/2.0 it is not


def test_the_top_half_threshold_comes_from_earlier_seasons_only():
    rng = np.random.default_rng(0)
    rows = []
    for season in (2021, 2022):
        for _ in range(600):
            q = rng.uniform(0.3, 0.7)
            rows.append({"season": season, "tour": "atp", "status": "completed", "y": float(rng.random() < q),
                         "q_new": q, "q_new_stage1": q, "q_old": q, "q_control": q, "pin_a": 2.0, "pin_b": 2.0,
                         "bol_a": np.nan, "bol_b": np.nan, "tournament_date": pd.Timestamp(f"{season}-05-01")})
    info = frame(rows)
    info.loc[info["season"] == 2022, "q_new"] = 0.99          # 2022's own edges must not set 2022's threshold
    old = B.SEASONS
    B.SEASONS = (2021, 2022)
    try:
        out = pd.DataFrame(B.roi_rows(info))
    finally:
        B.SEASONS = old
    top = out[(out["rule"] == "top 50% by edge") & (out["season"] == "2022") & (out["forecast"] == "new")].iloc[0]
    expected = B.median_edge(info[info["season"] == 2021], "new", "pin_a", "pin_b")
    assert top["threshold"] == pytest.approx(expected) and expected < 0.5
