"""P11's forward-capture test (src/eda/gap_downloads/pinnacle_capture.py): each matchup's captured close from the pulls,
its comparison with TennisExplorer's page of the same match, and the loop's skip while a bet-day pull runs. Synthetic
rows; every price is made up."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import pinnacle_capture as PC  # noqa: E402


def pull_row(t, usable=True, live=False, dh=1.50, da=2.60, start="2026-10-22T10:00:00+00:00", **kw):
    return {"retrieved_at": t, "matchup_id": 7, "league": "ITF Men Monastir - R16", "tour": "itf", "event": "Monastir",
            "phase": "R16", "level": "itf", "qualifying": False, "home": "Ann Bee", "away": "Cid Dee",
            "price_home": -200, "price_away": 160, "decimal_home": dh, "decimal_away": da, "p_home": 0.63,
            "overround": 1 / dh + 1 / da, "start_utc": start, "is_live": live, "usable": usable, **kw}


def test_close_is_the_last_usable_pre_start_pull():
    df = pd.DataFrame([pull_row("2026-10-22T08:00:00+00:00", dh=1.55, da=2.50),
                       pull_row("2026-10-22T09:50:00+00:00"),
                       pull_row("2026-10-22T10:10:00+00:00", usable=False, live=True)])
    c = PC.closes(df).iloc[0]
    assert c.decimal_home == 1.50 and c.n_pulls == 2 and bool(c.live_seen)
    assert c.close_min_before_start == 10.0 and c.open_pull == pd.Timestamp("2026-10-22T08:00:00Z")


def test_compare_orients_the_sides_and_flags_agreement():
    caps = PC.closes(pd.DataFrame([pull_row("2026-10-22T09:50:00+00:00")]))
    te = pd.DataFrame([{"te_id": 1, "p1": "Dee Cid", "p2": "Bee Ann", "start_utc": "2026-10-22T10:05:00+00:00",
                        "k1_last": "2.60", "k2_last": "1.50", "k1_last_t": "2026-10-22T09:40:00+00:00",
                        "k2_last_t": "2026-10-22T09:45:00+00:00"},
                       {"te_id": 2, "p1": "Bee Ann", "p2": "Eve Fox", "start_utc": "2026-10-22T10:00:00+00:00",
                        "k1_last": "1.10", "k2_last": "6.00", "k1_last_t": None, "k2_last_t": None}])
    out = PC.compare(caps, te).iloc[0]
    assert bool(out.linked) and bool(out.te_pinnacle) and bool(out.same_005)
    assert out.te_last_change_min_before_start == 20.0


def test_loop_skips_a_cycle_while_a_bet_day_pull_runs(monkeypatch):
    calls = []
    monkeypatch.setattr(PC, "bet_day_pull_running", lambda: calls.append(1) or (4242 if len(calls) == 1 else None))
    monkeypatch.setattr(PC.Capture, "__init__", lambda self: setattr(self, "client", type("X", (), {"sent": 0})()))
    monkeypatch.setattr(PC.Capture, "pull", lambda self: pd.DataFrame([pull_row("2026-10-22T09:50:00+00:00")]))
    clock = iter(range(0, 100_000, 10))
    monkeypatch.setattr(PC.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(PC.time, "sleep", lambda s: None)
    out = PC.loop(every=600, hours=0.5)
    assert out["skipped"] == 1 and out["pulls"] >= 1 and out["stopped"] is None
