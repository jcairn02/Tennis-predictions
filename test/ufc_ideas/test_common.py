"""The corrected harness preserves earlier unpenalized point estimates for the same features,
replaces iid intervals/evidence labels, and accepts any baseline column.

Needs the earlier study's tables on disk (stage4_features.parquet, stage4_ranking.csv); skipped otherwise.
Run: ./python.sh -m pytest test/ufc_ideas/test_common.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.ufc_ideas import common as U  # noqa: E402

pytestmark = pytest.mark.skipif(not (U.STAGE4_FEATURES.exists() and U.STAGE4_RANKING.exists()),
                                reason="the earlier study's Stage 4 tables are not on disk")


@pytest.fixture(scope="module")
def check_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("harness")
    pool = U.load_pool(["rating_matchup|single", "elo_games|single"])
    frame = tmp / "frame.parquet"
    pool.to_parquet(frame)
    tasks = [U.task("atp", "rating_matchup", "single", "ratings through the iid model", "check", ["rating_matchup|single"]),
             U.task("atp", "elo_games", "single", "games-weighted Elo", "check", ["elo_games|single"]),
             U.task("wta", "rating_matchup", "single", "ratings through the iid model", "check", ["rating_matchup|single"],
                    wta_box_from_2019=True),
             U.task("wta", "elo_games", "single", "games-weighted Elo", "check", ["elo_games|single"])]
    res = U.rundown(frame, tasks, tmp / "check", workers=2)
    return res["ranking"].set_index(["tour", "id"])


def test_reproduces_stage4_scores(check_run):
    ref = U.stage4_reference(["rating_matchup", "elo_games"]).set_index(["tour", "id"])
    for key in check_run.index:
        for col in ("alone_imp", "elo_imp", "market_imp"):
            got, exp = check_run.loc[key, col], ref.loc[key, col]
            if isinstance(exp, (bool, np.bool_)):
                assert bool(got) == bool(exp), (key, col)
            else:
                assert abs(float(got) - float(exp)) < 1e-6, (key, col, got, exp)
        assert check_run.loc[key, "elo_ci_method"] == "paired_four_week_cluster_t"
        assert check_run.loc[key, "elo_week_clusters"] >= check_run.loc[key, "elo_block4week_clusters"] > 1


def test_any_base_column(tmp_path):
    """A feature scored against its own probability as the base adds nothing (the base already holds it)."""
    pool = U.load_pool(["rating_matchup|single"])
    pool["p_self"] = 1 / (1 + np.exp(-pool["rating_matchup|single"].to_numpy(dtype="float64")))
    frame = tmp_path / "frame.parquet"
    pool.to_parquet(frame)
    t = U.task("atp", "rating_matchup", "single", "ratings", "check", ["rating_matchup|single"],
               scores=("self",), bases={"self": "p_self"})
    res = U.rundown(frame, [t], tmp_path / "self", workers=1, reading_base="self")
    row = res["ranking"].iloc[0]
    assert abs(float(row["self_imp"])) < 1e-6
    assert row["reading"] in ("no sign", "worse", "possible")


def test_score_plain_matches_rundown(check_run):
    pool = U.load_pool(["elo_games|single"])
    t = U.task("atp", "elo_games", "single", "games-weighted Elo", "check", ["elo_games|single"])
    plain = U.score_plain(pool, t)
    assert abs(plain["elo"]["imp"] - float(check_run.loc[("atp", "elo_games"), "elo_imp"])) < 1e-9
    for metric in ("lo", "hi", "week_lo", "week_hi", "raw_baseline_imp", "raw_baseline_lo", "raw_baseline_hi"):
        assert plain["elo"][metric] == pytest.approx(check_run.loc[("atp", "elo_games"), f"elo_{metric}"])
