"""The coverage alarm (src/eda/data_gaps_2026/coverage.py) on toy tables: a level that stops, a level lost for over a
year, a Slam that changes month, a box-score hole, and the unpriced-leads gate's own measure.
Run: ./python.sh -m pytest test/data_gaps_2026 -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.data_gaps_2026 import coverage as CV  # noqa: E402


def table(spec) -> pd.DataFrame:
    """spec: (tour, level, first Monday, last Monday, matches a week, share with a box score)."""
    rows = []
    for tour, level, a, b, n, share in spec:
        for i, d in enumerate(pd.date_range(a, b, freq="7D")):
            for k in range(n):
                rows.append({"match_id": f"{tour}{level}{i}_{k}", "tour": tour, "map_level": level,
                             "tournament_date": d, "has_box": k < round(n * share)})
    return pd.DataFrame(rows)


def run(m, as_of="2026-10-13", start="2026-01"):
    as_of = pd.Timestamp(as_of)
    c = CV.cells(m)
    return CV.monthly(c, as_of, pd.Period(start, "M")), CV.recent(m, as_of)


def test_a_level_that_stops_is_flagged_in_the_last_weeks_and_months():
    m = table([("wta", "ITF", "2024-01-01", "2026-05-25", 40, 1.0), ("wta", "CH", "2024-01-01", "2026-10-05", 10, 1.0)])
    mon, rec = run(m)
    r = rec.set_index(["level", "measure"])
    assert bool(r.loc[("ITF", "matches"), "flag"]) and r.loc[("ITF", "matches"), "now"] == 0
    assert not bool(r.loc[("CH", "matches"), "flag"])
    f = mon[mon["flag"] & mon["measure"].eq("matches")]
    assert {"2026-07", "2026-08"} <= set(f.loc[f["level"].eq("ITF"), "month"])
    assert not f["level"].eq("CH").any()


def test_a_level_lost_for_over_a_year_still_shows_against_two_years_earlier():
    m = table([("wta", "ITFQ", "2023-01-02", "2024-12-16", 30, 0.0), ("wta", "CH", "2023-01-02", "2026-10-05", 10, 1.0)])
    mon, rec = run(m)
    r = rec.set_index(["level", "measure"])
    assert bool(r.loc[("ITFQ", "matches"), "flag"])                              # 2026 against 2024
    one = CV.recent(m, pd.Timestamp("2026-10-13"), years=(1,)).set_index(["level", "measure"])
    assert not bool(one.loc[("ITFQ", "matches"), "flag"])                        # the year before alone: 0 against 0


def test_a_slam_that_changes_month_moves_no_count_flag_but_a_box_hole_does():
    m = pd.concat([table([("atp", "GS", "2025-06-30", "2025-06-30", 127, 1.0)]).assign(match_id=lambda f: "a" + f["match_id"]),
                   table([("atp", "GS", "2026-07-06", "2026-07-06", 127, 0.0)]).assign(match_id=lambda f: "b" + f["match_id"]),
                   table([("atp", "GS", "2024-07-01", "2024-07-01", 127, 1.0)]).assign(match_id=lambda f: "c" + f["match_id"])],
                  ignore_index=True)
    mon, _ = run(m, start="2026-05")
    g = mon[mon["level"].eq("GS")]
    assert not g.loc[g["measure"].isin(["matches", "box"]), "flag"].any()       # a Slam's count is not judged
    assert g.loc[g["measure"].eq("box_share"), "flag"].any()                    # 127 matches, no box score


def test_the_gate_measure_is_the_one_year_baseline():
    m = table([("atp", "ITF", "2025-01-06", "2026-06-01", 50, 1.0), ("atp", "CH", "2025-01-06", "2026-10-05", 50, 1.0)])
    c = CV.cells(m)
    mon = CV.monthly(c, pd.Timestamp("2026-10-13"), pd.Period("2026-07", "M"), years=(1,))
    row = mon[(mon["level"] == "ALL") & (mon["month"] == "2026-07") & (mon["measure"] == "box")].iloc[0]
    # June-August 2026: 14 Challenger Mondays and ITF's last week (1 June), against 13 + 13 Mondays of 2025
    assert row["now"] == 50 * 15 and row["year_before"] == 50 * 26
    assert abs(row["ratio"] - row["now"] / row["year_before"]) < 1e-12


def test_an_acknowledged_hole_is_quiet_only_in_its_months():
    """The ITF box-score hole of June-September 2026 is acknowledged month by month: the same cell in a later month,
    and the recent window, still raise the alarm."""
    as_of = pd.Timestamp("2026-10-13")
    assert CV.known("wta", "ITF", "box", as_of, "2026-07")
    assert CV.known("atp", "ALL", "box_share", as_of, "2026-08")
    assert CV.known("wta", "ITF", "box", as_of, "2026-11") is None
    assert CV.known("wta", "ITF", "box", as_of, None) is None                     # the recent window
    assert CV.known("wta", "ITF", "matches", as_of, "2026-07") is None            # counts are not acknowledged
    assert CV.known("wta", "ITF", "box", pd.Timestamp("2027-02-01"), "2026-07") is None
    assert CV.known("wta", "GSQ", "box", as_of, None)                             # whole-cell acknowledgements stay


def test_each_measure_takes_its_own_baseline():
    """ITF had box scores only from 2025: a 2026 without them is flagged even when 2024 (no box scores, more matches)
    is the larger baseline of matches."""
    m = pd.concat([table([("wta", "ITF", "2024-01-01", "2024-12-30", 60, 0.0)]).assign(match_id=lambda f: "a" + f["match_id"]),
                   table([("wta", "ITF", "2025-01-06", "2025-12-29", 40, 1.0)]).assign(match_id=lambda f: "b" + f["match_id"]),
                   table([("wta", "ITF", "2026-01-05", "2026-10-05", 40, 0.0)]).assign(match_id=lambda f: "c" + f["match_id"])],
                  ignore_index=True)
    mon, _ = run(m, start="2026-06")
    g = mon[(mon["level"] == "ITF") & (mon["month"] == "2026-07")].set_index("measure")
    assert not bool(g.loc["matches", "flag"])     # 14 Mondays x 40 against 13 x 60 two years before: 560 / 780 = 0.72
    assert bool(g.loc["box", "flag"]) and g.loc["box", "year_before"] > 0
    assert bool(g.loc["box_share", "flag"]) and g.loc["box_share", "year_before"] == 1.0
