"""The feed's alert on new "player in two main draws of one week" flags (src/eda/data_gaps_2026/two_draws.py): the flags
are the builder's player-weeks, and only a flag the baseline did not hold is new. Synthetic tables only."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.data_gaps_2026 import two_draws as D  # noqa: E402


def candidate(tmp: Path, rows: list[tuple], new: list[str]) -> Path:
    cols = ["match_id", "tournament_id", "tournament_name", "tournament_date", "round", "qualifying", "player_a_id",
            "player_b_id"]
    pd.DataFrame(rows, columns=cols).to_parquet(tmp / "stage0_matches.parquet", index=False)
    pd.DataFrame({"match_id": new}).to_parquet(tmp / "additions.parquet", index=False)
    return tmp


def test_flags_are_new_player_weeks_in_two_main_draws(tmp_path):
    rows = [("m1", "T1", "Montreux", "2026-09-07", "R32", False, "p1", "p2"),
            ("m2", "T2", "Guiyang", "2026-09-07", "R32", False, "p1", "p3"),     # p1 in two main draws that week
            ("m3", "T2", "Guiyang", "2026-09-07", "Q1", True, "p2", "p4"),      # qualifying: not a main draw
            ("m4", "T3", "Davis Cup", "2026-09-07", "RR", False, "p5", "p6"),   # round robin left out
            ("m5", "T4", "Old", "2026-06-15", "R32", False, "p7", "p8"),
            ("m6", "T5", "Old 2", "2026-06-15", "R32", False, "p7", "p9")]      # two draws, but no new match
    f = D.flags(candidate(tmp_path, rows, new=["m2", "m3", "m4"]))
    assert list(f["player_id"]) == ["p1"] and f["tournaments"].iloc[0] == "T1|T2"


def test_only_a_flag_the_baseline_lacks_is_new():
    base = pd.DataFrame({"player_id": ["p1"], "tournament_date": ["2026-06-15"], "tournaments": ["A|B"],
                         "names": ["x"]})
    cur = pd.DataFrame({"player_id": ["p1", "p2"], "tournament_date": ["2026-06-15", "2026-09-07"],
                        "tournaments": ["A|B", "C|D"], "names": ["x", "y"]})
    assert list(D.compare(cur, base)["player_id"]) == ["p2"]
    assert D.compare(base, base).empty
