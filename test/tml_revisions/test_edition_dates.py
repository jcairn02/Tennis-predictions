"""The weekly check of Tennis My Life's edition dates (src/eda/tml_revisions/edition_dates.py): which verdicts count as
misdated, and that only an edition outside the known list raises the alarm. Synthetic frames only."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.tml_revisions import edition_dates as E  # noqa: E402


def frame():
    return pd.DataFrame({
        "edition": ["atp|2024-2847|Tenerife 1|20240121", "atp|2026-9001|Lima|20260601", "atp|2026-9002|Oeiras|20260608",
                    "atp|2026-9003|Biella|20260615", "atp|2026-9004|Maia|20261012"],
        "date_error": ["another week (early)", "another week (late)", "right",
                       "unresolved (another week (late) on fewer than 3 rows)", None]})


def test_only_the_another_week_verdicts_count_as_misdated():
    assert list(E.is_misdated(frame()["date_error"])) == [True, True, False, False, False]


def test_a_known_edition_raises_no_alarm_and_a_new_or_redated_one_does():
    ed = frame()
    known = {"atp|2024-2847|Tenerife 1|20240121"}
    assert list(E.new_misdated(ed, known)["edition"]) == ["atp|2026-9001|Lima|20260601"]
    # Tennis My Life re-dates a known edition to another wrong week: its key changes, so it is new again
    ed.loc[0, "edition"] = "atp|2024-2847|Tenerife 1|20240128"
    assert sorted(E.new_misdated(ed, known)["edition"]) == ["atp|2024-2847|Tenerife 1|20240128",
                                                            "atp|2026-9001|Lima|20260601"]
