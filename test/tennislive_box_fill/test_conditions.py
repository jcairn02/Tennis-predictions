"""The gap-fill policy's two conditions (src/eda/tennislive_box_fill/conditions.py) on toy box layers."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.tennislive_box_fill import conditions as K  # noqa: E402


def _layers(n_shared: int, n_differ: int, completions: int) -> pd.DataFrame:
    """Men's Challenger box layers: n_shared matches the history already scores (n_differ of them with one count off,
    and every one without service games in the source), then `completions` applied completions."""
    rows = []
    for i in range(n_shared + completions):
        shared = i < n_shared
        r = {"match_id": f"m{i}", "tour": "atp", "bucket": "CH", "year": 2019, "stage0_has_box": shared,
             "kind": "revision" if shared else "completion", "applied": not shared, "passes_checks": True}
        for s in "AB":
            for c in C.BOX:
                r[f"old_{s}_{c}"] = 10.0 if shared else np.nan
                r[f"new_{s}_{c}"] = np.nan if c == "sv_gms" else 10.0
        if shared and i < n_differ:
            r["new_A_svpt"] = 11.0
        rows.append(r)
    return pd.DataFrame(rows)


def test_c1_compares_every_count_but_the_service_games_the_source_lacks():
    a, by = K.c1(_layers(100, 1, 0), "tennislive_pages")
    row = a.iloc[0]
    assert (row["shared"], row["all_equal"], row["share"]) == (100, 99, 0.99) and bool(row["pass"])
    assert "sv_gms" not in set(by["count"])
    a, _ = K.c1(_layers(100, 3, 0), "tennislive_pages")
    assert not bool(a.iloc[0]["pass"])                                    # 97% < 98%
    a, _ = K.c1(_layers(29, 0, 0), "tennislive_pages")
    assert not bool(a.iloc[0]["pass"])                                    # under 30 shared matches


def test_c1_reads_todays_tables_where_a_repair_replaced_the_frozen_counts():
    """The frozen copy carries an error a decided repair fixed (Roland Garros 2022-26): the source agrees with today's
    tables, so today's reading passes where the frozen one fails (14 Oct 2026, the owner: "Yes add and fix those")."""
    L = _layers(100, 5, 0)                                  # 5 matches whose frozen svpt differs from the source's
    counts = []
    for i in range(100):
        for s in "AB":
            counts.append({"match_id": f"m{i}", "side": s} | {c: 10.0 for c in C.BOX} | {"svpt": 11.0 if (
                s == "A" and i < 5) else 10.0})
    hist = {"boxed": {f"m{i}" for i in range(100)}, "counts": pd.DataFrame(counts).set_index(["match_id", "side"])}
    frozen, _ = K.c1(L, "tennislive_pages")
    today, _ = K.c1(L, "tennislive_pages", hist)
    assert not bool(frozen.iloc[0]["pass"]) and frozen.iloc[0]["share"] == 0.95
    assert bool(today.iloc[0]["pass"]) and today.iloc[0]["share"] == 1.0


def test_c2_needs_the_history_to_hold_half_the_cells_box_scores_before_the_fill():
    L = _layers(0, 0, 3)
    m = pd.DataFrame({"match_id": [f"h{i}" for i in range(4)] + ["m0", "m1", "m2"], "tour": "atp", "bucket": "CH",
                      "year": 2019, "status": "completed", "has_box": [True] * 4 + [False] * 3})
    out = K.c2(L, m).iloc[0]
    assert (out["completions"], out["completions_landing"], out["played"], out["with_box"]) == (3, 3, 7, 4)
    assert out["share_before"] == round(4 / 7, 4) and out["share_after"] == 1.0 and bool(out["pass"])
    m.loc[m["match_id"].eq("h0"), "has_box"] = False                      # 3 of 7 before: under half
    assert not bool(K.c2(L, m).iloc[0]["pass"])                           # and no other season to catch up with
    m.loc[m["match_id"].eq("m0"), "has_box"] = True                       # the tables already score one: it adds nothing
    assert K.c2(L, m).iloc[0]["completions_landing"] == 2


def _seasons(shares: dict, cell_year: int, cell_boxed: int, cell_played: int = 100) -> pd.DataFrame:
    """A level's matches by season: shares[year] of 100 played matches boxed; the cell's season with cell_boxed of
    cell_played, its unboxed ones named m0, m1, ... (the layers' completions)."""
    rows = []
    for y, s in shares.items():
        rows += [{"match_id": f"y{y}_{i}", "year": y, "has_box": i < round(100 * s)} for i in range(100)]
    rows += [{"match_id": f"c{i}", "year": cell_year, "has_box": True} for i in range(cell_boxed)]
    rows += [{"match_id": f"m{i}", "year": cell_year, "has_box": False} for i in range(cell_played - cell_boxed)]
    return pd.DataFrame(rows).assign(tour="atp", bucket="CH", status="completed")


def test_c2_lets_a_season_with_a_hole_catch_up_with_its_level():
    """Men's Slam qualifying 2018: 49% boxed against about 100% in other seasons; the fill brings it closer, so it passes
    though under half before. A level empty in most seasons (ITF before 2025) has a median near 0: a fill fails."""
    L = _layers(0, 0, 45)
    L["year"] = 2018
    m = _seasons({2013: 0.75, 2016: 0.0, 2019: 1.0, 2020: 1.0, 2021: 1.0, 2022: 1.0}, 2018, 49)
    out = K.c2(L, m).iloc[0]
    assert out["share_before"] == 0.49 and out["share_after"] == 0.94 and out["level_median_other_seasons"] == 1.0
    assert not bool(out["pass_half"]) and bool(out["pass_toward_level"]) and bool(out["pass"])
    m = _seasons({2013: 0.0, 2016: 0.0, 2019: 0.0, 2020: 0.0, 2025: 0.95}, 2018, 0)
    L2 = _layers(0, 0, 45)
    L2["year"] = 2018
    out = K.c2(L2, m).iloc[0]
    assert out["level_median_other_seasons"] == 0.0 and not bool(out["pass"])
