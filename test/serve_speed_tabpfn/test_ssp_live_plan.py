"""Offline tests of the daily collector's plan (live/atp_daily.py: each code once, every main draw first, a group staged
in full asking only its codes not complete, held matches keyed by season) and of a day's staging file kept across runs
(staging.add, speed_daily.collector). The faults of 24 Oct 2026 they pin are in the master pipeline's process log, Part
16. No request is sent; no real staging file is written."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.live import atp_daily as AD  # noqa: E402
from src.eda.serve_speed_tabpfn.live import common as LC  # noqa: E402
from src.eda.serve_speed_tabpfn.live import staging as ST  # noqa: E402
from src.ingest import speed_daily as SD  # noqa: E402

KEYS = ["year", "event_id", "match_code"]


def rounds(*pairs) -> pd.DataFrame:
    return pd.DataFrame([{"event_id": e, "round": r} for e, r in pairs])


def test_each_code_once_and_every_main_draw_first():
    """24 Oct 2026: each qualifying number was asked once per qualifying round (QS047 for Q1, then for Q2: one
    address), and Almaty's main draw sorted after Lyon's qualifying numbers, past the run's budget."""
    plan = AD.daily_plan(2026, rounds(("496", "Q1"), ("496", "Q2"), ("496", "QF"), ("9410", "QF"), ("9410", "R16")))
    codes = [(e, c) for _, e, c, _ in plan]
    assert len(codes) == len(set(codes)) == 4 + 4 + 8 + 63
    main = [x for x in codes if x[1].startswith("MS")]
    assert codes[:len(main)] == main and {e for e, _ in main} == {"496", "9410"}
    assert {r for _, _, c, r in plan if c.startswith("QS")} == {"Q2"}      # the latest qualifying round names them


def test_a_group_staged_in_full_asks_only_its_codes_not_complete():
    """Lyon's qualifying 2026: Tennis My Life lists 12 matches and the ATP numbers them QS004-QS015. Once 12 codes are
    staged, only the staged ones not complete are asked again, not the 51 numbers no match carries."""
    staged = {(2026, "496", f"QS{n:03d}") for n in range(4, 16)}
    held = staged - {(2026, "496", c) for c in ("QS004", "QS013", "QS015")}
    two = rounds(("496", "Q1"), ("496", "Q2"))
    plan = AD.daily_plan(2026, two, held, staged, {(2026, "496", AD.QUAL): 12})
    assert [c for _, _, c, _ in plan] == ["QS004", "QS013", "QS015"]
    # one match more listed than staged (a round played since): every number not held complete is asked
    assert len(AD.daily_plan(2026, two, held, staged, {(2026, "496", AD.QUAL): 13})) == 63 - 9
    # no count known: as before, every number not held complete
    assert len(AD.daily_plan(2026, two, held, staged)) == 63 - 9
    # a main-draw round of 12 matches (four byes) staged in full: the byes' codes are not asked
    r32 = {(2026, "496", f"MS{n:03d}") for n in range(16, 28)}
    assert AD.daily_plan(2026, rounds(("496", "R32")), r32, r32, {(2026, "496", "R32"): 12}) == []
    assert len(AD.daily_plan(2026, rounds(("496", "R32")), r32, r32, {(2026, "496", "R32"): 13})) == 4


def test_held_matches_are_keyed_by_season():
    """An event's codes recur each season: 2026's final held complete does not hold 2027's."""
    held = {(2026, "5014", "MS001")}
    assert AD.daily_plan(2027, rounds(("5014", "F")), held) == [(2027, "5014", "MS001", "F")]
    assert AD.daily_plan(2026, rounds(("5014", "F")), held) == []


def test_the_window_and_the_counts_read_the_same_rows():
    """played_rounds keeps the window's days; listed_matches counts every day up to its end, an event's qualifying
    rounds as one group, rounds without codes left out."""
    played = pd.DataFrame({"year": [2026] * 6, "event_id": ["496"] * 6, "round": ["Q1", "Q1", "Q2", "R32", "R32", "RR"],
                           "d_day": [100, 100, 101, 105, 108, 108]})
    pr = AD.played_rounds(105, 108, played)
    assert pr.to_dict("records") == [{"year": 2026, "event_id": "496", "round": "R32", "matches": 2},
                                     {"year": 2026, "event_id": "496", "round": "RR", "matches": 1}]
    assert AD.listed_matches(played) == {(2026, "496", AD.QUAL): 3, (2026, "496", "R32"): 2}


def test_plan_days_counts_a_group_over_days_before_the_window(monkeypatch):
    """Lyon's qualifying staged in full asks nothing when its last round is in the window and its first before it;
    the semi-finals of the window's last day are asked."""
    played = pd.DataFrame({"year": [2026] * 14, "event_id": ["496"] * 14,
                           "round": ["Q1"] * 8 + ["Q2"] * 4 + ["SF"] * 2, "d_day": [10] * 8 + [11] * 4 + [16] * 2})
    staged = {(2026, "496", f"QS{n:03d}") for n in range(4, 16)}
    monkeypatch.setattr(AD, "tml_played", lambda day_from, day_to: played)
    monkeypatch.setattr(AD, "held_codes", lambda: (staged, staged))
    assert AD.plan_days(11, 16) == [(2026, "496", "MS002", "SF"), (2026, "496", "MS003", "SF")]


def test_add_keeps_a_days_earlier_rows_and_the_newer_copy(tmp_path):
    """24 Oct 2026: the 07:30 task's run wrote only what it fetched over the notebook's run of ten minutes before."""
    def rows(*items):
        return ST.to_frame([{"year": 2026, "event_id": "496", "match_code": c, "p1_spd1": v, "match_completed": done,
                             "source": AD.SOURCE} for c, v, done in items])
    ST.add(rows(("MS005", 190.0, True), ("MS004", 180.0, False)), "atp_daily_2026-10-24", KEYS, tmp_path)
    ST.add(rows(("MS004", 191.0, True)), "atp_daily_2026-10-24", KEYS, tmp_path)
    day = pd.read_parquet(tmp_path / "atp_daily_2026-10-24.parquet").set_index("match_code")
    assert sorted(day.index) == ["MS004", "MS005"]
    assert day.loc["MS004", "p1_spd1"] == 191.0 and bool(day.loc["MS004", "match_completed"])
    assert day.loc["MS005", "p1_spd1"] == 190.0


def test_a_second_run_on_the_same_day_adds_to_the_first(tmp_path, monkeypatch):
    """The collector end to end without network (the plan, the fetch and the decryption stood in): the second run of a
    day keeps the first run's matches in the day's file."""
    found = iter([["MS005", "MS006"], ["MS004"]])
    plan = [(2026, "496", c, "QF") for c in ("MS004", "MS005", "MS006")]
    monkeypatch.setattr(AD, "plan_days", lambda day_from, day_to: plan)
    monkeypatch.setattr(AD, "enabled", lambda cfg=None: True)
    monkeypatch.setattr(AD, "fetch_daily", lambda day, plan, max_requests: {"files": []})

    def stage(paths, collected_on, rounds):
        return ST.to_frame([{"year": 2026, "event_id": "496", "match_code": c, "round": rounds[("496", c)],
                             "match_completed": True, "source": AD.SOURCE, "collected_on": collected_on}
                            for c in next(found)])
    monkeypatch.setattr(AD, "decrypt_and_stage", stage)
    for n in (2, 1):
        assert SD.collector(LC.day_of("2026-10-24"), tmp_path, 7, 200, False)["staged"] == n
    day = pd.read_parquet(tmp_path / "atp_daily_2026-10-24.parquet")
    assert sorted(day["match_code"]) == ["MS004", "MS005", "MS006"] and set(day["round"]) == {"QF"}
