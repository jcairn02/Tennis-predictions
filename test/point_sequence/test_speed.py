"""Item C serve-speed screen: the pre-registration lock, the offset logistic estimator, and the feature's own-history
windows, on synthetic data.

Run: ./python.sh -m pytest test/point_sequence/test_speed.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import speed_build as B  # noqa: E402
from src.eda.point_sequence import speed_screen as S  # noqa: E402


def test_refuses_when_the_prereg_hash_differs(tmp_path, monkeypatch):
    pre, hf = tmp_path / "p.md", tmp_path / "p.sha256"
    pre.write_text("registered text\n", encoding="utf-8")
    hf.write_text(hashlib.sha256(b"other text\n").hexdigest() + "  p.md\n", encoding="utf-8")
    monkeypatch.setattr(S, "PREREG", pre)
    monkeypatch.setattr(S, "HASHFILE", hf)
    with pytest.raises(SystemExit):
        S.check_hash()
    hf.write_text(hashlib.sha256(pre.read_bytes()).hexdigest() + "  p.md\n", encoding="utf-8")
    assert S.check_hash() == hashlib.sha256(pre.read_bytes()).hexdigest()


def test_newton_recovers_beta_with_offset():
    rng = np.random.default_rng(1)
    n = 60000
    off = logit(rng.uniform(0.2, 0.8, n))
    x = rng.normal(size=n)
    y = rng.binomial(1, expit(off + 0.15 * x)).astype(float)
    b, se = S.newton(off, x, y)
    assert abs(b - 0.15) < 3 * se and 0.005 < se < 0.02


def history(rows):
    df = pd.DataFrame(rows, columns=["match_id", "tour", "player_id", "tournament_id", "tdate", "round_order", "obs",
                                     "spd1_n", "spd1_d", "year", "order"])
    return df


def test_windows_follow_own_history_and_days():
    # player p: an event 30 days earlier (speed 190), an event 10 days earlier (two rounds, speed 180 and 170),
    # the target event's earlier round (speed 160), the target, a later round (speed 100: must be ignored), and a
    # same-week match at another event (speed 50: must be ignored)
    rows = [
        ("m1", "atp", "p", "E1", 0, 13, 0, 190 * 40, 40, 2023, 1),
        ("m2", "atp", "p", "E2", 20, 13, 20, 180 * 40, 40, 2023, 2),
        ("m3", "atp", "p", "E2", 20, 14, 21, 170 * 40, 40, 2023, 3),
        ("m4", "atp", "p", "E3", 28, 13, 29, 160 * 40, 40, 2023, 4),
        ("m5", "atp", "p", "E3", 28, 14, 31, 0, 0, 2023, 5),          # the target
        ("m6", "atp", "p", "E3", 28, 15, 33, 100 * 40, 40, 2023, 6),
        ("m7", "atp", "p", "E4", 28, 11, 30, 50 * 40, 40, 2023, 7),
    ]
    r = history(rows)
    win = B.window_feature(r, np.array([4]))
    # 2-week window (obs 31 - obs <= 14): m3 (age 10), m4 (age 2); m2 is age 11 -> also in; m1 age 31 -> out
    assert win.loc[4, "n2"] == 120 and abs(win.loc[4, "s2"] / win.loc[4, "n2"] - (180 + 170 + 160) / 3) < 1e-9
    assert win.loc[4, "n52"] == 160 and abs(win.loc[4, "s52"] / 160 - (190 + 180 + 170 + 160) / 4) < 1e-9
    x = B.side_values(win).iloc[0]
    assert abs(x - ((180 + 170 + 160) / 3 - (190 + 180 + 170 + 160) / 4)) < 1e-9


def test_side_missing_without_a_recent_match():
    rows = [("m1", "atp", "p", "E1", 0, 13, 0, 190 * 40, 40, 2023, 1),
            ("m2", "atp", "p", "E2", 60, 13, 60, 0, 0, 2023, 2)]
    win = B.window_feature(history(rows), np.array([1]))
    assert np.isnan(B.side_values(win).iloc[0])


def test_subsets_follow_the_registration():
    d = pd.DataFrame({"tour": ["atp"] * 4 + ["wta"] * 2, "year": [2019, 2019, 2021, 2023, 2019, 2023],
                      "level": ["GS", "T250", "T250", "T250", "T250", "GS"]})
    assert list(S.subset(d, "atp", "discovery").index) == [0, 2]
    assert list(S.subset(d, "atp", "replication").index) == [3]
    assert list(S.subset(d, "wta", "discovery").index) == []
    assert list(S.subset(d, "wta", "replication").index) == [5]
