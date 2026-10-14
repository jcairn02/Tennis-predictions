"""Tests of the event-levels study (src/eda/event_levels/).

Run: ./python.sh -m pytest test/event_levels -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.event_levels import common as C  # noqa: E402

# a synthetic frame: seasons 2010-2024 x the model's five levels, shuffled (order must not matter)
_rng = np.random.default_rng(0)
_n = 15 * 2500
SEASONS = _rng.permutation(np.repeat(np.arange(2010, 2025), 2500))
LEVELS = _rng.choice([0, 1, 2, 3, 4], size=_n, p=[0.2, 0.01, 0.23, 0.16, 0.4])
POPS = _rng.choice(["MT", "CH"], size=_n)


@pytest.mark.parametrize("arm", C.ARMS_A + ("exp",))
@pytest.mark.parametrize("season", C.SEASONS_A)
def test_no_a_arm_trains_on_the_season_or_later_or_before_the_floor(arm, season):
    for seed in C.SEEDS_A:
        m = C.train_mask_a(SEASONS, LEVELS, arm, season, seed)
        assert m.any()
        assert SEASONS[m].max() <= season - 1 and SEASONS[m].min() >= C.TRAIN_FROM


@pytest.mark.parametrize("level", C.TARGETS)
def test_own_and_drop_split_the_pool(level):
    code = C.LEVEL_CODES[level]
    for season in C.SEASONS_A:
        pool = C.train_mask_a(SEASONS, LEVELS, "exp", season, 0)
        own = C.train_mask_a(SEASONS, LEVELS, f"own_{level}", season, 0)
        drop = C.train_mask_a(SEASONS, LEVELS, f"drop_{level}", season, 0)
        assert np.array_equal(own | drop, pool) and not (own & drop).any()
        assert (LEVELS[own] == code).all() and (LEVELS[drop] != code).all()


@pytest.mark.parametrize("level", C.TARGETS)
@pytest.mark.parametrize("kind", ("w25", "w50"))
def test_weighted_arms_keep_every_own_row_and_thin_the_others(level, kind):
    code = C.LEVEL_CODES[level]
    season = 2024
    pool = C.train_mask_a(SEASONS, LEVELS, "exp", season, 0)
    own = C.train_mask_a(SEASONS, LEVELS, f"own_{level}", season, 0)
    draws = [C.train_mask_a(SEASONS, LEVELS, f"{kind}_{level}", season, k) for k in C.SEEDS_A]
    for m in draws:
        assert not (m & ~pool).any() and np.array_equal(m & own, own)
        others = pool & (LEVELS != code)
        share = (m & others).sum() / others.sum()
        assert abs(share - C.KEEP_P[kind]) < 0.03
    assert not np.array_equal(draws[0], draws[1])                                      # a new draw per seed
    assert np.array_equal(draws[0], C.train_mask_a(SEASONS, LEVELS, f"{kind}_{level}", season, 0))   # reproducible


@pytest.mark.parametrize("level", C.TARGETS)
def test_size_control_has_own_size_and_draws_from_every_level(level):
    for season in (2019, 2024):
        own = C.train_mask_a(SEASONS, LEVELS, f"own_{level}", season, 0)
        pool = C.train_mask_a(SEASONS, LEVELS, "exp", season, 0)
        for k in C.SEEDS_A:
            m = C.train_mask_a(SEASONS, LEVELS, f"size_{level}", season, k)
            assert m.sum() == own.sum() and not (m & ~pool).any()
            assert len(np.unique(LEVELS[m])) >= 4


def test_unknown_arms_are_refused():
    with pytest.raises(KeyError):
        C.train_mask_a(SEASONS, LEVELS, "own_FIN", 2024, 0)
    with pytest.raises(KeyError):
        C.train_mask_b(SEASONS, POPS, "nall", 2024)


@pytest.mark.parametrize("arm", C.ARMS_B)
@pytest.mark.parametrize("season", C.SEASONS_B)
def test_b_arms_train_on_their_populations_before_the_season(arm, season):
    m = C.train_mask_b(SEASONS, POPS, arm, season)
    assert SEASONS[m].max() <= season - 1 and SEASONS[m].min() >= C.TRAIN_FROM
    assert set(POPS[m]) == set(C.POP_B[arm])
    q = C.query_mask_b(SEASONS, POPS, season)
    assert (SEASONS[q] == season).all() and not (m & q).any()


def test_rank_bands():
    b = C.band_of(np.array([1, 10, 11, 100, 101, 1000, 1001, 5000, np.nan]))
    assert list(b) == ["1-10", "1-10", "11-20", "51-100", "101-150", "501-1000", "1001+", "1001+", "unranked"]


def test_odds_flag():
    assert C.has_odds_b("omtch") and not any(C.has_odds_b(a) for a in ("nmt", "nch", "nmtch"))


def _players(rows):
    """A Stage 0-like player table: (match_id, order, date, level, player, won, has_box) per row; each match's other
    side is a one-off opponent."""
    import pandas as pd
    out = []
    for mid, order, date, level, player, won, box in rows:
        for side, pid, w in (("A", player, won), ("B", f"opp{mid}", not won)):
            out.append({"match_id": mid, "side": side, "tour": "atp", "player_id": pid, "order": order,
                        "date": pd.Timestamp(date), "year": pd.Timestamp(date).year, "map_level": level,
                        "tier": C.TIER_OF[level], "has_box": box, "won": w, "status": "completed", "rank": 100.0})
    return pd.DataFrame(out)


def test_history_counts_the_previous_year_by_tier_and_earlier_rounds():
    from src.eda.event_levels import blend as BL
    p = _players([("m1", 1, "2014-01-06", "ITF", "X", True, False),
                  ("m2", 2, "2014-03-03", "CH", "X", False, True),
                  ("m3", 3, "2014-06-02", "T250", "X", True, True),
                  ("m4", 4, "2015-06-01", "T250", "X", True, True),     # 2014-06-02 is inside 365 days
                  ("m5", 5, "2015-06-01", "T250", "X", False, True)])   # a later round of the same event
    h = BL.history(None, p).set_index(["match_id", "side"])
    r = h.loc[("m3", "A")]
    assert (r["n_ITF"], r["n_CH"], r["n_MT"], r["n_CH_box"], r["n_ITF_box"], r["n_ITF_won"]) == (1, 1, 0, 1, 0, 1)
    assert r["low_share"] == 1.0 and r["home"] == "CH"                     # a tie in counts goes to the higher tier
    r = h.loc[("m4", "A")]
    assert (r["n_ITF"], r["n_CH"], r["n_MT"]) == (0, 0, 1) and r["low_share"] == 0.0
    r = h.loc[("m5", "A")]
    assert r["n_MT"] == 2 and r["n_won"] == 2 and r["win_share"] == 1.0
    assert np.isnan(h.loc[("m1", "A")]["low_share"]) if ("m1", "A") in h.index else True
    assert h.loc[("m2", "A")]["n_ITF"] == 1 and h.loc[("m2", "B")]["n_all"] == 0
