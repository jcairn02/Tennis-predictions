"""Tests of the leak-proof IOS solver (src/eda/match_timing/ios_time.py).

1. Equivalence: given Stage B's own clock (release = tournament week + 1 day, query = tournament week), the timed solver
   reproduces Stage B's weekly path with its incremental step, on a slice of the real history.
2. Isolation: on a hand-made history with a two-week event overlapping another event, changing the results of the
   two-week event's late rounds cannot move any rating of the overlapping event's early matches, while a match played
   after them must respond. Under Stage B's week clock the same change does move them (the leak this study removes).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import ios_time as IT  # noqa: E402
from src.eda.ufc_ideas import stageB_ios as I  # noqa: E402


def _td(pid, day, ev, rn, y, d, ok=None, typ=60.0):
    """A one-tour input in Stage B's layout: rows in pairs (A then B), position ^ 1 the opponent."""
    pid = np.asarray(pid, dtype=np.int64)
    n = len(pid)
    ok = np.ones(n, dtype=bool) if ok is None else np.asarray(ok, dtype=bool)
    day = np.asarray(day, dtype=np.int64)
    dates = pd.to_datetime(day, unit="D").to_numpy()
    return {"tour": "atp", "idx": np.arange(n), "pid": pid, "n_players": int(pid.max()) + 1, "day": day,
            "ev": np.asarray(ev, dtype=np.int64), "round_order": np.asarray(rn, dtype=np.int64),
            "tournament_date": dates, "tournament_id": np.asarray([f"e{e}" for e in ev], dtype=object),
            "year": pd.DatetimeIndex(dates).year.to_numpy(), "evaluation": np.ones(n, dtype=bool),
            "eval_level": np.ones(n, dtype=bool),
            "stats": {"spw": {"ok": ok, "x": np.asarray(y) * 0 + 40.0, "d": np.asarray(d, dtype=float),
                              "y": np.asarray(y, dtype=float), "mu": np.zeros(n), "typ": typ}}}


def _history(seed=0, late_flip=False):
    """Two events: E1 runs two weeks (round r on day 2r - 1: days 1-13), E2 starts on day 7, in E1's second week
    (round r on day 5 + 2r: days 7-15). E2's players met E1's players earlier (event E0, days -29 to -25), so a joint
    solve links them. E1's results from day 9 on are what E2's first two rounds (days 7 and 9) may not see."""
    rng = np.random.default_rng(seed)
    rows = []          # (A, B, day, ev, round)
    for r in range(1, 6):
        rows.append((0, 1, -30 + r, 0, r))          # E0: common opponents
        rows.append((2, 6, -30 + r, 0, r))
        rows.append((7, 3, -30 + r, 0, r))
    for r in range(1, 8):
        rows.append((0, 2, 2 * r - 1, 1, r))
        rows.append((1, 3, 2 * r - 1, 1, r))
    for r in range(1, 6):
        rows.append((6, 7, 5 + 2 * r, 2, r))
    pid, day, ev, rn, y, d = [], [], [], [], [], []
    for a, b, dd, e, r in rows:
        ya, yb = rng.normal(0.4, 0.3), rng.normal(0.4, 0.3)
        if late_flip and e == 1 and dd >= 9:
            ya, yb = -ya - 2.0, -yb + 2.0
        pid += [a, b]
        day += [dd, dd]
        ev += [e, e]
        rn += [r, r]
        y += [ya, yb]
        d += [60.0, 60.0]
    return np.array(pid), np.array(day), np.array(ev), np.array(rn), np.array(y), np.array(d)


def test_matches_stage_b_on_its_own_clock():
    pid, day, ev, rn, y, d = _history()
    week = (day // 7) * 7                          # Stage B's clock: each event's start week
    start = pd.Series(week).groupby(ev).transform("min").to_numpy()
    td = _td(pid, start, ev, rn, y, d)
    ref = I.run(td, "spw", h=52.0, kappa=1.0, tau=0, mode="weekly")
    got = IT.run_timed(td, "spw", 52.0, 1.0, 0, es=start.astype(float), lf=start.astype(float), obs=start.astype(float))
    assert np.allclose(got["O"], ref["O"], atol=1e-10, equal_nan=True)
    assert np.allclose(got["D"], ref["D"], atol=1e-10, equal_nan=True)


@pytest.mark.parametrize("clock", ["timed", "week"])
def test_late_rounds_of_an_overlapping_event_stay_out(clock):
    base = _history(late_flip=False)
    flip = _history(late_flip=True)
    out = []
    for pid, day, ev, rn, y, d in (base, flip):
        start = pd.Series(day).groupby(ev).transform("min").to_numpy()
        if clock == "timed":
            td = _td(pid, start, ev, rn, y, d)
            r = IT.run_timed(td, "spw", 52.0, 1.0, 0, es=day.astype(float), lf=day.astype(float), obs=day.astype(float))
        else:
            td = _td(pid, (start // 7) * 7, ev, rn, y, d)
            r = I.run(td, "spw", h=52.0, kappa=1.0, tau=0, mode="weekly")
        out.append(np.column_stack([r["O"], r["D"]]))
    moved = ~np.all(np.isclose(out[0], out[1], atol=1e-12), axis=1)
    early_e2 = (ev_of(base) == 2) & (base[1] <= 9)  # E2's first two rounds: not after any flipped result finished
    if clock == "timed":
        assert not moved[early_e2].any(), "a result from after the match leaked into its ratings"
        later = (ev_of(base) == 2) & (base[1] >= 12)
        assert moved[later].any(), "a match after the flipped results must respond"
    else:
        assert moved[early_e2].any(), "the week clock was expected to leak here (the defect this study fixes)"


def test_refuses_a_window_that_ends_before_it_starts():
    pid, day, ev, rn, y, d = _history()
    td = _td(pid, day, ev, rn, y, d)
    es, lf = day.astype(float), day.astype(float)
    lf[0] = lf[1] = es[0] - 1                       # one match released before its own earliest start
    with pytest.raises(ValueError):
        IT.run_timed(td, "spw", 52.0, 1.0, 0, es=es, lf=lf, obs=es)


def ev_of(h):
    return h[2]
