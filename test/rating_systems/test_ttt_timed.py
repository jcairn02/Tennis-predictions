"""TrueSkill Through Time on the leak-proof timeline (ratings.ttt_pass_timed).

1. Equivalence: given the tournament week as both its earliest start and its latest finish, smoothing after every batch
   over the same span, it reproduces ttt_pass exactly, round-by-round folding included.
2. Isolation: with a two-week event overlapping another event, changing the results of the long event's later rounds
   cannot move any forecast of the other event's matches played before them, while a match played after them responds.
   Under ttt_pass's week clock the same change does move them (the leak the timed pass removes).

Run: ./python.sh -m pytest test/rating_systems/test_ttt_timed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.rating_systems import ratings as R  # noqa: E402


def _random_history(seed: int = 0, weeks: int = 30, players: int = 24, quiet=(9, 10, 20)):
    """One date per week (day 7w); a few events a week, each a small knockout with a round robin now and then; a
    walkover now and then (no rating move); in the ``quiet`` weeks every match is a walkover, so nothing is released
    that week and forecasts must still drift to the new date. Rows in the table's order: week, event, round."""
    rng = np.random.default_rng(seed)
    week, event, rnd, ka, kb, won, upd = [], [], [], [], [], [], []
    ev = 0
    for w in range(weeks):
        pool = rng.permutation(players)
        for e in range(2):
            field = list(pool[e * 8:(e + 1) * 8])
            rr = rng.random() < 0.2
            r = 1
            while len(field) > 1:
                nxt = []
                for a, b in zip(field[::2], field[1::2]):
                    week.append(7 * w)
                    event.append(ev)
                    rnd.append(r)
                    ka.append(int(a))
                    kb.append(int(b))
                    x = bool(rng.random() < 0.5)
                    won.append(x)
                    upd.append(bool(rng.random() > 0.05) and w not in quiet)
                    nxt.append(a if x else b)
                if rr and r == 1:                    # a round robin's second match in the same round
                    week.append(7 * w)
                    event.append(ev)
                    rnd.append(r)
                    ka.append(int(field[0]))
                    kb.append(int(field[2]))
                    won.append(bool(rng.random() < 0.5))
                    upd.append(w not in quiet)
                field = nxt
                r += 1
            ev += 1
    return week, event, rnd, ka, kb, won, upd, players


def test_reproduces_ttt_pass_on_the_week_clock():
    # ttt_pass counts its smoothing window in batches, the timed pass in days: with a batch every week they agree
    week, event, rnd, ka, kb, won, upd, n = _random_history(quiet=())
    act = [True] * len(week)
    for window in (3, 8):
        ref = R.ttt_pass(week, event, rnd, ka, kb, won, act, upd, n, sigma0=2.0, gamma=0.4, window=window)
        got = R.ttt_pass_timed(week, week, event, rnd, ka, kb, won, act, upd, n, sigma0=2.0, gamma=0.4,
                               window_days=7.0 * window, smooth_every="batch")
        assert np.allclose(got, ref, atol=1e-12, equal_nan=True)


def test_quiet_weeks_still_drift_to_the_new_date():
    # weeks where nothing moves a rating release no batch; a forecast must still read the model drifted to its own
    # day (a window wide enough that both passes smooth every batch)
    week, event, rnd, ka, kb, won, upd, n = _random_history()
    act = [True] * len(week)
    ref = R.ttt_pass(week, event, rnd, ka, kb, won, act, upd, n, sigma0=2.0, gamma=0.4, window=100)
    got = R.ttt_pass_timed(week, week, event, rnd, ka, kb, won, act, upd, n, sigma0=2.0, gamma=0.4,
                           window_days=700.0, smooth_every="batch")
    assert np.allclose(got, ref, atol=1e-12, equal_nan=True)


def _overlap(late_flip: bool, seed: int = 1):
    """E0 (days -30..-26) links everyone; E1 runs two weeks from day 1 (round r on day 2r - 1, days 1-13) under the
    start date 0; E2 starts on day 7 (round r on day 5 + 2r, days 7-15). E1's results from day 9 on are what E2's
    first two rounds (days 7 and 9) may not see."""
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(1, 6):
        rows += [(0, 1, -30 + r, -30, 0, r), (2, 6, -30 + r, -30, 0, r), (7, 3, -30 + r, -30, 0, r)]
    for r in range(1, 8):
        rows += [(0, 2, 2 * r - 1, 0, 1, r), (1, 3, 2 * r - 1, 0, 1, r)]
    for r in range(1, 6):
        rows.append((6, 7, 5 + 2 * r, 7, 2, r))
    rows.sort(key=lambda x: (x[3], x[4], x[5]))          # the table's order: start date, event, round
    a, b, day, start, ev, rn = (list(x) for x in zip(*rows))
    won = [bool(rng.random() < 0.5) for _ in rows]
    if late_flip:
        won = [(not w) if (e == 1 and d >= 9) else w for w, e, d in zip(won, ev, day)]
    return a, b, day, start, ev, rn, won


def test_later_rounds_of_an_overlapping_event_stay_out():
    out = {}
    for clock in ("timed", "week"):
        res = []
        for flip in (False, True):
            a, b, day, start, ev, rn, won = _overlap(flip)
            n = 8
            act, upd = [True] * len(a), [True] * len(a)
            if clock == "timed":
                p = R.ttt_pass_timed(day, day, ev, rn, a, b, won, act, upd, n, window_days=60.0)
            else:
                p = R.ttt_pass(start, ev, rn, a, b, won, act, upd, n, window=8)
            res.append(p[:, :4])
        out[clock] = ~np.all(np.isclose(res[0], res[1], atol=1e-12), axis=1)
    a, b, day, start, ev, rn, won = _overlap(False)
    day, ev = np.array(day), np.array(ev)
    early_e2 = (ev == 2) & (day <= 9)
    assert not out["timed"][early_e2].any(), "a result from after the match reached its forecast"
    assert out["timed"][(ev == 2) & (day >= 12)].any(), "a match after the flipped results must respond"
    assert out["week"][early_e2].any(), "the week clock was expected to leak here (the defect the timed pass removes)"
