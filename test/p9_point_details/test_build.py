"""Tests of the P9 point-details builder's pieces (offline, hand-made data): the MatchBeats rally convention, the bands,
the match gate and the 52-week as-of sums."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import build_common as B  # noqa: E402


def _points(rows):
    cols = ["key", "server", "scorer", "result", "old", "tracked", "ra_shot", "ra_team", "ra_won", "ra_end"]
    p = pd.DataFrame(rows, columns=cols)
    p["old"] = p["old"].astype(float)
    return p


def test_convention_standard_rule():
    k = "p9|2026|1|MS001"
    p = _points([
        (k, 1, 1, "A", 0, True, 1, 1, True, "ACE"),            # ace: 1
        (k, 1, 2, "DF", 0, True, 1, 1, False, "DOUBLE FAULT"),  # double fault: 0
        (k, 1, 2, "UE", 4 + 4, True, 0, 0, False, ""),          # server erred on shot 9 (8 balls in): 9
        (k, 1, 1, "UE", 8 + 7, True, 0, 0, False, ""),          # returner erred on shot 16: 16
        (k, 1, 1, "W", 5 + 4, True, 0, 0, False, ""),           # server's winner on shot 9: 9
        (k, 2, 2, "UE", 0 + 1, True, 0, 0, False, ""),          # return error: 2
        (k, 1, 1, "FE", 1 + 0, True, 0, 0, False, ""),          # serve not returned (forced): 2
        (k, 1, 1, "W", 1, True, 0, 0, False, ""),               # a 'winner' with only the serve in: 2, returner's FE
        (k, 1, 1, "N", 1, True, 0, 0, False, ""),               # unclassified, only the serve in, server won: 2
        (k, 1, 1, "N", 3, True, 3, 1, True, ""),                # unclassified, rally file: server's winner on 3: 3
        (k, 1, 2, "N", 4, True, 5, 1, False, ""),               # unclassified, rally file: server erred on 5: 5
        (k, 1, 1, "N", 5, True, 0, 0, False, ""),               # unclassified, nothing to tell 5 from 6: unknown
        (k, 1, 2, "W", 3, True, 0, 0, False, ""),               # 3 balls in (server's last) but returner won: parity
        (k, 1, 1, "UE", 0, True, 0, 0, False, ""),              # an error with no ball in: untracked junk
        (k, 1, 1, "W", 0, False, 0, 0, False, ""),              # untracked
        (k, 1, 1, "UE", 5000, True, 0, 0, False, ""),           # garbage
    ])
    c = B.mb_convention(p)
    assert c["rally"].tolist() == [1, 0, 9, 16, 9, 2, 2, 2, 2, 3, 5, -1, -1, -1, -1, -1]
    assert c["how"].tolist()[-5:] == ["n_unresolved", "parity", "untracked", "untracked", "garbage"]
    # enders: the erring player, or the winner's hitter
    assert c["ender"].tolist()[2:8] == [1, 2, 1, 1, 2, 2]


def test_convention_inclusive_event():
    k = "infosys_slams|2026|520|MS001"
    rows = []
    # an event whose error counts include the erring shot: the last counted ball is the loser's
    for i in range(30):
        rows.append((k, 1, 1, "UE", 4, True, 0, 0, False, ""))   # returner erred on shot 4 (counted): 4
    rows.append((k, 1, 1, "W", 3, True, 0, 0, False, ""))        # winner on 3: 3
    c = B.mb_convention(_points(rows))
    assert set(c["rule"]) == {"inclusive"}
    assert c["rally"].tolist() == [4] * 30 + [3]


def test_bands_and_cap():
    r = np.array([-1, 0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 14])
    assert B.band_of(r).tolist() == [-1, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4]
    assert B.capped(np.array([1, 8, 9, 10, 11, 14])).tolist() == [1, 8, 9, 10, 9, 10]


def test_gate():
    key = pd.Series(["a"] * 10 + ["b"] * 10)
    end = pd.Series([1, 2] + [0] * 8 + [1, 2] + [0] * 8)
    rally = pd.Series([1, 0] + [3] * 8 + [1, 0] + [3] * 4 + [-1] * 4)
    g = B.match_gate(key, rally, end).set_index("key")
    assert bool(g.loc["a", "carries"]) and not bool(g.loc["b", "carries"])
    assert g.loc["b", "share"] == 0.5


def test_window_sums_matches_direct_lookback():
    rng = np.random.default_rng(1)
    days = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 900, 400), unit="D")
    rows = pd.DataFrame({"player_id": rng.choice(["p1", "p2", "p3"], 400), "tournament_date": days,
                         "tournament_id": rng.choice(["e1", "e2"], 400), "round_order": rng.integers(1, 6, 400),
                         "x": rng.integers(0, 100, 400).astype(float)})
    fast = B.window_sums(rows, ["x"])
    slow = B.window_sums_slow(rows, ["x"])
    assert np.allclose(fast["x"].to_numpy(), slow["x"].to_numpy())


def test_window_excludes_the_match_and_later_and_old():
    rows = pd.DataFrame({
        "player_id": ["p"] * 5,
        "tournament_date": pd.to_datetime(["2025-01-06", "2025-01-06", "2025-01-13", "2026-01-12", "2026-01-05"]),
        "tournament_id": ["e1", "e1", "e2", "e3", "e4"], "round_order": [11, 12, 11, 11, 11],
        "x": [1.0, 10.0, 100.0, 1000.0, 10000.0]})
    s = B.window_sums(rows, ["x"])["x"].tolist()
    # e1 R1 sees nothing; e1 R2 sees R1; e2 sees e1; e3 (2026-01-12) sees e2 (364 days before is 2025-01-13: inside
    # the window [d - 363, d - 1]? 2026-01-12 - 363 days = 2025-01-14, so e2 is out) and e4; e4 sees e2 (357 days)
    assert s == [0.0, 1.0, 11.0, 10000.0, 100.0]
