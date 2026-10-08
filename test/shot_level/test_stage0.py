"""Stage 0 of the shot-level study: the shot-string parser, player orientation, the linker, the time rule of the
history counts, and the detectable-gain formula (against a simulation).

Run: ./python.sh -m pytest test/shot_level/test_stage0.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stage0_coverage as COV  # noqa: E402
from src.eda.shot_level.stage0_sources import mcp_point  # noqa: E402


# ------------------------------------------------------------------------------------------------
# The Match Charting Project's shot strings

@pytest.mark.parametrize("first, second, expected", [
    # serve wide, forehand return to the middle, backhand, forehand winner: 4 shots
    ("4f2b3f1*", None, (4, True, False, True, False, True)),
    # an ace down the T
    ("6*", None, (1, True, False, True, False, False)),
    # first serve into the net; second serve to the body, forehand return landing short (depth 7), backhand slice error
    ("4n", "5f37b2s1@", (4, True, True, True, False, True)),
    # double fault: the second serve is long
    ("6d", "4w", (1, True, False, True, False, False)),
    # serve of unknown direction, forehand approach, backhand volley winner: a net point
    ("0f+1z3*", None, (3, False, False, True, True, True)),
    # a let, then a wide serve and a forehand winning return
    ("c4f1*", None, (2, True, False, True, False, True)),
    # a deep return (depth 9), point still unfinished in the chart (no outcome mark)
    ("5f19b2", None, (3, True, True, False, False, True)),
    # nothing charted
    ("", None, (0, False, False, False, False, False)),
])
def test_mcp_point(first, second, expected):
    assert mcp_point(first, second) == expected


# ------------------------------------------------------------------------------------------------
# Orientation and linking

def test_orient():
    assert S.orient("alcaraz", "sinner", "Carlos Alcaraz", "Jannik Sinner", "alcaraz", "sinner",
                    "Carlos Alcaraz", "Jannik Sinner") is True
    assert S.orient("alcaraz", "sinner", "C. Alcaraz", "J. Sinner", "sinner", "alcaraz",
                    "Jannik Sinner", "Carlos Alcaraz") is False
    # a married name on one side: the other side decides
    assert S.orient("riske", "kenin", "Alison Riske", "Sofia Kenin", "amritraj", "kenin",
                    "Alison Riske Amritraj", "Sofia Kenin") is True
    # sisters with one surname cannot be told apart by surname keys alone
    assert S.orient("wang", "wang", "Xiyu Wang", "Qiang Wang", "wang", "wang", "Qiang Wang", "Xiyu Wang") is None


def tiny_universe() -> pd.DataFrame:
    u = pd.DataFrame({
        "uid": [0, 1, 2], "match_id": ["m0", "m1", "m2"], "tour": ["M", "W", "M"], "year": [2024, 2024, 2024],
        "d": pd.to_datetime(["2024-03-04", "2024-03-04", "2024-06-24"]), "level": ["T1000", "T1000", "GS"],
        "draw": ["main", "main", "main"], "round": ["R32", "R16", "R64"], "tname": ["X", "X", "Wimbledon"],
        "id_a": ["atp:1", "wta:1", "atp:3"], "id_b": ["atp:2", "wta:2", "atp:4"],
        "name1": ["Carlos Alcaraz", "Alison Riske Amritraj", "Taylor Fritz"],
        "name2": ["Jannik Sinner", "Sofia Kenin", "Tommy Paul"], "creator": "stage0"})
    return S.prepare(u).drop(columns=["rid"]).reset_index(drop=True)


def test_linker_window_and_orientation():
    lk = S.Stage0Linker(tiny_universe())
    rows = pd.DataFrame({
        "tour": ["M", "M", "W", "M"],
        # played on day 5 of the event; 30 days late (outside the window); a married name; Wimbledon week 2
        "d": pd.to_datetime(["2024-03-09", "2024-04-03", "2024-03-10", "2024-07-03"]),
        "name1": ["J. Sinner", "Carlos Alcaraz", "Alison Riske", "T. Paul"],
        "name2": ["C. Alcaraz", "Jannik Sinner", "Sofia Kenin", "T. Fritz"],
        "round": ["R32", "R32", "R16", "R64"], "draw": "main"})
    out = lk.link(rows)
    assert out["match_id"].tolist()[0] == "m0" and out["a1"].tolist()[0] is False
    assert pd.isna(out["match_id"].tolist()[1])
    assert out["match_id"].tolist()[2] == "m1" and out["a1"].tolist()[2] is True
    assert out["match_id"].tolist()[3] == "m2" and out["a1"].tolist()[3] is False


# ------------------------------------------------------------------------------------------------
# The time rule of the history counts

def test_history_counts_time_rule():
    # player P: an event 400 days back (carries), event E1 (two rounds, both carry), event E2 (R32 does not carry,
    # R16 carries); opponents are new players each time
    rows = [
        ("old", "P", "O0", "2019-01-07", "T0", 13),
        ("e1r32", "P", "O1", "2020-02-10", "T1", 13),
        ("e1r16", "P", "O2", "2020-02-10", "T1", 14),
        ("e2r32", "P", "O3", "2020-02-17", "T2", 13),
        ("e2r16", "P", "O4", "2020-02-17", "T2", 14),
    ]
    mp = []
    for mid, a, b, d, t, r in rows:
        mp.append({"match_id": mid, "player_id": a, "side": "A", "tournament_date": pd.Timestamp(d),
                   "tournament_id": t, "round_order": r})
        mp.append({"match_id": mid, "player_id": b, "side": "B", "tournament_date": pd.Timestamp(d),
                   "tournament_id": t, "round_order": r})
    mp = pd.DataFrame(mp).sort_values(["tournament_date", "round_order", "side"]).reset_index(drop=True)
    carries = pd.DataFrame({"all|rally": [True, True, True, False, True]},
                           index=["old", "e1r32", "e1r16", "e2r32", "e2r16"])
    h = COV.history_counts(mp, carries)
    p = mp["player_id"].eq("P").to_numpy()
    got_career = dict(zip(mp.loc[p, "match_id"], h["career"][p, 0]))
    got_52w = dict(zip(mp.loc[p, "match_id"], h["52w"][p, 0]))
    assert got_career == {"old": 0, "e1r32": 1, "e1r16": 2, "e2r32": 3, "e2r16": 3}
    assert got_52w == {"old": 0, "e1r32": 0, "e1r16": 1, "e2r32": 2, "e2r16": 2}
    # the opponents have no history
    assert (h["career"][~p, 0] == 0).all()


# ------------------------------------------------------------------------------------------------
# The detectable gain

def test_mde_formula_value():
    # 2 (1.96 + 0.8416)^2 / n nats
    assert abs(float(S.mde_milli(10_000)) - 1000 * 2 * (1.96 + 0.8416) ** 2 / 10_000) < 1e-9
    assert abs(float(S.mde_milli(10_000, inflation=2.0)) - 4 * float(S.mde_milli(10_000))) < 1e-9


def test_mde_formula_by_simulation():
    """The per-match gain of the true model over a calibrated base has mean beta^2 v / 2 and standard deviation
    |beta| sqrt(v), so a test on n matches has z = |beta| sqrt(v n) / 2."""
    rng = np.random.default_rng(7)
    n, beta = 400_000, 0.12
    lb = rng.normal(0.0, 1.3, n)
    x = rng.normal(0.0, 1.0, n)
    p_true = expit(lb + beta * x)
    y = rng.random(n) < p_true
    p_base = expit(lb)

    def ll(p):
        return -(y * np.log(p) + (~y) * np.log(1 - p))
    d = ll(p_base) - ll(p_true)
    v = float(np.mean(p_base * (1 - p_base)))
    assert abs(d.mean() / (beta ** 2 * v / 2) - 1) < 0.15
    assert abs(d.std() / (beta * np.sqrt(v)) - 1) < 0.05
    # the gain the formula says a test of this size detects with 80% power, against the simulated z
    g = beta ** 2 * v / 2
    m = 2 * (1.96 + 0.8416) ** 2 / g          # matches needed for that gain
    z_at_m = d.mean() / d.std() * np.sqrt(m)
    assert abs(z_at_m - (1.96 + 0.8416)) < 0.35


def test_pool_read_has_no_result():
    assert "a_won" not in COV.POOL_READ
