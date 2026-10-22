"""The fast-court member's surface IOS in live runs (live_members.ios_table, frame_check; 16 Oct 2026).

The bug: live_members read the registered build's surface-IOS extract, pinned to the 10 Oct instance's table. A match
not played by then is never in it, so the venue member was missing for every live match. These tests rebuild that
situation on small tables: the panel the registered builders read gets no ace rating for an unplayed match from the
instance's table alone, and gets the run's own ratings once they are laid over it.
Run: ./python.sh -m pytest test/unpriced_leads/test_live_ios.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import live_members as LM  # noqa: E402
from src.eda.unpriced_leads import rebuild_pool as RP  # noqa: E402

OLD, LIVE = "atp|2026-0001-20260105|R16|atp:1|atp:2", "atp|2026-5014-20261007|QF|atp:3|atp:4"
IOS_COLS = RP.INSTANCE["ios"]["cols"][1:]


def instance_table(path: Path) -> Path:
    """An instance table that reached OLD only (as the 13 Oct extract reached nothing after its tables)."""
    t = pd.DataFrame({"match_id": [OLD]})
    for i, c in enumerate(IOS_COLS):
        t[c] = 0.1 * (i + 1)
    t.to_parquet(path, index=False)
    return path


def ace_rows(path: Path, rows: list[tuple]) -> Path:
    pd.DataFrame(rows, columns=["match_id", "side", "srf_O_eff_ace", "srf_D_eff_ace"]).to_parquet(path, index=False)
    return path


def test_unplayed_match_is_only_in_the_runs_ratings(tmp_path):
    inst = instance_table(tmp_path / "inst.parquet")
    old = LM.ios_table(inst, None, tmp_path / "old.parquet")                  # the table before the fix
    assert old["matches"] == 1 and LIVE not in set(pd.read_parquet(tmp_path / "old.parquet")["match_id"])
    rows = ace_rows(tmp_path / "ace.parquet", [(LIVE, "A", 0.9, -0.2), (LIVE, "B", 0.4, 0.1)])
    rec = LM.ios_table(inst, rows, tmp_path / "new.parquet")
    t = pd.read_parquet(tmp_path / "new.parquet").set_index("match_id")
    assert rec["added"] == 1 and rec["replaced"] == 0
    assert t.loc[LIVE, ["srf_O_eff_ace_a", "srf_O_eff_ace_b", "srf_D_eff_ace_a", "srf_D_eff_ace_b"]].tolist() == \
        [0.9, 0.4, -0.2, 0.1]
    assert np.isnan(t.loc[LIVE, "srf_O_eff_spw_a"])                         # only the ace columns come from the run
    assert t.loc[OLD, IOS_COLS].tolist() == pd.read_parquet(inst).set_index("match_id").loc[OLD, IOS_COLS].tolist()


def test_runs_ratings_win_where_both_hold_a_match(tmp_path):
    inst = instance_table(tmp_path / "inst.parquet")
    before = pd.read_parquet(inst).set_index("match_id").loc[OLD]
    rows = ace_rows(tmp_path / "ace.parquet", [(OLD, "A", 0.55, np.nan), (OLD, "B", 0.25, -0.05)])
    rec = LM.ios_table(inst, rows, tmp_path / "new.parquet")
    t = pd.read_parquet(tmp_path / "new.parquet").set_index("match_id").loc[OLD]
    assert rec["replaced"] == 1 and rec["added"] == 0
    assert t["srf_O_eff_ace_a"] == 0.55 and t["srf_O_eff_ace_b"] == 0.25 and t["srf_D_eff_ace_b"] == -0.05
    assert t["srf_D_eff_ace_a"] == before["srf_D_eff_ace_a"]                # no rating from the run: the table's stays
    assert t["srf_O_eff_spw_a"] == before["srf_O_eff_spw_a"]
    assert rec["replaced_max_abs_change"] == pytest.approx(max(abs(0.55 - before["srf_O_eff_ace_a"]),
                                                               abs(0.25 - before["srf_O_eff_ace_b"]),
                                                               abs(-0.05 - before["srf_D_eff_ace_b"])))


def test_ace_rows_must_be_one_per_match_and_side(tmp_path):
    inst = instance_table(tmp_path / "inst.parquet")
    rows = ace_rows(tmp_path / "ace.parquet", [(LIVE, "A", 0.9, -0.2), (LIVE, "A", 0.8, -0.2)])
    with pytest.raises(RuntimeError, match="one row per match"):
        LM.ios_table(inst, rows, tmp_path / "new.parquet")


def small_tables(tmp_path: Path, ios: Path) -> tuple[RP.Tables, pd.DataFrame]:
    """Stage 0, its players and the clock for OLD and LIVE, as the panel reads them."""
    m = pd.DataFrame({"match_id": [OLD, LIVE], "tournament_id": ["2026-0001", "2026-5014"],
                      "tournament_name": ["Somewhere", "Shanghai"], "round": ["R16", "QF"], "level": ["T250", "T1000"],
                      "best_of": [3, 3], "indoor": [False, False], "surface": ["Hard", "Hard"], "draw_size": [32, 96],
                      "player_a_id": ["atp:1", "atp:3"], "player_b_id": ["atp:2", "atp:4"]})
    p = pd.DataFrame([{"match_id": mid, "side": s, "rank": 10.0, "rank_points": 1000.0, "seed": np.nan, "entry": None,
                       "age": 25.0, "height": 185.0, "hand": "R", "country": "XXX"}
                      for mid in (OLD, LIVE) for s in ("A", "B")])
    t = pd.DataFrame({"match_id": [OLD, LIVE], "es": [20460.0, 20742.0], "lf": [20461.0, 20743.0],
                      "exact": [False, False]})
    for name, df in (("m", m), ("p", p), ("t", t)):
        df.to_parquet(tmp_path / f"{name}.parquet", index=False)
    T = RP.Tables("test", "small tables", str(tmp_path / "m.parquet"), str(tmp_path / "p.parquet"),
                  str(tmp_path / "t.parquet"), "", str(ios), "instance", "current")
    keys = pd.DataFrame({"match_id": [OLD, LIVE], "tour": ["atp", "atp"], "season": [2026, 2026],
                         "tournament_date": pd.to_datetime(["2026-01-05", "2026-10-07"]), "debut_season": [False, False]})
    return T, keys


def test_panel_gets_the_live_matchs_ace_gap_only_from_the_runs_table(tmp_path):
    inst = instance_table(tmp_path / "inst.parquet")
    LM.ios_table(inst, None, tmp_path / "old.parquet")
    T, keys = small_tables(tmp_path, tmp_path / "old.parquet")
    P = RP.panel(T, keys).set_index("match_id")
    assert np.isnan(P.loc[LIVE, "ios_srfO_ace_a"]) and np.isnan(P.loc[LIVE, "ios_srfO_ace_b"])   # the bug
    rows = ace_rows(tmp_path / "ace.parquet", [(LIVE, "A", 0.9, -0.2), (LIVE, "B", 0.4, 0.1)])
    LM.ios_table(inst, rows, tmp_path / "new.parquet")
    T, keys = small_tables(tmp_path, tmp_path / "new.parquet")
    P = RP.panel(T, keys)
    gap = P["ios_srfO_ace_a"].to_numpy(float) - P["ios_srfO_ace_b"].to_numpy(float)
    assert gap[1] == 0.9 - 0.4
    frame = tmp_path / "frame.parquet"
    pd.DataFrame({"match_id": [OLD, LIVE], "in_iosO_ace": [0.1 - 0.2, 0.9 - 0.4]}).to_parquet(frame, index=False)
    rec = LM.frame_check(frame, P["match_id"].to_numpy(str), gap)
    assert rec["equal"] == 2 and rec["max_abs_diff"] == 0.0


def test_frame_check_refuses_a_gap_the_run_did_not_make(tmp_path):
    frame = tmp_path / "frame.parquet"
    pd.DataFrame({"match_id": [OLD, LIVE], "in_iosO_ace": [0.1, 0.5]}).to_parquet(frame, index=False)
    ids = np.array([OLD, LIVE])
    with pytest.raises(RuntimeError, match="differs"):
        LM.frame_check(frame, ids, np.array([0.1, np.nan]))                 # the live match read no rating
    with pytest.raises(RuntimeError, match="differs"):
        LM.frame_check(frame, ids, np.array([0.1, 0.5 + 1e-9]))             # another table's rating
    assert LM.frame_check(frame, ids, np.array([0.1, 0.5]))["equal"] == 2
