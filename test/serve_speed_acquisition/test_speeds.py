"""The serve-speed acquisition's study script (offline): speed filtering, per-server point speeds, RG key statistics,
sides, and the new coverage scenarios."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.serve_speed_acquisition import speeds as S  # noqa: E402


def test_speed_drops_untimed_and_implausible_values():
    out = S.speed(["190", "0", "0.0", "", None, "300", "40", "40.5", "213 km/h", "199.4"])
    assert out.iloc[0] == 190.0 and out.iloc[7] == 40.5 and out.iloc[9] == 199.4
    assert out.notna().tolist() == [True, False, False, False, False, False, False, True, False, True]


def test_full_name():
    assert S.full_name("Jannik", "SINNER", "J.SINNER") == "Jannik SINNER"
    assert S.full_name(None, "SINNER", "J. Sinner") == "J. Sinner"
    assert S.full_name("", "", None) == ""


def test_point_speeds_by_server():
    p = pd.DataFrame({"slam": "RG", "year": 2025, "match_id": "SM001",
                      "server": ["1", "1", "1", "1", "2", "2", "0"],
                      "serve": ["1", "1", "2", "1", "1", "2", "1"],
                      "spd": [200.0, 190.0, 150.0, np.nan, 210.0, 160.0, 199.0],
                      "fault": [np.nan, np.nan, 205.0, np.nan, np.nan, np.nan, np.nan]})
    out = S.point_speeds(p).set_index("player_no")
    assert list(out.index) == ["1", "2"]                       # a server that is neither player is dropped
    assert out.loc["1", "spd1_n"] == 2 and out.loc["1", "spd1_mean"] == 195.0   # the untimed first serve is not counted
    assert out.loc["1", "service_points"] == 4
    assert out.loc["1", "spd2_mean"] == 150.0 and out.loc["1", "fault1_mean"] == 205.0
    assert out.loc["1", "spd_max"] == 200.0
    assert out.loc["2", "spd1_mean"] == 210.0 and out.loc["2", "spd2_n"] == 1


def test_key_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "INFO", tmp_path)
    rows = []
    for name, p1, p2 in (("1st Serve Average Speed", "199", "192"), ("2nd Serve Average Speed", "153", "165"),
                         ("Max Speed", "213", "0"), ("First Serve", "103/191 (54%)", "113/194 (58%)"),
                         ("Aces", "10", "12")):
        rows.append({"slam": "RG", "year": "2025", "match_id": "SM001", "set_key": "set0", "name": name,
                     "player1": p1, "player2": p2})
    rows.append({"slam": "RG", "year": "2025", "match_id": "SM001", "set_key": "set1",
                 "name": "1st Serve Average Speed", "player1": "1", "player2": "1"})
    pd.DataFrame(rows).to_parquet(tmp_path / "keystats.parquet")
    k = S.key_stats().set_index("player_no")
    assert k.loc["1", "ks_spd1"] == 199 and k.loc["2", "ks_spd2"] == 165
    assert np.isnan(k.loc["2", "ks_max"])                     # 0 = not timed
    assert (k.loc["1", "ks_first_in"], k.loc["1", "ks_first_total"]) == (103, 191)
    assert k.loc["2", "ks_first_in"] == 113


def test_side_of():
    a1 = pd.Series([True, True, False, False, None])
    no = pd.Series([1, 2, 1, 2, 1])
    assert S.side_of(a1, no).tolist() == ["A", "B", "B", "A", None]


def test_mantd_draw_quarter_finals_are_main_draw():
    # every stadie_id in ManTennisData 2021-26; "QF" starts with "Q" but is not qualifying
    rounds = pd.Series(["Q1", "Q2", "Q3", "QF", "R128", "R64", "R32", "R16", "SF", "F", "RR", "BR", ""])
    assert S.mantd_draw(rounds).tolist() == ["qual"] * 3 + ["main"] * 10


def test_stats_url_key():
    m = S.STATS_URL.search("https://www.atptour.com/en/scores/stats-centre/archive/2025/2205/qs017")
    assert m.groups() == ("2025", "2205", "qs017")
