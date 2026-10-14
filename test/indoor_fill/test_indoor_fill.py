"""Tests of the indoor rule (src/eda/indoor_fill/; docs/studies/indoor_fill/README.md), offline, on small made-up tables:

1. Each tour reads its sources in the decided order: the men Stage 0's flag, then tennis-data's Court (own row, then the
   event's rows), then the previous edition; the women the WTA's calendar, then tennis-data's Court, then the previous
   edition, then Stage 0's flag. The cases met in the data: Santiago (TML right, tennis-data wrong), the 2026 US Open
   (TML blank), Stuttgart (the WTA right, tennis-data wrong), Eastbourne (not in the WTA's calendar).
2. An event whose rows disagree gives no event value; the previous edition is an earlier one, never a later one.
3. A WTA edition is matched by TML's id when it is the WTA's, else by dates and name; Stage 0's name breaks a tie between
   editions in one city; nothing outside the dates or below the similarity floor is matched.
4. tennis-data rows are read by position only while their names are the ones Stage 1 recorded.
5. The frame builder's switch: --indoor-men-only gives the old input (men only), the default the rule.
6. The gate fails a live match whose indoor input is unknown.

Run: ./python.sh -m pytest test/indoor_fill -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.indoor_fill import status as ST  # noqa: E402


def stage0(rows: list[tuple]) -> pd.DataFrame:
    """(match_id, tour, year, tournament_id, tournament_name, date, indoor) -> Stage 0 rows."""
    m = pd.DataFrame(rows, columns=["match_id", "tour", "year", "tournament_id", "tournament_name", "tournament_date",
                                    "indoor"])
    m["level"] = "T250"
    m["tournament_date"] = pd.to_datetime(m["tournament_date"])
    m["indoor"] = m["indoor"].astype("boolean")
    return m[ST.MATCH_COLS]


def editions(rows: list[tuple]):
    """(id, title, city, start, end, I/O) -> a function of years, as status.rule takes the WTA's calendar."""
    e = pd.DataFrame(rows, columns=["tournament_id", "title", "city", "start", "end", "in_outdoor"])
    e["start"], e["end"] = pd.to_datetime(e["start"]), pd.to_datetime(e["end"])
    e["flag"] = e["in_outdoor"].map({"I": 1.0, "O": 0.0})
    return lambda years: e


def court(d: dict) -> pd.Series:
    return pd.Series(d, dtype="float64")


def by_id(out: pd.DataFrame) -> pd.DataFrame:
    return out.set_index("match_id")


# ------------------------------------------------------------------------------------------------ 1. the order

def test_men_read_stage0_first_then_court_then_previous_edition():
    m = stage0([
        ("santiago", "atp", 2024, "2024-8996", "Santiago", "2024-02-26", False),   # TML outdoor, tennis-data indoor
        ("uso25", "atp", 2025, "2025-560", "US Open", "2025-08-25", False),
        ("uso26", "atp", 2026, "2026-560", "US Open", "2026-08-31", pd.NA),        # TML blank
        ("uso26_live", "atp", 2026, "2026-560", "US Open", "2026-08-31", pd.NA),   # live: no tennis-data row
        ("new_live", "atp", 2026, "2026-9999", "Newtown", "2026-10-05", pd.NA),    # no source at all
    ])
    out = by_id(ST.rule(m, court({"santiago": 1.0, "uso26": 0.0}), pd.Series(dtype=object), None))
    assert (out.loc["santiago", "indoor"], out.loc["santiago", "source"]) == (0.0, "stage0")
    assert (out.loc["uso26", "indoor"], out.loc["uso26", "source"]) == (0.0, "own")
    assert (out.loc["uso26_live", "indoor"], out.loc["uso26_live", "source"]) == (0.0, "event")
    assert np.isnan(out.loc["new_live", "indoor"]) and out.loc["new_live", "source"] == "none"
    # the event's own rows not yet published: the previous edition (2025, TML outdoor)
    out = by_id(ST.rule(m, court({"santiago": 1.0}), pd.Series(dtype=object), None))
    assert (out.loc["uso26_live", "indoor"], out.loc["uso26_live", "source"]) == (0.0, "previous")


def test_women_read_the_wta_calendar_first_then_court_then_previous_then_stage0():
    m = stage0([
        ("stutt", "wta", 2016, "2016-1051", "Stuttgart", "2016-04-18", pd.NA),     # tennis-data outdoor, WTA indoor
        ("eastb", "wta", 2016, "2016-710", "Eastbourne", "2016-06-20", pd.NA),     # not in the WTA's calendar
        ("eastb_live", "wta", 2017, "2017-710", "Eastbourne", "2017-06-26", pd.NA),
        ("tml_only", "wta", 2026, "2026-5555", "Nowhere", "2026-03-02", True),
        ("nothing", "wta", 2026, "2026-6666", "Elsewhere", "2026-03-09", pd.NA),
    ])
    cal = editions([("1051", "Porsche Tennis Grand Prix - Stuttgart, Germany", "STUTTGART", "2016-04-18",
                     "2016-04-24", "I")])
    out = by_id(ST.rule(m, court({"stutt": 0.0, "eastb": 0.0}), pd.Series({"stutt": "Stuttgart"}), cal))
    assert (out.loc["stutt", "indoor"], out.loc["stutt", "source"]) == (1.0, "calendar")
    assert out.loc["stutt", "wta_how"] == "id"
    assert (out.loc["eastb", "indoor"], out.loc["eastb", "source"]) == (0.0, "own")
    assert (out.loc["eastb_live", "indoor"], out.loc["eastb_live", "source"]) == (0.0, "previous")
    assert (out.loc["tml_only", "indoor"], out.loc["tml_only", "source"]) == (1.0, "stage0")
    assert np.isnan(out.loc["nothing", "indoor"]) and out.loc["nothing", "source"] == "none"


def test_without_the_calendar_step_the_women_read_court():
    m = stage0([("stutt", "wta", 2016, "2016-1051", "Stuttgart", "2016-04-18", pd.NA)])
    out = by_id(ST.rule(m, court({"stutt": 0.0}), pd.Series(dtype=object), None))
    assert (out.loc["stutt", "indoor"], out.loc["stutt", "source"]) == (0.0, "own")


# ------------------------------------------------------------------------------------------------ 2. events and editions

def test_an_event_whose_rows_disagree_gives_no_event_value():
    m = stage0([("a", "atp", 2020, "2020-1", "X", "2020-02-03", pd.NA), ("b", "atp", 2020, "2020-1", "X", "2020-02-03", pd.NA),
                ("live", "atp", 2020, "2020-1", "X", "2020-02-03", pd.NA)])
    out = by_id(ST.rule(m, court({"a": 1.0, "b": 0.0}), pd.Series(dtype=object), None))
    assert out.loc["a", "indoor"] == 1.0 and out.loc["b", "indoor"] == 0.0
    assert np.isnan(out.loc["live", "event"]) and np.isnan(out.loc["live", "indoor"])


def test_the_previous_edition_is_never_a_later_one():
    m = stage0([("y20", "atp", 2020, "2020-7", "X", "2020-02-03", pd.NA),
                ("y22", "atp", 2022, "2022-7", "X", "2022-02-07", True),
                ("y21_live", "atp", 2021, "2021-7", "X", "2021-02-01", pd.NA),
                ("y23_live", "atp", 2023, "2023-7", "X", "2023-02-06", pd.NA)])
    out = by_id(ST.rule(m, court({"y20": 0.0}), pd.Series(dtype=object), None))
    assert out.loc["y21_live", "indoor"] == 0.0                 # 2020's, not 2022's
    assert out.loc["y23_live", "indoor"] == 1.0                 # the latest earlier one: 2022


def test_edition_series_drops_the_year():
    s = ST.edition_series(pd.Series(["wta", "wta", "atp"]),
                          pd.Series(["2013-W-PR-GER-1A-2013", "2026-1051", "2019-0339"]))
    assert s.tolist() == ["wta|W-PR-GER-1A", "wta|1051", "atp|0339"]


# ------------------------------------------------------------------------------------------------ 3. matching editions

def events(rows):
    e = pd.DataFrame(rows, columns=["tournament_id", "date", "name", "location"])
    e["date"] = pd.to_datetime(e["date"])
    return e


def test_match_by_id_when_tml_uses_the_wta_id():
    cal = editions([("1111", "The HSBC Championships - London, GBR", "LONDON", "2026-06-08", "2026-06-14", "O"),
                    ("2012", "Berlin Tennis Open - Berlin, GER", "BERLIN", "2026-06-08", "2026-06-14", "O")])(None)
    got = ST.match_editions(events([("2026-1111", "2026-06-08", "Queen's Club", None)]), cal)
    assert got.loc[0, "wta_id"] == "1111" and got.loc[0, "wta_how"] == "id"


def test_match_by_name_and_tie_broken_by_stage0_name():
    cal = editions([("a", "Yarra Valley Classic - Melbourne, Australia", "MELBOURNE", "2021-01-31", "2021-02-06", "O"),
                    ("b", "Gippsland Trophy - Melbourne, Australia", "MELBOURNE", "2021-01-31", "2021-02-06", "I")])(None)
    got = ST.match_editions(events([("2021-W-X", "2021-01-31", "Gippsland Trophy", "Melbourne")]), cal)
    assert got.loc[0, "wta_id"] == "b" and got.loc[0, "wta_how"] == "name"


def test_no_match_outside_the_dates_or_below_the_floor():
    cal = editions([("1", "Porsche Tennis Grand Prix - Stuttgart, Germany", "STUTTGART", "2016-04-18", "2016-04-24",
                     "I")])(None)
    far = ST.match_editions(events([("2016-W-X", "2016-05-02", "Stuttgart", None)]), cal)
    other = ST.match_editions(events([("2016-W-X", "2016-04-18", "Charleston", None)]), cal)
    assert far.loc[0, "wta_id"] is None and np.isnan(far.loc[0, "calendar"])
    assert other.loc[0, "wta_id"] is None


def test_court_flag_and_similarity():
    assert ST.court_flag(["Indoor", " outdoor ", "Clay", None]).tolist()[:2] == [1.0, 0.0]
    assert ST.court_flag(["Clay", None]).isna().all()
    assert ST.similarity("'s-Hertogenbosch", "S-HERTOGENBOSCH") == 1.0
    assert ST.similarity("Us Open", "US Open - New York, NY, USA") == 1.0
    assert ST.similarity("Rome", "Romania Open") < 1.0                 # no containment below four letters
    assert ST.similarity("", "anything") == 0.0


# ------------------------------------------------------------------------------------------------ 4. reading tennis-data rows

def test_td_fields_reads_by_position_only_while_the_names_match(tmp_path, monkeypatch):
    part = tmp_path / "2026.parquet"
    pd.DataFrame({"Winner": ["A X.", "C Z."], "Loser": ["B Y.", "D W."], "Court": ["Indoor", "Outdoor"]}).to_parquet(part)
    s1 = tmp_path / "stage1_odds.parquet"
    links = pd.DataFrame({"match_id": ["m1", "m2"], "td_file": [str(part)] * 2, "td_row": [1, 0],
                          "td_winner": ["C Z.", "A X."], "td_loser": ["D W.", "B Y."]})
    links.to_parquet(s1)
    monkeypatch.setattr(ST, "STAGE1", s1)
    got = ST.td_fields(["m1", "m2"], ["Court"])
    assert got.loc["m1", "Court"] == "Outdoor" and got.loc["m2", "Court"] == "Indoor"
    links.assign(td_row=[0, 1]).to_parquet(s1)                        # the rows moved: refused
    with pytest.raises(RuntimeError, match="other players"):
        ST.td_fields(["m1", "m2"], ["Court"])
    links.assign(td_row=[5, 0]).to_parquet(s1)
    with pytest.raises(RuntimeError, match="rebuild Stage 1"):
        ST.td_fields(["m1", "m2"], ["Court"])


# ------------------------------------------------------------------------------------------------ 5. the frame builder

def test_frame_builder_switch(tmp_path, monkeypatch):
    from src.eda.tabpfn_thinking import build_frame as BF
    f = pd.DataFrame({"match_id": ["m", "w"], "tour": ["atp", "wta"], "group": ["T250", "T250"]})
    m = pd.DataFrame({"indoor": pd.array([True, True], dtype="boolean")})
    old, src_old, info = BF.indoor_codes(f, m, men_only=True)
    assert old[0] == 1.0 and np.isnan(old[1]) and info["rule"].startswith("men only")
    s1 = tmp_path / "stage1.parquet"
    pd.DataFrame({"x": [1]}).to_parquet(s1)
    monkeypatch.setattr(BF.IF, "STAGE1", s1)
    monkeypatch.setattr(BF.IF, "for_matches", lambda ids: (np.array([1.0, 0.0]), pd.Series(["stage0", "calendar"])))
    new, src_new, info = BF.indoor_codes(f, m, men_only=False)
    assert new.tolist() == [1.0, 0.0] and src_new.tolist() == ["stage0", "calendar"]
    assert info["main_tour_rows_unknown"] == 0


# ------------------------------------------------------------------------------------------------ 6. the gate

def test_gate_fails_a_live_match_with_unknown_indoor(tmp_path):
    from src.eda.prediction_run import gate as G
    pd.DataFrame({"match_id": ["ok", "dark"], "in_indoor": [0.0, np.nan]}).to_parquet(tmp_path / "live_frame.parquet")
    table = pd.DataFrame({"match_id": ["ok", "dark", "box"], "complete": [True, True, False],
                          "reason": ["", "", "1 earlier match(es) without a box score"]})
    out = G.with_indoor(table, G.indoor_unknown(tmp_path))
    assert out["complete"].tolist() == [True, False, False]
    assert "indoor or outdoor unknown" in out.loc[1, "reason"]
    assert out.loc[2, "reason"] == "1 earlier match(es) without a box score"
    assert G.indoor_unknown(tmp_path / "nowhere") == set()
