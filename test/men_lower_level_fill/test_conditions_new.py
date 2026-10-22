"""The coverage condition for added matches and the near-pair listing (src/eda/men_lower_level_fill/conditions_new.py)
on toy tables."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.men_lower_level_fill import conditions_new as K  # noqa: E402


def _cells(rows: list[tuple]) -> pd.Series:
    idx = pd.MultiIndex.from_tuples([r[:3] for r in rows], names=["tour", "level", "season"])
    return pd.Series([r[3] for r in rows], index=idx)


def test_a_cell_passes_when_it_holds_at_least_as_many_as_it_gains():
    held = _cells([("atp", "ITF", y, 5000) for y in range(2013, 2020)])
    res = K.c2_cells(held, _cells([("atp", "ITF", 2016, 400)]))
    row = res.iloc[0]
    assert len(res) == 1 and bool(row["holds_at_least_as_many"]) and bool(row["pass"])


def test_a_season_with_a_hole_passes_by_moving_toward_its_neighbours():
    held = _cells([("atp", "CHQ", y, 3000) for y in range(2013, 2020) if y != 2018] + [("atp", "CHQ", 2018, 100)])
    row = K.c2_cells(held, _cells([("atp", "CHQ", 2018, 900)])).iloc[0]
    assert not bool(row["holds_at_least_as_many"]) and bool(row["closer_to_median"]) and bool(row["pass"])
    assert row["median_other_seasons"] == 3000


def test_a_level_empty_in_its_other_seasons_fails():
    # the other seasons hold under 30 played matches each: no median, so only the first branch can pass
    held = _cells([("atp", "ITFQ", y, 5) for y in range(2013, 2020)])
    row = K.c2_cells(held, _cells([("atp", "ITFQ", 2016, 50)])).iloc[0]
    assert np.isnan(row["median_other_seasons"]) and not bool(row["pass"])


def test_a_gain_that_overshoots_the_median_fails_when_it_lands_further_away():
    held = _cells([("atp", "CH", y, 1000) for y in range(2013, 2020) if y != 2015] + [("atp", "CH", 2015, 900)])
    row = K.c2_cells(held, _cells([("atp", "CH", 2015, 1500)])).iloc[0]
    assert not bool(row["pass"])           # 2,400 is further from 1,000 than 900 is, and 900 < 1,500


def _tables(rows: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = pd.DataFrame([{"match_id": r["id"], "tour": "atp", "map_level": r.get("level", "ITF"),
                       "tournament_id": r.get("tid", "t1"), "tournament_name": "Futures",
                       "tournament_date": pd.Timestamp(r["date"]), "round": r.get("round", "R32"), "score": "6-4 6-4",
                       "status": "completed", "player_a_id": r["a"], "player_b_id": r["b"]} for r in rows])
    mp = pd.DataFrame([{"match_id": r["id"], "side": s, "player_name": r[f"name_{s.lower()}"]}
                       for r in rows for s in "AB"])
    return m, mp


def test_near_pairs_finds_the_same_two_players_at_another_round_or_day_and_by_names():
    held_m, held_mp = _tables([
        {"id": "h1", "a": "p1", "b": "p2", "date": "2019-05-06", "round": "R16", "name_a": "Ann Lee", "name_b": "Bo Kim"},
        {"id": "h2", "a": "p3", "b": "p4", "date": "2019-05-06", "name_a": "Cy Ito", "name_b": "Di Roe"},
        {"id": "h3", "a": "x9", "b": "x8", "date": "2019-05-13", "name_a": "Ed Fox", "name_b": "Fa Gil"},
    ])
    add_m, add_mp = _tables([
        # the same ids, eight days later and another round: listed by ids
        {"id": "a1", "a": "p2", "b": "p1", "date": "2019-05-14", "round": "Q1", "name_a": "Bo Kim", "name_b": "Ann Lee"},
        # p3 v p4 again, 20 days later: not listed
        {"id": "a2", "a": "p3", "b": "p4", "date": "2019-05-26", "name_a": "Cy Ito", "name_b": "Di Roe"},
        # other ids, the same names: listed by names
        {"id": "a3", "a": "n1", "b": "n2", "date": "2019-05-13", "name_a": "Ed Fox", "name_b": "Fa Gil"},
    ])
    out = K.near_pairs(add_m, add_mp, held_m, held_mp)
    got = dict(zip(out["added_match_id"], out["held_match_id"]))
    assert got == {"a1": "h1", "a3": "h3"}
    assert set(out.loc[out["added_match_id"].eq("a1"), "paired_by"]) == {"ids+names"}
    assert set(out.loc[out["added_match_id"].eq("a3"), "paired_by"]) == {"names"}
