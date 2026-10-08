"""Tests of the leak-proof timeline's rules (src/eda/match_timing/timing.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import timing as TM  # noqa: E402


NO_CALIBRATION = pd.DataFrame({"cal_class": [], "before": [], "after": []})


def _links(rows):
    f = pd.DataFrame(rows, columns=["match_id", "source", "date_local", "date_basis", "link_method"])
    f["source_key"], f["start_utc"], f["score_agrees"], f["round_agrees"] = f["match_id"], pd.NaT, True, True
    f["day"] = pd.to_datetime(f["date_local"]).to_numpy().astype("datetime64[D]").astype("float64")
    return f


def test_each_source_is_widened_by_its_own_measured_clock_error():
    # 300 matches dated by a point log (TDI) and by a source that dates 2% of them a day after their first point and
    # 0.5% two days after: that class is widened two days before, and a class never compared takes the default
    start = pd.Timestamp("2024-03-04")
    rows, n = [], 300
    for i in range(n):
        d = start + pd.Timedelta(days=i % 5)
        late = 2 if i < 2 else (1 if i < 8 else 0)
        rows.append((f"m{i}", "tdi", d.date().isoformat(), "local", "identity_pair;first_point"))
        rows.append((f"m{i}", "sofascore", (d + pd.Timedelta(days=late)).date().isoformat(), "local", "listed_start"))
    rows.append(("x", "infosys", "2024-03-06", "local", "x"))
    L = _links(rows)
    m = pd.DataFrame({"match_id": [f"m{i}" for i in range(n)] + ["x"], "tournament_date": start})
    out, LL = TM.exact_days(m, L)
    cal = LL.attrs["calibration"].set_index("cal_class")
    assert (cal.loc["sofascore:local", "before"], cal.loc["sofascore:local", "after"]) == (2, 0)
    assert cal.loc["sofascore:local", "share_inside_calibrated"] == 1.0
    assert "tdi:local" not in cal.index                       # point-log links are the reference: no slack
    x = LL[LL["match_id"].eq("x")].iloc[0]                    # infosys: never compared, default slack, then its own +-1
    assert (x["day"] - x["lo"], x["hi"] - x["day"]) == (1, 1)                         # the claim: the clock rule only
    assert (x["day"] - x["cal_lo"], x["cal_hi"] - x["day"]) == (1 + TM.DEFAULT_SLACK[0], 1 + TM.DEFAULT_SLACK[1])
    # m0: the point log says day 0, the source day 2. The claims disagree (their covering interval); the calibrated
    # intervals overlap on the log's day
    o = out.set_index("match_id")
    d0 = float(np.datetime64("2024-03-04", "D").astype("int64"))
    assert (o.loc["m0", "exact_lo"], o.loc["m0", "exact_hi"]) == (d0, d0 + 2) and bool(o.loc["m0", "conflict"])
    assert (o.loc["m0", "cal_lo"], o.loc["m0", "cal_hi"]) == (d0, d0)


def test_exact_days_agreement_utc_and_conflict():
    m = pd.DataFrame({"match_id": ["a", "b", "c", "d"], "tournament_date": pd.to_datetime(["2024-01-15"] * 4)})
    L = _links([
        ("a", "tennis_data", "2024-01-17", "local", "x"),        # one local day
        ("b", "flashscore", "2024-01-17", "utc_date", "x"),      # a UTC day: the local day may be either neighbour
        ("c", "tennis_data", "2024-01-17", "local", "x"),        # two sources a week apart: a wide conflict
        ("c", "flashscore", "2024-01-24", "utc_date", "x"),
        ("d", "tennis_data", "2023-11-01", "local", "x"),        # implausibly far from the event: rejected
        ("e", "tennis_data", "2024-01-17", "local", "x"),        # two sources two days apart: a conflict
        ("e", "flashscore", "2024-01-19", "local", "x"),
        ("f", "tennis_data", "2024-01-17", "local", "x"),        # three sources against one: the three stand
        ("f", "flashscore", "2024-01-17", "local", "x"),
        ("f", "sofascore", "2024-01-16", "utc_date", "x"),
        ("f", "open_tennis_data", "2024-01-27", "local", "x"),
        ("g", "match_charting", "2024-01-17", "local", "x"),     # a loose-clock source: a day either side
    ])
    m = pd.concat([m, pd.DataFrame({"match_id": ["e", "f", "g"],
                                    "tournament_date": pd.to_datetime(["2024-01-15"] * 3)})])
    out, _ = TM.exact_days(m, L, calibration=NO_CALIBRATION, default=(0, 0))      # the base rules, no slack
    out = out.set_index("match_id")
    d17 = float(np.datetime64("2024-01-17", "D").astype("int64"))
    assert (out.loc["a", "exact_lo"], out.loc["a", "exact_hi"]) == (d17, d17)
    assert (out.loc["b", "exact_lo"], out.loc["b", "exact_hi"]) == (d17 - 1, d17 + 1)
    # disagreement never picks a source: the interval covers every reading (the most trusted source can be the wrong one)
    assert bool(out.loc["c", "conflict"]) and bool(out.loc["c", "wide_conflict"])
    assert (out.loc["c", "exact_lo"], out.loc["c", "exact_hi"]) == (d17, d17 + 8)
    assert bool(out.loc["e", "conflict"]) and not bool(out.loc["e", "wide_conflict"])
    assert (out.loc["e", "exact_lo"], out.loc["e", "exact_hi"]) == (d17, d17 + 2)
    assert out.loc["c", "outvoted_source"] == "" and out.loc["e", "outvoted_source"] == ""   # one against one: no vote
    assert bool(out.loc["f", "conflict"]) and not bool(out.loc["f", "wide_conflict"])
    assert (out.loc["f", "exact_lo"], out.loc["f", "exact_hi"]) == (d17, d17)
    assert out.loc["f", "outvoted_source"] == "open_tennis_data"
    assert (out.loc["g", "exact_lo"], out.loc["g", "exact_hi"]) == (d17 - 1, d17 + 1)
    assert "d" not in out.index


def test_a_day_far_from_its_round_is_not_trusted_alone():
    # event 0: three quarter-finals on day 109 and one misdated to day 102; a lone semi-final.
    # event 1: two second-round matches a week apart: which is right is unknown, so neither is trusted alone
    m = pd.DataFrame({"ev": [0, 0, 0, 0, 0, 1, 1], "round": ["QF"] * 4 + ["SF", "R32", "R32"], "exact": True,
                      "exact_lo": [109.0, 109.0, 109.0, 102.0, 110.0, 50.0, 57.0]})
    m["exact_hi"] = m["exact_lo"]
    got = TM.sibling_outliers(m)
    assert got.tolist() == [False, False, False, True, False, True, True]


def test_a_contradicted_draw_is_widened_never_inverted():
    # one player's run: R16 dated day 18, QF misdated day 12 (truly 19), SF dated day 20. Narrowing these as given would
    # invert the QF's window and let its result into its own ratings; the event takes union windows instead
    m = pd.DataFrame({"match_id": ["r16", "qf", "sf"], "ev": [0, 0, 0], "round_order": [1, 2, 3],
                      "player_a_id": ["p1", "p1", "p1"], "player_b_id": ["p2", "p3", "p4"],
                      "es": [18.0, 12.0, 20.0], "lf": [18.0, 12.0, 20.0]})
    union_lo, union_hi = np.array([15.0, 12.0, 17.0]), np.array([20.0, 21.0, 22.0])
    out, info = TM.narrow_with_guard(m, union_lo, union_hi)
    o = out.set_index("match_id")
    assert info["contradictory_events"] == 1 and out["contradictory_event"].all()
    assert (out["lf"] >= out["es"]).all()
    assert o.loc["qf", "es"] <= 19 <= o.loc["qf", "lf"]
    # an event without contradictions is narrowed as before and left unflagged
    ok = m.assign(es=[18.0, 19.0, 20.0], lf=[18.0, 19.0, 20.0])
    out2, info2 = TM.narrow_with_guard(ok, union_lo, union_hi)
    assert info2["contradictory_events"] == 0 and not out2["contradictory_event"].any()
    assert out2["es"].tolist() == [18.0, 19.0, 20.0]


def test_draw_narrowing_only_narrows_and_stays_inside_the_event():
    # one event: R1 (p1-p2, p3-p4), R2 (p1-p3). Another event the same week with p5-p1 must not bind.
    m = pd.DataFrame({
        "match_id": ["r1a", "r1b", "r2", "other"], "ev": [0, 0, 0, 1], "round_order": [1, 1, 2, 1],
        "player_a_id": ["p1", "p3", "p1", "p5"], "player_b_id": ["p2", "p4", "p3", "p1"],
        "es": [100.0, 100.0, 100.0, 90.0], "lf": [106.0, 106.0, 106.0, 120.0]})
    m.loc[m.match_id.eq("r2"), ["es", "lf"]] = [102.0, 102.0]       # R2 known exactly: day 102
    out, moved = TM.draw_narrowing(m)
    o = out.set_index("match_id")
    assert o.loc["r1a", "lf"] == 102 and o.loc["r1b", "lf"] == 102    # R1 finished by the day R2 finished
    assert o.loc["r2", "es"] == 102 and o.loc["r2", "lf"] == 102
    assert o.loc["other", "es"] == 90 and o.loc["other", "lf"] == 120 # another event is never linked
    assert (out["es"] >= m["es"]).all() and (out["lf"] <= m["lf"]).all() and moved > 0


def test_anchor_moves_to_the_nearest_monday_with_the_researched_exceptions():
    m = pd.DataFrame({
        "tournament_date": pd.to_datetime(["2024-03-06", "2024-03-03", "2024-03-04", "2024-02-02", "2012-07-23"]),
        "tournament_name": ["Indian Wells Masters", "Some 250", "Some 500", "Davis Cup WG R1: X vs Y", "London Olympics"],
        "level": ["T1000", "T250", "T500", "TEAM", "TEAM"], "tour": ["atp"] * 5, "year": [2024, 2024, 2024, 2024, 2012]})
    day = lambda s: float(np.datetime64(s, "D").astype("int64"))  # noqa: E731
    got = TM.anchor_day(m)
    assert got[0] == day("2024-03-04")          # a Wednesday-dated Masters: back to its Monday
    assert got[1] == day("2024-03-04")          # a Sunday start: forward to the Monday
    assert got[2] == day("2024-03-04")          # a Monday stays
    assert got[3] == day("2024-02-02")          # a Davis Cup tie counts from its own date
    assert got[4] == day("2012-07-30")          # the ATP London 2012 Olympics: a week later


def test_named_edition_overrides_the_class_window():
    m = pd.DataFrame({"tour": ["atp", "atp"], "level": ["GS", "GS"], "qualifying": [True, True],
                      "tournament_name": ["Australian Open", "Australian Open"], "year": [2021, 2023],
                      "round": ["Q1", "Q1"]})
    lo, hi, named = TM.rule_windows(m)
    assert named.all()
    assert (lo[0], hi[0]) == (-30 - TM.RULE_MARGIN, -26 + TM.RULE_MARGIN)   # 2021: Doha, four weeks early
    assert (lo[1], hi[1]) == (-7 - TM.RULE_MARGIN, -5 + TM.RULE_MARGIN)


def test_the_2021_australian_open_qualifying_is_not_read_as_the_us_open():
    m = pd.DataFrame({"tournament_name": ["Doha Aus Open Qualies", "Dubai Aus Open Qualies", "Us Open", "US Open",
                                          "Australian Open"],
                      "level": "GS", "qualifying": True, "year": [2021, 2021, 2022, 2022, 2022], "tour": "atp",
                      "round": ["Q3", "Q3", "Q1", "Q1", "Q1"]})
    assert TM.rule_label(m).tolist() == [TM.AO21_QUALIFYING] * 2 + ["US Open", "US Open", "Australian Open"]
    lo, hi, named = TM.rule_windows(m)
    assert named[:2].all() and (lo[0], hi[0]) == (2 - TM.RULE_MARGIN, 2 + TM.RULE_MARGIN)   # Q3 on Wed 13 Jan


def test_event_shift_reads_the_events_own_dated_days():
    ev = np.array([0, 0, 0, 0, 1, 1])
    rnd = np.array(["R32", "R32", "R16", "QF", "R32", "R16"])
    resid = np.array([3.0, 3.0, 2.0, np.nan, 0.0, np.nan])
    assert TM.event_shift(ev, rnd, resid).tolist() == [3.0, 3.0, 3.0, 3.0, 0.0, 0.0]
    # each match reading only the other rounds: R32 sees the R16 (2), the R16 the R32s (3), the undated QF all three
    s = TM.event_shift(ev, rnd, resid, exclude_own_round=True)
    assert s[:4].tolist() == [2.0, 2.0, 3.0, 3.0] and np.isnan(s[4]) and s[5] == 0.0


def test_class_window_holds_its_matches():
    rng = np.random.default_rng(0)
    n = 1000
    m = pd.DataFrame({"tour": "atp", "level": "CH", "phase": "main", "round": "R32", "era": "2021-2026",
                      "start": 100.0, "anchor": 100.0, "exact": True}, index=range(n))
    off = rng.integers(-1, 3, size=n).astype(float)
    m["exact_lo"], m["exact_hi"] = m["start"] + off, m["start"] + off
    w = TM.class_windows(m).iloc[0]
    assert w["basis"] == "empirical_era" and w["lo"] <= -2 and w["hi"] >= 3
