"""The states step's ace ratings for the pattern step's venue pace (dp_ios.recent_outputs, dp_state.write_ace_rows;
16 Oct 2026). Fast: a stand-in for the solver's setup and outputs; the real solver's values are checked by the replay.
Run: ./python.sh -m pytest test/daily_prediction/test_ace_rows.py -q
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

import dp_ios as IO
import dp_state as SP

DAYS = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])
S = SimpleNamespace(days=DAYS, query=np.repeat(DAYS, 2))      # rows 2k, 2k+1: one match a day


def fake_outputs(s, rows, targets):
    t = np.asarray(targets, dtype=np.int64)
    o = t.astype(float)
    o[t == 5] = np.nan                                         # a row the solver could not rate
    return {"rows": t, "O_eff": o, "D_eff": -t.astype(float)}


def test_recent_rows_are_the_solved_rows_after_the_checkpoint(monkeypatch):
    monkeypatch.setattr(IO, "outputs", fake_outputs)
    r = IO.recent_outputs(S, {}, np.array([8, 9]), d0=12)     # snapshot day 11 (the last before d0); targets on 14
    assert r["rows"].tolist() == [4, 6, 7]                     # queried 12..14, not the targets, row 5 unrated
    assert (r["from_day"], r["to_day"]) == (11.0, 14.0)
    assert r["O_eff"].tolist() == [4.0, 6.0, 7.0] and r["D_eff"].tolist() == [-4.0, -6.0, -7.0]


def test_without_a_checkpoint_the_window_is_capped(monkeypatch):
    monkeypatch.setattr(IO, "outputs", fake_outputs)
    assert IO.recent_outputs(S, {}, np.array([8, 9]), d0=0)["rows"].tolist() == [0, 1, 2, 3, 4, 6, 7]
    monkeypatch.setattr(IO, "RECENT_DAYS", 2.0)
    r = IO.recent_outputs(S, {}, np.array([8, 9]), d0=0)
    assert r["rows"].tolist() == [6, 7] and r["from_day"] == 12.0


def test_write_ace_rows_keeps_each_targets_own_row(tmp_path):
    cache = {"atp": {"key_match": np.array(["m0", "m0", "m1", "m1"]), "key_side": np.array(["A", "B", "A", "B"]),
                     "key_player": np.array(["p1", "p2", "p3", "p4"])}}
    results = [
        {"tour": "atp", "stat": "ace", "mode": "resume",
         "out": {"rows": np.array([2, 3]), "O_eff": np.array([0.3, 0.4]), "D_eff": np.array([-0.3, -0.4])},
         "recent": {"rows": np.array([0, 1, 3]), "O_eff": np.array([0.1, 0.2, 9.9]),
                    "D_eff": np.array([-0.1, -0.2, 9.9]), "from_day": 20000.0, "to_day": 20010.0}},
        {"tour": "atp", "stat": "df", "mode": "resume",
         "out": {"rows": np.array([2, 3]), "O_eff": np.array([7.0, 7.0]), "D_eff": np.array([7.0, 7.0])}}]
    rec = SP.write_ace_rows(tmp_path / "ace.parquet", cache, results)
    t = pd.read_parquet(tmp_path / "ace.parquet").set_index(["match_id", "side"])
    assert rec["rows"] == 4 and len(t) == 4
    assert t.loc[("m1", "B"), "srf_O_eff_ace"] == 0.4 and t.loc[("m1", "B"), "source"] == "target"
    assert t.loc[("m0", "A"), "srf_D_eff_ace"] == -0.1 and t.loc[("m0", "A"), "player_id"] == "p1"
    assert rec["tours"]["atp"] == {"mode": "resume", "recent_rows": 3, "from_day": "2024-10-04", "to_day": "2024-10-14"}
