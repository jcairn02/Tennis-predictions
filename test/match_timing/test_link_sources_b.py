"""Match timing, sources B (src/eda/match_timing/link_sources_b.py and its srcb_* helpers).

Synthetic tests of the pieces the links rest on: name keys, round labels, set scores, the expected
span, the one-to-one choice between candidates, Tennis My Life's day-level test, the Match Charting
clock and the Infosys match numbers. The last tests read the written links where they exist.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.match_timing import srcb_common as X  # noqa: E402
from src.eda.match_timing import srcb_sources as SRC  # noqa: E402
from src.eda.match_timing import srcb_tz as TZ  # noqa: E402

LINKS = X.OUT


# ------------------------------------------------------------------------------------------------
# names

def test_abbreviated_names_meet_full_name_variants():
    assert X.abbr_short("O. Otte") in X.abbr_variants("Oscar Otte")
    assert X.abbr_short("J. M. Del Potro") in X.abbr_variants("Juan Martin Del Potro")
    assert X.abbr_short("J.M. Del Potro") == X.abbr_short("J. M. Del Potro")
    assert X.abbr_short("P. Carreno-Busta") in X.abbr_variants("Pablo Carreno Busta")
    assert X.abbr_short("Otte O.") == "A:otte o"
    assert X.abbr_short("C. O'Connell") in X.abbr_variants("Christopher Oconnell")
    assert X.abbr_short("Roger Federer") == ""          # not abbreviated


def test_full_keys_ignore_order_accents_and_apostrophes():
    assert X.full_key("Zhizhen Zhang") == X.full_key("Zhang Zhizhen")
    assert X.full_key("Tomás Martín Etcheverry") == X.full_key("Tomas Martin Etcheverry")
    assert X.full_key("Christopher O'Connell") == X.full_key("Christopher Oconnell")
    assert X.full_key("Federer") == ""                  # one word is not a key
    assert "A:sun q" in X.abbr_from_full("Sun Qian")    # surname first
    assert X.share_word("Barbora Zahlavova Strycova", "Barbora Strycova")
    assert not X.share_word("Roberto Cid", "Marc Andrea Huesler")


# ------------------------------------------------------------------------------------------------
# rounds and scores

@pytest.mark.parametrize("label,qual,spec", [
    ("ATP Miami - 1/16-finals", False, "R32"), ("Canberra - Semi-finals", None, "SF|QREL1"),
    ("Alicante - Final", True, "QREL0"), ("Qualification Round 1", False, "Q1"), ("Qualifications", None, "Q"),
    ("Round of 32", None, "R32"), ("Match for 3rd place", False, "BR"), ("", None, ""), ("", True, "Q")])
def test_round_spec(label, qual, spec):
    assert X.round_spec(label, qual) == spec


def test_round_agreement():
    assert X.round_agree("F|QREL0", "Q3", True, 0) == 2      # a qualifying final read as the last round
    assert X.round_agree("F|QREL0", "F", False, None) == 2
    assert X.round_agree("SF|QREL1", "Q1", True, 0) == 0
    assert X.round_agree("Q", "Q2", True, 0) == 1           # some qualifying round
    assert X.round_agree("Q", "R32", False, None) == 0
    assert X.round_agree("QF|RR?", "RR", False, None) == 1  # a match number cannot be read in a round robin
    assert X.round_agree("", "R32", False, None) == 1


def test_set_scores():
    assert X.sets_agree(((6, 4), (3, 6), (7, 5)), ((4, 6), (6, 3), (5, 7))) == 2    # the loser's reading
    assert X.sets_agree(((6, 2), (6, 2), (0, 0), (0, 0), (0, 0)), ((6, 2), (6, 2))) == 2  # api-tennis padding
    assert X.sets_agree(((6, 4),), ((6, 4), (6, 0))) == 1   # cut short: neither confirms nor contradicts
    assert X.sets_agree((), ((6, 1),)) == 1
    assert X.sets_agree(((6, 1), (6, 1)), ((6, 2), (6, 1))) == 0
    assert X.sets_of_score("6-7(4) 7-6(5) [10-8]") == ((6, 7), (7, 6))
    assert SRC.api_sets('[{"score_first": "6.4", "score_second": "7.7", "score_set": "1"}]') == ((6, 7),)


def test_expected_span_is_round_aware():
    gap = np.array([-1, -1, 0, 1, -6, 3, 10])
    qual = np.array([False, False, False, False, True, True, False])
    late = np.array([False, True, True, True, False, False, False])
    end = np.array([9, 9, 9, 9, 9, 9, 9])
    assert X.expected(gap, qual, late, end).tolist() == [True, False, False, True, True, False, False]


# ------------------------------------------------------------------------------------------------
# the linker on a toy table

def toy_stage0():
    rows = [  # the same pair in the quarter-finals of two events a week apart
        ("atp|E1|QF|a|b", "atp", "QF", False, "2024-08-05", "Andrey Rublev", "Jannik Sinner", "6-3 1-6 6-2"),
        ("atp|E2|QF|a|b", "atp", "QF", False, "2024-08-12", "Andrey Rublev", "Jannik Sinner", "4-6 7-5 6-4"),
        ("atp|E3|R32|c|d", "atp", "R32", False, "2024-08-12", "Carlos Alcaraz", "Gael Monfils", "4-6 7-6(5) 6-4"),
    ]
    s0 = pd.DataFrame(rows, columns=["match_id", "tour", "round", "qualifying", "tournament_date", "a_name", "b_name", "score"])
    s0["tdate"] = pd.to_datetime(s0["tournament_date"])
    s0["sets"] = s0["score"].map(X.sets_of_score)
    s0["qrel"] = np.nan
    s0["end_days"] = 14
    s0["player_a_id"] = ["atp:1", "atp:1", "atp:3"]
    s0["player_b_id"] = ["atp:2", "atp:2", "atp:4"]
    return s0


def toy_source(rows):
    src = pd.DataFrame(rows, columns=["source_key", "date", "name1", "name2", "sets", "rspec"])
    src["tour"] = "atp"
    src["date"] = pd.to_datetime(src["date"])
    src["a1"], src["a2"] = src["name1"].map(lambda n: (X.abbr_short(n),)), src["name2"].map(lambda n: (X.abbr_short(n),))
    return src


def run(src, s0):
    L = X.Linker("toy", src, s0, s0.index)
    sl = X.src_long_from(src, a1="a1", a2="a2")
    L.pair_pass("names", sl, ["A"], s0_long_=X.s0_long(s0, s0.index))
    return L


def test_scores_pick_the_right_week():
    # dated the day before the second event: the nearest week alone would take E2
    src = toy_source([("x", "2024-08-11", "J. Sinner", "A. Rublev", ((3, 6), (6, 1), (2, 6), (0, 0)), "QF")])
    lk = run(src, toy_stage0()).result()
    assert lk["li"].tolist() == [0]


def test_round_aware_span_without_scores():
    # no score: a quarter-final cannot be the day before E2 starts, so E1 (day 6) is taken
    src = toy_source([("x", "2024-08-11", "J. Sinner", "A. Rublev", (), "QF")])
    lk = run(src, toy_stage0()).result()
    assert lk["li"].tolist() == [0]


def test_ties_are_ambiguous_and_matches_taken_once():
    s0 = toy_stage0()
    s0.loc[1, "tdate"] = s0.loc[0, "tdate"]           # two identical candidates
    s0.at[1, "score"] = s0.at[0, "score"]
    s0["sets"] = s0["score"].map(X.sets_of_score)
    src = toy_source([("x", "2024-08-09", "J. Sinner", "A. Rublev", (), "QF")])
    L = run(src, s0)
    assert L.result().empty and list(L.ambiguous) == [0]
    src2 = toy_source([("x", "2024-08-14", "C. Alcaraz", "G. Monfils", ((4, 6), (7, 6), (6, 4)), "R32"),
                       ("y", "2024-08-13", "C. Alcaraz", "G. Monfils", (), "R32")])
    L2 = run(src2, toy_stage0())
    assert L2.result()["ri"].tolist() == [0] and list(L2.lost) == [1]   # identical scores keep the match


# ------------------------------------------------------------------------------------------------
# sources

def test_tml_day_level_test():
    rows = []
    for r, d, n in (("R32", "2026-01-12", 8), ("R32", "2026-01-13", 8), ("R16", "2026-01-14", 8), ("QF", "2026-01-15", 4),
                    ("SF", "2026-01-16", 2), ("F", "2026-01-17", 1)):
        rows += [("day", r, d)] * n
    for r, n in (("R32", 16), ("R16", 8), ("QF", 4)):        # two blocks: early rounds on one day
        rows += [("block", r, "2019-07-27")] * n
    rows += [("block", "SF", "2019-07-29")] * 2 + [("block", "F", "2019-07-29")]
    rows += [("one", "R32", "2024-03-04")] * 16 + [("one", "F", "2024-03-04")]
    for r, d, n in (("R64", "2026-03-30", 16), ("R32", "2026-03-31", 16), ("R16", "2026-04-01", 8), ("QF", "2026-04-03", 4),
                    ("SF", "2026-04-04", 2), ("F", "2026-04-05", 1)):   # one date per round, not per match
        rows += [("round", r, d)] * n
    rows += [("tie", "RR", "2026-09-18")] * 2 + [("tie", "RR", "2026-09-19")] * 2   # Davis Cup rubbers by day
    t = pd.DataFrame(rows, columns=["event", "round", "tourney_date"])
    t["d"] = pd.to_datetime(t["tourney_date"])
    ev = SRC.day_level_events(t)
    assert ev["day_level"].to_dict() == {"block": False, "day": True, "one": False, "round": False, "tie": True}


def test_mcp_clock_and_infosys_rounds():
    assert SRC.mcp_clock("3pm") == (15, 0) and SRC.mcp_clock("11:10 AM") == (11, 10)
    assert SRC.mcp_clock("15:00") == (15, 0) and SRC.mcp_clock("7:00") is None and SRC.mcp_clock("Night") is None
    assert [SRC.infosys_round(c) for c in ("MS001", "MS003", "MS004", "MS016", "QS002", "MD001")] == \
        ["F", "SF", "QF|RR?", "R32|RR?", "Q", ""]
    assert SRC.atp_code("ATPTE51") == "TE51" and SRC.atp_code("K09F") == "K09F"


def test_zones():
    assert TZ.zone_for("USA", "indian wells masters") == "America/Los_Angeles"
    assert TZ.zone_for("USA", "newport beach ch") == "America/Los_Angeles"
    assert TZ.zone_for("USA", "newport") == "America/New_York"
    assert TZ.zone_for("AUS", "brisbane") == "Australia/Brisbane"
    assert TZ.zone_for("ESP", "tenerife ch") == "Atlantic/Canary"
    assert TZ.zone_for("ITA", "rome") == "Europe/Rome"
    assert TZ.zone_for("USA", "somewhere unknown") is None
    assert TZ.zone_for(None, "rome") is None


# ------------------------------------------------------------------------------------------------
# the written links

SOURCES = ("api_tennis", "live_tennis_api", "open_tennis_data", "match_charting", "infosys", "tml_days")


@pytest.mark.skipif(not all((LINKS / f"{s}.parquet").exists() for s in SOURCES), reason="links not built")
def test_written_links():
    m = pd.read_parquet(X.C.MATCHES, columns=["match_id"])
    for s in SOURCES:
        lk = pd.read_parquet(LINKS / f"{s}.parquet")
        assert list(lk.columns) == X.OUT_COLS
        assert lk["match_id"].is_unique and lk["source_key"].is_unique, s
        assert lk["match_id"].isin(m["match_id"]).all(), s
        assert lk["date_basis"].isin(["local", "utc_date"]).all(), s
        assert (lk["source"] == s).all()
        utc = lk["start_utc"].notna() & lk["date_basis"].eq("utc_date")
        if utc.any():   # a UTC day is the start's own day
            assert (lk.loc[utc, "start_utc"].dt.tz_convert("UTC").dt.date == lk.loc[utc, "date_local"]).all(), s
